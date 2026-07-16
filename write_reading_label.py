# Add styled reading status label to selected Write nodes
import nuke

nodes = nuke.selectedNodes("Write")
if not nodes:
    nuke.message("Select Write nodes first")
else:
    expr = '[python {"<font color=\\"#00FF00\\" size=\\"5\\"><b>READING</b></font>" if nuke.thisNode().knob("reading").value() else "<font color=\\"#FF8800\\" size=\\"5\\"><b>LIVE</b></font>"}]'
    for n in nodes:
        n["label"].setValue(expr)
    nuke.message("Styled label on " + str(len(nodes)) + " Write(s)")
