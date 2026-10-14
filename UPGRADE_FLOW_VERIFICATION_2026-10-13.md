# LSA for fnOS — 升级 / 卸载流程真机验证报告

**日期**：2026-10-13
**测试机**：`<NAS_IP>`（fnOS 1.2.0800，内核 `6.18.18.c1126-trim`）
**被测包**：`lsa-fnos/lsa.fpk`（28,125,050 B，version 8.17.10）
**测试工具**：`tools/skill/bin/trim-cli-windows-x64.exe`（WebSocket → fnOS）、paramiko（SSH）、无头 Chrome + 自写 CDP 客户端

---

## 1. 结论摘要

| # | 问题 | 结论 |
|---|------|------|
| 1 | **fnOS 是否支持用本地 FPK 就地升级？** | ❌ **不支持**。`POST /app-center/v1/install/task` 只要 `appname` 已存在就返回 `10236 = ErrCodeInstalledException`（前端文案「应用已安装」），**与版本号无关、与运行状态无关**。 |
| 2 | **那真实部署路径是什么？** | ✅ **卸载 → 全新安装**。已在真机完整走通并逐项验证通过。 |
| 3 | **改 `app/ui/config` 后重装能否生效？** | ✅ **能，且无需手工改库**。安装流程自动把 CGI 路径写入两处注册表（`appcenter.app_service` 与 `trim_sac.entry`）。 |
| 4 | **`upgrade_init` / `upgrade_callback` 会被执行吗？** | ❌ **不会**，属**死代码**（见 §4.4）。配置保留能力因此完全落空。 |
| 5 | **卸载是否干净？** | ⚠️ **脚本逻辑本身能卸干净**（插桩复跑验证通过），但存在**偶发中止**（`10392`）与**固定残留**（`lsa-fnos-start`）。 |
| 6 | **开机自愈（watchdog）是否生效？** | ❌ **开机场景下失效**。systemd 单元抢跑导致 `cmd/main start` 提前返回，watchdog 未启动（有日志实证，见 §4.5）。 |
| 7 | **应用功能是否正常？** | ✅ 5666 与 5667 双门户均正常渲染 LSA 中文界面（版本 `008.017.010.000`）。 |

---

## 2. 测试环境与前置备份

- 升级前完整备份：`/root/lsa-upgrade-backup-20261013`（109 MB）——含 `/opt/lsi` 完整 tar 包（52,622,114 B）、`conf/`、`bin/`、`nginx.conf`、`appui/`、`app_service.sql`、`entry.sql`、`lsistorageauthority.service`、`lsa-fnos-start`、`lsa-appdir.tgz`。
- 安装命令（含向导自定义参数，缺参数会报 `custom wizard parameters` 缺失）：

```bash
trim-cli --host <NAS_IP> --port 5666 --scheme ws --allow-insecure-ws \
  app install-fpk "C:\LSA_Linux\lsa-fnos\lsa.fpk" --volume-id 1 \
  --custom-parameters '[{"key":"wizard_web_port","value":"2463"},
                        {"key":"wizard_lsa_port","value":"9000"},
                        {"key":"wizard_install_mode","value":"gateway"}]' \
  --cancel-on-failure --yes
```

---

## 3. 就地升级为什么走不通（核心发现）

### 3.1 现象

三次尝试全部失败，错误完全一致：

```
Error: app-center request POST /app-center/v1/install/task failed:
       ({"code":10236,"data":null,"msg":""})
```

| 尝试 | 包版本 | 应用状态 | 结果 |
|------|--------|----------|------|
| 1 | 8.17.10（同版本） | running | 10236 |
| 2 | 8.17.10（同版本） | stopped | 10236 |
| 3 | **8.17.11（已升版本号）** | running | 10236 |
| 4 | **8.17.11（已升版本号）** | stopped | 10236 |

> 第 3/4 次是专门构建的版本号递增包（`manifest` 内嵌 `version = 8.17.11`，已解包核对），用于排除"同版本限制"假设。结果证明**与版本无关**。

### 3.2 错误码语义（从门户 bundle 提取）

