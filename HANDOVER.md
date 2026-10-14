# LSA for fnOS — 项目交接文档

> 本文档面向接管本项目的维护者。目标：在不读全部脚本的前提下，能准确理解项目、安全地改动、正确地构建与验证。

---

## 1. 项目定位

把 Broadcom/LSI **LSI Storage Authority (LSA) 8.17.10**（x64 Linux 商业软件，用于管理 Broadcom/LSI SAS / MegaRAID / iMR / HBA 控制器的 Web 管理台）**移植为飞牛 fnOS 的 FPK 应用**。

**关键性质：这是「外壳工程」，不是源码移植。** 上游 LSA 以不可修改的 deb 形式提供，本项目只做三件事：

1. **打包**：把厂商 deb 与 fnOS 生命周期脚本组装成 `.fpk`；
2. **适配**：解决 fnOS 运行环境与厂商假设不一致的地方（同源代理、权限、端口、启动时序）；
3. **本地化**：中文包提供 GWT 覆盖层与语言资源替换。

**许可证红线**：LSA 是 Broadcom 商业软件，仅限内部使用，**不可公开发布**。本仓库应保持私有、本地，不得推送到公开远端。

---

## 2. 上游输入与产出

### 上游输入（根目录）

| 文件 | 作用 |
| --- | --- |
| `LSA_Linux_64_readme.txt` | Broadcom 官方 README，是受支持控制器、安装方式、已知问题的权威来源 |
| `SUPPORTED_CONTROLLERS.md` | 由官方 README 整理的受支持控制器清单 |
| `FEATURE_OVERVIEW.md` | 面向 fnOS 用户的功能介绍 |
| `RELEASE_NOTES.md` | 本次发布（8.17.10）的变更说明 |
| `lsa-fnos/app/debs/`、`lsa-fnos-en/app/debs/` | 三个厂商 deb（主包 + lib_utils + lib_utils2/OpenSLP），**不可再生，务必保留** |

厂商 deb 清单（构建必需）：

- `LSIStorageAuthority-008.017.010.000-1_amd64.deb`（主程序，约 25MB）
- `LSA_lib_utils-1.18-1_amd64.deb`
- `LSA_lib_utils2-9.00-1_amd64.deb`（内含 OpenSLP / slpd）

### 产出

| 产出 | 说明 |
| --- | --- |
| `lsa-fnos/lsa.fpk` | 中文包，约 27MB，appname=`lsa` |
| `lsa-fnos-en/lsaen.fpk` | 英文包，约 26.6MB，appname=`lsaen` |

两个包**共用 LSA 服务目录与端口，不能同时安装或运行**。

---

## 3. 目录结构

```
E:/LSA_Linux/
├── LSA_Linux_64_readme.txt          # 上游官方 README
├── SUPPORTED_CONTROLLERS.md / FEATURE_OVERVIEW.md / RELEASE_NOTES.md
├── HANDOVER.md                      # 本文档
├── fnpack-1.2.3-windows-amd64.exe   # 打包工具（Windows）
├── lsa-fnos/                        # 中文包工程
│   ├── manifest                     # FPK 应用描述
│   ├── ICON.PNG / ICON_256.PNG
│   ├── build.sh                     # 构建辅助（见 §7 注意事项）
│   ├── cmd/                         # fnOS 生命周期脚本（核心）
│   ├── config/                      # privilege（root 运行）、resource
│   ├── wizard/                      # install / config 向导定义
│   └── app/
│       ├── debs/                    # 厂商 deb
│       └── ui/                      # 桌面入口 + CGI 代理 + 本地化资源
├── lsa-fnos-en/                     # 英文包工程（结构同中文包）
└── tools/skill/                     # trim-cli 真机验证工具（见 §9）
```

`cmd/` 脚本职责：

