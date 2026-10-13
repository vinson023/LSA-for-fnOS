# 飞牛 fnOS 应用开发技能手册

> 本文档是对 `reference-snapshot/`（飞牛开发者门户文档快照 + `@trimjs/web-app` SDK 0.4.2）的系统化学习成果，用于后续开发与维护 fnOS 应用（尤其是本项目 LSA）。
> 来源：https://developer.fnnas.com/docs/ 与 https://developer.fnnas.com/api/ ，以及本地快照 `reference-snapshot/fnnas-portal/raw/`、`reference-snapshot/npm/trimjs-web-app/`。

---

## 0. 快速索引

| 我要做什么 | 看哪一节 |
| --- | --- |
| 从零做一个应用 | §1 §3 §11 |
| 搞清该用哪种访问方式 | §4 |
| 写/改 manifest | §5 |
| 配权限与资源 | §6 |
| 写启停/安装脚本 | §7 §8 |
| 做安装配置界面 | §9 |
| 打包与安装 | §11 |
| 用开放 API 访问文件/页面 | §12 |
| 对照本项目 LSA 的实现 | §14 |

---

## 1. 开发总览

**三件套**：`fnpack`（开发机打包）→ `.fpk` → `appcenter-cli` / 应用中心（设备上安装）。

**开发前提**：一台专用 fnOS 测试设备（勿用存有重要数据的设备）、一台开发电脑（网络可达设备）、设备管理员权限、至少一个可用存储空间。

**最小流程**：
1. `fnpack create <appname>` 生成项目骨架
2. 改 `manifest`、`config/*`、`cmd/*`、`app/ui/*`
3. `fnpack build` → 生成 `<appname>.fpk`
4. `appcenter-cli install-fpk <appname>.fpk`（或应用中心手动安装）
5. 打开桌面图标验证

---

## 2. 应用包结构与安装后布局

### 包结构（开发期）

```
myapp/
├── manifest                 # 必需：应用描述
├── ICON.PNG                 # 必需：64x64
├── ICON_256.PNG             # 必需：256x256
├── cmd/                     # 必需：生命周期脚本
│   ├── install_init  install_callback
│   ├── main
│   ├── upgrade_init  upgrade_callback
│   ├── uninstall_init uninstall_callback
│   └── config_init   config_callback
├── config/                  # 必需
│   ├── privilege            # 必需：运行身份（合法 JSON）
│   └── resource             # 必需：资源声明（合法 JSON）
├── wizard/                  # 必需（目录存在即可）
│   ├── install  upgrade  uninstall  config
└── app/
    ├── ui/                  # desktop_uidir，入口配置
    │   ├── config
    │   └── images/icon_{0}.png
    ├── www/                 # 静态文件（index.cgi 场景）
    ├── server/              # 后端服务
    └── docker/              # Docker 项目（Compose）
```

### 安装后布局（`/var/apps/{appname}`）

```
/var/apps/{appname}
├── cmd/  config/  manifest  ICON.PNG  ICON_256.PNG
├── target -> /vol{n}/@appcenter/{appname}   # 应用文件与运行资源
├── etc    -> /vol{n}/@appconf/{appname}     # 配置
├── var    -> /vol{n}/@appdata/{appname}     # 持久运行数据
├── tmp    -> /vol{n}/@apptemp/{appname}     # 临时
├── home   -> /vol{n}/@apphome/{appname}     # 用户数据
├── meta  shares/  wizard/
```

> **铁律**：脚本里用 `TRIM_APPDEST` / `TRIM_PKGETC` / `TRIM_PKGVAR` 等变量定位，**不要硬编码路径**。

---

## 3. 关键设计约束（官方明确要求）

- 生命周期脚本要**可重复执行（幂等）**——安装/升级/配置流程都可能被重新执行。
- 静态页面或配置型应用：`ctl_stop=false` 隐藏启停控制。
- 路径、请求参数、用户 ID 一律**视为不可信输入**。
- `index.cgi` 每次请求都启动 CGI 进程，**不支持 WebSocket**；需要常驻服务/WebSocket/流式响应时改用端口服务或统一网关。

---

## 4. 三种访问模型（选择是本项目最关键的决策）

| 维度 | 端口服务 | index.cgi | 统一网关 |
| --- | --- | --- | --- |
| 简单静态页 | 可用 | **适合** | 支持 |
| 常驻服务 | 适合 | 不推荐 | **适合** |
| WebSocket | 支持 | **不支持** | 支持 |
| NAS 登录态 | 与登录态无关 | 调用前校验 | 转发前校验 + 注入用户 Header |
| 性能 | 直连端口 | 每次请求启动 CGI 进程 | 转发到长期运行服务 |
| 常见路径 | `http://host:<port>/` | `/cgi/ThirdParty/{appname}/index.cgi/` | `/app/{appname}` |
| 代码适配成本 | 低 | 低（静态页） | 服务需适配网关路由与鉴权 |

