# =============================================================================
# build.ps1 - Windows 环境下构建敏感词检测服务单架构镜像，生成离线部署包
#
# 用法：
#   .\scripts\build.ps1                       # latest + amd64
#   .\scripts\build.ps1 -Tag v0.1.0           # 指定 tag
#   .\scripts\build.ps1 -Tag v0.1.0 -Arch arm64   # 指定架构
#   .\scripts\build.ps1 -NoCache              # 禁用构建缓存
#
# 前置条件：已安装 Docker Desktop（含 buildx），在项目内任意位置运行均可。
#
# 产物（build\<tag>-<arch>\）：
#   - sensitive-word-filtering-<tag>-<arch>.tar
#   - docker-compose.yml / manage.sh / .env.example / DEPLOY.md
# =============================================================================

[CmdletBinding()]
param(
    [string]$Tag = "latest",
    [ValidateSet("amd64", "arm64")]
    [string]$Arch = "amd64",
    [switch]$NoCache
)

$ErrorActionPreference = "Stop"

$IMAGE_NAME = if ($env:IMAGE_NAME) { $env:IMAGE_NAME } else { "sensitive-word-filtering" }
$PLATFORM = "linux/$Arch"
$ArchTag = "$Tag-$Arch"
$FullTag = "${IMAGE_NAME}:${ArchTag}"
$TarName = "${IMAGE_NAME}-${ArchTag}.tar"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir "..")
$BuildRoot = Join-Path $RootDir "build"
$FinalDir = Join-Path $BuildRoot $ArchTag

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  $IMAGE_NAME - Build Image ($PLATFORM)" -ForegroundColor Cyan
Write-Host "========================================="
Write-Host "Image tag : $FullTag"

# 1. 检查 Docker 环境
Write-Host "`n[1/5] 检查 Docker 环境..." -ForegroundColor Yellow
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "未检测到 docker 命令，请先安装 Docker Desktop。"
}
$LAST = docker version 2>$null
if ($LASTEXITCODE -ne 0) { throw "Docker daemon 不可用，请启动 Docker Desktop 后重试。" }
$LAST = docker buildx version 2>$null
if ($LASTEXITCODE -ne 0) { throw "docker buildx 不可用。" }

# 2. 检查输出目录（拒绝覆盖）
Write-Host "`n[2/5] 检查输出目录..." -ForegroundColor Yellow
if (Test-Path -LiteralPath $FinalDir) {
    throw "输出目录已存在，拒绝覆盖: $FinalDir（先手动移除或换 tag/arch）"
}
New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
$WorkDir = Join-Path $BuildRoot (".tmp-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

try {
    # 3. 构建单架构镜像
    Write-Host "`n[3/5] 构建单架构镜像（buildx --load）..." -ForegroundColor Yellow
    $buildArgs = @(
        "buildx", "build",
        "--platform", $PLATFORM,
        "-f", (Join-Path $RootDir "Dockerfile"),
        "-t", $FullTag,
        "--load"
    )
    if ($NoCache) { $buildArgs += "--no-cache" }
    $buildArgs += "$RootDir"
    & docker @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "docker buildx build 执行失败，请查看上方日志。" }

    # 4. 导出镜像 tar
    Write-Host "`n[4/5] 导出镜像 tar..." -ForegroundColor Yellow
    & docker save -o (Join-Path $WorkDir $TarName) $FullTag
    if ($LASTEXITCODE -ne 0) { throw "docker save 执行失败。" }

    # 5. 组装部署包（构建脚本不进包：需要源码才有意义）
    Write-Host "`n[5/5] 组装部署包..." -ForegroundColor Yellow
    Copy-Item -LiteralPath (Join-Path $ScriptDir "docker-compose.yml") -Destination $WorkDir -Force
    Copy-Item -LiteralPath (Join-Path $ScriptDir "manage.sh") -Destination $WorkDir -Force
    Copy-Item -LiteralPath (Join-Path $ScriptDir "DEPLOY.md") -Destination $WorkDir -Force
    $envExample = (Get-Content -LiteralPath (Join-Path $ScriptDir ".env.example") -Raw) `
        -replace "__TAG__", $ArchTag
    [System.IO.File]::WriteAllText((Join-Path $WorkDir ".env.example"), $envExample, (New-Object System.Text.UTF8Encoding $false))

    Move-Item -LiteralPath $WorkDir -Destination $FinalDir
}
finally {
    if ($WorkDir -and (Test-Path -LiteralPath $WorkDir)) {
        Remove-Item -LiteralPath $WorkDir -Recurse -Force
    }
}

Write-Host "`n部署包生成成功: $FinalDir" -ForegroundColor Green
Write-Host "部署: 将该目录上传到服务器后执行 ./manage.sh load && ./manage.sh start" -ForegroundColor Green