```js
e[e.ErrCodeInstallingException = 10235] = `ErrCodeInstallingException`,
e[e.ErrCodeInstalledException  = 10236] = `ErrCodeInstalledException`,
...
[$.ErrCodeInstalledException, `应用已安装`],
```

appcenter 侧日志同样明确：

```
level=error msg="app already installed" appName=lsa class=install version=8.17.11
level=error msg="response error: &vo.Result{Code:10236, ...}"
```

### 3.3 有没有别的升级入口？

- `trim-cli app update <app> --version <v>` 存在，但走的是 **云端下载**（`POST /v1/download/task`），本地 FPK 不可用：

  ```
  Error: app-center request POST /app-center/v1/download/task failed: ({"code":10030,"msg":""})
  ```
  `--package-type local` 同样走 `download/task`，结果一致。

- 门户前端 bundle（`/usr/trim/www/assets/index-B0cXg_s1.js`，与门户共用同一份）中检索 `upgrade` 端点：**没有任何升级专用 API**；`install/task` 的请求体里也没有 `isUpgrade` / `force` / `overwrite` 之类的开关（唯一的 `overwrite` 属于文件操作枚举，与安装无关）。

**⇒ 结论：本 fnOS 版本对"本地 FPK"只提供安装语义，不提供升级语义。新包上线必须走「卸载 → 安装」。**

---

## 4. 卸载 / 安装链路的实测结果

### 4.1 卸载：脚本逻辑本身能卸干净

首次卸载（15:22:28）出现：

```
level=error msg="uninstall script error" appName=lsa class=uninstall error="10392:"
```

`10392 = ErrCodeUninstallInitException`（文案「执行脚本出错且原因未知」），即 `uninstall_init` 返回非零。其后果是可观察的：**软链已删、systemd 已 disable，但 3 个 deb 仍是 `ii`、`/opt/lsi` 仍在、systemd 单元文件仍在** —— 与"脚本执行到 `dpkg --purge ... || exit 1` 就中止"的行为完全吻合。

为定位，我把 `uninstall_init` 替换为**逐行 trace 版本**（`set -x` + `exec > /root/...log`），分别以「放宽 `exit 1`」和「**保留原版逻辑不变**」两种形态各跑一次卸载：

- 两次**全部步骤成功**：`dpkg --purge` 三个包退出码均为 `0`，`/opt/lsi` 被完全删除，单元文件被删除。
- 关键行输出示例：

  ```
  + sudo dpkg --purge lsistorageauthority   → rc=0
  + sudo dpkg --purge lsa-lib-utils         → rc=0
  + sudo dpkg --purge lsa-lib-utils2        → rc=0
  + sudo rm -rf /opt/lsi/LSIStorageAuthority
  + sudo rmdir /opt/lsi
  + sudo rm -f /etc/systemd/system/lsistorageauthority.service
  ```

- 独立验证 `prerm` 本身无问题：`bash -x .../lsistorageauthority.prerm remove` → `prerm_exit=0`。

**⇒ 首次的 `10392` 未能复现，判定为偶发。** appcenter 的错误日志中反复出现同源的钩子运行器缺陷（`msg="hook error" ... error="runtime error: invalid memory address or nil pointer dereference"`，2026-08-24 ~ 08-27 共 10 余次），说明 fnOS 侧的脚本钩子执行器本身不稳定。

> 复现测试完成后，插桩文件已被重新安装的安装流程自动还原（`md5sum` 与原始 `2215c5c978b954fad4c05cc791e07102` 一致），设备无残留。

### 4.2 卸载残留（固定，两次都出现）

`uninstall_init` 删除了 systemd 单元文件，但**没有删除包装器**：

```
-rwxr-xr-x 1 root root 1614  /usr/local/sbin/lsa-fnos-start
```

即"卸载后系统上仍留有一个指向已删除目录的启动脚本"。属应修的固定缺陷。

### 4.3 安装：干净系统与脏系统都能装

| 场景 | 结果 |
|------|------|
| 在**首次卸载残留**（`/opt/lsi` 仍在、deb 仍 `ii`）之上安装 | ✅ 成功 |
| 在**完全干净**（`/opt/lsi` 已删、deb 已 purge）之上安装 | ✅ 成功 |
| 卸载后重新安装（第二次循环） | ✅ 成功 |