| 脚本 | 时机 | 职责 |
| --- | --- | --- |
| `install_init` | 安装前 | 校验 x86_64 架构 |
| `install_callback` | 安装后 | 装 deb、写端口、装本地化、兼容软链、systemd 单元 —— **最重要、最长** |
| `main` | 运行时 | `start` / `stop` / `status`，含看门狗 |
| `config_init` / `config_callback` | 改配置 | 停服、改端口、重启 |
| `upgrade_init` / `upgrade_callback` | 升级 | 备份配置 → 升级 → 恢复配置 + 重刷本地化 |
| `uninstall_init` / `uninstall_callback` | 卸载 | 停服、purge deb、清理 `/opt/lsi` |

---

## 4. 运行时架构

请求链路（自上而下）：

```
fnOS 桌面图标 (app/ui/config, type=iframe, port=${wizard_web_port})
   └─> /cgi/ThirdParty/lsa/index.cgi        (app/ui/index.cgi)
          └─> cgi_proxy.py                  (同源代理，注入 <base href> + URL 拦截器)
                 └─> http://127.0.0.1:2463   (LSA 自带 nginx)
                        └─> LSA 后端进程     (服务端口 9000)
                               └─> RAID 控制器 / 磁盘
```

安装与启停生命周期由 `cmd/` 脚本 + systemd 单元 `lsistorageauthority.service`（执行 `/usr/local/sbin/lsa-fnos-start`）负责。

关键安装路径：

- `LSA_HOME = /opt/lsi/LSIStorageAuthority`
- 库路径：`/opt/lsi/LSA/libs`（捆绑 OpenSSL 3.2+）、`/opt/lsi/LSA/libs2`（捆绑 OpenSLP）
- 默认端口：Web `2463`、LSA 服务 `9000`
- 端口持久化文件：`$LSA_HOME/conf/fnos_ports.conf`（`web=` / `service=`）

---

> **规范对照与开发技能**：飞牛 fnOS 应用开发的完整规范（访问模型、manifest、权限资源、生命周期、环境变量、向导、开放 API）已整理为 `FNOS_DEV_GUIDE.md`，其中 §14 专门列出本项目与官方规范的差异清单与改进方向。改动本项目前建议先读该文档。

## 5. 移植机制详解

> **重要澄清（访问模型，2026-10-13 更新）**：历史上 `RELEASE_NOTES.md` 8.17.10 记录"应用入口改为**端口服务模式**：桌面图标以 iframe 直连 LSA Web 管理端口"，此后一段时间生效的入口是端口服务（`app/ui/config` 的 `port=${wizard_web_port}` + `url=/ui/remoteserver/index.html`，iframe 直连 LSA 自带 nginx 的 2463）。
>
> **但端口服务模式在 HTTPS 门户下会失效**：fnOS 桌面前端拼 iframe 地址时，`protocol`/`port` 缺省会回退到 `location.protocol`/`location.port`，于是从 `https://<nas>:5667/` 打开会得到 `https://<nas>:2463/...`，而 2463 只有明文 HTTP、无 TLS → 握手失败，窗口内容区空白破图（HTTP 5666 下正常，故容易漏测）。
>
> **现已改回 index.cgi 同源路径模式**（`url=/cgi/ThirdParty/lsa/index.cgi/`，不声明 `protocol`/`port`），HTTP 与 HTTPS 门户均可正常工作。包内的 CGI 代理（`index.cgi` + `cgi_proxy.py`）因此**重新成为正式入口**。详见根目录 `HTTPS_ACCESS_FIX_2026-10-13.md` 与 `FNOS_DEV_GUIDE.md` §4。

### 5.1 同源代理（正式入口）

LSA 是 GWT 应用，使用 `/ui/core/index.html`、`/LSI/Storage/MR/API/...` 这类**原点绝对路径**导航，这些路径在 fnOS 域名下不存在。fnOS 又不允许第三方应用往自身 nginx 加 location。

解法：`app/ui/index.cgi` 拉起 `cgi_proxy.py`，把 LSA 页面代理到 `/cgi/ThirdParty/lsa/index.cgi/` 下，并对**每个 HTML 响应**：

