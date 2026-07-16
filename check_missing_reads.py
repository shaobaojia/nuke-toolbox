import nuke
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
import shutil


class ReadManagerTable(QtWidgets.QDialog):
    def __init__(self, reads, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Read Read Manager")
        self.setMinimumSize(860, 400)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # --- Table ---
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

        # --- Stats label ---
        error_count = sum(1 for _, e, _ in reads if e)
        self.stats = QtWidgets.QLabel(
            f"Total: {len(reads)} Read nodes  |  Errors: {error_count}"
        )
                layout.addWidget(self.stats)

        # --- Path Replace ---
        replace_w = QtWidgets.QWidget()
        replace_layout = QtWidgets.QHBoxLayout(replace_w)
        replace_layout.setContentsMargins(0, 0, 0, 0)
        replace_layout.setSpacing(4)

        replace_layout.addWidget(QtWidgets.QLabel("Source:"))
        self.src_path = QtWidgets.QLineEdit()
        self.src_path.setPlaceholderText("path prefix to replace")
        replace_layout.addWidget(self.src_path)

        self.pick_btn = QtWidgets.QPushButton("Pick")
        self.pick_btn.setFixedWidth(48)
        self.pick_btn.clicked.connect(self._pick_path)
        replace_layout.addWidget(self.pick_btn)

        replace_layout.addWidget(QtWidgets.QLabel("Target:"))
        self.dst_path = QtWidgets.QLineEdit()
        self.dst_path.setPlaceholderText("replacement path")
        replace_layout.addWidget(self.dst_path)

        self.replace_btn = QtWidgets.QPushButton("Replace")
        self.replace_btn.setFixedWidth(64)
        self.replace_btn.clicked.connect(self._replace_path)
        replace_layout.addWidget(self.replace_btn)

        layout.addWidget(replace_w)

        # --- Buttons ---
        btn = QtWidgets.QHBoxLayout()
        self.copy_all = QtWidgets.QPushButton("Copy All Errors")
        self.copy_sel = QtWidgets.QPushButton("Copy Selected")
        self.select_btn = QtWidgets.QPushButton("Select in Node Graph")
        self.collect_btn = QtWidgets.QPushButton("Collect to...")
        self.refresh_btn = QtWidgets.QPushButton("Refresh Data")
        self.reload_btn = QtWidgets.QPushButton("Reload UI")

        btn.addWidget(self.copy_all)
        btn.addWidget(self.copy_sel)
        btn.addWidget(self.select_btn)
        btn.addWidget(self.collect_btn)
        btn.addStretch()
        btn.addWidget(self.refresh_btn)
        btn.addWidget(self.reload_btn)
        layout.addLayout(btn)

        # --- Connections ---
        self.copy_all.clicked.connect(self._copy_all)
        self.copy_sel.clicked.connect(self._copy_selected)
        self.select_btn.clicked.connect(self._select_in_graph)
        self.refresh_btn.clicked.connect(self._refresh)
        self.collect_btn.clicked.connect(self._collect)
        self.reload_btn.clicked.connect(self._reload)
        self.table.doubleClicked.connect(self._select_in_graph)

    def _populate(self):
        self.table.setRowCount(len(self.reads))
        for i, (name, has_error, path) in enumerate(self.reads):
            # Node name
            name_item = QtWidgets.QTableWidgetItem(name)
            # Status
            status_item = QtWidgets.QTableWidgetItem("ERROR" if has_error else "OK")
            # Path
            path_item = QtWidgets.QTableWidgetItem(path)

            if has_error:
                status_item.setForeground(QtGui.QColor(255, 80, 80))
                name_item.setForeground(QtGui.QColor(255, 160, 140))
            else:
                status_item.setForeground(QtGui.QColor(80, 200, 80))

            self.table.setItem(i, 0, name_item)
            self.table.setItem(i, 1, status_item)
            self.table.setItem(i, 2, path_item)

        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)

    def _selected_rows(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        return rows

    def _copy_all(self):
        lines = []
        for i in range(self.table.rowCount()):
            if self.table.item(i, 1).text() == "ERROR":
                name = self.table.item(i, 0).text()
                path = self.table.item(i, 2).text()
                lines.append(f"{name}: {path}")
        if lines:
            QtWidgets.QApplication.clipboard().setText("\n".join(lines))
            nuke.display(f"Copied {len(lines)} paths to clipboard")

    def _copy_selected(self):
        lines = []
        for row in self._selected_rows():
            name = self.table.item(row, 0).text()
            path = self.table.item(row, 2).text()
            lines.append(f"{name}: {path}")
        if lines:
            QtWidgets.QApplication.clipboard().setText("\n".join(lines))
            nuke.display(f"Copied {len(lines)} paths to clipboard")


    def _collect(self):
        try:
            self.__collect()
        except Exception as e:
            import traceback
            QtWidgets.QMessageBox.critical(self, "Read Read Manager", traceback.format_exc())

    def __collect(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Read Manager", "Please select at least one row")
            return

        to_copy = []
        for row in rows:
            status = self.table.item(row, 1).text()
            if status == "ERROR":
                name = self.table.item(row, 0).text()
                QtWidgets.QMessageBox.warning(self, "Read Manager", "Cannot collect: " + repr(name) + " is missing. Deselect error rows first.")
                return
            to_copy.append(row)

        if not to_copy:
            return

        dest_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose target directory")
        if not dest_dir:
            return
        if not os.path.isdir(dest_dir):
            try:
                os.makedirs(dest_dir)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Read Manager", "Cannot create directory: " + str(e))
                return

        seen = {}
        collisions = []
        entries = []
        for row in to_copy:
            src = self.table.item(row, 2).text()
            fname = os.path.basename(src)
            if fname in seen:
                collisions.append(fname + " (" + seen[fname] + " vs " + src + ")")
            else:
                seen[fname] = src
                entries.append((row, src, os.path.join(dest_dir, fname)))

        if collisions:
            QtWidgets.QMessageBox.warning(self, "Read Manager", "Filename conflict. Aborted. " + "; ".join(collisions[:3]))
            return

        copied = 0
        errors = []
        for row, src, dst in entries:
            try:
                shutil.copy2(src, dst)
                name = self.table.item(row, 0).text()
                node = nuke.toNode(name)
                if node:
                    node["file"].setValue(dst.replace("\\", "/"))
                copied += 1
            except Exception as e:
                errors.append(os.path.basename(src) + ": " + str(e))

        msg = "Collected " + str(copied) + " file(s) to " + dest_dir
        if errors:
            msg += " | Errors: " + "; ".join(errors)
        QtWidgets.QMessageBox.information(self, "Read Manager", msg)
        self._refresh()
    def _pick_path(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Read Manager", "Please select rows first")
            return

        dirs = []
        for row in rows:
            p = self.table.item(row, 2).text()
            if p:
                d = os.path.dirname(p.replace("\\", "/"))
                dirs.append(d)

        if len(dirs) == 1:
            self.src_path.setText(dirs[0])
        else:
            # Find common prefix across all paths
            prefix = dirs[0]
            for d in dirs[1:]:
                while prefix and not d.startswith(prefix):
                    prefix = prefix[:prefix.rfind("/")] if "/" in prefix else ""
            self.src_path.setText(prefix)

    def _replace_path(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Read Manager", "Please select rows first")
            return

        src_prefix = self.src_path.text().strip().replace("\\", "/")
        dst_prefix = self.dst_path.text().strip().replace("\\", "/")

        if not src_prefix:
            QtWidgets.QMessageBox.warning(self, "Read Manager", "Source path is empty")
            return

        count = 0
        for row in rows:
            old_path = self.table.item(row, 2).text().replace("\\", "/")
            if old_path.startswith(src_prefix):
                new_path = dst_prefix + old_path[len(src_prefix):]
                name = self.table.item(row, 0).text()
                node = nuke.toNode(name)
                if node:
                    node["file"].setValue(new_path)
                    self.table.item(row, 2).setText(new_path)
                    count += 1

        QtWidgets.QMessageBox.information(self, "Read Manager", "Updated " + str(count) + " node(s)")

    def _reload(self):
        import importlib
        importlib.reload(__import__("check_missing_reads"))
        self.close()
        check_missing_reads()
    

    def _select_in_graph(self):
        rows = self._selected_rows()
        if not rows:
            return
        for n in nuke.allNodes():
            n.setSelected(False)
        for row in rows:
            name = self.table.item(row, 0).text()
            node = nuke.toNode(name)
            if node:
                node.setSelected(True)

    def _refresh(self):
        self.reads = []
        for node in nuke.allNodes("Read"):
            name = node.name()
            has_error = node.hasError()
            path = node.knob("file").value()
            self.reads.append((name, has_error, path))
        self._populate()
        error_count = sum(1 for _, e, _ in self.reads if e)
        self.stats.setText(
            f"Total: {len(self.reads)} Read nodes  |  Errors: {error_count}"
        )
        nuke.display(f"Refreshed: {error_count} errors / {len(self.reads)} total")


_panel = None


def check_missing_reads():
    global _panel
    reads = []
    for node in nuke.allNodes("Read"):
        name = node.name()
        has_error = node.hasError()
        path = node.knob("file").value()
        reads.append((name, has_error, path))

    _panel = ReadManagerTable(reads)
    _panel.show()
