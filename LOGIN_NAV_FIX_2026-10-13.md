# 登录后跳转到 fnOS 404 — 根因分析与修复

日期：2026-10-13
影响：`lsa` / `lsaen` 两个 FPK 包
测试机：`<NAS_IP>`（fnOS，端口 5666=HTTP、5667=HTTPS）
改动文件：`lsa-fnos/app/ui/cgi_proxy.py`、`lsa-fnos-en/app/ui/cgi_proxy.py`

---

## 1. 现象

在 fnOS 桌面（HTTP 5666 / HTTPS 5667 两个门户均复现）打开"LSI 存储管理"：

1. LSA 主界面正常渲染（`#remoteServer` 远程服务器发现页）；
2. 点界面上的「登录」→ 弹出登录对话框 → 填 `admin` / 密码 → 点「登录」；
3. 浏览器地址栏变成 `https://<nas>:5667/ui/core/index.html?locale=zh-CN&serverID=...`，
   内容变成 **fnOS 的 404 Not Found 页**，应用不可用。

而在此之前，同一 CGI 代理下的 XHR/fetch、`<a href>` 跳转都是正常的
（控制器列表能拉出来），所以"登录"这一步是唯一坏掉的环节。

## 2. 根因

GWT 的登录提交走的是**跨文档赋值**：

```js
location.href = '/ui/core/index.html?locale=en&serverID=/LSI/Storage/MR/API/1.0/servers/a0:36:9f:...';
```

这是**原点绝对路径**，在 fnOS 域名下不存在 —— 我们的 CGI 把它代理在
`/cgi/ThirdParty/lsa/index.cgi/` 前缀下，赋值漏过代理前缀就落到 fnOS 自己的 nginx 上 → 404。

原有拦截器覆盖了 `XMLHttpRequest.open`、`fetch`、`<a href>`、`location.assign/replace`、
`window.open`，唯独**没法覆盖 `location.href = ...` 赋值**：按 WebIDL 规范，
`Location.prototype.href` 上的描述符不存在（`href` 是 Location **实例**上的
`[LegacyUnforgeable]` 自有属性，`configurable:false`），所以：

```js
Object.getOwnPropertyDescriptor(Object.getPrototypeOf(window.location), 'href')  // → undefined
```

即插桩点在原型上取不到 setter，整个补丁是死代码。这一点已用探针页在真机浏览器实测确认
（同页还发现 `document.location` 与 `window.location` 是两个宿主对象，
`document.location.href` 改不动 `location.href` 本身）。

## 3. 修复

改用 **Navigation API**（`navigation.navigate` 的兄弟接口，但走事件订阅）作为脚本发起导航的唯一可靠钩子：

```js
var navigationPrefixes = ['/ui/'];          // 只拦 LSA 模块交接路径，避免误伤门户自身路径
window.navigation.addEventListener('navigate', function (event) {
  var d = event.destination;
  if (!d || d.sameDocument) return;         // 同文档跳转(hash)交给原有逻辑
  var path = normalizeToPath(d.url);        // 归一化为原点相对路径；跨源直接放过
  if (path === null || path.charAt(0) !== '/' || !isPrefixMatched(path)) return;
  if (path.indexOf(cgiBase) === 0) return;  // 已在代理前缀内
  var target = cgiBase + path.substring(1);
  try {
    event.intercept({ handler: function () { return navigation.navigate(target, { history: 'replace' }); } });
  } catch (e) {
    try { window.location.replace(target); } catch (e2) {}   // 兜底
  }
});
```

配套调整：

- **删除** `location.href` 的原型补丁死代码；
- `location.assign` / `location.replace` 的 patch 保留（LSA 也会用）；
- `rewriteUrl()` 增加 `normalizeToPath()`：非字符串、跨源 URL 一律原样放过，减少误判；
- 导航守卫加**前缀白名单** `['/ui/']`：只改 LSA 模块交接路径
  （`/ui/core/index.html`、`/ui/server/index.html`…），不碰 fnOS 门户自身路径。

## 4. 验证（真机实测，Chrome + CDP）

门户会话有效的前提下，走完整链路：

```
入口  https://<NAS_IP>:5667/cgi/ThirdParty/lsa/index.cgi/        # #remoteServer 页
  │  点「登录」→ 填 admin / 密码 → 提交
  ▼
core  .../index.cgi/ui/core/index.html?locale=en&serverID=/LSI/Storage/MR/API/1.0/servers/a0:36:9f:a0:00:4b
  ▼
server .../index.cgi/ui/server/index.html?locale=en&&eventURI=...&serverID=...#server
```

最终状态 = **完整 LSA 控制台**：标题"LSI 存储管理 - v008.017.010.000"，
显示"1 此服务器上的控制器""Linux 6.18.18.c1126-trim""控制器 ID：0 PERC H740P Adapter"，
75 行表格数据，控制器状态"最佳"。
**全程 URL 都在 CGI 前缀内，未再出现 fnOS 404 页。**

同一逻辑的桌面原型页也用本机 Chrome 单独验证过 `event.intercept()` 的可用性与改道结果。

## 5. 兼容性与已知限制

- Navigation API 需要 Chrome/Edge 102+（2022-06）。fnOS 桌面 WebView 与本机浏览器均满足。
  若不满足，守卫注册时静默退出，行为退化为修复前（仅 `assign`/`replace` 被改）。
- 守卫只拦**脚本发起的跨文档导航**；用户在地址栏手输 `/ui/...` 仍会 404（属预期）。
- 真机上的部署：先手工 SFTP 替换 `/vol1/@appcenter/lsa/ui/cgi_proxy.py`（md5 已核对一致）完成验证，
  随后双包已重新 `fnpack build` 并核对包内 `ui/cgi_proxy.py` 与真机部署版 md5 一致
  （新 `lsa.fpk` md5 `ca4b9abb1ef4411d8dfaf9794976d026`、`lsaen.fpk` md5 `48d1a8e933e809e979935d4d3e1b6e48`）。
  fnOS 无本地 FPK 就地升级能力（见 `UPGRADE_FLOW_VERIFICATION_2026-10-13.md`），实际路径仍是卸载 → 安装。
- 英文包（`lsaen`）同步了同一改动，两个文件除 `CGI_BASE`（`lsa` / `lsaen`）外完全一致。
