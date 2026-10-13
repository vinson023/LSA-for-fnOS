# LSA_Linux 项目长期记忆

## 项目本质
把 Broadcom/LSI **LSI Storage Authority (LSA)** 8.17.10（x64 Linux 商业软件，管理 SAS/MegaRAID 控制器的 Web 工具）**移植为飞牛 fnOS 的 FPK 应用**。非源码级移植，而是"打包+适配+本地化"式移植。

## 关键事实
- 工作区根：`E:/LSA_Linux`（**非 git 仓库**，无版本控制）。
- 上游输入：`LSA_Linux_64_readme.txt`（Broadcom 官方 README）、`SUPPORTED_CONTROLLERS.md`、`FEATURE_OVERVIEW.md`、`RELEASE_NOTES.md`。
- 交付物：`lsa-fnos/lsa.fpk`（中文，27MB）、`lsa-fnos-en/lsaen.fpk`（英文，26.6MB）。
- 打包工具：根目录 `fnpack-1.2.3-windows-amd64.exe`（Windows 可跑 `fnpack build`）。
- 真机验证工具：`tools/skill/`（trim-cli skill，可用 WebSocket 连 fnOS 做登录/应用/存储/文件验证）。
- 安装目标路径：`/opt/lsi/LSIStorageAuthority`；库路径 `/opt/lsi/LSA/libs`、`/opt/lsi/LSA/libs2`。
- 默认端口：Web 2463、LSA 服务 9000。
- fnOS 不允许第三方应用往自身 nginx 加路由 → 用 CGI 代理方案（`app/ui/index.cgi` + `cgi_proxy.py`）在 fnOS 同源下代理 LSA 的 GWT 页面。

## 中英双包差异（仅 3 处）
1. `cmd/main`：中文版把 `health_spec` 指向 `zh-CN/healthspec.json`；英文版指向 `en-US`。
2. `cmd/install_callback`：中文版多装 message_zh.js 覆盖层 + zh-CN 语言资源；英文版只删除 message_zh.js 恢复原生英文。
3. `app/ui/cgi_proxy.py`：`CGI_BASE` 路径 `lsa` vs `lsaen`；`app/ui/config` 的 desktop 入口 title/name。
- 英文包**不含** `message_zh.js` 和 `languages/` 目录；两个 README.md 完全相同（沿用中文说明，属遗漏）。

## 待办/风险（接管时注意）
- 无版本控制，建议 `git init`。
- `cmd/main` 与 systemd wrapper `lsa-fnos-start` 里 WEB_PORT/BACKEND_PORT **硬编码 2463/9000**，与安装向导自定义端口不完全一致（自定义端口非充分验证路径）。
- `install_callback` 硬编码 `/lib/x86_64-linux-gnu` 兼容软链（libcrypt/libldap/liblber），依赖具体发行版布局。
- `main` 用 `pkill -9 -f '/bin/LSA'`，范围偏宽。
- 卸载脚本会 purge deb 并删 `/opt/lsi`，注意与 fnOS 其他包的同名系统软链隔离（已用 `remove_owned_symlink` 处理）。
