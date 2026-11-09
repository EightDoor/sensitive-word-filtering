# standalone-sensitive-word-api 设计决策

## 决策 1：复制而非共享代码

选择：把 `agent-backend/app/core/sensitive_word/detector.py` 的实现**复制**到本项目
`src/sensitive_word_filtering/detector.py`，仅调整包资源路径。

- 目标是独立可部署：两个仓库不共享包、不互相依赖、各自演进。
- 备选：发布共享 Python 包——拒绝，需求只有一份可独立运行的服务，引入包版本管理不值得。
- 备选：新服务反向调用原接口——拒绝，原接口是聊天链路，带鉴权与副作用，且不可离线。

已知取舍：未来检测语义若需变更，两个仓库要各自同步（记入 README 已知限制）。

## 决策 2：命中是正常结果，不是拒绝

选择：`POST /api/v1/check` 命中返回 200 `contains_sensitive_word: true`。

- 本服务职责是「检测」，是否拒绝由调用方决定；沿用聊天接口的 422 拒绝语义会让语义错位。
- 备选：命中返回 409/422——拒绝，检查类 API 用非 2xx 表达正常结果会让调用方与网关误判。

## 决策 3：请求体上限放在 ASGI 中间件

选择：自定义纯 ASGI 中间件在路由读取请求体之前限制 128 KiB：先查 `Content-Length`（非数字或
超限直接 413），再包装 `receive` 累计实际字节，超限抛内部异常由中间件自己返回 413 JSON。

- FastAPI 的 Pydantic 解析发生在路由之前，若只在路由内校验，超大体已先被完整接收与解析。
- 必须同时覆盖分块传输/缺失 Content-Length 的场景，只查头可被绕过。
- 抛出点尚未发送响应（正文解析在响应开始前），中间件捕获后返回 413 是安全的。
- 备选：`await request.body()` 后判长——拒绝，需要把 body 提前缓冲，与依赖注入顺序冲突且重复读取。

## 决策 4：同步路由 + 线程池

选择：`/api/v1/check` 用 `def`（同步）路由，由 Starlette 线程池执行；自动机只读共享。

- 匹配是 CPU 密集操作，放在 `async def` 会阻塞事件循环。
- 单 Uvicorn worker：词库自动机 6.4 万词条只构建一次，多 worker 会重复占内存，需求未要求吞吐。

## 决策 5：结构化错误统一在异常处理器

选择：注册 `RequestValidationError`、`HTTPException`、未捕获异常三个处理器，
统一输出 `{"detail": {"code", "message"}}`，固定文案常量集中在 `errors.py`。

- FastAPI 默认校验错误会回显输入（Pydantic 错误里带 `input` 值），必须覆盖掉。
- 检测器异常 → 500 `INTERNAL_ERROR`，不降级为未命中，避免把故障当「干净」返回。

## 决策 6：部署包不含构建脚本

选择：`build/<tag>-<arch>/` 只放镜像 tar、docker-compose.yml、manage.sh、配置模板、部署说明。

- 构建脚本需要源码与 Dockerfile 才有意义，放进部署包是死文件。
- 备选：把源码与构建脚本一起打包——拒绝，违背「无源码部署」目标。

## 决策 7：单架构单包，默认 amd64

选择：构建脚本一次只构建一个架构，镜像标签与输出目录都带架构后缀，默认 `amd64`。

- `docker save` 单架构镜像体积更小；混装多架构 manifest 会显著增大 tar 且部分老 Docker 不支持 load。
- 非法架构直接失败退出，不静默回退，避免产出与预期架构不符的包。

## 决策 8：uv + uv_build + 冻结锁

选择：uv 管理依赖，`uv_build` 后端与 `src/` 布局，Docker 内 `uv sync --frozen`；依赖初始版本沿用
原项目锁定版本（FastAPI 0.140.0 / Pydantic 2.13.4 / Uvicorn 0.51.0 / pyahocorasick 2.3.1）。

- 词库为包内非 .py 资源，wheel 冒烟测试必须验证其被 file included（uv_build 默认只排
  `__pycache__` 等，实测为准）。
- 与 agent-backend 保持同 <PII type="CASE_ID" id="117"/>依赖主版本，降低两边修复经验不通用的风险。
