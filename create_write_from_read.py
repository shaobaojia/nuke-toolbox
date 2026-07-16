import nuke
import os
import re


def add_fix_suffix(path):
    """Insert _fix before frame pattern or before file extension."""
    path = path.replace('\\', '/')
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)

    for regex, handler in [
        (r'\.(%0(\d+)d)', lambda m: f'_fix.{m.group(1)}'),   # .%04d
        (r'\.(%d)',        lambda m: f'_fix.{m.group(1)}'),   # .%d
        (r'\.(#+)',        lambda m: f'_fix.{m.group(1)}'),   # .####
        (r'\.(\$F\d*)',    lambda m: f'_fix.{m.group(1)}'),   # .$F4 / .$F
    ]:
        m = re.search(regex, basename)
        if m:
            new_basename = basename[:m.start()] + handler(m) + basename[m.end():]
            return dirname + '/' + new_basename

    name, ext = os.path.splitext(basename)
    return dirname + '/' + name + '_fix' + ext


def create_write_from_read():
    selected = nuke.selectedNodes('Read')
    if not selected:
        nuke.message('Please select a Read node first.')
        return

    for read in selected:
        file_path = read['file'].value()
        if not file_path:
            nuke.message('Read node {} has no file path.'.format(read.name()))
            continue

        out_path = add_fix_suffix(file_path)

        write = nuke.createNode('Write')
        write['file'].setValue(out_path)

        x = read.xpos()
        y = read.ypos() + read.screenHeight() + 40
        write.setXYpos(x, y)

        write.setInput(0, read)

        nuke.message('Write created:\n' + write.name() + '\n' + out_path)
create_write_from_read() 