### 4.4 `upgrade_init` / `upgrade_callback` 是死代码

由于 fnOS 不存在就地升级路径（§3），这两个脚本**永远不会被调用**。它们原本承担"升级时保留 `LSA.conf` / `nginx.conf` / `key.store` / `value.store` / `managedservers/` / `monitor/`"的职责，现在这部分能力**完全落空**。

后果：一旦卸载流程被修正为"彻底 purge"（§4.1 已证明能做到），**用户配置将在重装时丢失**。目前之所以"看起来没丢"，纯粹是因为首次卸载中止、`/opt/lsi` 被意外保留 —— 属侥幸，不是设计。

**建议**：把配置保留改到正确的位置上：

- `uninstall_init`：先 `tar` 备份 `/opt/lsi/LSIStorageAuthority/conf`（+ `bin/key.store`、`bin/value.store`、`bin/managedservers`）到 `$TRIM_PKGVAR/backup/`，再执行 purge。`$TRIM_PKGVAR`（`/vol1/@appdata/lsa`）在卸载后**依然保留**（实测）。
- `install_callback`：检测到 `$TRIM_PKGVAR/backup/` 存在时还原。
- 或者：保留 `upgrade_*` 脚本作为未来 fnOS 支持升级时的备用，但**不要**把配置安全寄托在它们身上。

### 4.5 开机自愈失效（有日志实证）

`cmd/main` 内置 watchdog（`start_watchdog`，每 10 s 检查 `pgrep -x LSA`，进程没了就拉起）。但它在第 108 行才被调用，而第 77–80 行有一个**提前返回**：

```bash
if port_open "$WEB_PORT" && lsa_running; then
    echo "LSA is already running; keeping the existing instance"
    exit 0        # ← 到不了第 108 行的 start_watchdog
fi
```

同时 `install_callback` 又写了一个 `enabled` 的 systemd 单元（`WantedBy=multi-user.target`）。**开机时两者赛跑**，日志证明 systemd 抢先：

```
2026-10-13T08:33:16  systemd 启动 lsistorageauthority.service（单元 Duration 6h49m13s 佐证）
2026-10-13T08:33:24  appName=lsa class=start  msg="already running"  code=0
                     ↑ cmd/main start 在第 79 行提前返回 → watchdog 从未启动
```

**⇒ 开机后系统处于"无自愈"状态**：LSA 进程一旦崩溃不会被拉起（这正是早前报告里 P1「自愈缺失」的真实成因）。

> 对照：本次"安装后立即启动"的场景下 watchdog **是**运行的（`/run/lsa-fnos-watchdog.pid` = `main start` 子壳 PID），因为单元当时没被 systemd 启动，`main start` 得以走到第 108 行。

**建议（二选一）**：
- **A（推荐）**：删除 systemd 单元，完全交给 fnOS 的 `cmd/main` 生命周期 —— 符合飞牛规范，且避免双启动。
- **B**：保留单元，但把 `main start` 的提前返回改为"先 `start_watchdog` 再返回"，或让 `main start` 直接委托 `systemctl start`。

### 4.6 systemd 单元的 `ExecStop` 有缺陷

单元里的：

```ini
ExecStop=/usr/bin/bash -c 'pkill -TERM -x LSA 2>/dev/null || true; /opt/lsi/LSIStorageAuthority/server/nginx -s stop -p .'
```

缺 `cd`，`-p .` 会解析成 systemd 的工作目录（`/`），于是每次停止都报：

```
nginx: [alert] could not open error log file: open() "./logs/error.log" failed (2: No such file or directory)
[emerg] open() "./conf/nginx.conf" failed (2: No such file or directory)
lsistorageauthority.service: Control process exited, code=exited, status=1/FAILURE
```

结果：**每次停止都会把单元打成 `failed`**。本次安装后单元状态即为 `failed` + `enabled`（`Result=exit-code`），且 `daemon-reload` 不会清除该状态。

修复：`ExecStop=/usr/bin/bash -c 'pkill -TERM -x LSA 2>/dev/null || true; cd /opt/lsi/LSIStorageAuthority/server && ./nginx -s stop -p .'`

