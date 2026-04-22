#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="web/.env.production"
if [[ -z "${DEEPINSIGHT_ENV_FILE:-}" ]]; then
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "未找到生产环境文件: $ENV_FILE" >&2
    echo "请先根据 web/.env.example 创建 web/.env.production，或显式设置 DEEPINSIGHT_ENV_FILE" >&2
    exit 1
  fi
  export DEEPINSIGHT_ENV_FILE="$ENV_FILE"
fi

echo "启动 DeepInsight 生产模式"
echo "环境文件: ${DEEPINSIGHT_ENV_FILE}"

exec python3 scripts/run_gunicorn.py "$@"
