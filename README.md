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

## 安装

所有 `.py` 文件放到 `~/.nuke/` 目录下。`toolbox/` 子目录下的脚本由效率面板自动加载。

Nuke 13 / 14 / 16 兼容（PySide2 / PySide6 自动适配）。
