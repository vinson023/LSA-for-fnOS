#!/bin/bash

PYTHON_BIN="$(command -v python3 2>/dev/null)"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -z "$PYTHON_BIN" ]; then
    printf 'Status: 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\npython3 is required'
    exit 1
fi
exec "${PYTHON_BIN}" "${SCRIPT_DIR}/cgi_proxy.py"
