#!/bin/bash

# LSA FPK Build Script
# This script prepares and builds the LSA FPK package

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
DEB_SOURCE_DIR="$SCRIPT_DIR/../gcc_11.2.x"

echo "=== LSA FPK Build Script ==="
echo ""

# Step 1: Copy deb packages to app/debs/
echo "[1/4] Copying deb packages..."
mkdir -p "$PROJECT_DIR/app/debs"

# Copy LSA main package
if [ -f "$DEB_SOURCE_DIR/LSIStorageAuthority-008.017.010.000-1_amd64.deb" ]; then
    cp "$DEB_SOURCE_DIR/LSIStorageAuthority-008.017.010.000-1_amd64.deb" "$PROJECT_DIR/app/debs/"
    echo "  - LSA main package copied"
else
    echo "  ERROR: LSA main package not found at $DEB_SOURCE_DIR/LSIStorageAuthority-008.017.010.000-1_amd64.deb"
    exit 1
fi

# Copy lib_utils packages
if [ -f "$DEB_SOURCE_DIR/LSA_lib_utils-1.18-1_amd64.deb" ]; then
    cp "$DEB_SOURCE_DIR/LSA_lib_utils-1.18-1_amd64.deb" "$PROJECT_DIR/app/debs/"
    echo "  - LSA lib_utils copied"
fi

if [ -f "$DEB_SOURCE_DIR/LSA_lib_utils2-9.00-1_amd64.deb" ]; then
    cp "$DEB_SOURCE_DIR/LSA_lib_utils2-9.00-1_amd64.deb" "$PROJECT_DIR/app/debs/"
    echo "  - LSA lib_utils2 (OpenSLP) copied"
fi

# Step 2: Generate placeholder icons if not present
echo ""
echo "[2/4] Checking icons..."
if [ ! -f "$PROJECT_DIR/ICON.PNG" ]; then
    echo "  WARNING: ICON.PNG not found. Please provide a 64x64 PNG icon."
    echo "  Creating placeholder..."
    # Create a simple placeholder using ImageMagick if available
    if command -v convert > /dev/null 2>&1; then
        convert -size 64x64 xc:steelblue -gravity center -pointsize 10 -fill white -annotate 0 "LSA" "$PROJECT_DIR/ICON.PNG"
        echo "  - Placeholder ICON.PNG created"
    else
        echo "  - Please manually create ICON.PNG (64x64 PNG)"
    fi
fi

if [ ! -f "$PROJECT_DIR/ICON_256.PNG" ]; then
    echo "  WARNING: ICON_256.PNG not found. Please provide a 256x256 PNG icon."
    if command -v convert > /dev/null 2>&1; then
        convert -size 256x256 xc:steelblue -gravity center -pointsize 24 -fill white -annotate 0 "LSA" "$PROJECT_DIR/ICON_256.PNG"
        echo "  - Placeholder ICON_256.PNG created"
    else
        echo "  - Please manually create ICON_256.PNG (256x256 PNG)"
    fi
fi

if [ ! -f "$PROJECT_DIR/app/ui/images/icon_64.png" ]; then
    mkdir -p "$PROJECT_DIR/app/ui/images"
    if command -v convert > /dev/null 2>&1; then
        convert -size 64x64 xc:steelblue -gravity center -pointsize 10 -fill white -annotate 0 "LSA" "$PROJECT_DIR/app/ui/images/icon_64.png"
        echo "  - Placeholder app icon created"
    fi
    if [ -f "$PROJECT_DIR/ICON_256.PNG" ] && command -v convert > /dev/null 2>&1; then
        cp "$PROJECT_DIR/ICON_256.PNG" "$PROJECT_DIR/app/ui/images/icon_256.png"
    fi
fi

# Step 3: Ensure all scripts are executable
echo ""
echo "[3/4] Setting permissions..."
chmod +x "$PROJECT_DIR/cmd/"* 2>/dev/null || true
echo "  - Scripts marked as executable"

# Step 4: Build FPK
echo ""
echo "[4/4] Building FPK package..."
if command -v fnpack > /dev/null 2>&1; then
    cd "$PROJECT_DIR"
    fnpack build
    echo ""
    echo "=== Build Complete ==="
    echo "FPK package created successfully!"
else
    echo "  WARNING: fnpack not found in PATH."
    echo "  Download fnpack from: https://developer.fnnas.com/docs/cli/fnpack/"
    echo ""
    echo "  After installing fnpack, run:"
    echo "    cd $PROJECT_DIR"
    echo "    fnpack build"
    echo ""
    echo "=== Preparation Complete ==="
    echo "All files are ready. Install fnpack and run 'fnpack build' to create the FPK."
fi