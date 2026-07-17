import nuke
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
import os, shutil

BS = chr(92)
FS = "/"

class ReadManagerTable(QtWidgets.QDialog):
    def __init__(self, reads, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Read Manager")
        self.setMinimumSize(860, 480)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Node", "Status", "File Path"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.reads = reads
        self._populate()
        layout.addWidget(self.table)
        ec = sum(1 for _, e, _ in reads if e)
        self.stats = QtWidgets.QLabel("Total: " + str(len(reads)) + " Read nodes  |  Errors: " + str(ec))
        layout.addWidget(self.stats)
        rw = QtWidgets.QWidget()
        rl = QtWidgets.QHBoxLayout(rw)
        rl.setContentsMargins(0, 4, 0, 0)
        rl.setSpacing(4)
        rl.addWidget(QtWidgets.QLabel("Source:"))
        self.src_path = QtWidgets.QLineEdit()
        self.src_path.setPlaceholderText("path prefix to replace")
        rl.addWidget(self.src_path)
        self.pick_btn = QtWidgets.QPushButton("Pick")
        self.pick_btn.setFixedWidth(48)
        self.pick_btn.clicked.connect(self._pick_path)
        rl.addWidget(self.pick_btn)
        rl.addWidget(QtWidgets.QLabel("Target:"))
        self.dst_path = QtWidgets.QLineEdit()
        self.dst_path.setPlaceholderText("replacement path")
        rl.addWidget(self.dst_path)
        self.replace_btn = QtWidgets.QPushButton("Replace+Copy")
        self.replace_btn.setFixedWidth(90)
        self.replace_btn.clicked.connect(self._replace_path)
        rl.addWidget(self.replace_btn)
        self.rel_btn = QtWidgets.QPushButton("Rel")
        self.rel_btn.setFixedWidth(36)
        self.rel_btn.clicked.connect(self._to_relative)
        rl.addWidget(self.rel_btn)
        layout.addWidget(rw)
        btn = QtWidgets.QHBoxLayout()
        self.copy_all = QtWidgets.QPushButton("Copy All Errors")
        self.copy_sel = QtWidgets.QPushButton("Copy Selected")
        self.select_btn = QtWidgets.QPushButton("Select in Node Graph")
        self.refresh_btn = QtWidgets.QPushButton("Refresh Data")
        self.reload_btn = QtWidgets.QPushButton("Reload UI")
        btn.addWidget(self.copy_all)
        btn.addWidget(self.copy_sel)
        btn.addWidget(self.select_btn)
        btn.addStretch()
        btn.addWidget(self.refresh_btn)
        btn.addWidget(self.reload_btn)
        layout.addLayout(btn)
        self.copy_all.clicked.connect(self._copy_all)
        self.copy_sel.clicked.connect(self._copy_selected)
        self.select_btn.clicked.connect(self._select_in_graph)
        self.refresh_btn.clicked.connect(self._refresh)
        self.reload_btn.clicked.connect(self._reload)
        self.table.doubleClicked.connect(self._select_in_graph)

    def _populate(self):
        self.table.setRowCount(len(self.reads))
        for i, (name, has_error, path) in enumerate(self.reads):
            ni = QtWidgets.QTableWidgetItem(name)
            si = QtWidgets.QTableWidgetItem("ERROR" if has_error else "OK")
            pi = QtWidgets.QTableWidgetItem(path)
            if has_error:
                si.setForeground(QtGui.QColor(255, 80, 80))
                ni.setForeground(QtGui.QColor(255, 160, 140))
            else:
                si.setForeground(QtGui.QColor(80, 200, 80))
            self.table.setItem(i, 0, ni)
            self.table.setItem(i, 1, si)
            self.table.setItem(i, 2, pi)
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)

    def _selected_rows(self):
        return sorted(set(idx.row() for idx in self.table.selectedIndexes()))

    def _copy_all(self):
        lines = []
        for i in range(self.table.rowCount()):
            if self.table.item(i, 1).text() == "ERROR":
                lines.append(self.table.item(i, 0).text() + ": " + self.table.item(i, 2).text())
        if lines:
            QtWidgets.QApplication.clipboard().setText(chr(10).join(lines))

    def _copy_selected(self):
        lines = []
        for row in self._selected_rows():
            lines.append(self.table.item(row, 0).text() + ": " + self.table.item(row, 2).text())
        if lines:
            QtWidgets.QApplication.clipboard().setText(chr(10).join(lines))

    def _select_in_graph(self):
        rows = self._selected_rows()
        if not rows: return
        for n in nuke.allNodes():
            n.setSelected(False)
        for row in rows:
            node = nuke.toNode(self.table.item(row, 0).text())
            if node: node.setSelected(True)

    def _refresh(self):
        self.reads = []
        for node in nuke.allNodes("Read"):
            try: node["reload"].execute()
            except: pass
            self.reads.append((node.name(), node.hasError(), node.knob("file").value()))
        self._populate()
        ec = sum(1 for _, e, _ in self.reads if e)
        self.stats.setText("Total: " + str(len(self.reads)) + " Read nodes  |  Errors: " + str(ec))
        nuke.tprint("Refreshed: " + str(len(self.reads)) + " Read nodes, " + str(ec) + " errors")

    def _reload(self):
        import importlib
        importlib.reload(__import__("check_missing_reads"))
        self.close()
        check_missing_reads()

    def _pick_path(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Read Manager", "Please select rows first")
            return
        dirs = []
        for row in rows:
            p = self.table.item(row, 2).text()
            if p:
                d = os.path.dirname(p.replace(BS, FS))
                dirs.append(d)
        if len(dirs) == 1:
            self.src_path.setText(dirs[0] + FS)
        else:
            prefix = dirs[0]
            for d in dirs[1:]:
                while prefix and not d.startswith(prefix):
                    idx = prefix.rfind(FS)
                    if idx < 0: prefix = ""; break
                    prefix = prefix[:idx]
            self.src_path.setText(prefix + FS)

    def _replace_path(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Read Manager", "Please select rows first")
            return
        sp = self.src_path.text().strip().replace(BS, FS).rstrip(FS) + FS
        dp = self.dst_path.text().strip().replace(BS, FS).rstrip(FS) + FS
        if not sp:
            QtWidgets.QMessageBox.warning(self, "Read Manager", "Source path is empty")
            return
        for row in rows:
            if self.table.item(row, 1).text() == "ERROR":
                QtWidgets.QMessageBox.warning(self, "Read Manager", "Cannot process missing files. Deselect error rows.")
                return
        seen = {}
        entries = []
        for row in rows:
            op = self.table.item(row, 2).text().replace(BS, FS)
            if not op.startswith(sp): continue
            np = dp + op[len(sp):]
            if np in seen:
                QtWidgets.QMessageBox.warning(self, "Read Manager", "Destination conflict: " + np)
                return
            seen[np] = op
            entries.append((row, op, np))
        progress = QtWidgets.QProgressDialog("Copying files...", "Cancel", 0, len(entries), self)
        progress.setWindowTitle("Read Manager")
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setMinimumDuration(500)
        count = 0
        errors = []
        for idx, (row, op, np) in enumerate(entries):
            if progress.wasCanceled():
                errors.append("Cancelled by user")
                break
            progress.setValue(idx)
            try:
                src_dir = os.path.dirname(op)
                dst_dir = os.path.dirname(np)
                if dst_dir and not os.path.isdir(dst_dir):
                    os.makedirs(dst_dir)
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                name = self.table.item(row, 0).text()
                node = nuke.toNode(name)
                if node:
                    clean = np
                    if len(clean) > 1 and clean[1] == ":" and clean[2] != FS:
                        clean = clean[:2] + FS + clean[2:]
                    clean = os.path.normpath(clean).replace(BS, FS)
                    node["file"].setValue(clean)
                    self.table.item(row, 2).setText(clean)
                count += 1
            except Exception as e:
                errors.append(os.path.basename(op) + ": " + str(e))
        progress.setValue(len(entries))
        msg = "Replaced " + str(count) + " file(s)"
        if errors: msg += " | Errors: " + "; ".join(errors)
        QtWidgets.QMessageBox.information(self, "Read Manager", msg)
        self._refresh()

    def _to_relative(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Read Manager", "Please select rows first")
            return
        script_dir = nuke.script_directory()
        if not script_dir:
            QtWidgets.QMessageBox.warning(self, "Read Manager", "Save the Nuke script first")
            return
        count = 0
        skipped = 0
        for row in rows:
            name = self.table.item(row, 0).text()
            node = nuke.toNode(name)
            if not node: continue
            p = node.knob("file").value()
            if p and os.path.isabs(p):
                try:
                    rel = os.path.relpath(p, script_dir).replace(BS, FS)
                    node["file"].setValue(rel)
                    self.table.item(row, 2).setText(rel)
                    count += 1
                except ValueError:
                    skipped += 1
                except: pass
        msg = "Converted " + str(count) + " to relative"
        if skipped: msg += " | " + str(skipped) + " skipped (different drive)"
        QtWidgets.QMessageBox.information(self, "Read Manager", msg)
        self._refresh()

_panel = None

def _nuke_main_window():
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance()
    if app:
        for w in app.topLevelWidgets():
            if 'DockMainWindow' in w.metaObject().className():
                return w
    return None

def check_missing_reads():
    global _panel
    if _panel:
        try: _panel.close()
        except: pass
    reads = []
    for node in nuke.allNodes("Read"):
        reads.append((node.name(), node.hasError(), node.knob("file").value()))
    _panel = ReadManagerTable(reads, _nuke_main_window())
    _panel.show()
