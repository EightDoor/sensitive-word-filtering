#!/usr/bin/env bash
# =============================================================================
# manage.sh - 敏感词检测服务部署管理（load / start / stop / remove / logs）
#
# 用法：
#   ./manage.sh load              # 加载包内镜像 tar（文件名由 .env 的 TAG 决定）
#   ./manage.sh start             # 首次自动从 .env.example 创建 .env 后启动
#   ./manage.sh stop              # 停止容器
#   ./manage.sh remove            # 移除容器与网络（保留镜像 / 配置 / 日志）
#   ./manage.sh logs              # 一次性快照，写入 logs/
#   ./manage.sh logs --follow     # 持续跟随，追加写入 logs/
#
# 配置（.env，首次 start 自动从模板创建，之后不覆盖）：
#   TAG / HOST_BIND / HOST_PORT
# 日志（可选环境变量，默认）：
#   LOG_DIR=<deploy>/logs  LOG_KEEP_DAYS=30  LOG_MAX_SIZE_MB=50
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="${IMAGE_NAME:-sensitive-word-filtering}"
LOG_DIR="${LOG_DIR:-${SCRIPT_DIR}/logs}"
LOG_PREFIX="${LOG_PREFIX:-manage}"
LOG_KEEP_DAYS="${LOG_KEEP_DAYS:-30}"
LOG_MAX_SIZE_MB="${LOG_MAX_SIZE_MB:-50}"

die() { echo "ERROR: $*" >&2; exit 1; }

usage() {
  sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

require_docker() {
  command -v docker >/dev/null 2>&1 || die "未检测到 docker 命令"
  docker version >/dev/null 2>&1 || die "Docker daemon 不可用"
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    die "未找到 docker compose"
  fi
}

# 从 .env 读取 KEY 的值（只解析不执行文件内容）
env_value() {
  local key="$1"
  grep -E "^${key}=" "${SCRIPT_DIR}/.env" | tail -1 | cut -d= -f2-
}

ensure_env() {
  if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    [ -f "${SCRIPT_DIR}/.env.example" ] || die "缺少 .env.example，无法创建配置"
    cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
    echo "已从模板创建 .env（默认配置）"
  fi
}

cmd_load() {
  require_docker
  ensure_env
  local tag tar
  tag="$(env_value TAG)"
  [ -n "$tag" ] || die ".env 缺少 TAG"
  [ "$tag" != "__TAG__" ] || die ".env 的 TAG 仍是占位符，请使用构建脚本产出的部署包"
  tar="${SCRIPT_DIR}/${IMAGE_NAME}-${tag}.tar"
  [ -f "$tar" ] || die "镜像包不存在: ${tar}（load 只加载包内既定文件，不扫描任意 tar）"
  docker load -i "$tar"
}

# 按日分 file names + 单文件大小轮转（.1..9，保留 LOG_KEEP_DAYS 天）
rotate_log() {
  mkdir -p "$LOG_DIR"
  local f="${LOG_DIR}/${LOG_PREFIX}-$(date +%F).log"
  local max=$((LOG_MAX_SIZE_MB * 1024 * 1024))
  if [ -f "$f" ] && [ "$(wc -c < "$f")" -ge "$max" ]; then
    rm -f "${f}.10"
    local i
    for i in 9 8 7 6 5 4 3 2 1; do
      if [ -f "${f}.${i}" ]; then
        mv -f "${f}.${i}" "${f}.$((i + 1))"
      fi
    done
    mv -f "$f" "${f}.1"
  fi
  find "$LOG_DIR" -name "${LOG_PREFIX}-*.log*" -mtime +"$LOG_KEEP_DAYS" -delete 2>/dev/null || true
}

cmd_logs() {
  require_docker
  ensure_env
  rotate_log
  local f="${LOG_DIR}/${LOG_PREFIX}-$(date +%F).log"
  case "${1:-}" in
    --follow | -f)
      # shortcut: follow 仅在启动时检查大小轮转，跟随期间依赖按日分 file names
      compose logs -f --no-color 2>&1 | tee -a "$f"
      ;;
    *)
      compose logs --no-color > "$f" 2>&1
      echo "已写入 ${f}"
      ;;
  esac
}

cmd_start() {
  require_docker
  ensure_env
  compose up -d
}

cmd_stop() {
  require_docker
  ensure_env
  compose stop
}

# 仅移除容器与 Compose 网络：镜像、部署包、.env 与 logs 全部保留（不加 -v / --rmi）
cmd_remove() {
  require_docker
  ensure_env
  compose down
}

case "${1:-}" in
  load) cmd_load ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  remove) cmd_remove ;;
  logs)
    shift
    cmd_logs "$@"
    ;;
  *) usage ;;
esac
