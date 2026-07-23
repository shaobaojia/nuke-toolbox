import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'toolbox'))

import nuke_bridge
nuke_bridge.get_bridge()

nuke.pluginAddPath("./NukeSurvivalToolkit")
