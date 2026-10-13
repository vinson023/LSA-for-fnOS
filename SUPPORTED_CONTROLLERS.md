# LSI Storage Authority 受支持的控制器说明

本说明以随 LSI Storage Authority Linux 64 位安装包提供的 Broadcom 官方 README 为准。它表明 LSA 可管理的控制器系列，并不等同于每个具体型号都支持所有 RAID 和维护功能。

## 官方列出的受支持控制器

| 控制器系列或平台 | 定位 | 说明 |
| --- | --- | --- |
| Broadcom 3916 SAS3/PCIe 4.0 Tri-Mode RAID on Chip | RAID on Chip | 支持 SAS/SATA/NVMe Tri-Mode 的 SoC RAID 平台。 |
| SAS 3516 (Ventura) 系 | MegaRAID / iMR | 包括基于 3516 的 MegaRAID 与 iMR 控制器。 |
| SAS 3108 (Invader) 系 | MegaRAID / iMR | 包括基于 3108 的 MegaRAID 与 iMR 控制器。 |
| SAS 3008 (Fury) 系 | HBA | 包括基于 3008 的 HBA。 |
| Wellsburg / Lewisburg SATA 芯片组 | 软件 RAID | 基于该 SATA 芯片组的 Software RAID。 |
| SAS3816 系 | IOC | 基于 SAS3816 的 I/O 控制器。 |
| SAS3808 系 | IOC | 基于 SAS3808 的 I/O 控制器。 |
| SAS3008 系 | HBA | 基于 SAS3008 的 HBA。 |
| Initiator-Target 3 (IT3) | IT 控制器 | 以直通传输为主的 Initiator-Target 控制器。 |
| 9660 系列 | RAID 适配器 | Broadcom 9660 Family RAID Adapters。 |
| 9670 系列 | RAID 适配器 | Broadcom 9670 Family RAID Adapters。 |
| 9600 系列 | eHBA 适配器 | Broadcom 9600 Family eHBA Adapters。 |
| 9620 系列 | eHBA 适配器 | Broadcom 9620 Family eHBA Adapters。 |

## 使用时的边界

- LSA 可管理不代表该控制器支持所有 RAID 级别、缓存策略、JBOD、固件更新或 NVMe 管理功能。
- 实际功能取决于具体适配器型号、固件版本、驱动、许可证、背板和磁盘连接拓扑。
- HBA、IT 和 eHBA 以盘柜/设备发现与健康信息管理为主；它们未必提供 MegaRAID 那样的硬件 RAID 配置界面。
- 在生产环境执行初始化、重建、删除虚拟磁盘、切换缓存策略等操作前，请先确认阵列及备份状态。

## 应用中心简版说明

支持 Broadcom/LSI MegaRAID、iMR、HBA、IT 和 eHBA 控制器，包括 9660、9670 RAID 适配器与 9600、9620 eHBA 适配器。具体可用功能以硬件型号、固件、许可证与连接拓扑为准。
