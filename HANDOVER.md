# LSI Storage Authority for fnOS — 项目交接文档

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

## 5. 移植机制详解

### 5.1 同源代理（解决"fnOS 不允许第三方应用加 nginx 路由"）

LSA 是 GWT 应用，使用 `/ui/core/index.html`、`/LSI/Storage/MR/API/...` 这类**原点绝对路径**导航，这些路径在 fnOS 域名下不存在。fnOS 又不允许第三方应用往自身 nginx 加 location。

解法：`app/ui/index.cgi` 拉起 `cgi_proxy.py`，把 LSA 页面代理到 `/cgi/ThirdParty/lsa/index.cgi/` 下，并对**每个 HTML 响应**：

1. 注入 `<base href>`，镜像原文档目录（GWT 资源是相对引用）；
2. 注入 URL 拦截器，改写 `<a href>`、`XMLHttpRequest.open`、`fetch`、`location.assign/replace/href`、`window.open`，把原点绝对路径拉回代理前缀；
3. 剥离 `X-Frame-Options` / `Content-Security-Policy`，允许 iframe 内嵌。

> 修改代理逻辑时，`CGI_BASE` 必须与 manifest 的 `appname` 对应：中文包 `/cgi/ThirdParty/lsa/index.cgi/`，英文包 `/cgi/ThirdParty/lsaen/index.cgi/`。

### 5.2 桌面入口

`app/ui/config` 定义 `.url` 条目：`type=iframe`、`port=${wizard_web_port}`、`url=/ui/remoteserver/index.html`。`manifest` 的 `desktop_applaunchname` 指向它（`lsa.main` / `lsaen.main`）。

### 5.3 全权限模式

厂商默认 `readOnly=1`，登录后隐藏 RAID 操作菜单。`install_callback`、`main start`、`config_init`、`upgrade_callback` 四处都会把 `LSA.conf` 刷为：

```
readOnly = 0
full_access_groups = Administrators,fnos-admin
readonly_access_groups =
```

注意 `main start` 在**后端就绪后**再刷一次，因为 LSA 后端初始化时会重写这些默认值。

### 5.4 幂等启动与看门狗（解决"真机枚举慢 / 端口被占导致启动误报失败"）

- 厂商 init 脚本在 nginx 或 LSA 已存在时返回失败；fnOS 开机竞争场景很常见。
- `install_callback` 写入 `/usr/local/sbin/lsa-fnos-start`（幂等包装器）与 `lsistorageauthority.service`（`Type=oneshot`、`RemainAfterExit=yes`、`TimeoutStartSec=180`）。
- 包装器逻辑：先等 `slpd` 的 UDP 427 端口就绪（必要时自行拉起 `/opt/lsi/LSA/libs2/slpd`）；nginx 端口未开才启动；首次启动前清掉残留 LSA；最后 `./LSA -start`。
- `cmd/main` 启动后启动 10s 轮询看门狗，后端掉线自动拉起；启动等待上限 `LSA_START_TIMEOUT`（默认 120s），不再用旧的 5 秒固定窗口误判失败。
- 环境变量：`LD_LIBRARY_PATH="/opt/lsi/LSA/libs:/opt/lsi/LSA/libs2:$LSA_HOME/lib:$LSA_HOME/bin:$LSA_HOME/plugins"`。

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

- **安装**：`install_init` 校验架构 → 释放文件 → `install_callback` 依次 `dpkg -i`（lib_utils2 → lib_utils → 主包）→ 写 `fnos_ports.conf` → 装本地化 → 建兼容软链 → 修 `LSA.conf` → 写 systemd 单元并 `enable`。
- **端口**：`install_callback` 把 nginx.conf 的 `nginx_default` / `LSA_Default` 占位符替换成向导端口，并改 `LSA.conf` 的 `listening_port` / `client_listening_port`。
- **升级**：`upgrade_init` 备份 `LSA.conf`、`nginx.conf`、`smtpServer`、`key.store`、`value.store`、`managedservers/`、`monitor/` 到 `$TRIM_TEMP_UPGRADE_FOLDER` → `upgrade_callback` 恢复并重刷本地化与权限。
- **卸载**：`uninstall_init` 停 systemd 单元、停进程与 nginx、`dpkg --purge` 三个包、删 `/opt/lsi` 与 `/opt/lsi/LSA`、`rmdir /opt/lsi`。兼容软链用 `remove_owned_symlink` 只删"确实指向本项目目标"的链接，避免误删其他包的同名系统软链。

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

---

## 11. 维护约定

- 改动 `cmd/` 脚本后**必须同时改中英两包**，除 §6 明确的三处差异外保持同步。
- 任何会写入 `$LSA_HOME/conf/LSA.conf` 的改动，都要考虑 LSA 后端初始化时会重写默认值 —— 权限相关设置需在**后端就绪后**再刷。
- 本地化资源是"双写"（zh-CN 与 en-US 各一份），新增资源文件时不要只写一处。
- 改动 `cgi_proxy.py` 时同步核对 `CGI_BASE` 与 manifest `appname`。
- 交付前在真机走一遍：安装 → 启动 → 应用内入口 → 登录 → 改端口 → 重启 → 卸载清理。

---

## 12. 变更记录

- **2026-10-13**：项目接管。建立 git 版本控制（分支 `main`，本地身份 `LSA fnOS Maintainer`）；新增 `.gitignore`（排除 `*.fpk`、fnpack 可执行文件、`tools/skill/bin/` 平台二进制）；撰写本交接文档；记录 §10 风险清单。
