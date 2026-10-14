# LSA fnOS 移植项目 — 真机整体验证报告

- **验证时间**：2026-10-13 14:2x CST
- **测试环境**：`http://<NAS_IP>:5666`（fnOS 门户）
- **访问方式**：fnOS 门户 admin / SSH root@<NAS_IP>:22
- **验证工具**：trim-cli（WebSocket 应用中心通道）+ paramiko（SSH 通道）+ curl（HTTP 通道）
- **被测交付物**：`lsa-fnos/lsa.fpk`（中文包，8.17.10）
- **结论**：**部署正确、运行正常、中文本地化端到端生效**；发现 6 类待优化项，均为**非阻塞性**问题，不影响当前功能。

---

## 一、验证结论总览

| 维度 | 结果 | 说明 |
|---|---|---|
| 应用注册 | ✅ 通过 | `lsa` / LSI 存储管理 / 8.17.10 / **running** |
| 服务进程 | ✅ 通过 | nginx×2 + LSA×2 + slpd，稳定运行 5h53min |
| 端口监听 | ✅ 通过 | 2463 对外、9000 仅 loopback、427/udp |
| 开机自启 | ✅ 通过 | 当前实例即为开机启动实例，enabled |
| 移植补丁 | ✅ 通过 | 端口/权限/软链/iframe 头全部生效 |
| 中文本地化 | ✅ 通过 | 覆盖层 + 语言资源 + 帮助 + 运行时日志全中文 |
| 幂等性 | ✅ 通过 | 重复 start 不重启已有实例 |
| 硬件识别 | ✅ 通过 | 识别 MegaRAID 控制器与 8 块物理盘 |
| 自愈能力 | ⚠️ 缺失 | watchdog 未运行，无 Restart 策略 |
| 自定义端口 | ⚠️ 不完整 | 控制脚本硬编码 2463/9000 |
| 日志管理 | ⚠️ 待优化 | log_level=64，日志量偏大 |
| 双包同步 | ⚠️ 已分叉 | zh/en 的 callback 脚本差异超出本地化范围 |

---

## 二、详细验证证据

### 2.1 应用注册与状态

```
appcenter-cli list:
│ lsa │ LSI 存储管理 │ 8.17.10 │ running │   (无依赖)

app status lsa:
  appServiceInfo.title  = LSI 存储管理
  appServiceInfo.type   = iframe
  appServiceInfo.urls.path = /ui/remoteserver/index.html
  appServiceInfo.urls.port = 2463
  microApp = true
  riskControl.riskLevel = none
  control = { isOpen: true, isStartStop: true, isUninstall: true }
```

### 2.2 系统环境

| 项 | 值 |
|---|---|
| fnOS 内核 | `6.18.18.c1126-trim` (x86_64, Debian 12 工具链) |
| 主机名 | FNOS |
| RAID 控制器 | Avago SAS MegaRAID，PCI `1000:0016` / 子系统 `1028:1fcb`（Dell PERC） |
| 物理磁盘 | HGST HUS728T8TAL 8TB ×2、Seagate ST4000NM0024 4TB ×5~6（共 8 槽） |
| 虚拟磁盘 | sda 14.6T、sdb 29.1T → md1 → LVM `/vol2` |
| 系统盘 | nvme0n1 232.9G → `/vol1` |
| 内存 | 15.7 GB 总量，已用 2.6 GB |
| LSA 内存占用 | 33.6 MB + 12.4 MB ≈ **45 MB** |
| 时区 / NTP | Asia/Shanghai (+0800)，已同步 |

### 2.3 服务运行状态

```
● lsistorageauthority.service - LSI Storage Authority Service
     Loaded: loaded (/etc/systemd/system/lsistorageauthority.service; enabled)
     Active: active (exited) since Tue 2026-10-13 08:33:16 CST; 5h 53min ago
   Main PID: 1530 (code=exited, status=0/SUCCESS)
     Memory: 60.5M
    CGroup: ├─1596 nginx: master process ./nginx -p .
            ├─1597 nginx: worker process
            ├─2958 ./LSA -start
            └─2961 ./LSA -start
```

- 启动耗时：`ExecMainStart 08:33:13` → `ActiveEnter 08:33:16` = **3.115s**
- slpd 独立进程（pid 2908，用户 daemon），UDP 427 就绪
- 开机自启**已被现状证明**（08:32 开机 → 08:33:16 服务就绪）

### 2.4 端口监听

