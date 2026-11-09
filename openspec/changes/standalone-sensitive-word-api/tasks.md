# standalone-sensitive-word-api 任务列表

## Phase 1：OpenSpec artifacts

- [x] `proposal.md` / 三个 capability 的 `spec.md` / `design.md` / `tasks.md` 创建完成
- [x] `openspec validate standalone-sensitive-word-api --type change --strict` 通过（最终复验仍 valid）

## Phase 2：项目骨架与检测核心

- [x] `pyproject.toml`（name `sensitive-word-filtering`、requires-python `>=3.11,<3.12`、
      fastapi==0.140.0 / pydantic==2.13.4 / uvicorn==0.51.0 / pyahocorasick==2.3.1、
      dev 依赖 pytest / httpx、uv_build 后端 + src 布局）
- [x] `uv lock` 独立锁文件（24 包；`uv sync --frozen` 与 Docker 内一致）
- [x] `src/sensitive_word_filtering/detector.py`：normalize / initialize / contains / is_ready
      （包资源 `dictionaries/sensitive_word_dict.txt`、fail-closed、幂等、命中即停）
- [x] 词库 + `LICENSE.txt` + `NOTICE.md` 复制完成，三个文件 SHA-256 与源仓库逐一一致（64,418 行）
- [x] `src/sensitive_word_filtering/__init__.py`

## Phase 3：FastAPI 服务

- [x] `errors.py`：5 个错误码与固定文案常量
- [x] `main.py`：lifespan 初始化、`POST /api/v1/check`（同步路由、text ≤10,000、extra=forbid）、
      `GET /health`、RequestValidationError / StarletteHTTPException / 未捕获异常三个结构化处理器
      （400→`INVALID_REQUEST`：body 解析失败含非法 UTF-8，属客户端错误不冒充服务端错误）
- [x] 请求体 128 KiB ASGI 中间件：**预读缓冲 + Content-Length 与实际字节双校验**→ 413；
      （原 receive 抛异常方案被 FastAPI 包成 400 的问题已定位并弃用，见 design/代码注释）
- [x] `.gitignore`、`LICENSE`（Apache-2.0，取自词库许可文件）、`THIRD_PARTY_NOTICES.md`

## Phase 4：测试

- [x] `tests/test_detector.py`：固定词表 12 例（命中/未命中/大小写/全半角/空白标点不忽略/
      空输入/归一化/未初始化抛错/词库缺失与空词库拒启/幂等/is_ready/命中即停）
- [x] `tests/test_dictionary.py`：真实词库 >6 万词条 + 真实词条命中
- [x] `tests/test_api.py`：true/false、空串、10,000 边界、缺字段/null/非字符串/超长/额外字段→422、
      畸形 JSON、health(200/503)、未启动 500 不返回 false、词库为空拒启、OpenAPI、
      结构化 404/405、非法 UTF-8→400 `INVALID_REQUEST`、检测异常→500 不回显输入
- [x] `tests/test_body_limit.py`：裸 ASGI 直测 6 例（Content-Length 超限 / 非数字头 /
      无头分块超限 / 谎报头 / 恰好等于上限 / 正常请求），超限均不进检测器
- [x] `uv run pytest -q` → **41 passed**

## Phase 5：Docker 与部署脚本

- [x] `Dockerfile`：python:3.11-slim 多阶段、`uv sync --frozen --no-dev --no-editable`（词库进
      site-packages）、非 root（swf）、HEALTHCHECK /health、单 worker uvicorn :8000
- [x] `.dockerignore`（venv/env/tests/OpenSpec/build 等；不排词库与许可）
- [x] `scripts/docker-compose.yml`：image-only、`${TAG:?}` fail-fast、env_file、
      `${HOST_BIND:-127.0.0.1}:${HOST_PORT:-8000}:8000` 回环默认、restart、json-file
bdYe 轮转
- [x] `scripts/build.sh` / `scripts/build.ps1`：tag + amd64|arm64（默认 amd64，ValidateSet/case 双拦非法架构）、
      buildx 单架构 --load、`build/<tag>-<arch>/` 临时目录原子发布、拒绝覆盖、部署包不含构建脚本
- [x] `scripts/manage.sh`：load（仅包内既定 tar）/ start（.env 不存在才从模板创建）/ stop /
      remove（不删镜像配置日志）/ logs（快照 + --follow、按日分 file names、50 MiB×.1..9、30 天清理）
- [x] `scripts/.env.example`（TAG 占位由构建脚本替换为 `<tag>-<arch>`）、`scripts/DEPLOY.md`
- [x] `README.md`（API/开发/构建/部署/词库更新/已知限制/许可证）

## Phase 6：验证（实测结果）

- [x] `uv run pytest -q` → 41 passed
- [x] `uv build` wheel 含词库+LICENSE+NOTICE；仓库外 venv 安装后 资源可读 + hit/miss/大小写 全对
- [x] `bash -n build.sh manage.sh` 通过；shell 脚本 LF 无 BOM；`build.ps1` UTF-8 **带 BOM** + PowerShell parser 通过
- [x] 非法架构（riscv）→ 脚本非零退出；已存在输出目录 → 拒绝覆盖（均实测）
- [x] amd64 构建 + 部署包 5 件套（tar/compose/manage.sh/.env.example/DEPLOY.md）齐；容器实测：
      health ok、中文 hit/miss/空串 200、非法 UTF-8→400 `INVALID_REQUEST`、缺字段→422、404→`NOT_FOUND`、
      128 KiB→413、openapi 200、logs 快照、stop/remove 干净、镜像保留
- [x] arm64 构建 + 部署包生成；**QEMU 下运行时冒烟通过**（initialize + 中文 hit）
- [x] 排查记录：Git-Bash curl `-d '中文'` 按本地代码页发字节导致的 400 为测试工具问题（UTF-8 file inside 实证服务正确）；
      该问题同时暴露并修复了 400→INTERNAL_ERROR 的错误映射
- [x] 原 `agent-backend` / `agent-frontend` 工作区干净，无未提交残留（本轮零改动）