> ⚠️ **端口服务模式在 HTTPS 门户下会失效（本项目踩过的坑）**
>
> 桌面前端把入口解析为 `{host, path, port, protocol}` 后按下式拼 iframe 地址（门户 bundle 中的 `wYe()`）：
>
> ```js
> wYe = (e, t) => {
>   if (!le && t) return t;                                   // full_url 优先
>   if (de && e.fnDomain && e.port) return `https://${e.fnDomain}.${location.host}${e.path}`;
>   let n = e.host || location.hostname,
>       r = e.path || '',
>       i = e.port || location.port;
>   return `${e.protocol || location.protocol.replace(':','')}://${n}:${i}${r}`;
> }
> ```
>
> 注意 `protocol` 与 `port` **缺省时回退到 `location.protocol` / `location.port`**。
> 因此端口服务模式下若应用自己的端口只有明文 HTTP，从 `https://<nas>:5667/` 打开时会得到
> `https://<nas>:<port>/...`，TLS 握手失败（同时触发混合内容拦截），表现为**窗口内容区空白破图**。
>
> - 只走 HTTP 门户（5666）时不会暴露该问题，容易漏测。
> - **需要同时支持 HTTP 与 HTTPS 门户时，应使用 index.cgi（同源路径）或统一网关。**
> - 若坚持端口服务模式，则应用端口必须同时提供 TLS，或把 `protocol` 固定为 `http`
>   （但 HTTPS 门户下仍会被混合内容策略拦截，不可行）。

**统一网关机制**：
- 入口声明 `gatewayPrefix`（`/app/{appname}` 或带子路径）与 `gatewaySocket`（如 `app.sock`，只填文件名，Socket 放在 `target/` 下）。
- 请求 `/app/myapp` → fnOS 校验会话 → 转发到 `/var/apps/myapp/target/app.sock`。
- 网关**忽略** `protocol` 与 `port`。
- 认证通过后注入 Header：`X-Trim-Userid`、`X-Trim-Isadmin`（`true`/`false`）、`X-Trim-Username`。
- **不要信任客户端传来的用户 ID**，用网关 Header；网关只管登录态，**业务鉴权仍由应用负责**。
- WebSocket 复用同一前缀与 Socket，建议放稳定子路径（如 `/app/myapp/ws`）；连接建立时获得同样身份上下文，之后应把连接绑定到 `X-Trim-Userid`。
- Docker 应用也可用网关：把 `${TRIM_APPDEST}` 挂进容器，让容器内服务在该目录建 Socket。

---

## 5. manifest 字段全表

| 分类 | 字段 | 说明 |
| --- | --- | --- |
| 基础 | `appname` | 应用唯一标识 |
| | `version` | 如 `1.0.0` / `2.1.3-beta` |
| | `display_name` | 应用中心/设置/UI 显示名 |
| | `desc` | 描述，**必要时可用 HTML** |
| | `source` | 第三方固定 `thirdparty` |
| 平台 | `platform` | `x86` / `arm` / `all`（`all` 仅用于不含特定架构二进制时）。**原 `arch` 字段已废弃** |
| 开发者 | `maintainer` / `maintainer_url` | 开发者名称与链接 |
| | `distributor` / `distributor_url` | 发布者（与开发者不同时填） |
| 兼容 | `os_min_version` / `os_max_version` | 支持的系统版本范围，按实测填，勿虚标 |
| 运行控制 | `ctl_stop` | `true` 显示启停与状态；`false` 隐藏 |
| 安装 | `install_type` | 空=用户选存储位置；`root`=装到系统分区 |
| | `install_dep_apps` | 依赖，`:` 分隔，**从右到左安装/启用**；`>` 声明最低版本（如 `database>2.2.2:cache`）。**依赖不递归解析** |
| 桌面 | `desktop_uidir` | UI 目录，默认 `ui` |
| | `desktop_applaunchname` | 多入口时指定应用卡片打开的入口 ID |
| 端口 | `service_port` | 服务端口；不监听固定端口可省略 |
| | `checkport` | 启动前是否检查端口，默认 `true` |
| 授权 | `disable_authorization_path` | `true` 隐藏"授权目录"设置（仅当应用不需要文件/目录授权时） |
| 更新 | `changelog` | 更新说明 |
| 微应用 | `micro_app` | **调用 JS SDK 必须 `micro_app=true`**（否则页面不按微应用环境加载） |