1. 注入 `<base href>`，镜像原文档目录（GWT 资源是相对引用）；
2. 注入 URL 拦截器，改写 `<a href>`、`XMLHttpRequest.open`、`fetch`、`location.assign/replace`、`window.open`，并用 **Navigation API 的 `navigate` 事件 + `event.intercept()`** 兜住 `location.href = ...` 这类跨文档赋值（`href` 是 `[LegacyUnforgeable]` 自有属性，无法 patch），把原点绝对路径拉回代理前缀。详见 `LOGIN_NAV_FIX_2026-10-13.md`；
3. 剥离 `X-Frame-Options` / `Content-Security-Policy`，允许 iframe 内嵌。

> 修改代理逻辑时，`CGI_BASE` 必须与 manifest 的 `appname` 对应：中文包 `/cgi/ThirdParty/lsa/index.cgi/`，英文包 `/cgi/ThirdParty/lsaen/index.cgi/`。

### 5.2 桌面入口

`app/ui/config` 定义 `.url` 条目：`type=iframe`、`url=/cgi/ThirdParty/lsa/index.cgi/`（**不声明 `protocol`/`port`**，由 fnOS 沿用当前访问域名）。`manifest` 的 `desktop_applaunchname` 指向它（`lsa.main` / `lsaen.main`）。

> **改这个文件后必须重装/升级才会生效**：桌面入口在**安装期**被写入两处注册表 —— `appcenter` 库 `app_service` 表的 `url`/`default_url`，以及 `trim_sac` 库 `entry` 表的 `url`。运行期不会重读 `app/ui/config`，仅重启应用也不会刷新这两处。
> 其中 `app-center` 服务是**实时读取** `appcenter.app_service` 的，改库后无需重启服务即生效。

### 5.3 全权限模式

厂商默认 `readOnly=1`，登录后隐藏 RAID 操作菜单。`install_callback`、`main start`、`config_init`、`upgrade_callback` 四处都会把 `LSA.conf` 刷为：

```
readOnly = 0
full_access_groups = Administrators,fnos-admin
readonly_access_groups =
```

注意 `main start` 在**后端就绪后**再刷一次，因为 LSA 后端初始化时会重写这些默认值。

### 5.4 幂等启动与看门狗（解决"真机枚举慢 / 端口被占导致启动误报失败"）

> ⚠️ **已知缺陷：开机场景下看门狗实际不会启动（2026-10-13 实测）**
> `cmd/main` 的 `start_watchdog` 在第 108 行，但第 77–80 行有提前返回：
> ```bash
> if port_open "$WEB_PORT" && lsa_running; then
>     echo "LSA is already running; keeping the existing instance"
>     exit 0        # ← 到不了 start_watchdog
> fi
> ```
> 而 `install_callback` 又写了 `enabled` 的 systemd 单元（`WantedBy=multi-user.target`）。开机时二者赛跑，**日志实证 systemd 抢先**：
> ```
> 08:33:16  systemd 启动 lsistorageauthority.service
> 08:33:24  appName=lsa class=start  msg="already running"  code=0
> ```
> ⇒ 开机后处于**无自愈**状态。注意：**安装后立即启动**的场景下看门狗是正常的（单元未被 systemd 启动，`main start` 走到了第 108 行）。
> **修复建议**：删除 systemd 单元、统一走 `cmd/main`（推荐）；或把提前返回改为"先 `start_watchdog` 再返回"。

- 厂商 init 脚本在 nginx 或 LSA 已存在时返回失败；fnOS 开机竞争场景很常见。
- `install_callback` 写入 `/usr/local/sbin/lsa-fnos-start`（幂等包装器）与 `lsistorageauthority.service`（`Type=oneshot`、`RemainAfterExit=yes`、`TimeoutStartSec=180`）。
- 包装器逻辑：先等 `slpd` 的 UDP 427 端口就绪（必要时自行拉起 `/opt/lsi/LSA/libs2/slpd`）；nginx 端口未开才启动；首次启动前清掉残留 LSA；最后 `./LSA -start`。
- `cmd/main` 启动后启动 10s 轮询看门狗，后端掉线自动拉起；启动等待上限 `LSA_START_TIMEOUT`（默认 120s），不再用旧的 5 秒固定窗口误判失败。
- 环境变量：`LD_LIBRARY_PATH="/opt/lsi/LSA/libs:/opt/lsi/LSA/libs2:$LSA_HOME/lib:$LSA_HOME/bin:$LSA_HOME/plugins"`。

