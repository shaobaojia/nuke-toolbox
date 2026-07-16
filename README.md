# Nuke Toolbox

Nuke 效率面板工具集 — Read/Write 节点操作、Postage Stamp 管理。

## 脚本

| 脚本 | 功能 |
|:--|:--|
| `toolbox_panel.py` | PySide 效率面板 UI（分组卡片、暗色主题） |
| `convert_paths_to_relative.py` | Read/Write 节点绝对路径 → 相对路径 |
| `create_write_from_read.py` | 选中 Read → 自动生成 Write 节点 |
| `write_reading_color.py` | Write 节点按扩展名着色 |
| `write_reading_label.py` | Write 节点按路径设标签 |
| `aov_generator_pro.py` | EXR 多通道 AOV 合成链生成器 |
| `check_missing_reads.py` | 检测丢失的 Read 节点 |

Nuke 13 / 14 / 16 兼容（PySide2 / PySide6 自动适配）。

## 安装

```bash
git clone https://github.com/shaobaojia/nuke-toolbox.git
```

将 `.py` 文件复制到 `~/.nuke/`：

```bash
# 面板和独立脚本 → .nuke 根目录
cp nuke-toolbox/toolbox_panel.py ~/.nuke/
cp nuke-toolbox/aov_generator_pro.py ~/.nuke/
cp nuke-toolbox/check_missing_reads.py ~/.nuke/

# 内部工具脚本 → .nuke/toolbox/
mkdir -p ~/.nuke/toolbox
cp nuke-toolbox/convert_paths_to_relative.py ~/.nuke/toolbox/
cp nuke-toolbox/create_write_from_read.py ~/.nuke/toolbox/
cp nuke-toolbox/write_reading_color.py ~/.nuke/toolbox/
cp nuke-toolbox/write_reading_label.py ~/.nuke/toolbox/
```

在 `~/.nuke/init.py` 中添加：

```python
import toolbox_panel
```

在 `~/.nuke/menu.py` 末尾添加菜单入口：

```python
nuke.menu("Nuke").addCommand("Toolbox/效率面板", "toolbox_panel.show_toolbox()")
nuke.menu("Nuke").addCommand("Toolbox/AOV Generator Pro", "import aov_generator_pro; aov_generator_pro.launch_pro()", "F2")
nuke.menu("Nuke").addCommand("Toolbox/Check Missing Reads", "import check_missing_reads; check_missing_reads.check_missing_reads()")
```

重启 Nuke，菜单栏 `Toolbox → 效率面板` 即可打开。
