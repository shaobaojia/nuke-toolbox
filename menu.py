# === Nuke Toolbox Menu ===
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'toolbox'))

import nuke

# ── 菜单 ─────────────────────────────────────────────

nuke.menu('Nodes').addMenu('custom').addCommand('Z Fog v1.1',
    "nuke.nodePaste(r'C:/Users/shaobaojia/.nuke/Z_fog_v1.1.gizmo')")

nuke.menu("Nuke").addCommand("Toolbox/Bridge Monitor",
    "import nuke_bridge; nuke_bridge.show_monitor()")
nuke.menu("Nuke").addCommand("Toolbox/Read 管理器",
    "import check_missing_reads; check_missing_reads.check_missing_reads()")
nuke.menu("Nuke").addCommand("Toolbox/AOV Generator Pro",
    "import aov_generator_pro; aov_generator_pro.launch_pro()", "F2")
nuke.menu("Nuke").addCommand("Toolbox/效率面板",
    "import toolbox_panel; toolbox_panel.show_toolbox()")
nuke.menu("Nuke").addCommand("Toolbox/工程管理",
    "import nuke_project_manager; nuke_project_manager.show_panel()")