> ⚠️ **systemd 单元的两处附加缺陷**：
> 1. `ExecStop` 缺 `cd`，`-p .` 被解析成 systemd 的工作目录（`/`），每次停止都报 `open() "./conf/nginx.conf" failed` 并把单元打成 `failed`；`daemon-reload` 不会清除该状态。
> 2. `appcenter.app.is_systemd_uint` 对 lsa 为 `f` —— fnOS **不认为**本应用是 systemd 单元应用，这个单元是项目自行附加的，脱离了 fnOS 生命周期管理。

### 5.5 中文本地化（中文包核心）

1. **GWT 覆盖层** `app/ui/message_zh.js`（约 130KB / 2400 行）：`install_callback` 复制到 `$LSA_HOME/server/html/js/message_zh.js`，并改写 6 个 `ui/*/index.html`（`core integratedraid server megaraid managedserver remoteserver`）的脚本顺序 —— **必须先 message_zh.js、后 GWT 的 `.nocache.js`**，否则 GWT 首渲染会缓存英文。
2. **语言资源替换**：把 `languages/zh-CN/` 下的 `healthspec.json`、`mr_errors_spec.ini`、`mr_events_spec.ini`、`mr8_events_spec.ini`、`alertparam.ini`、`alertspec.json` 复制进 `$LSA_HOME/conf/languages/zh-CN/`，并**同时覆盖 `en-US/` 同名文件**（厂商运行时固定从 en-US 取错误/事件/告警）。
3. **静态页**：`50x.html`、`ui/core/ServerNotReachable.html`、`files/App_statusCode_description.html`、`files/credits.html` 替换。
4. **帮助页**：`help/integratedraid`、`help/megaraid` 下翻译后的 html 覆盖（仅 html，保留厂商图片/样式）。
5. `health_spec` 路径在 `main start` 与 `config_init` 中反复确认，防止被还原成英文。

---

## 6. 中英双包差异

除 `manifest`（appname/display_name/desc/desktop_applaunchname）与 `app/ui/config` 的标题外，逻辑差异**仅 3 处**：

| 位置 | 中文包 | 英文包 |
| --- | --- | --- |
| `cmd/main` | `health_spec` → `zh-CN/healthspec.json` | → `en-US/healthspec.json` |
| `cmd/install_callback` | 安装 message_zh.js 覆盖层 + zh-CN 语言资源 | **删除** message_zh.js 恢复原生英文；不装语言资源 |
| `app/ui/cgi_proxy.py` | `CGI_BASE=/cgi/ThirdParty/lsa/index.cgi/` | `.../lsaen/...` |

英文包**不含** `message_zh.js` 与 `languages/` 目录（符合设计）。

> 待改进：两份 `README.md` 完全相同，英文包 README 未本地化。

---

## 7. 构建

**推荐（Windows 当前环境）**：

```bash
cd lsa-fnos        # 或 lsa-fnos-en
../fnpack-1.2.3-windows-amd64.exe build
```

生成的 `lsa.fpk` / `lsaen.fpk` 位于工程目录内。fpk 结构已确认 = `tar.gz(app.tgz + cmd/ + config/ + wizard/ + manifest + 图标)`，其中 `app.tgz` 内含 `debs/` 与 `ui/`。

**`build.sh` 注意事项**：脚本第 1 步从 `../gcc_11.2.x/` 复制 deb，但**该源目录在当前工作区不存在**（deb 已在 `app/debs/`）。因此 `build.sh` 在此环境会第一步报错退出；应直接 `fnpack build`，或在有 `gcc_11.2.x/` 源目录的机器上运行 `build.sh`。

**打包工具**：`fnpack 1.2.3`，命令 `build` / `create`。下载：https://developer.fnnas.com/docs/cli/fnpack/

---

## 8. 安装 / 升级 / 卸载生命周期要点