### 4.7 `systemd` 与 fnOS 应用模型的关系

`appcenter.app` 表存在 `is_systemd_uint` 列，lsa 实测为 `f`（false）。也就是说 **fnOS 并不认为本应用是 systemd 单元应用** —— 这个单元是本项目自行附加的，脱离了 fnOS 的生命周期管理，因此才出现 §4.5 / §4.6 的一系列不一致。

---

## 5. 安装流程逐项验证（全部通过）

### 5.1 注册表：入口被自动刷新为 CGI 模式 ✅

**这是"改 `app/ui/config` 后重装即可生效"假设的关键验证点 —— 通过。**

```sql
-- appcenter 库
SELECT id, app_id, service_name, url, default_url FROM app_service WHERE service_name LIKE 'lsa%';
69 | 56 | lsa.main | ://${host}/cgi/ThirdParty/lsa/index.cgi/ | ://${host}/cgi/ThirdParty/lsa/index.cgi/

-- trim_sac 库
SELECT id, app_id, url FROM entry WHERE url LIKE '%lsa%';
165 | 56 | {"path":"/cgi/ThirdParty/lsa/index.cgi/"}
```

（id / app_id 每次安装递增：`36/30` → `67/54` → `69/56`，属正常现象。）

### 5.2 服务与端口 ✅

```
LSA=running   slpd=running
LISTEN 127.0.0.1:9000
LISTEN 0.0.0.0:2463 / [::]:2463
```

### 5.3 配置 ✅

```
/opt/lsi/LSIStorageAuthority/conf/fnos_ports.conf : web=2463  service=9000
/opt/lsi/LSIStorageAuthority/installtype          : gateway
                                                      service:x-mgmt.avago:lsa://<NAS_IP>:9000
LSA.conf : listening_port = 9000
           client_listening_port = 2463
           readOnly = 0
           full_access_groups = Administrators,fnos-admin
           readonly_access_groups =
           installation_type = 0
nginx.conf : listen 2463 default_server
             add_header X-Frame-Options "ALLOWALL"
```

> 注：`LSA.conf` 的 `health_spec` 仍指向 `../conf/languages/en-US/healthspec.json`。这是**无害的** —— `install_callback` 刻意把中文 `healthspec.json` 同时写进 `zh-CN` 与 `en-US` 两处，实测两者 `md5` 与源文件完全一致（`a9dc391c438d186c008a4f8baf3cb604`），功能上等价于中文。

### 5.4 中文本地化 ✅

- `message_zh.js` 落地：`/opt/lsi/LSIStorageAuthority/server/html/js/message_zh.js`，`md5 = b3489c55f1b3ac52a5d98fc989941442`，与包内源文件一致。
- 6 个 GWT 模块的 `index.html` 注入计数全部为 `1`：`core` / `integratedraid` / `server` / `megaraid` / `managedserver` / `remoteserver`。
- 注入顺序正确（`message_en.js` → `message_zh.js` → `xxx.nocache.js`）：

  ```html
  <script type="text/javascript" src="../../js/message_en.js"></script>
  <script type="text/javascript" src="../../js/message_zh.js"></script>
  <script type="text/javascript" src="remoteserver/remoteserver.nocache.js"></script>
  ```
- `conf/languages/zh-CN` 与 `en-US` 各含 6 个资源文件（`alertparam.ini`、`alertspec.json`、`healthspec.json`、`mr8_events_spec.ini`、`mr_errors_spec.ini`、`mr_events_spec.ini`）。
- 静态页中文化已落地：`50x.html`、`ui/core/ServerNotReachable.html`、`files/App_statusCode_description.html`、`files/credits.html`；帮助页 `help/integratedraid`、`help/megaraid` 已就位。
- 兼容软链齐全：`libcrypt.so.2`、`libldap-2.4.so.2`、`liblber-2.4.so.2`、`/usr/local/nginx-hardened`。
- `index.cgi` 与 `cgi_proxy.py` 权限均为 `755`。

### 5.5 浏览器端到端（无头 Chrome + CDP）✅

