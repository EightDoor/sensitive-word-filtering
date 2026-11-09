# sensitive-word-detector 规格变更

## ADDED Requirements

### Requirement: 词库与输入使用同一归一化

检测前 MUST 对词库词条与输入文本使用同一归一化函数：`unicodedata.normalize("NFKC", text).casefold()`。

- 归一化 MUST 折叠全角/半角兼容字符（如 `ＡＢＣ１２３` → `ABC123`）并忽略英文大小写。
- MUST NOT 移除或忽略空格、标点；输入中插入的空白或标点 MUST NOT 被当作可跳过字符。
- MUST NOT 实现繁简转换、拼音、谐音或形近字匹配。

#### Scenario: 大小写与全半角归一化

- **WHEN** 词库包含小写词条，输入为等价的大写或全角形式
- **THEN** MUST 判定命中

#### Scenario: 空白不被忽略

- **WHEN** 输入在词条中间插入空格或标点
- **THEN** MUST NOT 判定命中

### Requirement: 启动期构建且失败即拒启

系统 MUST 在应用启动（lifespan）阶段构建 Aho-Corasick 自动机，且仅当词库可读、解码成功、
有效词条数大于零时才完成初始化。

- 词库缺失、不可读、编码错误或有效词条为零时，启动 MUST 失败（fail-closed）。
- MUST NOT 在请求期懒加载自动机；未初始化时检测调用 MUST 抛异常，MUST NOT 静默返回 `false`。
- 词库 MUST 以包资源形式随包分发，加载 MUST NOT 依赖进程工作目录。

#### Scenario: 词库缺失启动失败

- **WHEN** 词库文件缺失或有效词条为零
- **THEN** 应用启动 MUST 失败并给出明确错误

#### Scenario: 未初始化拒绝检测

- **WHEN** 自动机尚未初始化时调用检测
- **THEN** MUST 抛出异常，MUST NOT 返回未命中

### Requirement: 只读复用与命中即停

初始化成功后，自动机 MUST 以只读方式供并发请求复用，MUST NOT 在请求期重建或修改。

- 初始化 MUST 幂等：重复调用不重建已就绪实例。
- 检测 MUST 在首个命中词条处返回，不扫描剩余文本。

#### Scenario: 幂等初始化

- **WHEN** 初始化被调用多次
- **THEN** 后续调用复用同一实例，不重复构建

#### Scenario: 命中即停

- **WHEN** 输入命中词库
- **THEN** 检测器只消费到首个匹配即返回 `true`

### Requirement: 词库与许可随包分发

词库 `dictionaries/sensitive_word_dict.txt`（64,418 行，houbb/sensitive-word-data
commit `fe6fc2921836217b8c90619db81b24af8b22d80f`）MUST 随 Python 包与容器镜像一同分发，
并附带上游 Apache-2.0 许可证全文与来源说明（NOTICE）。

- 词库更新方式 MUST 为替换文件 + 重新构建镜像 + 重启服务；MUST NOT 依赖运行期热加载。

#### Scenario: 构建产物包含词库

- **WHEN** 构建 wheel 或容器镜像
- **THEN** 产物内 MUST 包含词库、LICENSE 与 NOTICE