> ⚠️ **升级路径的重要事实（2026-10-13 真机实测）**：fnOS **不支持**用本地 FPK 就地升级 —— `POST /app-center/v1/install/task` 只要 `appname` 已存在就返回 `10236 = ErrCodeInstalledException`（「应用已安装」），**与版本号无关、与运行状态无关**（已用版本号递增到 8.17.11 的包验证）。`app update` 只走云端下载，本地包不可用。
> **⇒ 新包上线 = 卸载 → 全新安装。** 详见 `UPGRADE_FLOW_VERIFICATION_2026-10-13.md`。

- **安装**：`install_init` 校验架构 → 释放文件 → `install_callback` 依次 `dpkg -i`（lib_utils2 → lib_utils → 主包）→ 写 `fnos_ports.conf` → 装本地化 → 建兼容软链 → 修 `LSA.conf` → 写 systemd 单元并 `enable`。
- **端口**：`install_callback` 把 nginx.conf 的 `nginx_default` / `LSA_Default` 占位符替换成向导端口，并改 `LSA.conf` 的 `listening_port` / `client_listening_port`。
- **入口注册表**：安装期会把 `app/ui/config` 的 `url` 写入 `appcenter.app_service`（`url` + `default_url`）与 `trim_sac.entry`（`url`）两处。**实测确认：改 `app/ui/config` 后重装即自动生效，无需手工改库。**
- **升级**：`upgrade_init` / `upgrade_callback` 存在，但**在当前 fnOS 上属死代码**（没有就地升级路径，永不会被调用）。其"升级保留配置"的职责因此**完全落空**；目前配置之所以在重装后还在，只是因为首次卸载中止、`/opt/lsi` 被意外保留 —— 属侥幸。
- **卸载**：`uninstall_init` 停 systemd 单元、停进程与 nginx、`dpkg --purge` 三个包、删 `/opt/lsi` 与 `/opt/lsi/LSA`、`rmdir /opt/lsi`。兼容软链用 `remove_owned_symlink` 只删"确实指向本项目目标"的链接，避免误删其他包的同名系统软链。
  - 插桩实测：**脚本逻辑本身能把三个 deb 全部 purge、`/opt/lsi` 完全删除**。
  - 但**首次卸载曾以 `10392 = ErrCodeUninstallInitException` 中止**（未复现，两次插桩复跑均成功），推测与 appcenter 钩子执行器的偶发 panic 有关（其 `error.log` 中反复出现 `hook error ... nil pointer dereference`）。中止的后果是留下半卸载状态（deb 仍 `ii`、`/opt/lsi` 仍在）。
  - **固定残留**：`/usr/local/sbin/lsa-fnos-start` **不会被删除**（两次卸载都如此）。

---

## 9. 真机验证

`tools/skill/` 是 **trim-cli** skill：通过 WebSocket 连 fnOS，可登录、管理应用中心（安装/启动/停用/卸载 fpk）、查看存储与文件、执行系统/日志操作。

典型验证流程（参考 `tools/skill/reference/workflows/device-validation.md`）：

1. `login` 建立 session；
2. 先做只读探测（`app list`、`storage pools`）确认连接与权限；
3. 执行单一写操作（如 `app install-fpk`）后立刻回归（`app status`）；
4. 记录写前/写后状态对比，无法客观对比不得宣称通过。

验证账号使用用户明确提供或已授权的账号，**不得在产物中记录测试密码**。

---

## 10. 已知风险与未验证路径

按优先级排列，接管后应逐项处理：

