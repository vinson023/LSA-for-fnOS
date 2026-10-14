# LSA for fnOS

> 把 **LSI Storage Authority** 移植到**飞牛 fnOS** 的第三方应用包

把 Broadcom / LSI 的 **LSI Storage Authority（LSA）** Web 管理界面移植到**飞牛 fnOS**，让 fnOS 桌面可以直接打开 RAID 控制器的管理界面，无需另开浏览器访问裸端口。

> 本项目**只包含移植层**（fnOS 应用包装、生命周期脚本、同源 CGI 代理、本地化资源），
> **不包含** Broadcom 的专有二进制。构建前需自行获取原厂固件，见 [NOTICE.md](NOTICE.md)。

---

## 这是什么

LSI Storage Authority 是管理 Broadcom/LSI SAS RAID 控制器的 Web 应用（MegaRAID、iMR、HBA、IT、eHBA 等）。
它本身以 `deb` + 自带 nginx 的形式发布，直接装到 fnOS 上有三个问题：

1. **没有 fnOS 应用入口** —— 装完不会出现在桌面，只能手动敲 `http://<nas>:2463`；
2. **端口服务模式在 HTTPS 门户下失效** —— fnOS 用 `https://<nas>:5667` 访问时，iframe 会被指向
   无 TLS 的 2463 端口，内容区空白破图；
3. **界面是英文的**，且缺少 fnOS 的安装/卸载/启停生命周期管理。

本项目通过 **fnOS 应用包（FPK）+ 同源 CGI 代理**解决上述问题：

- 桌面图标走 `index.cgi` 同源路径（不声明 `protocol`/`port`），HTTP(5666) 与 HTTPS(5667) 门户**都能正常打开**；
- 代理为每个 HTML 响应注入 `<base href>` 和 URL 拦截器，把 LSA 的原点绝对路径导航拉回代理前缀；
- 提供中文/英文两个包，中文化了界面文案、告警、健康规格等资源；
- 完整接管安装、启动、停止、卸载流程。

## 特性

- **桌面一键打开**：fnOS 桌面图标直接进入 LSA，跟随当前访问域名与协议
- **HTTP / HTTPS 双门户可用**：不受端口服务模式的 TLS 限制
- **全权限模式**：默认解除厂商的 `readOnly` 限制，登录后可见 RAID 配置与维护菜单
- **中英双语**：两个独立 FPK 包，中文包提供界面本地化
- **生命周期管理**：安装校验架构、写端口配置、装依赖、建兼容软链、注册 systemd 单元、卸载清理
- **故障自愈**：`cmd/main` 内置看门狗
- **登录跳转修复**：用 Navigation API 拦截 GWT 的 `location.href` 跨文档赋值，避免跳到 fnOS 404

## 目录结构

```
.
├── lsa-fnos/                  # 中文包工程（appname=lsa）
│   ├── manifest               # FPK 应用描述
│   ├── cmd/                   # fnOS 生命周期脚本（核心）
│   ├── config/                # privilege（root 运行）、resource
│   ├── wizard/                # 安装 / 配置向导定义
│   └── app/
│       ├── debs/              # ← 需自行放入原厂 deb（见 NOTICE.md）
│       └── ui/                # 桌面入口 + CGI 代理 + 本地化资源
├── lsa-fnos-en/               # 英文包工程（appname=lsaen）
├── docs/                      # 真机验证截图
├── HANDOVER.md                # 交接文档：架构、构建、已知风险、维护约定
├── FNOS_DEV_GUIDE.md          # 飞牛 fnOS 开发规范技能手册
├── FEATURE_OVERVIEW.md        # 功能说明
├── SUPPORTED_CONTROLLERS.md   # 兼容控制器型号
├── LOGIN_NAV_FIX_*.md         # 登录跳转 404 修复报告
├── HTTPS_ACCESS_FIX_*.md      # HTTPS 入口修复报告
├── UPGRADE_FLOW_VERIFICATION_*.md  # 升级/卸载流程真机实测报告
└── VERIFICATION_REPORT_*.md   # 整体验证报告
```

## 构建

**前置**：先按 [NOTICE.md](NOTICE.md) 把 3 个原厂 deb 放入 `app/debs/`。

```bash
# 1. 获取打包工具 fnpack 1.2.3
#    https://developer.fnnas.com/docs/cli/fnpack/

# 2. 构建（在各自工程目录内执行）
cd lsa-fnos     && ../fnpack-1.2.3-windows-amd64.exe build   # 产出 lsa.fpk
cd lsa-fnos-en  && ../fnpack-1.2.3-windows-amd64.exe build   # 产出 lsaen.fpk
```

> `build.sh` 依赖 `../gcc_11.2.x/` 目录复制 deb，若该目录不存在会第一步报错退出；
> 直接用 `fnpack build` 即可。详见 `HANDOVER.md` §7。

## 安装

fnOS **不支持本地 FPK 就地升级**，因此新版本上线一律走 **卸载 → 安装**：

```bash
# 生成包后在 fnOS 应用中心上传安装，或用 trim-cli
trim-cli app install <path-to>/lsa.fpk
```

安装后桌面会出现「LSI 存储管理」图标。默认端口：Web 管理 `2463`、LSA 服务 `9000`。

> ⚠️ 两个包共用 LSA 服务目录与端口，**不能同时安装或运行**。

## 兼容性

- 架构：x86_64
- 系统：飞牛 fnOS
- 浏览器：需要支持 Navigation API（Chrome/Edge 102+，2022-06 起）；fnOS 桌面 WebView 满足
- 控制器：见 [SUPPORTED_CONTROLLERS.md](SUPPORTED_CONTROLLERS.md)

## 文档导航

| 想了解 | 看这里 |
| --- | --- |
| 整体架构、安装链路、已知风险 | [HANDOVER.md](HANDOVER.md) |
| 飞牛 fnOS 开发规范（泛用） | [FNOS_DEV_GUIDE.md](FNOS_DEV_GUIDE.md) |
| 为什么 HTTPS 门户打不开、怎么修的 | [HTTPS_ACCESS_FIX_2026-10-13.md](HTTPS_ACCESS_FIX_2026-10-13.md) |
| 登录后跳 404 的原因与修法 | [LOGIN_NAV_FIX_2026-10-13.md](LOGIN_NAV_FIX_2026-10-13.md) |
| 升级/卸载流程实测结论 | [UPGRADE_FLOW_VERIFICATION_2026-10-13.md](UPGRADE_FLOW_VERIFICATION_2026-10-13.md) |
| 第三方组件与授权 | [NOTICE.md](NOTICE.md) |

## 授权与声明

**开发者 / 发布者**：[@vinson023](https://github.com/vinson023)

本项目的移植层代码以 [MIT License](LICENSE) 发布。

**但请注意**：本项目**不包含也不授权** Broadcom / LSI 的任何专有软件（LSI Storage Authority 及其依赖库）。
这些组件由其各自的权利人提供，需自行从官方渠道获取并遵守其许可条款。详见 [NOTICE.md](NOTICE.md)。

> ⚠️ `app/ui/help/`、`app/ui/static/`、`app/ui/images/` 为从原厂安装包提取的界面资源，
> 版权归 Broadcom / LSI，详见 [NOTICE.md §2.4](NOTICE.md)。

`LSI`、`MegaRAID`、`Broadcom` 等为其各自权利人的商标。本项目与 Broadcom / LSI **无隶属关系**，
亦未获其背书。fnOS / 飞牛为飞牛科技的产品。
