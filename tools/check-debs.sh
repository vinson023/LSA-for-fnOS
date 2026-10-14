#!/bin/bash
# 构建依赖检查：确认 3 个 Broadcom/LSI 原厂 deb 已就位。
#
# 用法：  bash tools/check-debs.sh
#
# 这些 deb 不随仓库分发（版权与体积原因），需自行从 Broadcom 官方获取。
# 详见仓库根目录 NOTICE.md。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

REQUIRED=(
  "LSIStorageAuthority-008.017.010.000-1_amd64.deb"
  "LSA_lib_utils-1.18-1_amd64.deb"
  "LSA_lib_utils2-9.00-1_amd64.deb"
)

TARGETS=(
  "$REPO_ROOT/lsa-fnos/app/debs"
  "$REPO_ROOT/lsa-fnos-en/app/debs"
)

echo "=== 检查构建依赖（Broadcom/LSI 原厂 deb）==="
echo ""

missing=0

for target in "${TARGETS[@]}"; do
  rel="${target#"$REPO_ROOT"/}"
  echo "[$rel]"
  for deb in "${REQUIRED[@]}"; do
    if [ -f "$target/$deb" ]; then
      size="$(du -h "$target/$deb" | cut -f1)"
      echo "  OK       $deb  ($size)"
    else
      echo "  缺失     $deb"
      missing=$((missing + 1))
    fi
  done
  echo ""
done

if [ "$missing" -eq 0 ]; then
  echo "全部就位，可以构建："
  echo "  cd lsa-fnos    && ../fnpack-1.2.3-windows-amd64.exe build"
  echo "  cd lsa-fnos-en && ../fnpack-1.2.3-windows-amd64.exe build"
  exit 0
else
  echo "有 $missing 个文件缺失，无法构建。"
  echo ""
  echo "请从 Broadcom 官方渠道获取上述 deb，放入对应 app/debs/ 目录。"
  echo "它们不随本仓库分发，详见 NOTICE.md。"
  exit 1
fi
