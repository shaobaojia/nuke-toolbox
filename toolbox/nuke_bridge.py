"""Nuke Bridge — 独立 TCP 桥 + 监看面板（手动端口、回包验证、可重启）"""
import socket, threading, sys, traceback, time, os
from io import StringIO
import nuke
try: from PySide6 import QtWidgets, QtCore, QtGui
except ImportError: from PySide2 import QtWidgets, QtCore, QtGui

BASE_PORT = 54322
MAX_LOG = 500


class BridgeServer:
    """TCP 桥服务，线程安全日志、可重启。"""

    def __init__(self, port=None):
        self.port = port or self._find_port()
        self.running = False
        self.active = 0
        self.started_at = None
        self._listen_sock = None
        self.log = BridgeLog()
        self.verified = False  # 收到过至少一次成功回包才为 True

    def _find_port(self):
        for p in range(BASE_PORT, BASE_PORT + 10):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p)); s.close(); return p
            except OSError: continue
        return None

    def start(self):
        if self.running:
            return
        self.port = self.port or self._find_port()
        if self.port is None:
            self.log.add("error", "No free port in range {}-{}".format(BASE_PORT, BASE_PORT + 9))
            return False
        self.running = True
        self.started_at = time.time()
        self.log.add("info", "Bridge started on port {}".format(self.port))
        t = threading.Thread(target=self._listen, daemon=True)
        t.start()
        return True

    def stop(self):
        self.running = False
        self.verified = False
        if self._listen_sock:
            try: self._listen_sock.close()
            except: pass
            self._listen_sock = None
        self.log.add("info", "Bridge stopped")

    def _listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(0.5)
        try:
            s.bind(("127.0.0.1", self.port))
        except OSError as e:
            self.log.add("error", "Bind failed: {}".format(e))
            self.running = False
            return
        s.listen(2)
        self._listen_sock = s
        while self.running:
            try:
                c, addr = s.accept()
                self.active += 1
                self.log.add("conn", "Connected {}:{}".format(addr[0], addr[1]))
                t = threading.Thread(target=self._handle, args=(c, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break
        try: s.close()
        except: pass

    def _handle(self, conn, addr):
        try:
            conn.settimeout(10)
            data = b""
            while True:
                try:
                    chunk = conn.recv(4096)
                    if not chunk: break
                    data += chunk
                    if len(data) > 2 * 1024 * 1024:  # 2MB hard cap
                        self.log.add("error", "Request too large from {}:{}".format(addr[0], addr[1]))
                        return
                except socket.timeout:
                    break
            if not data:
                return
            code = data.decode("utf-8", errors="replace")
            summary = code[:80].replace("\n", " ") + ("..." if len(code) > 80 else "")
            self.log.add("exec", "→ {}".format(summary))

            out, err = StringIO(), StringIO()
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = out, err
            try:
                nuke.executeInMainThreadWithResult(
                    lambda: exec(code, {"__name__": "__main__", "nuke": nuke})
                )
            except Exception:
                traceback.print_exc(file=err)
            sys.stdout, sys.stderr = old_out, old_err
            result = out.getvalue() + err.getvalue()

            if err.getvalue():
                self.log.add("error", "← Error", err.getvalue()[:500])
            elif result:
                self.verified = True  # 成功回包 → 标记 verified
                display = result[:100].replace("\n", " ")
                self.log.add("exec", "← {}".format(display) + ("..." if len(result) > 100 else ""))

            resp = result.encode("utf-8")
            limit = 1024 * 1024  # 1MB
            if len(resp) > limit:
                self.log.add("error", "Response truncated {} → {} bytes".format(len(resp), limit))
                resp = resp[:limit]
            try:
                conn.sendall(resp)
                conn.shutdown(socket.SHUT_WR)
            except Exception as e:
                self.log.add("error", "Send failed: {}".format(e))
        except Exception as e:
            self.log.add("error", "Handle error: {}".format(e))
        finally:
            self.active -= 1
            self.log.add("conn", "Disconnected {}:{}".format(addr[0], addr[1]))
            try: conn.close()
            except: pass


class BridgeLog:
    """线程安全的日志，可绑定监听器供 UI 实时刷新。"""

    def __init__(self):
        self.entries = []
        self._lock = threading.Lock()
        self.listeners = []

    def add(self, kind, msg, detail=""):
        entry = {"time": time.strftime("%H:%M:%S"), "kind": kind, "msg": msg, "detail": detail}
        with self._lock:
            self.entries.append(entry)
            if len(self.entries) > MAX_LOG * 2:  # keep double buffer
                self.entries = self.entries[-MAX_LOG:]
        for cb in self.listeners:
            try: cb(entry)
            except: pass

    def on_add(self, cb):
        self.listeners.append(cb)


# ── 监看面板 ─────────────────────────────────────────────

class BridgeMonitor(QtWidgets.QDialog):
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.setWindowTitle("Bridge Monitor")
        self.setMinimumSize(780, 520)
        self.resize(820, 580)
        self.setStyleSheet("""
            QWidget { background: #1e1e1e; color: #d4d4d4; font-size: 12px; }
            QTableWidget { background: #252525; gridline-color: #333; border: 1px solid #333; }
            QHeaderView::section { background: #2a2a2a; border: none; padding: 4px; }
            QPushButton { background: #2d2d2d; border: 1px solid #444; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background: #3a3a3a; border-color: #0078d4; }
            QLineEdit { background: #252525; border: 1px solid #444; border-radius: 4px; padding: 6px 8px; }
            QLineEdit:focus { border-color: #0078d4; }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # ── 状态行 ──
        sr = QtWidgets.QHBoxLayout()
        self.dot = QtWidgets.QLabel("●")
        sr.addWidget(self.dot)
        self.status = QtWidgets.QLabel()
        sr.addWidget(self.status)
        sr.addStretch()
        self.active_label = QtWidgets.QLabel()
        sr.addWidget(self.active_label)
        self.restart_btn = QtWidgets.QPushButton("Restart")
        self.restart_btn.clicked.connect(self._restart)
        sr.addWidget(self.restart_btn)
        layout.addLayout(sr)

        # ── 端口控制行 ──
        pr = QtWidgets.QHBoxLayout()
        pr.addWidget(QtWidgets.QLabel("Port:"))
        self.port_edit = QtWidgets.QLineEdit(str(self.bridge.port))
        self.port_edit.setFixedWidth(60)
        pr.addWidget(self.port_edit)
        self.test_btn = QtWidgets.QPushButton("Test")
        self.test_btn.setMinimumWidth(48)
        self.test_btn.clicked.connect(self._test_port)
        pr.addWidget(self.test_btn)
        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.connect_btn.setMinimumWidth(64)
        self.connect_btn.clicked.connect(self._connect_port)
        pr.addWidget(self.connect_btn)
        pr.addStretch()
        layout.addLayout(pr)

        # ── 日志表格 ──
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Time", "Type", "Message"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)

        # ── 底部：输入 + 按钮 ──
        br = QtWidgets.QHBoxLayout()
        self.cmd = QtWidgets.QLineEdit()
        self.cmd.setPlaceholderText("Python cmd — Enter to execute in Nuke")
        self.cmd.returnPressed.connect(self._send)
        br.addWidget(self.cmd)
        self.send_btn = QtWidgets.QPushButton("Send")
        self.send_btn.clicked.connect(self._send)
        br.addWidget(self.send_btn)
        self.copy_sel_btn = QtWidgets.QPushButton("Copy Selected")
        self.copy_sel_btn.clicked.connect(self._copy_selected)
        br.addWidget(self.copy_sel_btn)
        self.copy_btn = QtWidgets.QPushButton("Copy Last Error")
        self.copy_btn.clicked.connect(self._copy_error)
        br.addWidget(self.copy_btn)
        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear)
        br.addWidget(self.clear_btn)
        layout.addLayout(br)

        self._t = QtCore.QTimer(); self._t.timeout.connect(self._tick); self._t.start(500)
        self._log_idx = 0  # 已显示到的日志索引（主线程安全）
        self._tick()
        self._replay_log()

    # ── 状态轮询 ──
    def _tick(self):
        # 灯逻辑：running AND verified 才绿，否则红
        ok = self.bridge.running and self.bridge.verified
        self.dot.setText("●" if ok else "○")
        self.dot.setStyleSheet("color: {}; font-size: 14px; font-weight: bold;".format("#00FF00" if ok else "#FF4444"))
        if self.bridge.running and self.bridge.started_at:
            s = int(time.time() - self.bridge.started_at); m, sec = divmod(s, 60)
            txt = "Port {}  |  Up {}m{:02d}s".format(self.bridge.port, m, sec)
            if not self.bridge.verified:
                txt += "  |  unverified"
            self.status.setText(txt)
        else:
            self.status.setText("Port {}  |  Stopped".format(self.bridge.port))
        self.active_label.setText("Active: {}".format(self.bridge.active))
        # 轮询新日志（主线程安全，不从桥线程回调）
        with self.bridge.log._lock:
            new_entries = self.bridge.log.entries[self._log_idx:]
            self._log_idx = len(self.bridge.log.entries)
        for e in new_entries:
            self._append_row(e)

    def _replay_log(self):
        with self.bridge.log._lock:
            for entry in self.bridge.log.entries:
                self._append_row(entry)
            self._log_idx = len(self.bridge.log.entries)

    def _on_log(self, entry):
        pass  # 不再使用回调，改为 _tick 轮询

    def _append_row(self, entry):
        row = self.table.rowCount()
        self.table.insertRow(row)
        ti = QtWidgets.QTableWidgetItem(entry["time"])
        colors = {"conn": (100, 180, 255), "exec": (180, 200, 100),
                  "error": (255, 80, 80), "info": (150, 150, 150)}
        ki = QtWidgets.QTableWidgetItem(entry["kind"].upper())
        if entry["kind"] in colors:
            ki.setForeground(QtGui.QColor(*colors[entry["kind"]]))
        text = entry["msg"] + ("\n" + entry["detail"] if entry.get("detail") else "")
        mi = QtWidgets.QTableWidgetItem(text)
        mi.setToolTip(text)
        if entry["kind"] == "error":
            mi.setForeground(QtGui.QColor(255, 140, 140))
        self.table.setItem(row, 0, ti)
        self.table.setItem(row, 1, ki)
        self.table.setItem(row, 2, mi)
        self.table.scrollToBottom()
        while self.table.rowCount() > MAX_LOG:
            self.table.removeRow(0)

    # ── 端口控制 ──
    def _test_port(self):
        """异步测试端口：后台线程执行，不冻结 UI。"""
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            self.bridge.log.add("error", "Invalid port number")
            return
        self.bridge.log.add("info", "Testing port {}...".format(port))
        self.test_btn.setEnabled(False)
        self.test_btn.setText("...")
        t = threading.Thread(target=self._test_port_bg, args=(port,), daemon=True)
        t.start()

    def _test_port_bg(self, port):
        """后台执行 Test，结果通过日志输出。"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect(("127.0.0.1", port))
            s.sendall(b'print("PING")')
            s.shutdown(socket.SHUT_WR)
            time.sleep(10)
            resp = b""
            s.settimeout(8)
            try:
                while True:
                    c = s.recv(4096)
                    if not c: break
                    resp += c
            except: pass
            s.close()
            if b"PING" in resp:
                self.bridge.log.add("info", "Port {} OK — received PING back".format(port))
                self.bridge.verified = True
            else:
                self.bridge.log.add("error", "Port {} connected but no response (wrong Nuke?)".format(port))
        except Exception as e:
            self.bridge.log.add("error", "Port {} test failed: {}".format(port, e))
        finally:
            # 恢复按钮（用 QTimer.singleShot 确保主线程执行）
            def restore():
                self.test_btn.setEnabled(True)
                self.test_btn.setText("Test")
            QtCore.QTimer.singleShot(0, restore)

    def _connect_port(self):
        """切换到新端口并重启桥。"""
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            self.bridge.log.add("error", "Invalid port number")
            return
        if port == self.bridge.port:
            self.bridge.log.add("info", "Port unchanged ({})".format(port))
            return
        self.bridge.stop()
        self.bridge.port = port
        self.bridge.log.add("info", "Switching to port {}...".format(port))
        QtCore.QTimer.singleShot(600, lambda: (self.bridge.start(), self._tick()))

    # ── 按钮回调 ──
    def _clear(self):
        self.table.setRowCount(0)

    def _restart(self):
        self.bridge.stop()
        QtCore.QTimer.singleShot(600, lambda: (self.bridge.start(), self._tick()))

    def _send(self):
        code = self.cmd.text().strip()
        if not code:
            return
        self.cmd.clear()
        self.bridge.log.add("exec", "→ [panel] {}".format(code[:80]))
        out, err = StringIO(), StringIO()
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            nuke.executeInMainThreadWithResult(lambda: exec(code, {"__name__": "__main__", "nuke": nuke}))
        except Exception:
            traceback.print_exc(file=err)
        sys.stdout, sys.stderr = old_out, old_err
        result = out.getvalue() + err.getvalue()
        if err.getvalue():
            self.bridge.log.add("error", "← [panel] Error", err.getvalue()[:500])
        elif result.strip():
            self.bridge.verified = True
            self.bridge.log.add("exec", "← [panel] {}".format(result.strip()[:200]))

    def _copy_selected(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if not rows:
            return
        lines = []
        for row in rows:
            t = self.table.item(row, 0).text()
            k = self.table.item(row, 1).text()
            m = self.table.item(row, 2).text()
            lines.append(t + "  " + k + "  " + m)
        QtWidgets.QApplication.clipboard().setText(chr(10).join(lines))
        nuke.tprint("Copied " + str(len(lines)) + " log entries")

    def _copy_error(self):
        for entry in reversed(self.bridge.log.entries):
            if entry["kind"] == "error" and entry.get("detail"):
                QtWidgets.QApplication.clipboard().setText(entry["detail"])
                nuke.tprint("Copied last error to clipboard")
                return
        nuke.tprint("No errors in log")


# ── 单例入口 ──
_bridge = None
_monitor = None

def get_bridge():
    global _bridge
    if _bridge is None:
        _bridge = BridgeServer()
        _bridge.start()
    return _bridge

def _nuke_main_window():
    app = QtWidgets.QApplication.instance()
    if app:
        for w in app.topLevelWidgets():
            if "DockMainWindow" in w.metaObject().className():
                return w
    return None

def show_monitor():
    global _monitor
    if _monitor:
        try: _monitor.close()
        except: pass
    _monitor = BridgeMonitor(get_bridge(), _nuke_main_window())
    _monitor.show()
