# 此目录需放入 3 个 Broadcom / LSI 原厂 deb 后才能构建。
#
#   LSIStorageAuthority-008.017.010.000-1_amd64.deb   (~24 MB)
#   LSA_lib_utils-1.18-1_amd64.deb                    (~2.4 MB)
#   LSA_lib_utils2-9.00-1_amd64.deb                   (~376 KB)
#
# 这些文件不随本仓库分发（版权与体积原因），请从 Broadcom 官方渠道
# 下载对应版本，并遵守其 EULA。详见仓库根目录 NOTICE.md。
#
# 就位后执行：
#   cd .. && ../fnpack-1.2.3-windows-amd64.exe build
#
# 或先跑依赖检查：
#   bash ../../../tools/check-debs.sh