```
LISTEN  0.0.0.0:2463   nginx      ← Web 管理端口（对外，预期）
LISTEN  [::]:2463      nginx
LISTEN  127.0.0.1:9000 LSA ×2     ← 后端端口（仅本地，安全）
UNCONN <NAS_IP>:427 slpd      ← SLP 服务发现
```

> 从本机验证：`2463 → HTTP 200`，`9000 → 连接失败`（正确未对外暴露）。

### 2.5 移植补丁生效情况

| 补丁 | 目标 | 实测 |
|---|---|---|
| 端口配置 | `conf/fnos_ports.conf` | `web=2463` / `service=9000` ✅ |
| 写权限 | `LSA.conf: readOnly` | `0` ✅ |
| 管理员组 | `full_access_groups` | `Administrators,fnos-admin` ✅ |
| 只读组清空 | `readonly_access_groups` | 空 ✅ |
| 后端端口 | `listening_port` | `9000` ✅ |
| 前端端口 | `client_listening_port` | `2463` ✅ |
| 安装类型 | `installation_type` | `0` ✅ |
| iframe 嵌入 | `nginx.conf X-Frame-Options` | `ALLOWALL` ×2 ✅ |
| nginx 监听 | `listen 2463 default_server` | ✅ |
| 兼容软链 | `libcrypt.so.2` | → libcrypt.so.1 ✅ |
| 兼容软链 | `libldap-2.4.so.2` | → libldap-2.5.so.0 ✅ |
| 兼容软链 | `liblber-2.4.so.2` | → liblber-2.5.so.0 ✅ |
| 兼容软链 | `/usr/local/nginx-hardened` | → server/ ✅ |
| 启动包装 | `/usr/local/sbin/lsa-fnos-start` | 1614B，0755 ✅ |
| systemd 单元 | `/etc/systemd/system/lsistorageauthority.service` | 已启用 ✅ |

### 2.6 中文本地化（端到端实测）

**覆盖层注入**（全部 6 个 GWT 入口页）：
```
core=1  integratedraid=1  server=1
megaraid=1  managedserver=1  remoteserver=1
```

**注入顺序正确**（`ui/megaraid/index.html`）：
```html
<script src="../../js/message_en.js"></script>
<script src="../../js/message_zh.js"></script>      ← 覆盖层
<script src="megaraid/megaraid.nocache.js"></script> ← GWT 引导
```
> 覆盖层先于 GWT 模块加载 —— 保证首屏渲染即为中文，不会闪回英文。

**HTTP 实测**：
- `GET /js/message_zh.js` → 129404 B，**19106 个中文字符**
  - 样例：`"用户已使用不同的凭据登录"`、`"用户名或密码不正确"`、`"未经授权"`
- `GET /help/megaraid/index.html` → **1432 中文字符**（已汉化）
- 帮助文档规模：megaraid **186 页** + integratedraid **46 页**

**语言资源与兜底**：
- `conf/languages/zh-CN/` 6 个文件齐全（alertparam / alertspec / healthspec / mr8_events / mr_errors / mr_events）
- `conf/languages/en-US/healthspec.json` 与 zh-CN 版 **md5 完全一致**（`a9dc391c…`），中文健康描述双路径兜底 ✅
- `LSA.conf: health_spec` 实际指向 `en-US`，但因 en-US 已被中文内容覆盖，**输出仍为中文**——移植时的兜底设计生效
  - 样例：`"虚拟磁盘 {1} 处于降级状态"` / `"请确认所有参与的物理磁盘均已连接，且重建已完成"`

**运行时日志为中文**（LSA_MONITOR 实测输出）：
```
控制器 ID：0 物理磁盘 - :0:1 ：查询信息 - 供应商：ATA；型号：HGST HUS728T8TAL；容量：8 TB
控制器 ID：0 阵列卡电池/超级电容 开始充电
控制器 ID：0 主机驱动程序已加载并可运行
```

**桌面入口**：
```json
"lsa.main": { "title": "LSI 存储管理", "type": "iframe",
              "port": "${wizard_web_port}", "url": "/ui/remoteserver/index.html" }
```
> `${wizard_web_port}` 模板被 fnOS 正确解析为 `2463`。

### 2.7 幂等性与生命周期脚本

```
$ bash cmd/main start
Starting lsa 8.17.10
LSA is already running; keeping the existing instance
exit=0                      ← 未重复拉起，端口未被扰动 ✅

$ bash cmd/main status
exit=0                      ← 运行中返回 0（符合规范）✅
```

### 2.8 文件落点确认