**示例**：

```
appname=HelloFnos
version=1.0.0
display_name=Hello fnOS
desc=一个最小的飞牛 fnOS 应用。
source=thirdparty
platform=all
maintainer=Example Team
maintainer_url=https://example.com
os_min_version=1.2.0
desktop_uidir=ui
desktop_applaunchname=HelloFnos.Application
ctl_stop=false
checkport=false
```

---

## 6. config/privilege 与 config/resource

### config/privilege（运行身份）

```json
{ "defaults": { "run-as": "package" }, "username": "myapp_user", "groupname": "myapp_group" }
```

- `run-as=package`（**默认首选**）：以专用应用用户运行，与系统权限隔离；`username`/`groupname` 省略时按 `appname` 生成。
- `join-groups`：追加系统用户组（如 `["video","render"]`）以访问特定资源；**每加一组都会扩大可访问范围，只加确实需要的**。
- `run-as=root`：**强烈不推荐**。仅当生命周期脚本必须做特权准备（系统集成、访问包用户无法处理的设备）时使用。长期运行且对外提供服务的进程应尽量非 root；root 脚本可用 `runuser -u "$TRIM_USERNAME" -- <cmd>` 降权。
- 用户文件访问：默认**无**广泛权限，需用户授权目录或在 `config/resource` 声明共享目录。

### config/resource（资源声明）

```json
{
  "data-share": { "shares": [ { "name": "myapp/documents" } ] },
  "usr-local-linker": { "bin": ["bin/myapp-cli"], "lib": ["lib/mylib.so"], "etc": ["etc/myapp.conf"] },
  "docker-project": { "projects": [ { "name": "myapp-stack", "path": "docker" } ] },
  "api-scope": ["trim.file.userAccess", "trim.file.userAcl"]
}
```

- `data-share.shares[].name`：共享目录名。安装时自动创建，使用 **Windows ACL**（非 POSIX ACL），并自动给应用运行用户授权。可通过 `TRIM_DATA_SHARE_PATHS` 或 `/var/apps/{appname}/share/<子目录>` 访问。建议以应用名为顶级目录（`myapp/documents`）。
- `data-share.shares[].permission`：`{ "rw": [...], "ro": [...] }`，仅当其他应用/系统用户需访问时配置。
- `usr-local-linker`：`bin`→`/usr/local/bin/`、`lib`→`/usr/local/lib/`、`etc`→`/usr/local/etc/`。命令名带应用标识（如 `myapp-cli`），避免与系统命令冲突。
- `docker-project.projects[]`：`name` 项目名（保持稳定），`path` 相对 `app/` 的 Compose 目录。
- `api-scope`：声明要用到的开放能力 Scope（见 §12.2）。
- **原则**：只声明真正用到的能力；资源名在版本间保持稳定。

---

## 7. cmd/ 生命周期脚本

| 脚本 | 时机 | 典型用途 |
| --- | --- | --- |
| `install_init` | 安装文件前 | 环境/架构预检 |
| `install_callback` | 安装文件后 | 初始化配置、生成密钥、写服务单元 |
| `main` | 运行控制 | `start` / `stop` / `status` |
| `upgrade_init` | 升级前 | 备份配置与数据 |
| `upgrade_callback` | 升级后 | 数据迁移、配置迁移、兼容性检查 |
| `uninstall_init` | 卸载前 | 停服务、清理 |
| `uninstall_callback` | 卸载清理后 | 收尾 |
| `config_init` | 配置变更前 | 停服、写新配置 |
| `config_callback` | 配置变更后 | 重启服务 |

> ⚠️ **`upgrade_init` / `upgrade_callback` 在本 fnOS 版本上是死代码（2026-10-13 实测）**
> fnOS 应用中心**不提供本地 FPK 的就地升级能力**：`POST /app-center/v1/install/task` 只要 `appname` 已存在就返回 `10236 = ErrCodeInstalledException`（「应用已安装」），**与版本号无关、与运行状态无关**（已用版本号递增到 8.17.11 的包验证）；`app update` 只走云端下载（`/v1/download/task`），本地包不可用。
> **⇒ 新包上线必须走「卸载 → 全新安装」，因此这两个钩子永远不会被调用。** 需要"跨重装保留配置"时，应把职责放在 `uninstall_init`（备份到 `$TRIM_PKGVAR`，该目录卸载后仍保留）+ `install_callback`（还原），**不要**依赖 `upgrade_*`。