1. **无版本控制** → 本次已 `git init`（分支 `main`），见 §12。**务必保持私有**。
2. **端口硬编码**：`cmd/main` 与 `lsa-fnos-start` 包装器把 `WEB_PORT=2463`、`BACKEND_PORT=9000` 写死。而向导与 `config_init` 允许自定义端口，只改了 nginx.conf / LSA.conf / `fnos_ports.conf`，启停与状态检测仍按 2463/9000 判断 —— **自定义端口属未充分验证路径**。建议改为从 `fnos_ports.conf` 读取。
3. **安装向导的"安装模式"未接线**：`wizard/install` 收集 `wizard_install_mode`（gateway/standalone/directagent/lightweight），但 `install_callback` 无条件写 `installtype=gateway`、`installation_type=0`。该选项目前是**装饰性的**，要么接线、要么从向导移除。
4. **发行版相关硬编码**：`install_callback` 在 `/lib/x86_64-linux-gnu` 下建 `libcrypt.so.2`、`libldap-2.4.so.2`、`liblber-2.4.so.2` 兼容软链，绑定具体发行版布局。
5. **进程匹配偏宽**：`cmd/main` 使用 `pkill -9 -f '/bin/LSA'`，理论上可能误伤同名字符串进程。
6. **`build.sh` 依赖缺失目录**（见 §7）。
7. **英文包 README 未本地化**（见 §6）。
8. **入口注册表不会随运行期变更同步**：桌面入口只在安装期写入 `appcenter.app_service` 与 `trim_sac.entry`。若日后要支持"免重装切换访问模型/端口"，需在 `cmd/` 中主动同步这两处，否则用户改完 `app/ui/config` 会看不到效果。**（已实测确认：重装会自动同步，所以当前"改 config → 重装"的流程是可行的。）**
9. **HTTPS 门户路径曾长期未验证**：直到 2026-10-13 才在真机确认端口服务模式在 5667 下失效（见 §5 澄清）。后续任何改动入口/协议/端口的变更，**都必须在 5666 与 5667 两个门户各走一遍**。

### 10.1 2026-10-13 升级流程实测新增（详见 `UPGRADE_FLOW_VERIFICATION_2026-10-13.md`）

10. **fnOS 无本地 FPK 就地升级能力**（P0 认知项）：`install/task` 对已存在的 `appname` 恒返回 `10236`，与版本/运行状态无关。**新包上线 = 卸载 → 安装**；所有发布说明与用户指引都必须按此表述。
11. **开机后看门狗失效**（P1，见 §5.4）：systemd 单元抢跑 → `main start` 提前返回 → `start_watchdog` 未执行。修复方向见 §5.4。
12. **卸载不删 `/usr/local/sbin/lsa-fnos-start`**（P1）：两次卸载均残留。
13. **`uninstall_init` 的 `|| exit 1` 过于激进**（P1）：`purge_package` 内 `sudo dpkg --purge "$package" || exit 1` 会让单点失败导致**后续清理全部跳过**，留下半卸载状态（deb 仍 `ii`、`/opt/lsi` 仍在）。应改为记录到 `$TRIM_TEMP_LOGFILE` 后继续。
14. **卸载偶发中止**（P2）：首次卸载以 `10392 = ErrCodeUninstallInitException` 中止，插桩复跑两次均完整成功，未能复现。appcenter `error.log` 中反复出现 `hook error ... nil pointer dereference`，推测为其钩子执行器不稳定。
15. **`ExecStop` 缺 `cd`**（P2，见 §5.4）：单元每次停止都变 `failed`。
16. **配置保留职责落空**（P2）：`upgrade_*` 是死代码，配置保留应迁到 `uninstall_init`（备份到 `$TRIM_PKGVAR`）+ `install_callback`（还原）。
17. **厂商硬编码字符串无法本地化**（P3，非本项目缺陷）：`Gateway - Authenticate`、`Load More` 等不在 `message_en.js` 键集中，被编译进 GWT 模块，`message_zh.js` 覆盖层无法触及。
18. **登录跳转依赖 Navigation API**（P2，见 `LOGIN_NAV_FIX_2026-10-13.md`）：CGI 注入的拦截器用 `navigation.navigate` 事件 + `event.intercept()` 兜住 GWT 的 `location.href` 赋值，需浏览器/WebView 支持 Chrome 102+（fnOS 桌面 WebView 满足）。用户在地址栏手输 `/ui/...` 仍会 404（预期行为）。真机除手工 SFTP 部署外，已重新 `fnpack build` 双包并核对包内 `ui/cgi_proxy.py` 与真机部署版 md5 一致（中文包 `9dfee3c8…`）。

---

## 11. 维护约定