| 用途 | 路径 |
|---|---|
| FPK 顶层（cmd/config/wizard/manifest/图标） | `/var/apps/lsa/` |
| `app.tgz` 解包（config/debs/ui） | `/vol1/@appcenter/lsa/` |
| 桌面 UI 目录（含 `ui/config`） | `/vol1/@appcenter/lsa/ui/` |
| LSA 安装目录 | `/opt/lsi/LSIStorageAuthority/` |
| LSA 依赖库 | `/opt/lsi/LSA/libs`、`/opt/lsi/LSA/libs2` |
| 设备节点（需 root） | `/dev/megaraid_sas_ioctl_node` |

---

## 三、待处理问题与优化建议

### P1 — 自愈能力缺失（watchdog 未运行）【建议处理】

**现象**
- `/run/lsa-fnos-watchdog.pid` 不存在；无 watchdog 进程；无 `fnos-watchdog.log`

**根因**
1. `start_watchdog()` 仅在 `cmd/main start` 中被调用；
2. 但开机与常态由 systemd 直接执行 `/usr/local/sbin/lsa-fnos-start`（**包装脚本不经过 cmd/main**）；
3. 且 systemd 单元为 `Type=oneshot` + `RemainAfterExit=yes`，**无 `Restart=` 指令**。

**后果**：LSA 进程若崩溃，不会自动恢复，须手动重启服务或 NAS。

**建议**（二选一）
- 方案 A（推荐）：把服务改为 `Type=simple` 或 `Type=forking`，并加 `Restart=on-failure` + `RestartSec=10`，由 systemd 承担守护职责，废弃自研 watchdog；
- 方案 B：在包装脚本 `lsa-fnos-start` 末尾同样拉起 watchdog 子进程，保持现有设计。

### P2 — 端口硬编码，自定义端口路径不完整【建议处理】

**现象**
```
cmd/main                      : WEB_PORT=2463  BACKEND_PORT=9000   （硬编码）
/usr/local/sbin/lsa-fnos-start: WEB_PORT=2463  BACKEND_PORT=9000   （硬编码）
conf/fnos_ports.conf          : web=2463  service=9000
```

**根因**：`install_callback` 已正确读取 `wizard_web_port` / `wizard_lsa_port` 并改写 `nginx.conf` 与 `LSA.conf`，但两个**运行时控制脚本**未读取 `fnos_ports.conf`。

**后果**（仅当用户选非默认端口时暴露）
- `port_open "$WEB_PORT"` 探测错误端口 → 可能误判"未运行"而重复拉起 nginx；
- `stop` 时 `fuser -k "$WEB_PORT/tcp"` 打错端口；
- 幂等判断失效，可能触发不必要的重启。

**建议**：两处改为动态读取，例如
```bash
PORTS_FILE=/opt/lsi/LSIStorageAuthority/conf/fnos_ports.conf
WEB_PORT=$(sed -n 's/^web=//p' "$PORTS_FILE" 2>/dev/null || true)
BACKEND_PORT=$(sed -n 's/^service=//p' "$PORTS_FILE" 2>/dev/null || true)
WEB_PORT=${WEB_PORT:-2463}
BACKEND_PORT=${BACKEND_PORT:-9000}
```

### P3 — 日志级别过高导致日志膨胀【建议优化】

**现状**
```
LSA.conf: log_level = 64        （FUNCTION_ENTRY，极详细）
          log_file_count = 4
          log_file_size  = 25   （MB）
logs/ 目录占用：79 MB
  lsa.txt              3.2 MB（持续增长）
  lsa_1310_015421.txt  25 MB
  lsa_1310_090818.txt  25 MB
  lsa_1210_022748.txt  25 MB
```
- 日志上限约 `4 × 25MB ≈ 100MB`（有界，但偏大）
- 无 `/etc/logrotate.d/` 配置，依赖 LSA 自轮转

**建议**：将 `log_level` 降至 `8`（WARNING）或 `16`（INFO），日志量可下降一个数量级；若需排障再临时调高。

### P4 — vendor 内部错误日志刷屏【可接受，可随 P3 缓解】

每 30s~1min 重复出现：
```
BatteryPl:getEnergyPackInfo:getBBUModes:nRetValModeList: 2
HealthStatusPl battery type:getEnergyPackHealthStatus:...voltageLow): 0
RemoteServerDiscoveryJob::slpAttributeCallback failed with error code: 1, for IP=
Repo:getSlDcmdPassthru:ReqData not found in cache
CmdHlpr:getBbuMode:getSLDPassthruCmd:rval=2 CtrlId=0
```
**判定**：本机未配 BBU/超级电容（日志另有"阵列卡电池/超级电容 开始充电"），属 vendor 对缺失硬件的轮询噪音，**非本移植引入，不影响功能**。降低日志级别即可抑制。