> ⚠️ **不要自行添加 systemd 单元来启动应用（除非应用确实是系统服务）**
> fnOS 用 `cmd/main` 管理应用生命周期，`appcenter.app` 表的 `is_systemd_uint` 字段标记应用是否走 systemd。自行附加 `enabled` 的单元会与 `cmd/main` **双启动**，并带来两个具体后果：
> 1. 开机时单元抢跑 → `main start` 检测到"已在运行"提前返回 → **位于 `main start` 后段的看门狗/自愈逻辑被跳过**。
> 2. 单元的 `ExecStop` 若未 `cd` 到正确目录，`-p .` 会解析到 systemd 的工作目录（`/`），**每次停止都把单元打成 `failed`**，且 `daemon-reload` 不会清除该状态。
>
> **推荐做法**：把启动/停止/自愈全部收敛到 `cmd/main`；确需 systemd 时，让 `main start|stop` 委托 `systemctl`，避免两套机制并存。

**`main` 退出码约定**（关键）：
- `0`：成功；在 `status` 中表示**正在运行**
- `1`：失败
- `3`：在 `status` 中表示**未运行**

**用户可见错误**：以非零码退出前，把简短可执行的错误写入 `$TRIM_TEMP_LOGFILE`：

```bash
if [ ! -f "$TRIM_PKGETC/config.conf" ]; then
  echo "Missing configuration file." > "$TRIM_TEMP_LOGFILE"
  exit 1
fi
```

**典型 main 骨架**（官方示例，使用 `TRIM_SERVICE_PORT` 定位进程）：

```bash
case "$1" in
start)
  cd "$TRIM_APPDEST"
  ./myapp --config "$TRIM_PKGETC/config.conf" --data "$TRIM_PKGVAR" \
          --port "$TRIM_SERVICE_PORT" --log "$TRIM_TEMP_LOGFILE" &
  ;;
status)
  pgrep -f "myapp.*$TRIM_SERVICE_PORT" >/dev/null && exit 0
  exit 3
  ;;
stop)
  pkill -f "myapp.*$TRIM_SERVICE_PORT"
  ;;
*)
  echo "Unknown command: $1" > "$TRIM_TEMP_LOGFILE"; exit 1
  ;;
esac
```

---

## 8. 环境变量全表

**应用信息**：`TRIM_APPNAME`、`TRIM_APPVER`、`TRIM_OLD_APPVER`（升级时旧版本）、`TRIM_APP_STATUS`（`INSTALL`/`START`/`UPGRADE`/`UNINSTALL`/`STOP`/`CONFIG`）

**应用路径**：`TRIM_APPDEST`(target)、`TRIM_PKGETC`(etc)、`TRIM_PKGVAR`(var)、`TRIM_PKGTMP`(tmp)、`TRIM_PKGHOME`(home)、`TRIM_PKGMETA`(meta)、`TRIM_APPDEST_VOL`(安装所在存储空间)

**用户与权限**：`TRIM_USERNAME`(应用用户)、`TRIM_GROUPNAME`、`TRIM_UID`、`TRIM_GID`、`TRIM_RUN_USERNAME`(当前执行脚本用户，特权操作下可能不同)、`TRIM_RUN_GROUPNAME`、`TRIM_RUN_UID`、`TRIM_RUN_GID`

**网络与资源**：`TRIM_SERVICE_PORT`、`TRIM_DATA_SHARE_PATHS`(`:` 分隔)、`TRIM_DATA_ACCESSIBLE_PATHS`(用户授权路径，`:` 分隔)

**开放 API**：`TRIM_API_TOKEN`（后端调开放 API 的认证 token，**每次从环境变量读取，勿持久化**）

**日志与临时**：`TRIM_TEMP_LOGFILE`(用户可见错误)、`TRIM_TEMP_UPGRADE_FOLDER`(升级临时目录)、`TRIM_PKGINST_TEMP_DIR`(安装解压临时)、`TRIM_TEMP_TPKFILE`(包解压目录)

**系统上下文**：`TRIM_SYS_VERSION`、`TRIM_SYS_VERSION_MAJOR/MINOR/BUILD`、`TRIM_SYS_ARCH`、`TRIM_KERNEL_VERSION`、`TRIM_SYS_MACHINE_ID`、`TRIM_SYS_LANGUAGE`

**向导变量**：向导字段直接成为同名环境变量，**不使用 `TRIM_` 前缀**。

---

## 9. wizard 表单

四种文件：`wizard/install`（安装）、`upgrade`、`uninstall`、`config`（安装后从应用设置进入，值继续作为环境变量提供给应用）。

结构：JSON 数组，每项 `{ stepTitle, items: [...] }`；表单项 `{ type, field, label, initValue, rules, options/helpText }`。

