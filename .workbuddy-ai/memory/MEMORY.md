# LSA_Linux 项目长期记忆

## 项目本质
把 Broadcom/LSI **LSI Storage Authority (LSA)** 8.17.10（x64 Linux 商业软件，管理 SAS/MegaRAID 控制器的 Web 工具）**移植为飞牛 fnOS 的 FPK 应用**。非源码级移植，而是"打包+适配+本地化"式移植。

## 关键事实
- 工作区根：`E:/LSA_Linux`（网络盘 `\\192.168.5.141\codex`）。**本会话开始前已存在的文件在沙箱内不可写**（新建文件可写），详见文末"环境限制"。
- 本地可写副本：`C:\LSA_Linux`（2026-10-13 用 robocopy 全量复制，修复与打包在此完成）。
- 上游输入：`LSA_Linux_64_readme.txt`（Broadcom 官方 README）、`SUPPORTED_CONTROLLERS.md`、`FEATURE_OVERVIEW.md`、`RELEASE_NOTES.md`。
- 交付物：`lsa-fnos/lsa.fpk`（中文，约 28.1MB）、`lsa-fnos-en/lsaen.fpk`（英文，约 27.8MB）。
- 打包工具：根目录 `fnpack-1.2.3-windows-amd64.exe`。在**包目录内**执行 `../fnpack-...exe build`，产物落在该目录。
- 真机验证工具：`tools/skill/`（trim-cli skill，可用 WebSocket 连 fnOS 做登录/应用/存储/文件验证）。
- 安装目标路径：`/opt/lsi/LSIStorageAuthority`；库路径 `/opt/lsi/LSA/libs`、`/opt/lsi/LSA/libs2`。
- 默认端口：Web 2463、LSA 服务 9000。
- fnOS 不允许第三方应用往自身 nginx 加路由 → 用 CGI 代理方案（`app/ui/index.cgi` + `cgi_proxy.py`）在 fnOS 同源下代理 LSA 的 GWT 页面。

## 桌面入口与访问模型（2026-10-13 重要变更）
- **现用 index.cgi 同源路径模式**：`app/ui/config` → `{"type":"iframe","url":"/cgi/ThirdParty/{lsa|lsaen}/index.cgi/"}`，**不声明 `protocol`/`port`**。
- 原因：端口服务模式（`protocol=""`+`port=${wizard_web_port}`）在 **HTTPS 门户(5667)** 下会失效 —— 门户前端 `wYe()` 让 `protocol`/`port` 回退到 `location.protocol`/`location.port`，iframe 变成 `https://<host>:2463/...`，而 2463 只有明文 HTTP → 空白破图。HTTP(5666) 下正常，故易漏测。
- 官方文档明确：CGI 入口**忽略 `protocol`/`port`**，沿用当前访问域名；调用前校验 NAS 登录态；不支持 WebSocket（LSA 不用 WebSocket，无影响）。
- **改 `app/ui/config` 后必须重装/升级**：入口在**安装期**写入两处注册表 —— `appcenter` 库 `app_service`（`url`/`default_url`）与 `trim_sac` 库 `entry`（`url`）。运行期不重读 `ui/config`。
- `app-center` 服务**实时读取** `appcenter.app_service`，改库后无需重启即生效（`GET /app-center/v1/service/list` 可验证）。
- 入口数据在 API 中形如 `{host, path, port, protocol}` + 独立 `fullUrl`；`fullUrl` 非空时优先直用。
- 官方 API 也支持改入口：`POST /app-center/v2/config/app/entry/full-url`、`.../visibility`。