- 改动 `cmd/` 脚本后**必须同时改中英两包**，除 §6 明确的三处差异外保持同步。
- 任何会写入 `$LSA_HOME/conf/LSA.conf` 的改动，都要考虑 LSA 后端初始化时会重写默认值 —— 权限相关设置需在**后端就绪后**再刷。
- 本地化资源是"双写"（zh-CN 与 en-US 各一份），新增资源文件时不要只写一处。
- 改动 `cgi_proxy.py` 时同步核对 `CGI_BASE` 与 manifest `appname`。
- 交付前在真机走一遍：安装 → 启动 → 应用内入口 → 登录 → 改端口 → 重启 → 卸载清理。
- **发布/交付时不要承诺"就地升级"**：fnOS 不支持本地 FPK 升级，用户必须先卸载再安装（见 §8 顶部提示）。发布说明里应写明这一点。

---

## 12. 变更记录

- **2026-10-13（接管）**：项目接管。建立 git 版本控制（分支 `main`，本地身份 `LSA fnOS Maintainer`）；新增 `.gitignore`（排除 `*.fpk`、fnpack 可执行文件、`tools/skill/bin/` 平台二进制）；撰写本交接文档；记录 §10 风险清单。提交 `b1f9650`。
- **2026-10-13（学习规范）**：精读 `reference-snapshot/` 门户文档与 JS SDK，产出 `FNOS_DEV_GUIDE.md`（15 节技能手册）。提交 `012a2c0`。
- **2026-10-13（真机验证）**：在 `<NAS_IP>` 完成整体验证，产出 `VERIFICATION_REPORT_2026-10-13.md`。提交 `ae36597`。
- **2026-10-13（修复 HTTPS 入口）**：定位并修复"HTTPS(5667) 打开应用空白破图"。根因是端口服务模式在 HTTPS 门户下把 iframe 指向无 TLS 的 2463；改用 index.cgi 同源路径入口。同步更新 `app/ui/config`（中英双包）、`FNOS_DEV_GUIDE.md` §4/§14、`HANDOVER.md` §5/§10，新增 `HTTPS_ACCESS_FIX_2026-10-13.md`。提交 `5ed44cc`。
- **2026-10-13（升级流程实测）**：用新构建的 FPK 在真机走完整部署链路，得出「fnOS 无本地 FPK 就地升级能力（`10236`），实际路径为卸载 → 安装」的结论；安装后逐项验证（注册表自动刷新为 CGI、本地化落地、双门户渲染）全部通过；并发现开机看门狗失效、卸载残留 `lsa-fnos-start`、`uninstall_init` 的 `|| exit 1` 过于激进、`ExecStop` 缺 `cd`、`upgrade_*` 属死代码等 7 项新问题。新增 `UPGRADE_FLOW_VERIFICATION_2026-10-13.md`、`docs/upgrade-flow/`；更新本文件 §5.4/§8/§10/§10.1。
- **2026-10-13（修复登录跳转 404）**：修复"登录后跳到 fnOS 404"。根因是 GWT 用 `location.href = '/ui/core/index.html?...'` 做跨文档赋值，而 `href` 是 Location 实例上的 `[LegacyUnforgeable]` 属性、原型上无描述符，原有拦截器补不进去。改用 Navigation API `navigate` 事件 + `event.intercept()` 兜底（带 `/ui/` 前缀白名单与 `location.replace` 兜底），删除 `location.href` 死代码，`rewriteUrl` 增加 `normalizeToPath` 归一化。中英双包同步（仅 `CGI_BASE` 不同）。真机实测完整登录闭环（入口 → core 页 → server 控制台，控制器 PERC H740P 状态"最佳"）。部署：先手工 SFTP 替换 `/vol1/@appcenter/lsa/ui/cgi_proxy.py` 完成验证，再重新 `fnpack build` 双包并核对包内该文件 md5 与真机一致（中文包 `9dfee3c8…`，新 `lsa.fpk` md5 `ca4b9abb…`、`lsaen.fpk` md5 `48d1a8e9…`）。新增 `LOGIN_NAV_FIX_2026-10-13.md`；更新本文件 §5.1、§10.1、§12。
