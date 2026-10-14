# NOTICE — 第三方组件与授权声明

本仓库采用 **"移植层与厂商二进制分离"** 的方式发布。
本文件说明：哪些内容由本项目授权、哪些内容**不在**本仓库内、以及如何自行获取后者。

---

## 1. 本项目包含的内容（MIT，见 LICENSE）

本仓库**仅包含移植与集成层**，由 **vinson023**（https://github.com/vinson023）编写：

| 内容 | 位置 |
| --- | --- |
| fnOS 应用描述与打包配置 | `lsa-fnos/manifest`、`lsa-fnos-en/manifest`、`build.sh` |
| fnOS 生命周期脚本 | `lsa-fnos/cmd/`、`lsa-fnos-en/cmd/` |
| 权限 / 资源 / 向导定义 | `lsa-fnos/config/`、`lsa-fnos/wizard/`（及英文包同名目录） |
| 同源 CGI 代理 | `lsa-fnos/app/ui/index.cgi`、`cgi_proxy.py`（及英文包同名文件） |
| 桌面入口定义 | `lsa-fnos/app/ui/config`（及英文包同名文件） |
| 中文本地化资源 | `lsa-fnos/app/ui/message_zh.js`、`languages/zh-CN/` |
| 图标与应用说明 | `ICON.PNG`、`ICON_256.PNG`、`README.md`、`FEATURE_OVERVIEW.md` |
| 文档与验证报告 | 根目录各 `*.md`、`docs/` |

## 2. 本项目**不包含**的内容（需自行获取）

出于版权与仓库体积考虑，以下第三方/厂商组件**已从本仓库移除**（包括 git 历史）：

### 2.1 Broadcom / LSI 原厂软件包（必需）

| 文件 | 大小 | 说明 |
| --- | --- | --- |
| `LSIStorageAuthority-008.017.010.000-1_amd64.deb` | ~24 MB | LSA 主程序、自带 nginx 与 Web 界面 |
| `LSA_lib_utils-1.18-1_amd64.deb` | ~2.4 MB | LSA 依赖库 |
| `LSA_lib_utils2-9.00-1_amd64.deb` | ~376 KB | LSA 依赖库 |

**放置位置**（构建前必须就位）：

```
lsa-fnos/app/debs/      ← 上述 3 个文件
lsa-fnos-en/app/debs/   ← 同上（内容完全相同的同一份）
```

**获取方式**：请从 Broadcom 官方支持站点下载对应型号与版本的 LSI Storage Authority
（Linux / Debian 包），或使用服务器厂商提供的配套版本。请遵守 Broadcom 的最终用户许可协议
（EULA）——**本项目不对这些文件授予任何权利**。

> 版本号 `008.017.010.000` 是本项目验证过的版本。使用其他版本时，`cmd/` 脚本中的
> 包名与路径可能需要相应调整。

### 2.2 fnOS 官方真机验证工具（可选）

原开发环境使用飞牛官方的 **`trim-cli`** 命令行工具与配套技能文档（`tools/skill/`）做真机验证
与部署。该工具由其官方发布，**不属于本项目**，已从仓库移除。

如需复现真机验证流程，请从飞牛官方渠道获取；`tools/skill/` 目录缺失不影响 FPK 的构建与安装。

### 2.3 其他已移除内容

| 内容 | 说明 |
| --- | --- |
| `reference-snapshot/` | 飞牛 fnOS 门户文档与 JS SDK 的离线快照，版权归飞牛所有；请查阅官方开发者文档 |
| `fnpack-1.2.3-windows-amd64.exe` | 官方打包工具；见 https://developer.fnnas.com/docs/cli/fnpack/ |
| `*.fpk` | 构建产物，可由 `fnpack build` 重新生成 |
| `tools/skill/` | 飞牛官方 trim-cli 真机验证工具与文档 |

## 2.4 ⚠️ 仓库中保留的厂商界面资源（重要）

以下内容**当前随本仓库分发**，但其版权归 **Broadcom / LSI** 所有，并非本项目作者的创作。它们是构建 FPK 所必需的界面资源：

| 路径 | 体积 | 性质 |
| --- | --- | --- |
| `lsa-fnos*/app/ui/help/` | ~1.6 MB | Broadcom 产品帮助文档（236 个 HTML） |
| `lsa-fnos*/app/ui/static/` | ~222 KB | LSA 界面静态资源（含状态码说明、开源许可清单） |
| `lsa-fnos*/app/ui/images/` | ~5 KB | 应用图标（含 Broadcom/LSI 商标） |

**这些文件来源于公开分发的 LSA 安装包**（原厂 deb），本项目未对它们做实质修改。
它们的存在**不构成对这些内容的授权**。

> **若你要基于本仓库公开发布或再分发**，请自行评估上述资源的版权合规性。
> 稳妥做法是从仓库中移除这些目录，改为构建时从原厂 deb 自动提取
> （`cgi_proxy.py` 的多数字体资源依赖它们，移除后需在构建流程中还原）。

## 2.5 本项目作者创作、随仓库分发的本地化成果

以下内容由 **vinson023** 编写，属 MIT 授权范围：

| 路径 | 说明 |
| --- | --- |
| `lsa-fnos/app/ui/message_zh.js` | 简体中文界面覆盖层（129 KB，逐条翻译） |
| `lsa-fnos/app/ui/languages/zh-CN/` | 中文告警 / 健康规格等语言资源 |

## 3. 商标声明

`LSI`、`MegaRAID`、`MegaRAID`、`Broadcom`、`CacheVault` 等名称与标识为其各自权利人的商标或注册商标。
`fnOS`、`飞牛` 为飞牛科技的产品与商标。

本项目为**非官方的第三方移植**，与 Broadcom Inc.、LSI、飞牛科技**均无隶属、赞助或背书关系**。

## 4. 免责声明

- 本项目涉及 **RAID 存储硬件的管理操作**，错误操作可能导致**数据丢失或不可逆的磁盘状态变更**。
- 作者不对因使用本项目造成的任何直接或间接损失负责。**使用前请确保数据已有备份。**
- `config/privilege` 以 **root** 身份运行（访问 RAID 设备节点所必需），这会扩大应用的权限面，
  请自行评估风险。
