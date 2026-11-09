# sensitive-word-filtering-api 规格变更

## ADDED Requirements

### Requirement: 检测接口返回布尔结果

系统 MUST 提供 `POST /api/v1/check`，请求体为 `{"text": "<字符串>"}`，
成功时返回 HTTP 200 与 `{"contains_sensitive_word": true|false}`。

- 命中 MUST 作为正常检测结果返回，MUST NOT 复用聊天接口的 422 拒绝语义。
- 空字符串与纯空白字符串 MUST 被接受并返回 `false`；MUST NOT 裁剪输入首尾空白后再检测。

#### Scenario: 命中

- **WHEN** 输入包含词库词条
- **THEN** 返回 200 与 `contains_sensitive_word: true`

#### Scenario: 未命中

- **WHEN** 输入不包含任何词条
- **THEN** 返回 200 与 `contains_sensitive_word: false`

#### Scenario: 空输入

- **WHEN** `text` 为空字符串
- **THEN** 返回 200 与 `contains_sensitive_word: false`

### Requirement: 输入严格校验

`text` MUST 为字符串且长度不超过 10,000 个字符；缺失、`null`、非字符串类型、
超长与未声明的额外字段 MUST 被拒绝。

#### Scenario: 非法字段拒绝

- **WHEN** 请求缺少 `text`、`text` 为 `null`/数字/数组，或包含额外字段
- **THEN** MUST 返回 HTTP 422 与错误码 `INVALID_REQUEST`

#### Scenario: 超长文本拒绝

- **WHEN** `text` 长度为 10,001
- **THEN** MUST 返回 HTTP 422 与错误码 `INVALID_REQUEST`

#### Scenario: 长度边界

- **WHEN** `text` 长度恰为 10,000
- **THEN** MUST 正常检测

### Requirement: 请求体大小上限

单次请求体 MUST 限制为 128 KiB；系统 MUST 同时校验 `Content-Length` 头与实际接收字节数，
使分块传输或缺失 `Content-Length` 的请求无法绕过上限。

- 校验失败 MUST 返回 HTTP 413 与错误码 `REQUEST_TOO_LARGE`。
- 超限请求 MUST NOT 进入检测逻辑。

#### Scenario: Content-Length 超限

- **WHEN** `Content-Length` 大于 128 KiB
- **THEN** MUST 返回 413 且不执行检测

#### Scenario: 分块传输超限

- **WHEN** 请求不携带或谎报 `Content-Length`，实际累计字节超过 128 KiB
- **THEN** MUST 返回 413 且不执行检测

### Requirement: 结构化错误且不回显输入

所有错误响应 MUST 为 `{"detail": {"code": "<错误码>", "message": "<固定文案>"}}` 形状。

- 校验错误 `INVALID_REQUEST`、超限错误 `REQUEST_TOO_LARGE`、意外内部错误 `INTERNAL_ERROR`
  各 MUST 使用稳定错误码与固定安全文案。
- 响应与服务端日志 MUST NOT 包含请求正文、命中词或校验失败的原始输入。
- 检测过程意外失败 MUST 返回 500 `INTERNAL_ERROR`，MUST NOT 降级为 `contains_sensitive_word: false`。

#### Scenario: 校验错误形状

- **WHEN** 输入校验失败
- **THEN** 响应 `detail.code` MUST 为 `INVALID_REQUEST`，且不含原始输入

#### Scenario: 检测异常不误报未命中

- **WHEN** 检测器调用抛出异常
- **THEN** MUST 返回 500 `INTERNAL_ERROR`，MUST NOT 返回 `contains_sensitive_word: false`

### Requirement: 健康检查反映就绪状态

系统 MUST 提供 `GET /health`：自动机就绪时返回 HTTP 200 与 `{"status": "ok"}`，
未就绪时返回 503。响应 MUST NOT 暴露词库内容或内部路径。

#### Scenario: 就绪

- **WHEN** 应用完成启动初始化
- **THEN** `/health` 返回 200 与 `{"status": "ok"}`

### Requirement: 文档与默认暴露面

系统 MUST 保留 FastAPI 自动生成的 `/docs` 与 `/openapi.json`；MUST NOT 实现应用层鉴权或 CORS 中间件。

#### Scenario: OpenAPI 可访问

- **WHEN** 请求 `/openapi.json`
- **THEN** 返回包含 `/api/v1/check` 与 `/health` 的规范
