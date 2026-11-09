#!/usr/bin/env bash
# =============================================================================
# build.sh - 构建敏感词检测服务单架构镜像，生成离线部署包（build/<tag>-<arch>/）
#
# 用法：
#   ./scripts/build.sh                 # latest + amd64
#   ./scripts/build.sh v0.1.0          # 指定 tag + amd64
#   ./scripts/build.sh v0.1.0 arm64    # 指定 tag + arm64
#   TAG=... ARCH=... ./scripts/build.sh    # 环境变量兜底（命令行参数优先）
#
# 产物（build/<tag>-<arch>/）：
#   - sensitive-word-filtering-<tag>-<arch>.tar   镜像包
#   - docker-compose.yml / manage.sh / .env.example / DEPLOY.md
#
# 部署：上传该目录到目标机器后：
#   cd build/<tag>-<arch> && ./manage.sh load && ./manage.sh start
# =============================================================================
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-sensitive-word-filtering}"
TAG_INPUT="${1:-${TAG:-latest}}"
ARCH="${2:-${ARCH:-amd64}}"

case "$ARCH" in
  amd64) PLATFORM="linux/amd64" ;;
  arm64) PLATFORM="linux/arm64" ;;
  *)
    echo "ERROR: 不支持的架构: ${ARCH}（仅允许 amd64 | arm64）" >&2
    exit 1
    ;;
esac

ARCH_TAG="${TAG_INPUT}-${ARCH}"
FULL_TAG="${IMAGE_NAME}:${ARCH_TAG}"
TAR_NAME="${IMAGE_NAME}-${ARCH_TAG}.tar"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_ROOT="${ROOT_DIR}/build"
FINAL_DIR="${BUILD_ROOT}/${ARCH_TAG}"

die() { echo "ERROR: $*" >&2; exit 1; }

echo "=========================================="
echo "  ${IMAGE_NAME} - Build Image (${PLATFORM})"
echo "=========================================="
echo "Root dir : ${ROOT_DIR}"
echo "Image tag : ${FULL_TAG}"
echo

echo "[1/5] 检查 Docker 环境 ..."
command -v docker >/dev/null 2>&1 || die "未检测到 docker 命令，请先安装 Docker。"
docker version >/dev/null 2>&1 || die "Docker daemon 不可用，请确认服务已启动。"
docker buildx version >/dev/null 2>&1 || die "docker buildx 不可用。"
echo "Docker    : $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo unknown)"
echo "buildx    : $(docker buildx version --format '{{.Version}}' 2>/dev/null || echo unknown)"

echo "[2/5] 检查输出目录 ..."
if [ -e "$FINAL_DIR" ]; then
  die "输出目录已存在，拒绝覆盖: ${FINAL_DIR}（先手动移除或换 tag/arch）"
fi
mkdir -p "$BUILD_ROOT"
WORK_DIR="$(mktemp -d "${BUILD_ROOT}/.tmp-XXXXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "[3/5] 构建单架构镜像（buildx --load）..."
docker buildx build \
  --platform "$PLATFORM" \
  -f "${ROOT_DIR}/Dockerfile" \
  -t "$FULL_TAG" \
  --load \
  "$ROOT_DIR"

echo "[4/5] 导出镜像 tar ..."
docker save -o "${WORK_DIR}/${TAR_NAME}" "$FULL_TAG"
echo "镜像包  : ${TAR_NAME}"

echo "[5/5] 组装部署包 ..."
# 构建脚本不进部署包：它需要源码与 Dockerfile 才有意义
cp "${SCRIPT_DIR}/docker-compose.yml" "${SCRIPT_DIR}/manage.sh" "${SCRIPT_DIR}/DEPLOY.md" "${WORK_DIR}/"
sed "s/__TAG__/${ARCH_TAG}/g" "${SCRIPT_DIR}/.env.example" > "${WORK_DIR}/.env.example"
chmod +x "${WORK_DIR}/manage.sh"

# 临时目录与目标同文件系统，原子发布；目标已存在时上面已拦截
mv "$WORK_DIR" "$FINAL_DIR"
trap - EXIT

echo
echo "部署包生成成功: ${FINAL_DIR}"
ls -la "$FINAL_DIR"
echo
echo "部署: cd build/${ARCH_TAG} && ./manage.sh load && ./manage.sh start"
