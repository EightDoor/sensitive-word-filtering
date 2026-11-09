# 词库来源与许可

- 文件：`sensitive_word_dict.txt`
- 来源仓库：<PII type="URL" id="50"/>
- 固定 commit：`fe6fc2921836217b8c90619db81b24af8b22d80f`
- 许可证：Apache License 2.0（全文见同目录 `LICENSE.txt`）
- 条目数：64,418 行（中文主词库；未引入 `sensitive_word_dict_en.txt` 英文库与
  `sensitive_word_allow.txt` 白名单）

## 更新方式

首期不做热更新：从上述仓库重新拉取 `sensitive_word_dict.txt` 覆盖本文件后重启服务。
更新时同步更新本文件的 commit 与条目数，并用真实问法抽样回归误报。
