# 离线部署说明（sensitive-word-filtering）

目标：在只有 Docker 的 Linux 服务器上部署敏感词检测服务，无需源码与外网依赖。

## 部署包内容

| 文件 | 用途 |
|---|---|
| `sensitive-word-filtering-<tag>-<arch>.tar` | 单架构镜像包（`docker load` 用） |
| `docker-compose.yml` | 仅 `image:` 引用，无 `build:`；默认回环绑定 |
| `manage.sh` | 生命周期：load / start / stop / remove / logs |
| `.env.example` | 配置模板（首次 `start` 自动生成 `.env`，之后不覆盖） |
| `logs/`（运行后生成） | `logs` 子命令的归档目录 |

## 服务器前置

- 已安装 Docker 与 Compose（`docker compose` 或 `docker-compose` 任一）。
- 架构必须与镜像一致：`amd64` 包 → x86_64；`arm64` 包 → ARM 服务器。
  load 时架构不匹配会失败，不会静默运行错架构。

## 部署步骤

```bash
# 1. 上传部署包目录到服务器（scp / U 盘 / 制品平台任选）
scp -r build/<tag>-<arch> user@server:/opt/swf-filter

# 2. 进入目录并加载镜像
cd /opt/swf-filter
chmod +x manage.sh
./manage.sh load

# 3. 启动（首次自动创建 .env）
./manage.sh start

# 4. 验证
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/v1/check \
  -H 'Content-Type: application/json' \
  -d '{"text":"代办001工程许可"}'
```

## 配置（.env）

| 变量 | 默认 | 说明 |
|---|---|---|
| `TAG` | 由构建脚本写入 | 镜像标签（含架构后缀），决定 load 的 tar 文件名 |
| `HOST_BIND` | `127.0.0.1` | 端口绑定地址；**可信内网**部署改为内网 IP，`0.0.0.0` 需配合防火墙 |
| `HOST_PORT` | `8000` | 宿主机端口 |

编辑 `.env` 后 `./manage.sh start` 生效。**该服务无鉴权，不要直接暴露公网**；
跨主机调用请置于反向代理 / 内网防火墙之后。

## 日志

```bash
./manage.sh logs              # 快照写入 logs/manage-YYYY-MM-DD.log
./manage.sh logs --follow     # 持续跟随并追加
```

- 按日期分 file names；单文件默认 50 MiB 触发 `.1..9` 轮转；保留 30 天自动清理。
- 可用环境变量覆盖：`LOG_KEEP_DAYS` / `LOG_MAX_SIZE_MB` / `LOG_DIR`。
- Docker 侧另有 `json-file
bdYe` 轮转（10 MiB × 3），与归档独立。

## 生命周期说明

- `./manage.sh stop`：停容器，保留一切。
- `./manage.sh remove`：删容器与 Compose 网络；**保留**镜像、`.env`、日志与包目录。
- `.env` 一旦创建不会被脚本覆盖；模板更新不会影响既有配置。

## 升级 / 回滚

```bash
./manage.sh remove
# 上传新 tag 的部署包目录（新目录，互不覆盖）
cd ../<new-tag>-<arch> && ./manage.sh load && ./manage.sh start
```

## 常见失败

| 现象 | 原因与处理 |
|---|---|
| `TAG is required` | `.env` 缺失且无 `.env.example`（包不完整），重新取包 |
| load 找不到 tar | `.env` 的 `TAG` 与包内文件名不一致，勿手改 `TAG` |
| `exec format error` / 反复重启 | 镜像架构与服务器不符，使用对应 `amd64` / `arm64` 包 |
| 启动即退出 | 词库缺失或为空（fail-closed），`./manage.sh logs` 查看后换完整包 |
