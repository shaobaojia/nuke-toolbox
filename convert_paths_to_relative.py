# Convert selected Read/Write nodes: absolute -> relative
import nuke, os

script_dir = nuke.script_directory()
if not script_dir:
    nuke.message("Save .nk first")
    raise RuntimeError("not saved")

nodes = nuke.selectedNodes()
if not nodes:
    nuke.message("Select Read or Write nodes first")
    raise RuntimeError("no selection")

converted = 0
for node in nodes:
    if node.Class() not in ("Read", "Write"):
        continue
    k = node.knob("file")
    if not k:
        continue
    p = k.value()
    if not p or not os.path.isabs(p):
        continue
    k.setValue(os.path.relpath(p, script_dir).replace("\\", "/"))
    converted += 1

nuke.message("Converted {} nodes".format(converted))