| 门户 | 桌面图标点击 | iframe 实际 src | 结果 |
|------|--------------|-----------------|------|
| `https://<NAS_IP>:5667` | CLICKED | `https://<NAS_IP>:5667/cgi/ThirdParty/lsa/index.cgi/` | ✅ 同源，界面完整渲染 |
| `http://<NAS_IP>:5666` | CLICKED | `http://<NAS_IP>:5666/cgi/ThirdParty/lsa/index.cgi/` | ✅ 同源，界面完整渲染 |

渲染内容抽查（两门户一致）：

```
LSI 存储管理
- v008.017.010.000
版权所有 © 2026 Broadcom Inc. 保留所有权利
远程服务器发现 / Windows / Linux / VMware ESXi
<NAS_IP>  主机名: FNOS  操作系统名称: Linux  操作系统架构: x64
服务器 ID：a0:36:9f:a0:00:4b
操作：重新发现服务器 / 前往管理服务器页面 / 手动发现
```

服务端探活：`5667 = 200 (0.0035s)`、`5666 = 200 (0.0006s)`。

截图归档：`docs/upgrade-flow/`

### 5.6 发现的本地化遗漏（厂商层面，非本项目缺陷）

点开「前往管理服务器页面」后弹出的网关认证框仍有三个英文串：

```
Gateway - Authenticate      （对话框标题）
HOST                        （字段标签）
Load More                   （分页按钮）
```

核查结论：

- `message_en.js` 中**不存在**这三个串对应的键 —— 它们被硬编码在编译后的 GWT 模块里，**无法通过 `message_zh.js` 覆盖层翻译**。
- `"HOST"` 这个键确实存在（en: `"\ HOST"`，zh: `" HOST"`），值相同属有意的技术名词保留。
- 覆盖层键数：zh `2347` vs en `2351`。

**⇒ 属厂商实现限制，本项目侧无可行的修复路径；除非改写 GWT 编译产物。**

---

## 6. 建议修复清单

| 优先级 | 项目 | 建议动作 |
|--------|------|----------|
| **P1** | 开机后 watchdog 失效（§4.5） | 删除 systemd 单元，统一走 `cmd/main`；或让 `main start` 提前返回前先 `start_watchdog` |
| **P1** | 卸载不删 `lsa-fnos-start`（§4.2） | `uninstall_init` 增加 `sudo rm -f /usr/local/sbin/lsa-fnos-start` |
| **P1** | `uninstall_init` 用 `\|\| exit 1` 导致"一处失败全盘中止"（§4.1） | 改为记录到 `$TRIM_TEMP_LOGFILE` 后**继续执行**剩余清理，避免留下半卸载状态 |
| **P2** | `ExecStop` 缺 `cd` 导致单元恒为 `failed`（§4.6） | 补 `cd` 或用绝对 `-p` 路径 |
| **P2** | 配置保留落空（§4.4） | 把保留职责从死掉的 `upgrade_*` 迁到 `uninstall_init`（备份到 `$TRIM_PKGVAR`）+ `install_callback`（还原） |
| **P3** | 文档需注明"升级 = 卸载 + 安装" | `HANDOVER.md` §8、`FNOS_DEV_GUIDE.md` §14 已同步更新 |
| **P3** | 端口硬编码（旧风险 2） | `cmd/main` 与 `lsa-fnos-start` 仍写死 2463/9000；建议从 `conf/fnos_ports.conf` 读取 |

---

## 7. 附录：关键证据位置

| 证据 | 位置 |
|------|------|
| appcenter 安装/卸载日志 | 设备 `/var/log/trim_app_center/info.log` |
| appcenter 错误日志（含 `10236` / `10392`） | 设备 `/var/log/trim_app_center/error.log` |
| 开机竞态证据 | `info.log` 中 `2026-10-13T08:33:24 ... msg="already running" appName=lsa class=start` |
| systemd 单元 `ExecStop` 失败 | `journalctl -u lsistorageauthority.service` |
| 门户前端错误码/API 清单 | `index-B0cXg_s1.js`（已从设备下载） |
| 验证截图 | `docs/upgrade-flow/` |
| 升级前完整备份 | 设备 `/root/lsa-upgrade-backup-20261013` |