**字段类型**：`text`、`password`（密钥/令牌）、`radio`、`checkbox`、`select`、`switch`、`tips`（只读提示）。

**校验规则** `rules[]`：`required`、`min`/`max`、`len`、`pattern`，各带 `message`。

**命名约定**：
- 字段名即环境变量名，**保持稳定**（改名=改环境变量）。
- 自定义字段用 `wizard_` 前缀（如 `wizard_port`）。
- **禁止使用 `TRIM_` 前缀**（保留给系统）。
- 脚本中按字符串处理，使用前**再次校验**。

**访问模型对应**：CGI 入口不声明端口；服务类应用通过端口或统一网关暴露 UI。

---

## 10. 图标规范

- 包图标：`ICON.PNG`(64x64) + `ICON_256.PNG`(256x256)，放包根目录。
- 入口图标：`app/ui/images/icon_64.png`、`icon_256.png`，在 `app/ui/config` 用 `icon: "images/icon_{0}.png"` 引用，`{0}` 由系统替换为尺寸。
- 格式 PNG/JPG、sRGB、≤1024KB、完整正方形；**视觉主体用圆角矩形**（勿直角满铺），圆角/留白/阴影贴近系统图标；64px 下仍清晰，重要内容勿贴边。

---

## 11. 构建与安装

### fnpack（v1.2.3）

```bash
fnpack create <appname>                       # 普通应用
fnpack create <appname> --without-ui true     # 无桌面入口的服务
fnpack create <appname> --template docker     # Docker 应用
fnpack build                                  # 在项目目录打包
fnpack build --directory <path>               # 指定目录打包
```

**打包前校验**（缺任一则失败）：`manifest`（存在且含必要字段）、`config/privilege`（合法 JSON）、`config/resource`（合法 JSON）、`ICON.PNG`、`ICON_256.PNG`、`app/`、`cmd/`、`wizard/`，以及声明了 `desktop_uidir` 时该目录必须存在。

下载：`fnpack-1.2.3-{windows-amd64,linux-amd64,linux-arm64,darwin-amd64,darwin-arm64}`。

### appcenter-cli（设备上）

```bash
appcenter-cli install-fpk myapp.fpk [--env config.env]   # 装本地包（向导值走 env 文件）
appcenter-cli install-local                              # 项目已在设备上：本地打包并安装
appcenter-cli default-volume [n]                         # 查看/设置默认安装位置
appcenter-cli list / start <app> / stop <app>
```

> 敏感环境变量文件（账号/密码/Token）**不要提交到代码仓库**。

---

## 12. 开放 API

### 12.1 两类接口与基础接入

- **前端 JS SDK**（应用页面内）：打开授权页/文件管理器/应用设置，读平台配置，监听主题语言。
- **后端 API**（应用服务端）：查询授权路径、检查文件权限、读平台配置。

**版本要求**：系统 **≥ 1.2.0401**，App **≥ 1.34.0**。

**Scope 声明**（在 `config/resource` 的 `api-scope`）：

| 能力 | Scope |
| --- | --- |
| 应用共享授权管理 | `trim.file.sharedAccess` |
| 用户授权管理 | `trim.file.userAccess` |
| 文件权限检查 | `trim.file.userAcl` |
| 路径转换 | `trim.file.path` |
| 平台配置读取 | `trim.system.getPlatformConfig` |

> 只声明实际用到的 Scope；声明只是前提，实际可访问范围仍取决于用户授权、管理员设置与 token 校验。

**JS SDK 前置条件**：manifest 必须 `micro_app=true`，否则页面不按微应用环境加载。安装：`npm install @trimjs/web-app`（当前快照 0.4.2）。

**运行环境判定**：
- `isWeb`：是否 Web 运行时（移动端 App 内嵌页面通常为 `false`）
- `isStandaloneWeb`：是否独立浏览器页面（`true` 表示不在宿主中）
- 文件选择/授权：`isStandaloneWeb=false` → 直接调 `pickUserFile`/`pickSharedFile`；`=true` → 用 `openAppAuth` 打开授权页并用 `redirectUri` 收结果。
- `$on('os/theme'|'os/language')` **仅支持 Web 宿主**（`isWeb===true && isStandaloneWeb===false`）。

**授权回调要点**：用 `openAppAuth`（建议 `target:'_blank'`）→ 系统跳 `redirectUri` → 回调页 `parseAppAuthCallback` 解析 → **校验 `state`** → `window.opener.postMessage(..., origin)` 通知原页 → `window.close()`。必须由**用户点击**触发（自动打开会被浏览器拦截）。建议结合统一网关使原页与回调页同域；原页应保留"刷新授权状态"按钮兜底。

