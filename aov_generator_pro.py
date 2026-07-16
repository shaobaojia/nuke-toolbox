import nuke 
try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore 
 
class AOVGeneratorPro(QtWidgets.QWidget):
    def __init__(self, node):
        super().__init__()
        self.node  = node 
        self.all_aovs  = sorted({
            c.split('.')[0]  for c in node.channels() 
            if c.split('.')[0]  not in ['rgba', 'depth', 'beauty']
        })
        
        self.setWindowFlags(QtCore.Qt.Window) 
        self.setWindowTitle("AOV 合成系统 v4.1")
        self.setMinimumSize(450,  650)
        
        self.list_widget  = QtWidgets.QListWidget()
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection) 
        self.list_widget.setStyleSheet(""" 
            QListWidget::item { 
                padding: 8px;
                margin: 2px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: #2980B9;
                color: white;
            }
        """)
        
        for aov in self.all_aovs: 
            item = QtWidgets.QListWidgetItem(f"🎨 {aov.ljust(28)}") 
            item.setData(QtCore.Qt.UserRole,  aov)
            self.list_widget.addItem(item) 
        
        self.chk_merge  = QtWidgets.QCheckBox("合成链模式（Plus叠加）")
        self.chk_merge.setChecked(True) 
        self.btn_generate  = QtWidgets.QPushButton("生成节点流")
        
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(QtWidgets.QLabel( 
            "<h3 style='color:#2C3E50; margin-bottom:10px;'>AOV合成工作台</h3>"
        ))
        main_layout.addWidget(self.list_widget) 
        
        ctrl_layout = QtWidgets.QHBoxLayout()
        ctrl_layout.addWidget(self.chk_merge) 
        ctrl_layout.addStretch() 
        ctrl_layout.addWidget(self.btn_generate) 
        main_layout.addLayout(ctrl_layout) 
        
        self.setLayout(main_layout) 
        
        self.btn_generate.clicked.connect(self.generate_flow) 
        self.list_widget.itemDoubleClicked.connect(self.btn_generate.click) 
 
    def generate_flow(self):
        selected = [item.data(QtCore.Qt.UserRole) for item in self.list_widget.selectedItems()] 
        if not selected:
            nuke.message("🚩  请选择至少一个通道")
            return 
        
        base_x = self.node.xpos()  + 150 
        base_y = self.node.ypos()  + 250 
        shuffle_nodes = []
        
        for idx, aov in enumerate(selected):
            shuffle = nuke.nodes.Shuffle( 
                inputs = [self.node],
                name = f"SHF_{aov}",
                postage_stamp = True,
                tile_color = 0x8F8F8F00 
            )
            shuffle['in'].setValue(aov)
            shuffle['out'].setValue('rgba')
            shuffle.setXYpos(base_x  + idx*220, base_y)
            shuffle_nodes.append(shuffle) 
        
        if self.chk_merge.isChecked()  and len(shuffle_nodes)>=2:
            merge_chain = shuffle_nodes[0]
            for i in range(1, len(shuffle_nodes)):
                merge = nuke.nodes.Merge2( 
                    inputs = [merge_chain, shuffle_nodes[i]],
                    operation = "plus",
                    name = f"MRG_Plus_{i}",
                    tile_color = 0x27AE6000 
                )
                merge.setXYpos( 
                    shuffle_nodes[i].xpos(),
                    shuffle_nodes[i].ypos() + 800
                )
                merge_chain = merge 
        self.close() 
 
def launch_pro():
    try:
        node = nuke.selectedNode() 
        if node.Class() not in ["Read", "DeepRead"]:
            raise Exception("请选择EXR/深度文件节点")
        global _aov_pro 
        try: _aov_pro.close() 
        except: pass 
        _aov_pro = AOVGeneratorPro(node)
        _aov_pro.show() 
    except Exception as e:
        nuke.message(str(e)) 
 

