import nuke
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
import os, shutil, re

BS = chr(92)
FS = "/"

SEQ_EXTS = {"exr", "dpx", "png", "jpg", "jpeg", "tif", "tiff", "tga", "cin", "psd"}
MOVIE_EXTS = {"mov", "mp4", "mxf", "r3d", "avi"}
MEDIA_EXTS = SEQ_EXTS | MOVIE_EXTS

FRAME_FILE_RE = re.compile(r"^(?P<stem>.+)\.(?P<frame>\d+)\.(?P<ext>[A-Za-z0-9]+)$")

READ_CLASSES = ("Read", "DeepRead", "ReadGeo", "Camera2", "Camera")

HAS_FRAME_RANGE = {"Read", "DeepRead"}


def _all_reader_nodes():
    """Yield (name, class_name, has_error, file_path) for all reader-type nodes."""
    for n in nuke.allNodes():
        cls = n.Class()
        if cls not in READ_CLASSES:
            continue
        fk = n.knob("file")
        if not fk:
            continue
        p = fk.value()
        try:
            err = n.hasError()
        except Exception:
            err = bool(p) and not os.path.exists(p.replace(BS, FS))
        yield n.name(), cls, err, p


def _fix_path(p):
    p = p.replace(BS, FS)
    if len(p) > 1 and p[1] == ":" and (len(p) < 3 or p[2] != FS):
        p = p[:2] + FS + p[2:]
    return os.path.normpath(p).replace(BS, FS)


def _stem_ext_from_path(p):
    """Extract stem (no dir, no frame token, no ext) and ext from a node file path."""
    name = os.path.basename(p.replace(BS, FS))
    base, ext = os.path.splitext(name)
    base = re.sub(r"\.(%0?\d*d|#+|\$F\d*|\d+)$", "", base)
    return base, ext.lstrip(".").lower()


def _frame_token(p):
    """Return the frame token of a node path: %04d / #### / $F4, or None."""
    m = re.search(r"\.(%0?\d*d|#+|\$F\d*)\.", p)
    return m.group(1) if m else None


def scan_media(root, keyword=None, exact=True):
    """Walk root recursively, group files into sequence/file entries.

    Sequence files group by (dir, stem, ext) so memory is bounded by
    sequence KINDS, not total file count.
    Entry dict: kind, dir, stem, ext (display case), ext_l (lower),
                frames (set|None), pad (digit width), fname (files only).
    keyword=None collects all media; else filter by stem (case-insensitive).
    """
    root = root.replace(BS, FS).rstrip(FS)
    kw = keyword.strip().lower() if keyword else None
    seqs = {}
    files = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        d = dirpath.replace(BS, FS)
        for fn in filenames:
            m = FRAME_FILE_RE.match(fn)
            if m and m.group("ext").lower() in SEQ_EXTS:
                stem, frame_s, ext = m.group("stem"), m.group("frame"), m.group("ext")
                ext_l = ext.lower()
                if kw is not None:
                    if exact and stem.lower() != kw:
                        continue
                    if not exact and kw not in stem.lower():
                        continue
                key = (d, stem.lower(), ext_l)
                e = seqs.get(key)
                if e is None:
                    seqs[key] = {"kind": "seq", "dir": d, "stem": stem, "ext": ext,
                                 "ext_l": ext_l, "frames": {int(frame_s)},
                                 "pad": len(frame_s)}
                else:
                    e["frames"].add(int(frame_s))
                    e["pad"] = max(e["pad"], len(frame_s))
            else:
                base, ext = os.path.splitext(fn)
                ext_l = ext.lstrip(".").lower()
                if ext_l not in MEDIA_EXTS:
                    continue
                stem = re.sub(r"\.\d+$", "", base)
                if kw is not None:
                    if exact and stem.lower() != kw and base.lower() != kw:
                        continue
                    if not exact and kw not in base.lower():
                        continue
                files[(d, fn)] = {"kind": "file", "dir": d, "stem": stem,
                                  "ext": ext.lstrip("."), "ext_l": ext_l,
                                  "frames": None, "fname": fn}
    entries = list(seqs.values()) + list(files.values())
    entries.sort(key=lambda e: (e["dir"].lower(), e["stem"].lower()))
    return entries


