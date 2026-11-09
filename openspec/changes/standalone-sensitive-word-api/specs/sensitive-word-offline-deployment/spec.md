# sensitive-word-offline-deployment 规格变更

## ADDED Requirements

### Requirement: 单架构镜像构建

项目 MUST 提供 `Dockerfile`（Python 3.11 slim 多阶段构建，uv 冻结锁文件安装依赖、
非 editable 安装应用包、非 root 用户运行、容器内健康检查）与 Linux/Windows
构建脚本 `scripts/build.sh` / `scripts/build.ps1`。

- 构建脚本 MUST 接受版本 tag 与目标架构，架构 MUST 限定为 `amd64` 或 `arm64`，
  默认 `amd64`；非法参数 MUST 失败退出，MUST NOT 静默回退架构。
- 每次构建 MUST 产出单架构镜像与对应部署包目录 `build/<tag>-<arch>/`，
  镜像标签 MUST 包含版本与架构。
- 任一构建步骤失败 MUST 立即失败；目标输出目录已存在时 MUST 拒绝覆盖且不删除既有部署包。

#### Scenario: 默认 amd64

- **WHEN** 不指定架构执行构建脚本
- **THEN** 产出 `linux/amd64` 镜像与 `build/<tag>-amd64/` 部署包

#### Scenario: 指定 arm64

- **WHEN** 构建脚本以 arm64 架构参数执行且环境满足
- **THEN** 产出 `linux/arm64` 镜像与 `build/<tag>-arm64/` 部署包

#### Scenario: 非法架构拒绝

- **WHEN** 架构参数不是 amd64/arm64
- **THEN** 脚本 MUST 以非零状态退出并给出明确错误

### Requirement: 离线部署包完整自洽

每个部署包 MUST 至少包含：镜像 tar、`docker-compose.yml`、`manage.sh`、
无敏感值的配置模板与部署说明。MUST NOT 包含源码、真实配置、旧日志或需要源码才能工作的构建脚本。

- `docker-compose.yml` MUST 只引用固定 `image:`（含 `${TAG}` 或既定标签），MUST NOT 含 `build:`；
  MUST 声明 `env_file`，默认将服务绑定到 `127.0.0.1`，使用 `restart: unless-stopped`。

#### Scenario: 无源码部署

- **WHEN** 仅将部署包目录上传到已安装 Docker/Compose 的服务器
- **THEN** 无需源码与网络依赖安装即可 load 镜像并启动服务

#### Scenario: 默认回环绑定

- **WHEN** 未修改包内 Compose 配置
- **THEN** 服务端口仅绑定 `127.0.0.1`，不对局域网直接暴露

### Requirement: manage.sh 生命周期管理

部署包内 `manage.sh` MUST 提供 `load` / `start` / `stop` / `remove` / `logs` 子命令：

- `load` 加载包内既定名称的镜像 tar，MUST NOT 扫描或加载任意 tar。
- `start` MUST 在配置文件不存在时从模板创建默认配置，MUST NOT 覆盖既有配置。
- `logs` MUST 默认持久化输出（一次性快照或 `--follow` 跟随），归档按日期分 <PII type="CASE_ID" id="116"/> 轮转（默认单文件 50 MiB、保留 30 天）。
- `remove` MUST 仅移除本服务容器与 Compose 网络，MUST NOT 删除镜像、部署包、配置或日志。
- 脚本 MUST 为 LF 行尾、无 BOM；路径 MUST 基于脚本自身位置解析。

#### Scenario: 首次启动创建配置

- **WHEN** 部署目录尚无配置文件时执行 `manage.sh start`
- **THEN** 从模板创建默认配置后启动，既有配置文件不被覆盖

#### Scenario: remove 保留数据

- **WHEN** 执行 `manage.sh remove`
- **THEN** 镜像、部署包目录、配置与日志文件均被保留

### Requirement: 脚本语法可验证

构建与管理脚本 MUST 通过 `bash -n` 语法检查；`build.ps1` MUST 通过 PowerShell 解析器检查。

#### Scenario: 脚本语法检查

- **WHEN** 对 `build.sh`、`manage.sh` 执行 `bash -n`，对 `build.ps1` 执行 PowerShell parser
- **THEN** 无语法错误
