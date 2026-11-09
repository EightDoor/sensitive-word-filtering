# 第三方组件与声明

## sensitive-word-data（中文敏感词词库）

- 文件：`src/sensitive_word_filtering/dictionaries/sensitive_word_dict.txt`
- 来源仓库：<PII type="URL" id="50"/>
- 固定 commit：`fe6fc2921836217b8c90619db81b24af8b22d80f`
- 许可证：Apache License 2.0
- 许可证全文：`src/sensitive_word_filtering/dictionaries/LICENSE.txt`
- 条目数：64,418 行（中文主词库；未引入英文库与白名单文件）

## pyahocorasick

- 用途：Aho-Corasick 多模式匹配自动机（检测引擎）
- 许可证：Apache License 2.0（见其上游仓库）
- PyPI: <PII type="URL" id="51"/>

## 运行依赖（均为 Apache-2.0 / BSD 类开源许可）

- FastAPI、Starlette、Pydantic、Uvicorn（具体版本见 `uv.lock`）