## 安装 / 升级 / 卸载（2026-10-13 真机实测，必读）
- **fnOS 没有本地 FPK 就地升级能力。** `POST /app-center/v1/install/task` 只要 `appname` 已存在就返回 **`10236 = ErrCodeInstalledException`（「应用已安装」）**，**与版本号无关、与运行状态无关**（已用 `version=8.17.11` 的包 + running/stopped 各试，四次全 10236）。`trim-cli app update` 只走云端下载（`/v1/download/task`），本地包报 `10030`。
- **⇒ 真实部署路径 = 卸载 → 全新安装。** 发布说明里不要承诺"就地升级"。详细验证见 `UPGRADE_FLOW_VERIFICATION_2026-10-13.md`。
- **入口注册表在安装期自动刷新（已验证）**：装完即把 `app/ui/config` 的 `url` 写入 `appcenter.app_service`(`url`+`default_url`) 与 `trim_sac.entry`(`url`)。**所以"改 `app/ui/config` → 重装"是当前可行的变更方式，无需手工改库。** id/app_id 每次安装递增属正常。
- **`upgrade_init`/`upgrade_callback` 是死代码**（没有升级路径，永不被调用）。跨重装保留配置应改在 `uninstall_init`（备份到 `$TRIM_PKGVAR`，卸载后仍保留）+ `install_callback`（还原）。
- **开机后看门狗失效（P1）**：`cmd/main` 的 `start_watchdog` 在第 108 行，第 77–80 行有"已在运行就 exit 0"的提前返回；自行添加的 systemd 单元 `enabled` 且开机抢跑（日志实证 `08:33:24 msg="already running" appName=lsa class=start`）→ 提前返回 → **自愈从未生效**。安装后立即启动的场景下看门狗正常。修法：删单元统一走 `cmd/main`，或提前返回前先 `start_watchdog`。
- **卸载残留**：`/usr/local/sbin/lsa-fnos-start` **不会被删**（两次都如此）；`uninstall_init` 的 `purge_package` 里 `|| exit 1` 过于激进，单点失败会让后续清理全跳过（留 deb `ii` + `/opt/lsi`）。首次卸载曾报 `10392 = ErrCodeUninstallInitException`，**插桩复跑两次均完整成功、未能复现**（appcenter `error.log` 反复出现 `hook error ... nil pointer dereference`，疑其钩子执行器不稳）。
- **systemd 单元的两处缺陷**：`ExecStop` 缺 `cd`，`-p .` 解析到 `/` → 每次停止都报 `open() "./conf/nginx.conf" failed` 并打成 `failed`；`appcenter.app.is_systemd_uint` 对 lsa 为 `f`（fnOS 不认为它是 systemd 单元应用）。
- **厂商硬编码字符串无法本地化**：`Gateway - Authenticate`、`Load More`、`HOST` 不在 `message_en.js` 键集中（编译进 GWT），`message_zh.js` 覆盖层触及不到。属厂商限制。
- 设备侧查错入口：`/var/log/trim_app_center/info.log`（成功路径）与 `error.log`（`10236`/`10392`/`hook error`）。

## 中英双包差异（仅 3 处）
1. `cmd/main`：中文版把 `health_spec` 指向 `zh-CN/healthspec.json`；英文版指向 `en-US`。
2. `cmd/install_callback`：中文版多装 message_zh.js 覆盖层 + zh-CN 语言资源；英文版只删除 message_zh.js 恢复原生英文。
3. `app/ui/cgi_proxy.py`：`CGI_BASE` 路径 `lsa` vs `lsaen`；`app/ui/config` 的 desktop 入口 title/name。
- 英文包**不含** `message_zh.js` 和 `languages/` 目录；两个 README.md 完全相同（沿用中文说明，属遗漏）。

## CGI 拦截器机制（2026-10-13 定型）
- `cgi_proxy.py` 对每个 HTML 注入 `<base href>` + URL 拦截器：改写 `a[href]`/XHR/fetch/`location.assign`/`location.replace`/`window.open`。
- **`location.href = ...` 赋值无法 patch**（`href` 是 Location 实例 `[LegacyUnforgeable]` 属性，原型上无描述符）→ 用 **Navigation API** `navigate` 事件 + `event.intercept()` 兜住，这是 GWT 登录跳转（`/ui/core/index.html?locale=...&serverID=...`）能留在代理前缀内的唯一手段；需 Chrome/WebView 102+。
- 改后两包文件除 `CGI_BASE` 外完全一致；改完需同步中英双包（可用 `sed` 替换 `ThirdParty/lsa/`→`lsaen/` 派生）。
- 详见 `LOGIN_NAV_FIX_2026-10-13.md`。

