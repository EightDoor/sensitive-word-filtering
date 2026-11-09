# sensitive-word-filtering

独立敏感词检测 API 服务：**文本 → 是否包含敏感词（布尔）**。

- 检测核心：`pyahocorasick` Aho-Corasick 自动机 + houbb 中文词库（64,418 行，Apache-2.0，来源见
  `THIRD_PARTY_NOTICES.md`）
- 词库与输入统一 **NFKC 规范化并忽略英文大小写**；不忽略空格与标点（防拆字误报）
- 启动期构建只读自动机，命中即停；词库缺失 / 为空直接启动失败（fail-closed）
- FastAPI + Python 3.11 + uv；Docker 单架构镜像与**离线部署包**（镜像 tar + Compose + manage.sh）
- 与 `agent-backend` 聊天链路零耦合（检测语义为其抽取副本，两边各自演进）

## API

### POST /api/v1/check

```bash
curl -X POST http://127.0.0.1:8000/api/v1/check \
  -H 'Content-Type: application/json' \
  -d '{"text":"代办001工程许可"}'
# {"contains_sensitive_word":true}
```

- `text`：必填字符串，≤10,000 字符；空串允许（返回 `false`）；未知字段拒绝（422）
- 命中是正常 **200** 结果，由调用方决定是否拒绝
- 请求体上限 **128 KiB**（同时校验 Content-Length 与实际字节，分块无法绕过）→ 413

### GET /health

```json
{"status":"ok"}
```

未就绪（检测器未初始化）返回 503。

### 错误形状

所有错误统一为 `{"detail":{"code":"...","message":"固定文案"}}`，**不回显输入**：

| code | 状态码 | 含义 |
|---|---|---|
| `INVALID_REQUEST` | 422 | 字段缺失 / 类型 / 超长 / 多余字段 / 畸形 JSON |
| `REQUEST_TOO_LARGE` | 413 | 请求体超 128 KiB 或 Content-Length 非法 |
| `INTERNAL_ERROR` | 500 | 检测器异常（**不降级为未命中**） |
| `NOT_FOUND` / `METHOD_NOT_ALLOWED` | 404 / 405 | 路径 / 方法错误 |

OpenAPI 文档：`/docs` 与 `/openapi.json`。

## 本地开发

```bash
uv sync --all-groups          # 安装依赖（Python 3.11）
uv run pytest -q              # 测试
uv run uvicorn sensitive_word_filtering.main:app --port 8000   # 启动
```

## Docker 构建（单架构，amd64 默认）

```bash
./scripts/build.sh v0.1.0              # linux/amd64
./scripts/build.sh v0.1.0 arm64        # linux/arm64
# Windows（PowerShell，带 BOM）
.\scripts\build.ps1 -Tag v0.1.0 -Arch amd64
```

产物：`build/v0.1.0-amd64/`（镜像 tar + `docker-compose.yml` + `manage.sh` + `.env.example` + `DEPLOY.md`）。
非法架构 / 输出目录已存在 / Docker 或 buildx 不可用 → 明确报错退出，不静默回退、不覆盖既有部署包。

## 离线部署（服务器只需 Docker）

```bash
scp -r build/v0.1.0-amd64 user@server:/opt/swf-filter
cd /opt/swf-filter && chmod +x manage.sh
./manage.sh load     # docker load 包内镜像
./manage.sh start    # 首次自动从模板创建 .env（之后不覆盖）
curl http://127.0.0.1:8000/health
```

生命周期：`stop` / `remove`（仅删容器与网络，保留镜像、配置、日志）/ `logs [--follow]`
（按日分 file names、50 MiB 轮转、保留 30 天）。完整说明见 `scripts/DEPLOY.md`。

**Compose 默认只绑定 `127.0.0.1:8000`，服务无鉴权**；可信内网部署改 `HOST_BIND` 并配防火墙，不要直接暴露公网。

## 词库更新

覆盖 `src/sensitive_word_filtering/dictionaries/sensitive_word_dict.txt`（同步 `NOTICE.md` 的 commit 与条目数）
→ `uv run pytest` → 重新构建镜像 → 重启。**无热更新**：运行期词库永远来自镜像内。

## OpenSpec

变更规格见 `openspec/changes/standalone-sensitive-word-api/`（proposal / specs / design / tasks），
归档后主规格进 `openspec/specs/`。

## 已知限制

- **词库匹配不是语义审核**：存在变体绕过（插符号/繁简/谐音不识别）与正常词误报
  （普通地名/词条可能命中），上线前需真实问法抽样回归。
- 检测语义与 `agent-backend/app/core/sensitive_word` 为复制关系，语义变更需两边各自同步。
- 单 Uvicorn worker（自动机只读共享，内存一份）；需要横向扩容时前面挂负载均衡多实例。
- `logs --follow` 模式仅在启动时做大小轮转，跟随期间依赖按日分 file names。

## 许可证

本项目代码：Apache-2.0（`LICENSE`）。第三方组件与词库：见 `THIRD_PARTY_NOTICES.md`。
