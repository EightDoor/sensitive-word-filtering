# standalone-sensitive-word-api：独立敏感词检测 API 服务

## Why

现有敏感词过滤能力耦合在 `agent-backend` 聊天接口内部（`send_message` 前置 Hook），
其他系统想复用只能复制代码或走完整聊天链路。需要一份可独立部署、直接 HTTP 调用的
布尔检测服务：`文本 → 是否包含敏感词`。

本项目将检测核心（pyahocorasick 自动机 + houbb 中文词库）抽取为独立 Python 服务，
可打包成 Docker 离线部署包，在只有 Docker 的服务器上直接运行并调用 API。

## What Changes

- 新建独立项目 `sensitive-word-filtering`（Python 3.11 + uv + FastAPI），
  复用 `agent-backend/app/core/sensitive_word/` 的检测器实现与 64,418 行中文词库
  （来源 commit `fe6fc2921836217b8c90619db81b24af8b22d80f`，Apache-2.0，保留 LICENSE 与来源说明）。
- 检测语义与原实现一致：词库与输入统一 NFKC 规范化并忽略英文大小写；不忽略空格与标点；
  启动期构建只读自动机、命中即停、词库缺失或为空则启动失败（fail-closed）。
- HTTP 契约：
  - `POST /api/v1/check`，`{"text": "..."}` → `{"contains_sensitive_word": true|false}`（命中是正常 200 结果，
    不沿用聊天接口的 422 拒绝语义）；`text` 必须为字符串且 ≤10,000 字符，空串允许并返回 false。
  - 请求体上限 128 KiB，同时校验 Content-Length 与实际接收字节（覆盖分块传输），超限 413。
  - 结构化错误 `{"detail": {"code", "message"}}`：`INVALID_REQUEST`(422) /
    `REQUEST_TOO_LARGE`(413) / `INTERNAL_ERROR`(500)，固定文案、不回显输入。
  - `GET /health`：自动机就绪 200，否则 503。
  - 日志不记录正文、命中词与校验输入。
- Docker 交付：Python 3.11 slim 多阶段构建（uv 冻结锁、非 editable 安装、非 root、健康检查）；
  `scripts/build.sh` / `scripts/build.ps1` 按单架构（`linux/amd64` / `linux/arm64`，默认 amd64）
  构建并导出 `build/<tag>-<arch>/` 离线部署包（镜像 tar + docker-compose + manage.sh + 配置模板 + 部署说明）；
  Compose 默认 `127.0.0.1:8000` 回环绑定，仅 `image:` 无 `build:`。
- 项目采用 Apache-2.0 许可证；词库许可独立保留。

## Non-goals

- 不改动 `agent-backend` / `agent-frontend`，不把原聊天链路改为调用本服务。
- 不识别个人信息格式（手机号、身份证号等），不做语义审核。
- 不实现白名单、分类分级、命中词返回、批量接口、词库热更新、管理页面。
- 不实现繁简转换、拼音、谐音、跳字符匹配。
- 不提供应用层鉴权与 HTTPS（仅本机或可信内网部署，公网暴露交给反向代理）。
- 不推送镜像仓库，不自动提交 Git。

## Impact

- 新目录 `D:\project\my-project\github-opensource\sensitive-word-filtering`，与现有仓库零耦合。
- 依赖仅 FastAPI / Pydantic / Uvicorn / pyahocorasick（测试另加 pytest / httpx），运行期离线可用。
- 词库匹配存在变体绕过与正常词误报风险：上线前需真实问法抽样回归。

## Capabilities

### New Capabilities

- `sensitive-word-detector`：检测核心的归一化、fail-closed 初始化、只读复用与随包分发。
- `sensitive-word-filtering-api`：HTTP 契约、请求校验、请求体上限、结构化错误与日志约束。
- `sensitive-word-offline-deployment`：单架构 Docker 镜像与离线部署包交付。

### Modified Capabilities

- 无。