**后端 API 调用**：
```
POST /api/v1/trimapp
Unix Socket: /var/run/trim_open_gateway_apiscope.socket
Content-Type: application/json
Authorization: Bearer <token>     # token 来自环境变量 TRIM_API_TOKEN
```
请求体 `{ reqId, req, appName, data }`；响应 `{ reqId, code, msg, data }`（`code=0` 成功）。
**只能由应用服务端经 Unix Socket 调用**，切勿在前端直接调用或暴露 token。

### 12.2 授权与文件

**应用共享授权**（管理员操作，仅目录）：`pickSharedFile` / `authorizeSharedFile`（JS SDK）；`trim.file.getSharedAccessibleFolders` / `trim.file.delSharedAccessibleFolder`（后端）。
- 普通用户调用会失败：宿主内直调 `code:1, msg:"仅管理员可进行此操作"`；路由回调 `status:"error", error:"access_denied"`。

**用户个人授权**：`pickUserFile`（`directory:true` 目录 / `false` 文件，`accept` 限扩展名）/ `authorizeUserFile`；后端 `trim.file.getUserAccessibleFolders`(需 `uid`) / `trim.file.delUserAccessibleFolder`(需 `uid`+`path`)。
- **目录授权只支持单选**（传 `multiple` 也按单选）。
- **文件授权不写入 `getUserAccessibleFolders`**，直接用选择器/回调返回的路径。

**文件权限检查**：`trim.file.checkUserACL`，`data:{ uid, path }`（`path` 可为数组），返回 `[{ path, readable, writable, deletable }]`；路径不存在或无权读取时三者均为 `false`。**返回文件列表/预览/写入/删除前应按当前用户 uid 检查**。

**路径转换**：`trim.file.convertPath`，`data:{ path, language }`（**`language` 必传**，按当前界面语言），返回 `{ status:0, result:[{ path, semanticPath }] }`。页面**不要直接展示 `/vol1/...`**。

**SidebarGroup 枚举**：`myFiles`(我的文件) / `otherShare`(他人共享) / `external`(外接存储) / `remote`(远程挂载) / `favorites`(我的收藏) / `team`(团队空间)。

**`AppBridgeResponse<T>`**：`{ code, msg, data }`。

### 12.3 页面路由与交互（JS SDK）

| 方法 | 作用 |
| --- | --- |
| `openFile(path)` | 用宿主打开文件 |
| `showFileDetails(paths[], {admin?})` | 打开文件详情（含权限调整入口） |
| `openFileManager(path)` | 打开文件管理器并定位 |
| `openAppSetting()` | 打开当前应用设置页 |
| `openURL(url, target?, features?)` | 打开外链（Web 宿主=window.open；移动 WebView=系统浏览器） |
| `setTitle(title)` | 设置页面标题 |
| `setExitPageTips({title,content}?)` | 设置/清除离开确认（无参=清除） |
| `close()` | 关闭当前应用页面 |
| `getPlatformConfig()` | 读主题/语言/系统版本/日期时间格式 |
| `$on('os/theme'\|'os/language', cb)` | 监听主题/语言（仅 Web 宿主） |

### 12.4 平台配置

```ts
interface PlatformConfig {
  theme: 'dark' | 'light';
  language: string;
  systemLanguage?: string;
  appVersion?: string;
  systemVersion: string;
  format: { date?: string; time?: string };
}
```
后端 `trim.system.getPlatformConfig`（`data:{}`）仅返回 `{ systemLanguage, systemVersion }`。

### 12.5 错误码

**JSSDK**：`0` 成功；`1000000` 服务/内部异常；`1000001` 登录或认证失败；`1000002` 管理员权限或 Scope 不足；`1000030` 请求不合法/路径不支持；`1000300` 未找到已安装应用；`1000701` 路径不存在；`1003103` 应用权限校验失败；`1003201` 管理员已关闭普通用户授权能力。

**后端 API**：`200001` Invalid Params（200/400）；`200004` Unauthorized（401）；`200003` Forbidden（403，查 Scope 与 token）；`200005` Not Found（404，查 `req` 与系统版本）；`200006` Internal Error（200/500）。

**应用中心安装/卸载错误码**（从门户 bundle 提取，实测命中过前两个）：

