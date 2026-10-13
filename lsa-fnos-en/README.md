# LSA FPK - LSI Storage Authority for 飞牛 fnOS

将 Broadcom LSI Storage Authority (LSA) 移植为飞牛 fnOS FPK 应用，可在飞牛桌面直接打开进行 RAID 存储管理。

## 项目结构

```
lsa-fnos/
├── manifest              # FPK 应用描述文件
├── ICON.PNG              # 64x64 应用图标
├── ICON_256.PNG          # 256x256 应用图标
├── build.sh              # 打包辅助脚本
├── cmd/
│   ├── main              # 服务控制 (start/stop/status)
│   ├── install_init      # 安装前：安装 deb 包和配置端口
│   ├── install_callback  # 安装后：设置权限和开机启动
│   ├── upgrade_init      # 升级前：停止服务并备份配置
│   ├── upgrade_callback  # 升级后：恢复配置
│   ├── uninstall_init    # 卸载前：停止服务并清理
│   ├── uninstall_callback
│   ├── config_init       # 配置变更：更新端口
│   └── config_callback   # 配置变更后：重启服务
├── config/
│   ├── privilege         # 权限：root 运行
│   └── resource          # 资源声明
├── wizard/
│   ├── install           # 安装向导：端口和模式选择
│   └── config            # 配置向导：修改端口
└── app/
    ├── debs/             # 捆绑的 LSA deb 包（构建时填充）
    └── ui/
        ├── config        # 桌面入口配置
        └── images/       # 应用图标
```

## 系统要求

- **飞牛 fnOS** >= 1.0.0
- **架构**：x86_64 (不支持 ARM)
- **硬件**：需要 Broadcom/LSI SAS RAID 控制器
- **内核驱动**：fnOS 内核需包含对应控制器驱动 (mpt3sas / megaraid_sas / smartpqi)

## 支持的 RAID 控制器

- Broadcom 3916 SAS3/PCIe4 Tri-mode RAID on Chip
- SAS 3516 Ventura based MegaRAID and iMR
- SAS 3108 (Invader) based MegaRAID and iMR
- SAS 3008 (Fury) based HBAs
- 9660/9670/9600/9620 Family Adapters
- Wellsburg & Lewisburg SATA chipset based Software RAID

## 构建步骤

### 1. 准备环境

在开发电脑上安装 fnpack 工具：

```bash
# Linux
chmod +x fnpack-1.2.3-linux-amd64
sudo mv fnpack-1.2.3-linux-amd64 /usr/local/bin/fnpack
```

下载地址：https://developer.fnnas.com/docs/cli/fnpack/

### 2. 运行构建脚本

```bash
cd lsa-fnos
chmod +x build.sh
./build.sh
```

构建脚本会自动：
- 从 `gcc_11.2.x/` 目录复制 deb 包到 `app/debs/`
- 生成占位图标（需要 ImageMagick）
- 设置脚本执行权限
- 调用 fnpack 生成 .fpk 文件

### 3. 手动构建（可选）

如果不想用构建脚本，也可以手动操作：

```bash
# 复制 deb 包
cp ../gcc_11.2.x/LSIStorageAuthority-008.017.010.000-1_amd64.deb app/debs/
cp ../gcc_11.2.x/LSA_lib_utils-1.18-1_amd64.deb app/debs/
cp ../gcc_11.2.x/LSA_lib_utils2-9.00-1_amd64.deb app/debs/

# 打包
fnpack build
```

## 安装到飞牛 fnOS

### 方法一：通过应用中心安装

1. 将生成的 `.fpk` 文件复制到飞牛 fnOS 设备
2. 使用 appcenter-cli 安装：
   ```bash
   appcenter-cli install ./lsa-8.17.010.fpk
   ```

### 方法二：通过 Web 界面安装

1. 登录飞牛 fnOS 管理界面
2. 进入应用中心
3. 选择本地安装，上传 `.fpk` 文件

## 使用方法

1. 安装完成后，在飞牛桌面找到 **LSI Storage Authority** 图标
2. 点击图标即可在飞牛桌面窗口内打开 LSA 管理界面
3. 使用浏览器访问 `http://<飞牛IP>:<Web端口>` 也可以直接访问

### 默认端口

- Web 管理端口：2463
- LSA 服务端口：9000

端口可在安装向导中自定义，也可在应用设置中修改。

## 注意事项

1. **许可证**：LSA 是 Broadcom 的商业软件，仅限内部使用，不可公开发布
2. **硬件驱动**：确保 fnOS 内核已加载 RAID 控制器驱动
   ```bash
   # 检查驱动
   lsmod | grep -E "mpt3sas|megaraid|smartpqi"
   ```
3. **Root 权限**：LSA 需要 root 权限访问 RAID 控制器硬件
4. **仅管理员可见**：桌面入口默认仅对管理员用户显示

## 故障排查

### LSA 无法启动

```bash
# 检查服务状态
ssh root@<fnos-ip>
service LsiSASH status

# 查看日志
cat /opt/lsi/LSIStorageAuthority/logs/*.log
```

### 无法检测到 RAID 控制器

```bash
# 检查内核驱动
lsmod | grep -E "mpt3sas|megaraid|smartpqi"

# 检查硬件
lspci | grep -i "LSI\|Broadcom\|MegaRAID"
```

### 端口冲突

在应用设置中修改端口，或通过 SSH：
```bash
# 修改 Web 端口
sed -i 's/listen [0-9]\+ default_server/listen 新端口 default_server/' /opt/lsi/LSIStorageAuthority/server/conf/nginx.conf

# 重启服务
service LsiSASH restart
```

## 参考文档

- [飞牛应用开放平台](https://developer.fnnas.com/docs/guide/)
- [FPK 应用框架](https://developer.fnnas.com/docs/core-concepts/framework/)
- [fnpack 打包工具](https://developer.fnnas.com/docs/cli/fnpack/)