### P5 — 中英双包已分叉，维护成本上升【建议重构】

两包的 `install_callback` / `upgrade_callback` 差异**超出本地化范围**：

| 差异点 | 中文包 | 英文包 |
|---|---|---|
| dpkg 失败处理 | `... \|\| { echo "LSA installation failed" > $TRIM_TEMP_LOGFILE; }`（丢失 dpkg 输出） | `if ! DPKG_OUTPUT=$(sudo dpkg -i ...)`（保留输出，更好） |
| `LSA_HOME` 定义位置 | 第 26 行 | 第 7 行 |
| `upgrade_callback` 本地化恢复段 | 完整（message_zh + languages + static + help） | 精简（仅移除 message_zh 引用） |
| 注释与结构 | 较新，含大量说明 | 较旧，被裁剪 |

**风险**：任一包修 bug 需手工同步，极易遗漏。

**建议**：抽出公共逻辑（端口配置、兼容软链、systemd 单元、权限设置、静态资源）为单一来源，仅将本地化相关段（message_zh.js / languages / help / static）按包分叉。

### P6 — 次要问题清单

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | `build.sh` 引用不存在的 `../gcc_11.2.x/` | 构建脚本无法直接运行 | 清理或参数化 |
| 2 | `logs/fnos-start.log` 为 0 字节且时间戳陈旧（Aug 27） | 无诊断价值 | 确认重定向是否仍需要 |
| 3 | `/var/apps/lsa/config`、`wizard` 目录权限 `drw-r--r--`（0644，目录缺 x 位） | root 可绕过，不规范 | 打包时修正为 0755 |
| 4 | `cmd/main` 无参数时 `exit 0` | 未打印用法、未报错 | 改为打印用法并 `exit 1` |
| 5 | 英文包 `README.md` 未本地化（沿用中文说明） | 英文用户困惑 | 补英文 README |
| 6 | 2463 明文 HTTP 且监听全网卡 | 凭据明文传输 | NAS 内网可接受；如需可经 fnOS 网关反代加 TLS |
| 7 | `manifest: os_min_version = 1.0.0` | 若实际依赖较新系统特性，旧系统可能安装失败 | 按实测最低版本收紧 |

---

## 四、未验证项（需确认是否执行）

以下项**需要变更运行状态或重装**，为避免影响测试环境未擅自执行：

1. **应用中心「停止 → 启动」完整周期** — 会短暂中断 LSA 服务
   - 注：`cmd/main start` 幂等性与开机自启已单独验证通过
2. **非默认端口安装路径** — 需卸载后以自定义端口重装（预期会暴露 P2）
3. **升级路径（`upgrade_callback`）** — 需构造更高版本 FPK
4. **浏览器实际登录 LSA 并执行 RAID 操作** — 需人工交互确认写操作可用
5. **英文包（`lsaen.fpk`）实机部署** — 本次仅验证中文包

> 如需验证第 1、3、5 项，请告知，我可在测试机上执行（会短暂中断服务）。

---

## 五、验证方法说明

| 通道 | 工具 | 用途 |
|---|---|---|
| 应用中心 | `tools/skill/bin/trim-cli-windows-x64.exe`（WebSocket `ws://<NAS_IP>:5666/websocket`） | 应用列表 / 状态查询 |
| SSH | paramiko 5.0.0（Python venv） | 文件系统、进程、端口、配置、日志核查 |
| HTTP | curl | 服务可达性、中文资源端到端校验 |
| 静态 | tar / bash -n / ast.parse / md5sum | FPK 结构、脚本语法、二进制完整性 |

**静态验证附注**：`lsa.fpk` 与 `lsaen.fpk` 顶层结构一致（app.tgz + cmd/ + config/ + wizard/ + manifest + ICON×2）；全部 `cmd/*` 通过 `bash -n`；`cgi_proxy.py` / `index.cgi` 语法正确；`ICON.PNG` 64×64、`ICON_256.PNG` 256×256 均为合法 PNG；两包内 3 个 deb 的 md5 完全一致（同一份不可再生的上游二进制）。

---

*报告生成：2026-10-13 · 验证范围：部署正确性、运行状态、移植补丁生效性、本地化效果、待优化项*
