import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'toolbox'))

# 仅在有 Qt 的主进程中启动桥（worker 无 QApplication）
try: from PySide6 import QtWidgets
except ImportError: from PySide2 import QtWidgets
if QtWidgets.QApplication.instance():
    import nuke_bridge
    nuke_bridge.get_bridge()

nuke.pluginAddPath("./NukeSurvivalToolkit")
