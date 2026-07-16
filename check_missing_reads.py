import nuke
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui


class MissingReadsTable(QtWidgets.QDialog):
    def __init__(self, reads, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Check Missing Reads")
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

        # --- Buttons ---
        btn = QtWidgets.QHBoxLayout()
        self.copy_all = QtWidgets.QPushButton("Copy All Errors")
        self.copy_sel = QtWidgets.QPushButton("Copy Selected")
        self.select_btn = QtWidgets.QPushButton("Select in Node Graph")
        self.refresh_btn = QtWidgets.QPushButton("Refresh")

        btn.addWidget(self.copy_all)
        btn.addWidget(self.copy_sel)
        btn.addWidget(self.select_btn)
        btn.addStretch()
        btn.addWidget(self.refresh_btn)
        layout.addLayout(btn)

        # --- Connections ---
        self.copy_all.clicked.connect(self._copy_all)
        self.copy_sel.clicked.connect(self._copy_selected)
        self.select_btn.clicked.connect(self._select_in_graph)
        self.refresh_btn.clicked.connect(self._refresh)
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

    _panel = MissingReadsTable(reads)
    _panel.show()
