# AGENTS.md

> 给下一个 Agent（或下一个自己）的交接备忘录。**收工推送前必须更新「刚做完 / 正在做 / 下一步 / 坑」四个字段。**

## 接手前必读（环境/前置条件）

- 运行环境：Windows 10+，Nuke 13.2 / 16.0 共存（公司 PC：fsj1023，SSH 免密），Python 3.x（Nuke 自带）
- 部署位置：`C:/Users/shaobaojia/.nuke/`（init.py + menu.py + toolbox/），GitHub 仓库 = 运行真相的镜像，改动先改 PC 再推
- 前置操作：改完 Nuke 里 **Reload UI**（面板内）或重启 Nuke 才生效；import 有 sys.modules 缓存，菜单重开 ≠ 重新加载
- 远程操作：NAS → SSH → 公司 PC → TCP 桥（Nuke16 主进程桥默认 54322，被 13.2 worker 污染时手动切 54325+）

## 这个项目是干什么的

Nuke 效率面板工具箱——Read/Write 节点批量操作、素材路径修复（Relink/Replace+Copy/Move）、Postage Stamp 管理、AOV 拆层、工程管理、Bridge 远程操控。

## 刚做完

- Read 管理器新增 **Open Explorer**（按钮 + File Path 列路径解析）：hotknob 表达式路径（`[python {nuke.script_directory()}]/...`）先求值再打开，序列开目录、单文件定位
- Read 管理器新增 **Replace+Move**：前缀替换 + 移动文件（只移匹配 stem 的文件，源目录空则删，目标同名先覆盖）
- Read 管理器新增 **Node Graph 选中同步**：Node Graph 单击/双击 Read 类节点 → 列表自动选中 + 滚动（QTimer 500ms 轮询，非 updateUI）
- 全链路真机验证：hotknob 解析 30/30 节点存在性通过、选中同步 last_sel/ticks 确认
- 双击列表行为恢复为「选择节点」（不再打开资源管理器）

## 正在做

无（本次收工）。

## 下一步

- 仓库代码与 PC 已同步（本次推送），后续 PC 改动记得推
- 待用户安排：暂无明确任务

## 坑（已踩过的雷）

- **`nuke.addUpdateUI` 监听节点选中变化不可靠**：用户鼠标单击不触发，程序化 setSelected 却触发（bridge 测试假象）。监听选中变化用 QTimer 500ms 轮询，Qt 事件循环稳定触发
- **hotknob 表达式路径**：`[python {nuke.script_directory()}]/MEDIA/...` 字面字符串过 `os.path.isdir()` 必 False——所有磁盘操作前必须 `_resolve_path()` 求值（受控 eval 只注入 nuke）+ 相对路径基于 script_directory 拼绝对
- **Nuke13.2 worker 抢 bridge 端口**：13.2 worker 有 QApplication 会自己起桥（SO_REUSEADDR），54322-54324 是污染区；连接被路由到 worker 报 `Invalid function call in non-gui mode`。多实例手动切 54325+，Test 绿了才算通
- **Reload UI 不生效排查**：部署新代码后用户面板可能还是旧实例——bridge 查面板实例是否有新属性（如 `_sync_timer`），`importlib.reload(模块)` 刷内存后让用户**关面板重开**
- **bridge 测试时 `time.sleep` 阻塞主线程**：sleep 期间事件循环/QTimer/updateUI 全停，回调计数为 0 是测试方法问题不是功能问题；分两条命令，NAS 端等待
- **patch 正则转义**：改含 `\.` 的正则时参数里直接写单反斜杠，多写一层会变成 `\\.` 且 docstring 引号被转义破坏语法
- **`nuke.selectedNode()` 无选中时抛 ValueError**（"no node selected"）——用 `nuke.selectedNodes()` 判空或 try/except

## 细节指针

- 架构：`toolbox/` 自包含（init.py 注入 sys.path，menu.py 懒加载菜单命令），桥独立 `nuke_bridge.py` 由 init.py QApplication 守卫启动
- 桥协议：raw TCP，UTF-8 Python 代码 → `executeInMainThreadWithResult` 执行 → stdout+stderr 回传；请求 ≤2MB、响应 ≤1MB；**命令必须 print() 输出**，禁 nuke.message()
- 完整踩坑/模式：Hermes skill `nuke-pipeline`（开发铁律三铁：先看 → 再做 → 再审，有问题自己修）
