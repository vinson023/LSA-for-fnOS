# HTTPS(5667) 无法打开应用 — 根因分析与修复

日期：2026-10-13
影响：`lsa` / `lsaen` 两个 FPK 包
测试机：`<NAS_IP>`（fnOS，端口 5666=HTTP、5667=HTTPS）

---

## 1. 现象

- `http://<NAS_IP>:5666/` → 桌面点开"LSI 存储管理"，正常。
- `https://<NAS_IP>:5667/` → 同一入口打开后，窗口内容区**空白并显示破图图标**（iframe 加载失败）。

## 2. 根因

桌面入口此前使用 **端口服务模式**：

```json
{
  "type": "iframe",
  "protocol": "",
  "port": "${wizard_web_port}",
  "url": "/ui/remoteserver/index.html"
}
```

fnOS 桌面前端把入口地址解析为 `{host, path, port, protocol}` 四元组，再按下列逻辑拼出 iframe 的 `src`
（取自门户前端 bundle `index-*.js` 中的 `wYe()`）：

```js
wYe = (e, t) => {
  if (!le && t) return t;                                   // full_url 优先
  if (de && e.fnDomain && e.port) return `https://${e.fnDomain}.${location.host}${e.path}`;
  let n = e.host || location.hostname,
      r = e.path || '',
      i = e.port || location.port;
  return `${e.protocol || location.protocol.replace(':','')}://${n}:${i}${r}`;
}
```

因为 `protocol` 为空、`port` 为 `2463`，最终得到：

| 门户 | iframe src |
|---|---|
| HTTP 5666 | `http://<NAS_IP>:2463/ui/remoteserver/index.html` ✅ |
| HTTPS 5667 | `https://<NAS_IP>:2463/ui/remoteserver/index.html` ❌ |

**LSA 自带的 nginx 在 2463 上只监听明文 HTTP，没有 TLS。** HTTPS 门户下浏览器按 `https://` 去连 2463，
TLS 握手失败（同时也会被混合内容策略拦截），于是 iframe 变成空白破图。

也就是说：**问题不在 LSA 本身，而在"入口协议跟随门户、端口却固定指向无 TLS 的 2463"这一组合。**

## 3. 修复方案

改为 **index.cgi 模式**（同源路径入口）。官方文档《index.cgi》明确说明：

> 对于 CGI 入口，**protocol 和 port 会被忽略**。请求会**沿用当前访问域名**，直接按配置的路径访问。
> 飞牛 fnOS 会在调用 CGI 入口前校验 NAS 用户登录态。

修改 `app/ui/config`：

```json
{
  ".url": {
    "lsa.main": {
      "title": "LSI 存储管理",
      "icon": "images/icon_{0}.png",
      "type": "iframe",
      "url": "/cgi/ThirdParty/lsa/index.cgi/",
      "allUsers": true
    }
  }
}
```

（英文包为 `lsaen.main` / `/cgi/ThirdParty/lsaen/index.cgi/`。）

修复后 `urls = {host:"", path:"/cgi/ThirdParty/lsa/index.cgi/", port:"", protocol:""}`，
代入 `wYe()` 后 `protocol`/`port` 回退到 `location`，得到**与门户同源**的地址：

| 门户 | iframe src |
|---|---|
| HTTP 5666 | `http://<NAS_IP>:5666/cgi/ThirdParty/lsa/index.cgi/` ✅ |
| HTTPS 5667 | `https://<NAS_IP>:5667/cgi/ThirdParty/lsa/index.cgi/` ✅ |

### 为什么选 index.cgi 而不是统一网关

- 统一网关（`gatewayPrefix` + `gatewaySocket`）需要应用侧提供 Unix Socket 常驻服务，LSA 自带 nginx 不提供，
  需要额外桥接进程；且它注入 `X-Trim-Userid` 等身份头，而 LSA 有自己的登录体系，用不上。
- LSA 不使用 WebSocket（全量检索命中 0 处），所以 index.cgi 唯一的功能短板对本项目无影响。
- 同机 `fnaudio` 就是 index.cgi 模式的现成范例，HTTPS 下工作正常，可直接对标。

## 4. 验证（真机 <NAS_IP>）

1. `app-center` 接口 `GET /app-center/v1/service/list` 返回：
   - 修复前：`lsa -> {path:"/ui/remoteserver/index.html", port:"2463"}`
   - 修复后：`lsa -> {path:"/cgi/ThirdParty/lsa/index.cgi/", port:""}`（与 `fnaudio` 结构一致）
2. 无头 Chrome 登录 `https://<NAS_IP>:5667/`，点击桌面图标，抓取 iframe 实际 src：
   `https://<NAS_IP>:5667/cgi/ThirdParty/lsa/index.cgi/` —— **同源**。
3. 窗口内完整渲染 LSA 界面（Broadcom 头部、版本 008.017.010.000、中文界面、"远程服务器发现"面板）。
4. `http://<NAS_IP>:5666/` 回归验证通过，iframe src 为 `http://<NAS_IP>:5666/cgi/...`。

## 5. 部署侧需要改的两处

桌面入口在安装时会被写入两处注册表，**改 `app/ui/config` 后必须重装/升级**（或手工同步这两处）：

| 位置 | 字段 |
|---|---|
| `appcenter` 库 `app_service` 表（app_id=30, id=36） | `url`、`default_url` |
| `trim_sac` 库 `entry` 表（id=157） | `url` |

实测：`app-center` 服务**实时读取** `appcenter.app_service`，改库后无需重启服务即生效；
仅重启应用**不会**刷新这两处，因为它们是安装期写入的。

## 6. 遗留事项

- 原仓库位于网络盘 `E:\LSA_Linux`（`\\<FILE_SERVER_IP>\codex`），本次会话中该盘上"会话开始前已存在"的文件
  无法被沙箱写入，故全部工作改在副本 `C:\LSA_Linux` 上进行。
- 同步回 `E:` 需在沙箱外执行一次复制。