| 码 | 枚举名 | 前端文案 | 含义与处置 |
| --- | --- | --- | --- |
| `10236` | `ErrCodeInstalledException` | 应用已安装 | `install/task` 对已存在的 `appname` 恒返回，**与版本/运行状态无关** → 先 `app uninstall` |
| `10392` | `ErrCodeUninstallInitException` | 执行脚本出错且原因未知 | `uninstall_init` 返回非零 → 查 `error.log` 的 `msg="uninstall script error"`，并在脚本内加 trace |
| `10393` | `ErrCodeUninstallCallbackException` | 执行脚本出错且原因未知 | `uninstall_callback` 返回非零 |
| `10235` | `ErrCodeInstallingException` | 应用正在安装 | 上一任务未结束，等 `app task-status` |
| `10030` | （非安装类） | — | 实测出现在 `app update` / 云应用详情查询失败（本地包走云端接口）时 |

查错入口：`/var/log/trim_app_center/error.log`（`msg="app already installed"` / `msg="uninstall script error"` / `msg="hook error"`）。

---

## 13. 安全与最佳实践清单

- 用**最小权限**：默认 `run-as=package`；`join-groups` 只加必要组；避免长期面向用户的进程用 root；root 脚本启动服务前降权。
- 路径/参数/UID 一律不可信；拒绝 `..` 目录穿越；只从预期目录提供文件。
- 应用数据默认放应用目录内，除非用户授权共享位置。
- 只声明实际需要的资源与 `api-scope`；不要暴露内部工具/数据目录为共享资源。
- 密钥类输入用 `password` 类型，**不写日志**；生产凭据不硬编码、不提交仓库。
- 中间件（Redis/MinIO/RabbitMQ）使用独立 db/前缀/bucket/queue 做命名空间隔离。
- 发布前在**计划支持的系统版本与架构**上测试；覆盖依赖不可用/配置错误/资源不足的降级表现。
- 应用中心手动安装仅用于本地测试，**不作为公开分发方式**。

---

## 14. 本项目（LSA）与官方规范的对照

### 14.1 当前实现

| 项 | LSA 现状 | 官方规范 | 评估 |
| --- | --- | --- | --- |
| 访问模型 | **index.cgi 同源路径模式**（`app/ui/config` 用 `type=iframe` + `url=/cgi/ThirdParty/lsa/index.cgi/`，不再声明 `protocol`/`port`） | 端口服务 / index.cgi / 统一网关三选一 | 合规。**2026-10-13 由端口服务模式切换而来**，原因：端口服务模式下 HTTPS 门户(5667)打开会空白破图（详见 §4 的 ⚠️ 说明与根目录 `HTTPS_ACCESS_FIX_2026-10-13.md`） |
| CGI 代理 | 包内 `app/ui/index.cgi` + `cgi_proxy.py`（同源代理 + 注入 `<base href>` 与 URL 拦截器：改写 `a/XHR/fetch/location.assign/replace/window.open`，并用 **Navigation API `navigate` 事件 + `event.intercept()`** 兜住 GWT 的 `location.href` 赋值） | index.cgi 是独立访问模型 | **已转为正式入口**。真机验证：HTML/JS/后端 JSON API 均 200，目录穿越返回 400；每次请求约 0.03–0.04s，首屏 10–12 个资源，可接受。`location.href` 是 `[LegacyUnforgeable]` 属性、原型上无描述符，只能靠 Navigation API 拦截（详见根目录 `LOGIN_NAV_FIX_2026-10-13.md`） |
| `micro_app` | `micro_app=true` | 调 JS SDK 才需要 | 与官方用途不完全对应（LSA 的 GWT 界面未用 TrimApp SDK）；改动前需确认对 iframe 宿主行为的影响 |
| `config/privilege` | `run-as: root` | 强烈不推荐 root | **有理由的偏离**：需直接访问 RAID 控制器设备节点。可评估 `join-groups` 能否替代 |
| `config/resource` | `usr-local-linker` 三项均为空数组 | 只声明实际需要的资源 | 空声明等价于不声明；可考虑精简为 `{}` |
| `api-scope` | 未声明 | 按需声明 | LSA 未使用 fnOS 开放 API，**符合"只声明实际用到"原则** |
| 端口变量 | `cmd/main` 与 systemd 包装器**硬编码 2463/9000** | 推荐用 `TRIM_SERVICE_PORT` | **不符合规范**，且导致自定义端口路径未充分验证（详见 `HANDOVER.md` §10） |
| 向导字段名 | `wizard_web_port` / `wizard_lsa_port` / `wizard_install_mode` | 用 `wizard_` 前缀，勿用 `TRIM_` | 合规 |
| `wizard/install` 的安装模式 | 收集 `wizard_install_mode` 但 `install_callback` 无条件写 gateway | — | **未接线**，该选项目前是装饰性的 |
| manifest | 有 `service_port=2463`、`checkport=false`、`ctl_stop=true`、`platform=x86`、`micro_app=true`；缺 `changelog`、`distributor`、`os_max_version` | — | 基本合规；`platform=x86` 因含 x86 二进制，正确 |

