#!/bin/bash
set -euo pipefail
shopt -s globstar

cd util/api_common/bilibili_activity/protos

python -m grpc_tools.protoc \
  --proto_path=. \
  --python_out=. \
  --mypy_out=. \
  --grpc_python_out=. \
  --mypy_grpc_out=. \
  **/*.proto

# 移除空的 grpc 文件
for file in **/*_grpc.py; do
  if ! grep Stub $file -q; then
    rm $file ${file}i
  fi
done

# 修正 import
sed -i 's/\(from\|import\) bilibili/\1 util.api_common.bilibili_activity.protos.bilibili/' \
  **/*.py **/*.pyi