## 飞牛 fnOS 开发规范（2026-10-13 学习）
- 技能手册：根目录 **`FNOS_DEV_GUIDE.md`**（改本项目前先读它，§14 是 LSA 与官方规范的差异清单）。
- 参考资料：`reference-snapshot/`（门户文档 HTML + `@trimjs/web-app` 0.4.2 SDK + `_extracted/` 纯文本）。
- 三种访问模型：**端口服务**（iframe 直连应用自身端口；与登录态无关；**HTTPS 门户下需应用端口自带 TLS，否则失效**）/ **index.cgi**（**本项目现用**，同源路径、跟随访问域名、不支持 WebSocket）/ **统一网关**（`gatewayPrefix`+`gatewaySocket`，注入 `X-Trim-Userid/Isadmin/Username`，适合复用系统域名+登录态+常驻服务）。
- 铁律：脚本用 `TRIM_APPDEST/TRIM_PKGETC/TRIM_PKGVAR/TRIM_SERVICE_PORT`，勿硬编码路径与端口；`main` 退出码 0=运行/3=未运行/1=失败；错误写 `TRIM_TEMP_LOGFILE`。
- 调 JS SDK 必须 `micro_app=true`；后端开放 API 走 Unix Socket `/var/run/trim_open_gateway_apiscope.socket` + `Authorization: Bearer $TRIM_API_TOKEN`；系统 ≥1.2.0401、App ≥1.34.0。
- 官方默认 `run-as=package` 且不推荐 root；LSA 因需访问 RAID 设备节点而用 root，属有理由偏离。
- 读 HTML 文档注意：快照部分文件含 NUL 字节，Read 工具会判为二进制，需用 python 去 NUL。

## 版本控制约定（2026-10-13 建立）
- 已 `git init`，分支 `main`，本地身份 `LSA fnOS Maintainer <maintainer@local>`；仓库在 `//192.168.5.141/codex/LSA_Linux`（网络盘，已加 safe.directory）。
- **必须保持 `.gitattributes`（`* text=auto eol=lf`）与 `core.autocrlf=false`**：否则 cmd/ 与 app/ui/ 脚本在 Windows 检出时会变 CRLF，部署到 Linux 后 shebang 失效。
- 忽略 `*.fpk`、`fnpack-*.exe`、`tools/skill/bin/`；**deb 必须入库**（不可再生）。
- 交接文档：根目录 `HANDOVER.md`。首提交 `b1f9650`。

## 待办/风险（接管时注意）
- 无版本控制 → 已解决（见上）。
- `cmd/main` 与 systemd wrapper `lsa-fnos-start` 里 WEB_PORT/BACKEND_PORT **硬编码 2463/9000**，与安装向导自定义端口不完全一致（自定义端口非充分验证路径）。
- `install_callback` 硬编码 `/lib/x86_64-linux-gnu` 兼容软链（libcrypt/libldap/liblber），依赖具体发行版布局。
- `main` 用 `pkill -9 -f '/bin/LSA'`，范围偏宽。
- 卸载脚本会 purge deb 并删 `/opt/lsi`，注意与 fnOS 其他包的同名系统软链隔离（已用 `remove_owned_symlink` 处理）。

## 环境限制（2026-10-13 实测，重要）
- `E:\LSA_Linux` 是网络盘 `\\192.168.5.141\codex`。**本会话开始前已存在的文件无法写入**：append / cp / mv / rm / `sed -i` / `os.replace` / 硬链接全部 `Permission denied`；而**本会话新建的文件可正常读写**。ACL 正常、无只读属性、非文件占用。
- 沙箱按**文件标识（inode）**判定而非路径 —— 硬链接指向同一 inode 同样被拒。
- `git` 操作**可写**（`.git/` 被豁免），`git update-index` 可用；但 `git checkout` 无法落地工作区（unlink 被拒）。
- **绕行方案**：把项目整体 `robocopy` 到本地盘（如 `C:\LSA_Linux`）后再改；或用 `git` 提交（工作区会与 HEAD 不一致，有"日后 `git add -A` 把修复回滚"的风险，需谨慎）。
- 其他环境事实：curl 访问局域网需 `--noproxy '*'`；trim-cli 需 `--scheme ws --allow-insecure-ws`；本机装有系统 Chrome（可配合自写 CDP 客户端做无头浏览器验证，无需下载 Chromium）。