### 14.2 可考虑的改进方向（按价值排序）

1. **用 `TRIM_SERVICE_PORT` 替换硬编码端口**：`cmd/main` 与 `lsa-fnos-start` 从环境变量或 `conf/fnos_ports.conf` 读端口，彻底打通自定义端口路径。
2. **评估迁移到统一网关**：LSA 需要"复用系统域名 + NAS 登录态 + 常驻服务"，正是统一网关的目标场景（`gatewayPrefix` + `gatewaySocket` + `X-Trim-Userid`）。可去掉自带 nginx 的对外端口与 CGI 代理两套机制，但改造量大、风险高，需在真机充分验证。
3. ~~**清理或明确保留 CGI 代理**~~ **已完成**：`index.cgi`/`cgi_proxy.py` 现为正式入口（2026-10-13），不再是遗留路径。后续若要迁移统一网关，需连同这套代理一起评估替换。
4. **接线或移除安装模式选项**：让 `wizard_install_mode` 真正影响 `installtype`/`installation_type`，或从向导中删除。
5. **补齐 manifest 元数据**：`changelog`、`distributor`、按实测填写 `os_max_version`。
6. **让入口配置与注册表自动同步**：桌面入口在安装期写入 `appcenter.app_service(url/default_url)` 与 `trim_sac.entry(url)` 两处，运行期不重读 `app/ui/config`。若要做"免重装切换访问模型"，需在 `cmd/` 中主动同步这两处。**（已实测：重装会自动同步，因此"改 `app/ui/config` → 重装"是当前可行的变更方式。）**
7. **收敛启动机制**：删除自行添加的 systemd 单元，统一由 `cmd/main` 负责启动、停止与看门狗（理由见 §7 的 ⚠️ 说明）。当前单元既会在开机与 `cmd/main` 抢跑导致自愈失效，其 `ExecStop` 又因缺 `cd` 而恒失败。
8. **加固 `uninstall_init`**：
   - 去掉 `purge_package` 里的 `|| exit 1` —— 单点失败会让后续清理全部跳过，留下半卸载状态（deb 仍 `ii`、`/opt/lsi` 仍在）。应写入 `$TRIM_TEMP_LOGFILE` 后继续。
   - 补删 `/usr/local/sbin/lsa-fnos-start`（当前卸载后固定残留）。
9. **把配置保留职责从 `upgrade_*` 迁走**：见 §7 顶部说明 —— 备份到 `$TRIM_PKGVAR` + 安装时还原。

### 14.3 实测参考：一次完整部署链路的耗时与表现

在 `192.168.5.24`（fnOS 1.2.0800）上的实测数据：

| 步骤 | 耗时 | 说明 |
| --- | --- | --- |
| `app install-fpk`（本地 FPK，28 MB） | 安装任务 ~3 s，随后自动启动 ~2 s | 应用中心日志：`install_start` → `install_success` → `start_start` → `success` |
| `app uninstall` | ~3 s（含 3 个 deb purge、`/opt/lsi` 删除） | 脚本本身能卸干净，但见 §14.2 第 8 项 |
| CGI 入口响应 | 5667：0.0035 s / 5666：0.0006 s | 同源路径，无 TLS 协商开销 |
| 首次打开应用界面 | ~10 s | GWT 首屏加载 |

服务端日志位置：`/var/log/trim_app_center/info.log`（成功路径）与 `error.log`（`10236` 等错误码）。

---

## 15. 参考来源

本地快照：
- 门户文档：`reference-snapshot/fnnas-portal/raw/docs/`、`.../api/`（索引见 `reference-snapshot/fnnas-portal/manifest.json`）
- 纯文本提取：`reference-snapshot/_extracted/`（由 `reference-snapshot/_extract.py` 生成）
- SDK：`reference-snapshot/npm/trimjs-web-app/package-0.4.2/`（README.md 与 `dist/*.d.ts`）

官方在线：
- 开发指南 https://developer.fnnas.com/docs/guide/
- 开放 API https://developer.fnnas.com/api/overview/
- fnpack https://developer.fnnas.com/docs/cli/fnpack/
- SDK https://www.npmjs.com/package/@trimjs/web-app

文档更新日志要点：2026-07-31 新增开放 API 文档；2026-07-05 fnpack 升到 1.2.3；2026-05-09 新增统一网关；2025-12-31 `arch` 废弃改用 `platform`、fnpack 1.2.0。