def _entry_display(e):
    if e["kind"] == "seq":
        tok = "%0" + str(e["pad"]) + "d"
        s = e["dir"] + FS + e["stem"] + "." + tok + "." + e["ext"]
        frames = e["frames"]
        lo, hi = min(frames), max(frames)
        gap = (hi - lo + 1) - len(frames)
        s += "  [" + str(lo) + "-" + str(hi) + "]"
        if gap:
            s += " 缺" + str(gap) + "帧"
        return s
    return e["dir"] + FS + e["fname"]


def _entry_node_path(e, orig_path):
    """Build the path to write into the node, preserving the original frame token."""
    if e["kind"] == "seq":
        tok = _frame_token(orig_path) or ("%0" + str(e["pad"]) + "d")
        p = e["dir"] + FS + e["stem"] + "." + tok + "." + e["ext"]
    else:
        p = e["dir"] + FS + e["fname"]
    return _fix_path(p)


class ReadManagerTable(QtWidgets.QDialog):
    def __init__(self, reads, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Read Manager")
        self.setMinimumSize(860, 480)

        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root_layout.addWidget(self.splitter)

        # ---- left: original panel content ----
        left = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Node", "Type", "Status", "File Path"])
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
        ec = sum(1 for _, _, e, _ in reads if e)
        self.stats = QtWidgets.QLabel("Total: " + str(len(reads)) + " reader nodes  |  Errors: " + str(ec))
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
        self.search_toggle = QtWidgets.QPushButton("Search >>")
        self.search_toggle.setFixedWidth(72)
        self.search_toggle.clicked.connect(self._toggle_search)
        rl.addWidget(self.search_toggle)
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
        self.table.itemSelectionChanged.connect(self._on_table_sel)
        self.splitter.addWidget(left)

        # ---- right: search panel (hidden by default) ----
        self.search_panel = self._build_search_panel()
        self.search_panel.setVisible(False)
        self.splitter.addWidget(self.search_panel)

    # ---------- search panel ----------

    def _build_search_panel(self):
        w = QtWidgets.QWidget()
        w.setMinimumWidth(380)
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(4, 0, 0, 0)

        row1 = QtWidgets.QHBoxLayout()
        row1.addWidget(QtWidgets.QLabel("Path:"))
        self.search_root = QtWidgets.QLineEdit()
        self.search_root.setPlaceholderText("directory to scan")
        row1.addWidget(self.search_root)
        self.browse_btn = QtWidgets.QPushButton("Browse")
        self.browse_btn.setFixedWidth(56)
        self.browse_btn.clicked.connect(self._browse_root)
        row1.addWidget(self.browse_btn)
        lay.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("Name:"))
        self.kw_edit = QtWidgets.QLineEdit()
        self.kw_edit.setPlaceholderText("filename stem, e.g. beauty")
        row2.addWidget(self.kw_edit)
        self.exact_cb = QtWidgets.QCheckBox("Exact")
        self.exact_cb.setChecked(True)
        row2.addWidget(self.exact_cb)
        self.search_btn = QtWidgets.QPushButton("Search")
        self.search_btn.setFixedWidth(56)
        self.search_btn.clicked.connect(self._search)
        row2.addWidget(self.search_btn)
        lay.addLayout(row2)

        self.result_list = QtWidgets.QListWidget()
        self.result_list.itemDoubleClicked.connect(lambda _item: self._apply_selected())
        lay.addWidget(self.result_list)

        row3 = QtWidgets.QHBoxLayout()
        self.apply_btn = QtWidgets.QPushButton("Replace")
        self.apply_btn.clicked.connect(self._apply_selected)
        row3.addWidget(self.apply_btn)
        self.match_all_btn = QtWidgets.QPushButton("Match All")
        self.match_all_btn.clicked.connect(self._match_all)
        row3.addWidget(self.match_all_btn)
        row3.addStretch()
        lay.addLayout(row3)
        return w

    def _toggle_search(self):
        show = not self.search_panel.isVisible()
        self.search_panel.setVisible(show)
        if show:
            self.search_toggle.setText("<< Hide")
            self.resize(1320, max(self.height(), 520))
            self.splitter.setSizes([860, 460])
        else:
            self.search_toggle.setText("Search >>")
            self.resize(860, self.height())

    def _browse_root(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory",
                                                        self.search_root.text() or "")
        if d:
            self.search_root.setText(d.replace(BS, FS))

    def _on_table_sel(self):
        rows = self._selected_rows()
        if len(rows) == 1:
            p = self.table.item(rows[0], 3).text()
            stem, _ext = _stem_ext_from_path(p)
            if stem:
                self.kw_edit.setText(stem)
        if self.search_panel.isVisible():
            root = self.search_root.text().strip()
            kw = self.kw_edit.text().strip()
            if kw and root and os.path.isdir(root):
                self._search()

    def _search(self):
        root = self.search_root.text().strip()
        kw = self.kw_edit.text().strip()
        if not root or not os.path.isdir(root):
            QtWidgets.QMessageBox.warning(self, "Read Manager", "Path is not a valid directory")
            return
        if not kw:
            QtWidgets.QMessageBox.warning(self, "Read Manager", "Name is empty")
            return
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            entries = scan_media(root, kw, self.exact_cb.isChecked())
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        self.result_list.clear()
        for e in entries:
            item = QtWidgets.QListWidgetItem(_entry_display(e))
            item.setData(QtCore.Qt.UserRole, e)
            self.result_list.addItem(item)
        nuke.tprint("Search '" + kw + "' in " + root + ": " + str(len(entries)) + " match(es)")

    def _apply_selected(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Read Manager", "Please select rows first")
            return
        item = self.result_list.currentItem()
        if item is None:
            QtWidgets.QMessageBox.information(self, "Read Manager", "Please select a search result")
            return
        e = item.data(QtCore.Qt.UserRole)
        count = 0
        for row in rows:
            name = self.table.item(row, 0).text()
            node = nuke.toNode(name)
            if not node:
                continue
            newp = _entry_node_path(e, node["file"].value())
            node["file"].setValue(newp)
            self.table.item(row, 3).setText(newp)
            count += 1
        nuke.tprint("Replaced " + str(count) + " node(s) -> " + _entry_display(e))
        self._refresh()

    def _match_all(self):
        root = self.search_root.text().strip()
        if not root or not os.path.isdir(root):
            QtWidgets.QMessageBox.warning(self, "Read Manager", "Path is not a valid directory")
            return
        rows = [r for r in self._selected_rows()
                if self.table.item(r, 2).text() == "ERROR"]
        if not rows:
            QtWidgets.QMessageBox.information(self, "Read Manager", "No ERROR rows selected")
            return
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            entries = scan_media(root)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        idx = {}
        for e in entries:
            idx.setdefault((e["stem"].lower(), e["ext_l"]), []).append(e)
        ok, no_match, ambiguous, frame_bad, range_missing = [], [], [], [], []
        for row in rows:
            name = self.table.item(row, 0).text()
            node = nuke.toNode(name)
            if not node:
                continue
            old = node["file"].value()
            stem, ext = _stem_ext_from_path(old)
            cands = idx.get((stem.lower(), ext.lower()), [])
            if not cands:
                no_match.append(name + " (" + stem + "." + ext + ")")
                continue
            if len(cands) > 1:
                ambiguous.append(name + " -> " + "; ".join(_entry_display(c) for c in cands))
                continue
            e = cands[0]
            node_cls = node.Class()
            if e["kind"] == "seq" and node_cls in HAS_FRAME_RANGE:
                try:
                    first = int(node["origfirst"].value())
                    last = int(node["origlast"].value())
                except Exception:
                    first, last = 0, -1
                if last < first:
                    range_missing.append(name)
                    continue
                needed = set(range(first, last + 1))
                if e["frames"] != needed:
                    lo, hi = min(e["frames"]), max(e["frames"])
                    frame_bad.append(name + " (found [" + str(lo) + "-" + str(hi) + "] "
                                     + str(len(e["frames"])) + " frames, need "
                                     + str(first) + "-" + str(last) + ")")
                    continue
            newp = _entry_node_path(e, old)
            node["file"].setValue(newp)
            self.table.item(row, 3).setText(newp)
            ok.append(name)
        lines = ["Match All: " + str(len(ok)) + " relinked / " + str(len(rows)) + " ERROR rows"]
        if no_match:
            lines.append("No match: " + str(len(no_match)) + " -- " + ", ".join(no_match[:8])
                         + (" ..." if len(no_match) > 8 else ""))
        if ambiguous:
            lines.append("Ambiguous: " + str(len(ambiguous)) + " -- " + ", ".join(ambiguous[:8])
                         + (" ..." if len(ambiguous) > 8 else ""))
        if frame_bad:
            lines.append("Frame mismatch: " + str(len(frame_bad)) + " -- "
                         + ", ".join(frame_bad[:8]) + (" ..." if len(frame_bad) > 8 else ""))
        if range_missing:
            lines.append("Unknown range: " + str(len(range_missing)) + " -- "
                         + ", ".join(range_missing[:8]))
        msg = chr(10).join(lines)
        nuke.tprint(msg)
        QtWidgets.QMessageBox.information(self, "Read Manager", msg)
        self._refresh()

    # ---------- original methods ----------

    def _populate(self):
        self.table.setRowCount(len(self.reads))
        for i, (name, ntype, has_error, path) in enumerate(self.reads):
            ni = QtWidgets.QTableWidgetItem(name)
            ti = QtWidgets.QTableWidgetItem(ntype)
            si = QtWidgets.QTableWidgetItem("ERROR" if has_error else "OK")
            pi = QtWidgets.QTableWidgetItem(path)
            if has_error:
                si.setForeground(QtGui.QColor(255, 80, 80))
                ni.setForeground(QtGui.QColor(255, 160, 140))
                ti.setForeground(QtGui.QColor(255, 160, 140))
            else:
                si.setForeground(QtGui.QColor(80, 200, 80))
            self.table.setItem(i, 0, ni)
            self.table.setItem(i, 1, ti)
            self.table.setItem(i, 2, si)
            self.table.setItem(i, 3, pi)
        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        self.table.resizeColumnToContents(2)

    def _selected_rows(self):
        return sorted(set(idx.row() for idx in self.table.selectedIndexes()))

    def _copy_all(self):
        lines = []
        for i in range(self.table.rowCount()):
            if self.table.item(i, 2).text() == "ERROR":
                lines.append(self.table.item(i, 0).text() + ": " + self.table.item(i, 3).text())
        if lines:
            QtWidgets.QApplication.clipboard().setText(chr(10).join(lines))

    def _copy_selected(self):
        lines = []
        for row in self._selected_rows():
            lines.append(self.table.item(row, 0).text() + ": " + self.table.item(row, 3).text())
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
        self.reads = list(_all_reader_nodes())
        self._populate()
        ec = sum(1 for _, _, e, _ in self.reads if e)
        self.stats.setText("Total: " + str(len(self.reads)) + " reader nodes  |  Errors: " + str(ec))
        nuke.tprint("Refreshed: " + str(len(self.reads)) + " reader nodes, " + str(ec) + " errors")

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
            p = self.table.item(row, 3).text()
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
            if self.table.item(row, 2).text() == "ERROR":
                QtWidgets.QMessageBox.warning(self, "Read Manager", "Cannot process missing files. Deselect error rows.")
                return
        seen = {}
        entries = []
        for row in rows:
            op = self.table.item(row, 3).text().replace(BS, FS)
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
                    self.table.item(row, 3).setText(clean)
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
                    self.table.item(row, 3).setText(rel)
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
    try:
        from PySide6 import QtWidgets
    except ImportError:
        from PySide2 import QtWidgets
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
    reads = list(_all_reader_nodes())
    _panel = ReadManagerTable(reads, _nuke_main_window())
    _panel.show()
