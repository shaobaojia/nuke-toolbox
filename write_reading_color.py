# Set color expression + force refresh on selected Write nodes
# reading on = green, reading off = yellow
import nuke

nodes = nuke.selectedNodes("Write")
if not nodes:
    nuke.message("Select Write nodes first")
    raise RuntimeError("no selection")

EXPR = '[python {0x00FF00FF if nuke.thisNode()["reading"].value() else 0xFFFF00FF}]'
count = 0

for n in nodes:
    n["tile_color"].setExpression(EXPR)
    lock = {"busy": False}
    def make_cb(node, lk):
        def cb():
            if lk["busy"]:
                return
            lk["busy"] = True
            try:
                v = node["tile_color"].value()
                node["tile_color"].setValue(v)
                node["tile_color"].setExpression(EXPR)
            finally:
                lk["busy"] = False
        return cb
    nuke.addKnobChanged(make_cb(n, lock), node=n)
    count += 1

nuke.message("Applied color expression to {} Write node(s)".format(count))
