# === Nuke Bridge Server v7 ===
import socket, threading, sys, traceback, os
from io import StringIO
import nuke

# toolbox/ 目录加入 Nuke 的 import 路径（便携，不硬编码用户名）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'toolbox'))

BASE_PORT = 54321

def _find_port():
    for p in range(BASE_PORT, BASE_PORT + 10):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", p))
            s.close()
            return p
        except OSError:
            continue
    return None

PORT = _find_port()
if PORT is None:
    print("[NukeBridge] No free port")
else:
    import os, nukescripts

    SCRIPTS_DIR = os.path.join(os.path.dirname(__file__) or ".", "toolbox")
    os.makedirs(SCRIPTS_DIR, exist_ok=True)

    class ScriptManagerPanel(nukescripts.PythonPanel):
        def __init__(self):
            nukescripts.PythonPanel.__init__(self, "Bridge", "com.hermes.bridge")
            self._scripts = {}
            self.script_list = nuke.Enumeration_Knob("script", "script", [])
            self.addKnob(self.script_list)
            self.desc = nuke.Text_Knob("desc", "", "")
            self.addKnob(self.desc)
            self.addKnob(nuke.Text_Knob("sep1", "", ""))
            self.run_btn = nuke.PyScript_Knob("run", "Run")
            self.addKnob(self.run_btn)
            self.edit_btn = nuke.PyScript_Knob("edit", "Edit")
            self.addKnob(self.edit_btn)
            self.reveal_btn = nuke.PyScript_Knob("reveal", "Reveal")
            self.addKnob(self.reveal_btn)
            self.refresh_btn = nuke.PyScript_Knob("refresh", "Refresh")
            self.addKnob(self.refresh_btn)
            self._refresh()

        def _refresh(self):
            self._scripts.clear()
            items = []
            if os.path.isdir(SCRIPTS_DIR):
                for f in sorted(os.listdir(SCRIPTS_DIR)):
                    if f.endswith(".py") and not f.startswith("_"):
                        name = f[:-3].replace("_", " ")
                        self._scripts[name] = os.path.join(SCRIPTS_DIR, f)
                        items.append(name)
            if not items:
                items = ["(empty)"]
            self.script_list.setValues(items)
            self.script_list.setValue(items[0])
            if self._scripts:
                self._show_desc()

        def _show_desc(self):
            path = self._scripts.get(self.script_list.value())
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.desc.setValue(f.readline().strip())

        def knobChanged(self, knob):
            if knob is self.script_list:
                self._show_desc()
            elif knob is self.run_btn:
                self._run()
            elif knob is self.edit_btn:
                path = self._scripts.get(self.script_list.value())
                if path:
                    os.startfile(path)
            elif knob is self.reveal_btn:
                path = self._scripts.get(self.script_list.value())
                if path:
                    import subprocess
                    subprocess.Popen(["explorer", "/select,", path])
            elif knob is self.refresh_btn:
                self._refresh()

        def _run(self):
            path = self._scripts.get(self.script_list.value())
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            try:
                exec(code, {"__name__": "__main__", "nuke": nuke})
            except Exception as e:
                nuke.message("Error:\n" + str(e))

    _panel = None

    def show_script_manager():
        global _panel
        _panel = ScriptManagerPanel()
        _panel.show()


    nuke.menu("Nuke").addCommand("Toolbox/Bridge", "show_script_manager()")

    # Bridge
    _BRIDGE_GLOBALS = {
        "__name__": "__main__",
        "nuke": nuke,
        "show_script_manager": show_script_manager,
    }

    def _handle(conn):
        try:
            conn.settimeout(3)
            data = b""
            while True:
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                except socket.timeout:
                    break
            if not data:
                return
            code = data.decode("utf-8")
            out = StringIO()
            err = StringIO()
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = out, err
            try:
                nuke.executeInMainThreadWithResult(lambda: exec(code, _BRIDGE_GLOBALS))
            except Exception:
                traceback.print_exc(file=err)
            sys.stdout, sys.stderr = old_out, old_err
            result = out.getvalue() + err.getvalue()
            try:
                conn.sendall(result.encode("utf-8")[:65536])
            except:
                pass
        except Exception:
            pass
        finally:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                conn.close()
            except:
                pass

    def _start():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(1)
        s.bind(("127.0.0.1", PORT))
        s.listen(2)
        print("[NukeBridge v7] listening on {}:{}".format("127.0.0.1", PORT))
        while True:
            try:
                c, _ = s.accept()
                t = threading.Thread(target=_handle, args=(c,))
                t.daemon = True
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    t = threading.Thread(target=_start)
    t.daemon = True
    t.start()

nuke.menu('Nodes').addMenu('custom').addCommand('Z Fog v1.1', "nuke.nodePaste(r'C:/Users/shaobaojia/.nuke/Z_fog_v1.1.gizmo')")



nuke.menu("Nuke").addCommand("Toolbox/Read 管理器", "import check_missing_reads; check_missing_reads.check_missing_reads()")
nuke.menu("Nuke").addCommand("Toolbox/AOV Generator Pro", "import aov_generator_pro; aov_generator_pro.launch_pro()", "F2")
nuke.menu("Nuke").addCommand("Toolbox/效率面板", "import toolbox_panel; toolbox_panel.show_toolbox()")
nuke.menu("Nuke").addCommand("Toolbox/工程管理", "import nuke_project_manager; nuke_project_manager.show_panel()")
