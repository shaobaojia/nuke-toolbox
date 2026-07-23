# Nuke Toolbox

Nuke 效率工具箱 — Read 管理器、工程管理、AOV 拆层、效率面板。

## 目录结构

```
.                    → 复制到 ~/.nuke/
├── init.py          → 环境初始化（sys.path + 插件路径）
├── menu.py          → 菜单注册 + Nuke Bridge 服务端
│
└── toolbox/         → 复制到 ~/.nuke/toolbox/
    ├── toolbox_panel.py        → 效率面板（自包含：路径转换、Postage Stamp、Write 创建/标签）
    ├── check_missing_reads.py  → Read 管理器（支持 Read/DeepRead/ReadGeo/Camera2/Camera，含搜索面板和 Match All）
    ├── nuke_project_manager.py → 工程管理器（创建 Nuke 工程目录，模板复制，冲突检测）
    └── aov_generator_pro.py   → AOV 拆层工具（F2 快捷键）
```

## 安装

```bash
# 复制根文件
cp init.py menu.py ~/.nuke/

# 复制工具箱
cp -r toolbox ~/.nuke/
```

重启 Nuke。

## 菜单入口

| 菜单 | 功能 |
|------|------|
| Toolbox → 效率面板 | 一站式面板：路径转换、Stamp 开关、Write 工具 |
| Toolbox → Read 管理器 | Read/DeepRead/ReadGeo/Camera 文件路径管理 + 搜索换链 |
| Toolbox → 工程管理 | 创建标准化 Nuke 工程目录 |
| Toolbox → AOV Generator Pro | AOV 自动拆层（快捷键 F2） |

## 注意事项

- `init.py` 中的 `sys.path` 使用 `__file__` 相对路径，**换机器无需修改**
- `menu.py` 包含 Nuke Bridge（TCP:54321），已部署 v7 稳定版
- Read 管理器需要 PySide6（Nuke 15+）或 PySide2（Nuke 13-14）
