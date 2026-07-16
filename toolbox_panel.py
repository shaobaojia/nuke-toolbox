import nuke, os, sys
try: from PySide6 import QtWidgets, QtCore, QtGui
except ImportError: from PySide2 import QtWidgets, QtCore, QtGui

BASE = os.path.join(os.path.expanduser('~'), '.nuke')
TOOLBOX = os.path.join(BASE, 'toolbox')

TOOLS = {
    "Path Tools": [
        ("sel_reads", "\u9009\u62e9\u6240\u6709Read\u8282\u70b9", "\u4e00\u952e\u9009\u4e2d\u5f53\u524d\u5de5\u7a0b\u4e2d\u6240\u6709Read\u8282\u70b9"),
        ("sel_writes", "\u9009\u62e9\u6240\u6709Write\u8282\u70b9", "\u4e00\u952e\u9009\u4e2d\u5f53\u524d\u5de5\u7a0b\u4e2d\u6240\u6709Write\u8282\u70b9"),
        ("convert_paths_to_relative", "\u8def\u5f84\u8f6c\u76f8\u5bf9", "\u5c06Read\u8282\u70b9\u8def\u5f84\u8f6c\u4e3a\u76f8\u5bf9\u8def\u5f84"),
    ],
    "Write Tools": [
        ("create_write_from_read",  "\u4eceRead\u521b\u5efaWrite", "\u9009\u4e2dRead\u8282\u70b9\uff0c\u81ea\u52a8\u751f\u6210Write\u8282\u70b9"),
        ("write_reading_color",     "Write\u8282\u70b9\u7740\u8272",   "\u6309\u6269\u5c55\u540d\u81ea\u52a8\u8bbe\u7f6e\u6807\u8bc6\u989c\u8272"),
        ("write_reading_label",     "Write\u8282\u70b9\u6807\u7b7e",   "\u6309\u8f93\u51fa\u8def\u5f84\u81ea\u52a8\u8bbe\u7f6e\u6807\u7b7e"),
    ],
    "Stamp Tools": [
        ("stamp_off",      "\u5173\u95ed\u7f29\u7565\u56fe", "\u9009\u4e2d\u8282\u70b9 \u2192 \u5173\u95edPostage Stamp"),
        ("stamp_on",       "\u5f00\u542f\u7f29\u7565\u56fe", "\u9009\u4e2d\u8282\u70b9 \u2192 \u5f00\u542fPostage Stamp"),
        ("stamp_off_all",  "\u5173\u95ed\u6240\u6709",   "\u5173\u95ed\u5f53\u524d\u5de5\u7a0b\u6240\u6709Postage Stamp"),
    ],
}

STAMP_ACTIONS = {
    "stamp_on":      lambda ns: [n["postage_stamp"].setValue(True)  for n in ns if "postage_stamp" in n.knobs()],
    "stamp_off":     lambda ns: [n["postage_stamp"].setValue(False) for n in ns if "postage_stamp" in n.knobs()],
    "stamp_off_all": lambda _:  [n["postage_stamp"].setValue(False) for n in nuke.allNodes() if "postage_stamp" in n.knobs()],
    "sel_reads": lambda _: [n.setSelected(True) for n in nuke.allNodes() if n.Class() == "Read"],
    "sel_writes": lambda _: [n.setSelected(True) for n in nuke.allNodes() if n.Class() == "Write"],
}

# Pairs of tools to put side-by-side: (group_name, [tool1, tool2])
SIDE_BY_SIDE = {("Stamp Tools", "stamp_off", "stamp_on"), ("Write Tools", "write_reading_color", "write_reading_label"), ("Path Tools", "sel_reads", "sel_writes")}

STYLE = """
QWidget { background: #1e1e1e; color: #d4d4d4; font-size: 12px; }
QLabel#title { font-size: 16px; font-weight: bold; color: #ffffff; padding: 8px 0; }
QGroupBox { border: 1px solid #3a3a3a; border-radius: 6px; margin-top: 12px; padding: 12px 8px 8px 8px; font-weight: bold; color: #9cdcfe; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QPushButton { background: #2d2d2d; border: 1px solid #444; border-radius: 4px; padding: 8px 12px; text-align: left; color: #d4d4d4; }
QPushButton:hover { background: #3a3a3a; border-color: #0078d4; }
QPushButton:pressed { background: #1a1a1a; }
QPushButton#refresh { background: #0e639c; border-color: #0078d4; }
QPushButton#refresh:hover { background: #1177bb; }
QPushButton#stamp_on { background: #1a3a1a; border-color: #2e7d32; }
QPushButton#stamp_on:hover { background: #2a4a2a; }
QPushButton#stamp_off { background: #3a2a1a; border-color: #e65100; }
QPushButton#stamp_off:hover { background: #4a3a2a; }
QPushButton#stamp_off_all { background: #3a1a1a; border-color: #c62828; }
QPushButton#stamp_off_all:hover { background: #4a2a2a; }
QLabel#desc { color: #808080; font-size: 11px; padding: 0 0 4px 4px; }
QScrollArea { border: none; background: transparent; }
"""

class ToolRow(QtWidgets.QWidget):
    clicked = QtCore.Signal(str)
    def __init__(self, mod_name, label, desc, style_class=""):
        super().__init__()
        self.mod_name = mod_name
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        self.btn = QtWidgets.QPushButton(label)
        self.btn.setCursor(QtCore.Qt.PointingHandCursor)
        if style_class:
            self.btn.setObjectName(style_class)
        layout.addWidget(self.btn)
        self.desc_label = QtWidgets.QLabel(desc)
        self.desc_label.setObjectName("desc")
        layout.addWidget(self.desc_label)
        self.btn.clicked.connect(lambda: self.clicked.emit(mod_name))

class ToolboxWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("\u6548\u7387\u9762\u677f")
        self.setMinimumSize(480, 680)
        self.resize(480, 680)
        self.setStyleSheet(STYLE)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self._paths = {}

        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(16, 12, 16, 16)
        main.setSpacing(4)

        title = QtWidgets.QLabel("\u6548\u7387\u9762\u677f")
        title.setObjectName("title")
        main.addWidget(title)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_w = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_w)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        for group_name, tools in TOOLS.items():
            gb = QtWidgets.QGroupBox(group_name)
            gb_layout = QtWidgets.QVBoxLayout(gb)
            gb_layout.setSpacing(2)

            i = 0
            while i < len(tools):
                mod_name, label, desc = tools[i]
                # Check if this tool + next should be side-by-side
                if i + 1 < len(tools):
                    next_mod, next_label, next_desc = tools[i + 1]
                    pair_key = (group_name, mod_name, next_mod)
                    if pair_key in SIDE_BY_SIDE:
                        row_w = QtWidgets.QWidget()
                        row_layout = QtWidgets.QHBoxLayout(row_w)
                        row_layout.setContentsMargins(0, 0, 0, 0)
                        row_layout.setSpacing(6)

                        sc_a = mod_name if mod_name.startswith("stamp_") else ""
                        sc_b = next_mod if next_mod.startswith("stamp_") else ""
                        row_a = ToolRow(mod_name, label, desc, sc_a)
                        row_b = ToolRow(next_mod, next_label, next_desc, sc_b)
                        row_a.clicked.connect(self._handle)
                        row_b.clicked.connect(self._handle)
                        row_layout.addWidget(row_a)
                        row_layout.addWidget(row_b)

                        for mn in [mod_name, next_mod]:
                            if mn not in STAMP_ACTIONS:
                                for loc in [os.path.join(TOOLBOX, mn+".py"), os.path.join(BASE, mn+".py")]:
                                    if os.path.isfile(loc): self._paths[mn]=loc; break
                        gb_layout.addWidget(row_w)
                        i += 1
                    else:
                        sc = mod_name if mod_name.startswith("stamp_") else ""
                        row = ToolRow(mod_name, label, desc, sc)
                        row.clicked.connect(self._handle)
                        gb_layout.addWidget(row)
                        if mod_name not in STAMP_ACTIONS:
                            for loc in [os.path.join(TOOLBOX, mod_name+".py"), os.path.join(BASE, mod_name+".py")]:
                                if os.path.isfile(loc): self._paths[mod_name]=loc; break
                else:
                    sc = mod_name if mod_name.startswith("stamp_") else ""
                    row = ToolRow(mod_name, label, desc, sc)
                    row.clicked.connect(self._handle)
                    gb_layout.addWidget(row)
                    if mod_name not in STAMP_ACTIONS:
                        for loc in [os.path.join(TOOLBOX, mod_name+".py"), os.path.join(BASE, mod_name+".py")]:
                            if os.path.isfile(loc): self._paths[mod_name]=loc; break
                i += 1

            scroll_layout.addWidget(gb)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_w)
        main.addWidget(scroll)

        refresh = QtWidgets.QPushButton("\u21bb  \u5237\u65b0\u9762\u677f")
        refresh.setObjectName("refresh")
        refresh.setCursor(QtCore.Qt.PointingHandCursor)
        refresh.clicked.connect(self._refresh)
        self.status = QtWidgets.QLabel("");self.status.setObjectName("desc");self.status.setAlignment(QtCore.Qt.AlignCenter);main.addWidget(self.status);main.addWidget(refresh)

        QtCore.QTimer.singleShot(0, self._fit_content)

    def _fit_content(self):
        sa = self.findChild(QtWidgets.QScrollArea)
        if sa and sa.widget():
            h = sa.widget().sizeHint().height()
            extra = self.height() - sa.height()
            self.resize(480, h + extra + 8)

    def _handle(self, mod_name):
        _orig = nuke.message
        nuke.message = lambda m: self.status.setText("  " + str(m))
        try:
            self._run(mod_name)
        finally:
            nuke.message = _orig

    def _run(self, mod_name):
        if mod_name in STAMP_ACTIONS:
            try:
                nodes = nuke.selectedNodes()
                if mod_name in ("stamp_on","stamp_off") and not nodes:
                    nuke.message("\u8bf7\u5148\u9009\u62e9\u8282\u70b9")
                    return
                STAMP_ACTIONS[mod_name](nodes)
            except Exception as e: nuke.message("Error: "+str(e))
            return
        path = self._paths.get(mod_name)
        if not path: return
        with open(path,"r",encoding="utf-8") as f: code = f.read()
        try: exec(code,{"__name__":"__main__","nuke":nuke,"__file__":path})
        except Exception as e: nuke.message("Error: "+str(e))

    def _refresh(self):
        import importlib
        importlib.reload(__import__("toolbox_panel"))
        self.close()
        show_toolbox()

_toolbox_window = None

def show_toolbox():
    global _toolbox_window
    if _toolbox_window:
        try: _toolbox_window.close()
        except: pass
    _toolbox_window = ToolboxWindow()
    _toolbox_window.show()
