# -*- coding: utf-8 -*-
# Nuke Project Manager - toolbox panel
# Compatible with Nuke 13-16 (PySide2 / PySide6)

import os
import shutil

import nuke

try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore

STYLE_SHEET = (
    "QWidget { background: #1e1e1e; color: #d4d4d4; font-size: 12px; }"
    "QLineEdit { background: #2d2d2d; border: 1px solid #444; border-radius: 4px; padding: 6px; color: #d4d4d4; }"
    "QPushButton { background: #0e639c; border: 1px solid #0078d4; border-radius: 4px; padding: 8px 16px; color: #ffffff; font-weight: bold; }"
    "QPushButton:hover { background: #1177bb; }"
    "QLabel { color: #d4d4d4; }"
)


def _norm(path):
    """Normalize path and force forward slashes."""
    return os.path.normpath(path).replace(chr(92), "/")


class ProjectManagerDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(ProjectManagerDialog, self).__init__(parent)
        self.setWindowTitle("Project Manager")
        self.setStyleSheet(STYLE_SHEET)
        self.setMinimumWidth(420)

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Path field (default: current script directory)
        path_label = QtWidgets.QLabel()
        path_label.setText(u"路径")
        self.path_edit = QtWidgets.QLineEdit()
        try:
            default_dir = nuke.script_directory()
        except Exception:
            default_dir = os.getcwd()
        self.path_edit.setText(_norm(default_dir))
        layout.addWidget(path_label)
        layout.addWidget(self.path_edit)

        # Pick button: fill path and name from current .nk
        self.pick_btn = QtWidgets.QPushButton()
        self.pick_btn.setText(u"拾取")
        self.pick_btn.clicked.connect(self._pick_current)
        layout.addWidget(self.pick_btn)

        # Project name field
        name_label = QtWidgets.QLabel()
        name_label.setText(u"工程名")
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText(u"输入工程名")
        layout.addWidget(name_label)
        layout.addWidget(self.name_edit)

        # Create button
        self.create_btn = QtWidgets.QPushButton()
        self.create_btn.setText(u"创建")
        self.create_btn.clicked.connect(self._on_create)
        layout.addWidget(self.create_btn)

    def _pick_current(self):
        """Fill path and project name from current .nk file."""
        current = _norm(nuke.root().name())
        if not current or current.lower() == "root" or not os.path.isfile(current):
            nuke.message(u"请先保存当前工程")
            return
        self.path_edit.setText(_norm(os.path.dirname(current)))
        name = os.path.splitext(os.path.basename(current))[0]
        self.name_edit.setText(name)

    def _find_conflict(self, base_dir, project_name):
        """Return True if a subdirectory starting with project_name (case-insensitive) exists."""
        if not os.path.isdir(base_dir):
            return False
        prefix = project_name.lower()
        for entry in os.listdir(base_dir):
            full = os.path.join(base_dir, entry)
            if os.path.isdir(full) and entry.lower().startswith(prefix):
                return True
        return False

    def _resolve_name(self, base_dir, project_name):
        """Append _01, _02, ... until no conflicting directory exists."""
        candidate = project_name
        index = 1
        while self._find_conflict(base_dir, candidate):
            candidate = "{0}_{1:02d}".format(project_name, index)
            index += 1
        return candidate

    def _on_create(self):
        base_dir = _norm(self.path_edit.text().strip())
        project_name = self.name_edit.text().strip()

        # a. validate fields
        if not base_dir:
            nuke.message(u"请输入路径")
            return
        if not project_name:
            nuke.message(u"请输入工程名")
            return

        final_name = project_name

        # c/d. conflict check
        if self._find_conflict(base_dir, project_name):
            proceed = nuke.ask(u"目录已存在类似名称的项目，是否继续创建？")
            if not proceed:
                return
            # e. auto suffix
            final_name = self._resolve_name(base_dir, project_name)

        # f. create directory structure
        # If the path already ends with /nuke, create .nk directly there.
        # Otherwise, create {name}/nuke/{name}.nk under the path.
        if os.path.basename(base_dir.rstrip("/").rstrip(chr(92))) == "nuke":
            nuke_dir = base_dir
            target_nk = _norm(os.path.join(nuke_dir, final_name + ".nk"))
        else:
            project_dir = _norm(os.path.join(base_dir, final_name))
            nuke_dir = _norm(os.path.join(project_dir, "nuke"))
            target_nk = _norm(os.path.join(nuke_dir, final_name + ".nk"))
        try:
            os.makedirs(nuke_dir)
        except OSError as err:
            nuke.message(u"创建目录失败: {0}".format(err))
            return

        # g. copy current .nk as template
        current_nk = _norm(nuke.root().name())
        if not current_nk or current_nk.lower() == "root" or not os.path.isfile(current_nk):
            nuke.message(u"请先保存当前工程")
            return

        try:
            shutil.copy2(current_nk, target_nk)
        except (IOError, OSError) as err:
            nuke.message(u"复制模板失败: {0}".format(err))
            return

        # h. open the new .nk
        nuke.scriptOpen(target_nk)

        # i. success message
        nuke.message(u"项目创建成功:\n{0}".format(target_nk))
        self.accept()


_panel = None


def _nuke_main_window():
    """Find Nuke's main DockMainWindow to use as parent."""
    try:
        from PySide6 import QtWidgets
    except ImportError:
        from PySide2 import QtWidgets
    app = QtWidgets.QApplication.instance()
    if app:
        for w in app.topLevelWidgets():
            if "DockMainWindow" in w.metaObject().className():
                return w
    return None


def show_panel():
    global _panel
    if _panel:
        try:
            _panel.close()
        except:
            pass
    _panel = ProjectManagerDialog(_nuke_main_window())
    _panel.show()


if __name__ == "__main__":
    show_panel()
