# LSA for fnOS — 英文包工程

本目录是 **英文包**（`appname=lsaen`，产物 `lsaen.fpk`）的 FPK 工程。
中文包见 `../lsa-fnos/`（`appname=lsa`，产物 `lsa.fpk`）。

> **两个包共用 LSA 服务目录与端口，不能同时安装或运行。**

本包提供**原生英文界面**（不注入中文覆盖层），适合英文环境或多语言混用场景。

## 工程结构

```
lsa-fnos-en/
├── manifest              # FPK 应用描述（appname=lsaen）
├── ICON.PNG              # 64x64 应用图标
├── ICON_256.PNG          # 256x256 应用图标
├── build.sh              # 打包辅助脚本（依赖 ../gcc_11.2.x/，见下）
├── cmd/                  # fnOS 生命周期脚本（核心）
├── config/               # privilege（root 运行）、resource
├── wizard/               # 安装 / 配置向导定义
└── app/
    ├── debs/             # ← 需放入原厂 deb（见 debs/README.md 与仓库 NOTICE.md）
    └── ui/               # 桌面入口 + CGI 代理
```

## 与中文包的差异

1. `cmd/main`：本包把 `health_spec` 指向 `en-US/healthspec.json`
2. `cmd/install_callback`：本包不安装中文覆盖层，并会**删除** `message_zh.js` 恢复原生英文
3. `app/ui/cgi_proxy.py`：本包 `CGI_BASE=/cgi/ThirdParty/lsaen/index.cgi/`
4. `app/ui/config`：桌面入口使用英文 `title`（`LSI Storage Authority`）

> 除上述差异外，两个工程的文件内容相同。修改其一后需同步另一侧，
> 注意 `CGI_BASE` 与 manifest 的 `appname` 必须保持对应。

## 构建

### 前置：准备原厂 deb

3 个 Broadcom / LSI 原厂 deb **不随仓库分发**，需自行从官方渠道获取。
内容与中文包所用完全相同（同一份厂商二进制）：

```
app/debs/LSIStorageAuthority-008.017.010.000-1_amd64.deb   (~24 MB)
app/debs/LSA_lib_utils-1.18-1_amd64.deb                    (~2.4 MB)
app/debs/LSA_lib_utils2-9.00-1_amd64.deb                   (~376 KB)
```

获取方式与授权说明见仓库根目录 `NOTICE.md`。就位后可用下面的脚本检查：

```bash
bash ../tools/check-debs.sh
```

### 打包

```bash
# 在仓库根目录（fnpack 位于此处）
../fnpack-1.2.3-windows-amd64.exe build     # Windows
../fnpack-1.2.3-linux-amd64 build           # Linux
```

产物为当前目录下的 `lsaen.fpk`。

> **关于 `build.sh`**：该脚本第 1 步从 `../gcc_11.2.x/` 复制 deb。若此目录不存在会直接报错退出，
> 因此在本仓库中**建议直接用 `fnpack build`**，或按上面「前置」手动放置 deb。

fnpack 下载：https://developer.fnnas.com/docs/cli/fnpack/

## 安装到飞牛 fnOS

fnOS **不支持本地 FPK 就地升级**，新版本一律走**卸载 → 安装**。

**方式一：应用中心 Web 界面**（推荐）
登录 fnOS → 应用中心 → 选择本地安装 → 上传 `lsaen.fpk`

**方式二：命令行**
```bash
trim-cli app install ./lsaen.fpk
```

安装后桌面出现「LSI Storage Authority」图标。默认端口：Web 管理 `2463`、LSA 服务 `9000`。

## 相关文档

- 仓库根目录 `README.md` — 项目总览
- 仓库根目录 `HANDOVER.md` — 架构、构建链路、已知风险、维护约定
- 仓库根目录 `FNOS_DEV_GUIDE.md` — 飞牛 fnOS 开发规范手册
