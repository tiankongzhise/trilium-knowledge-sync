# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/) 的版本思想；正式发布前以 git tag 为准。

## [Unreleased]

### Added

- 初始化 `trilium-knowledge-sync` skill 仓库。
- 新增 `SKILL.md`：定义 Trilium 写入场景、token 位置硬规则、ETAPI 流程、安全边界和写后核验。
- 新增 `scripts/trilium_etapi.py`：基于 Python 标准库的 ETAPI CLI/helper。
- 新增 Windows PowerShell 与 Bash 安装脚本，通过 junction/symlink 挂载技能，避免复制。
- 新增项目文档、上手指南、安装文档、配置文档、CLI 参考、安全模型、架构说明、项目发现、PRD、测试计划、开发指南与故障排查。
- 新增单元测试、mock ETAPI 端到端测试、仓库校验脚本和 GitHub Actions CI/CD 模板。
- 端口自动探测在识别 Trilium ETAPI 响应形状前不发送 token；healthcheck 自动发现仅接受 loopback 地址。
- `upsert-note` 与 `put-content` 写入后重新读取正文/父关系进行核验。
- 文档治理框架：`AGENTS.md` 文档地图确立每份文档的唯一职责与事实归属；`docs/PROJECT_STATE.md` 成为全部时效性状态的唯一登记处。
- `tools/validate_repo.py` 新增机器强制检查：过渡性状态词句禁扫（白名单外出现即失败）、文档地图完整性（未登记/缺失/重复即失败）。
- `tests/test_validate_repo.py` 覆盖文档治理校验逻辑。
- `tools/verify.py` 统一本地验证入口，替代散落在五份文档中的逐字命令清单；CI 各步骤改经同一入口执行。
- `.github/PULL_REQUEST_TEMPLATE.md` 增加文档治理核对清单。
- 发布策略确立为发版 PR 制：版本号以 helper 的 `VERSION` 常量为真相源，tag 与 CHANGELOG 必须一致；见 `docs/development.md`「发布流程」。
- `upsert-note` 遇到同一父笔记下多个同名未删除笔记时拒绝执行，stderr 列出全部候选的 noteId 与辨识信息，不再静默选择第一个（owner 决策 2026-11-25）。
- `docs/security.md` 新增「残余风险：agent 运行时遵守无法验证」显著披露。
- CI 安装 smoke test 补齐删除路径覆盖（bash 与 PowerShell 双套）：副本无 force 不动、force 替换为链接、uninstall 无 force 保留副本、有 force 删除副本、无 `SKILL.md` 目录守卫不删（owner 决策 2026-11-25）。
- `docs/security.md` 记录 endpoint 自动发现的已接受残余风险；`docs/configuration.md` 增加显式 URL 主路径建议与多实例静默错库警告（owner 决策 2026-11-25）。
- `validate_repo.py` 文档治理枚举改为以 git 追踪文件为准：未追踪的本机文件不再触发地图完整性/禁词扫描（治理管的是入库内容）；git 仓库外回退为工作区扫描。

### Changed

- **breaking**：`stdin` 不再是合法 token source（owner 决策 2026-11-25：stdin 注入暴露面与字面 token 相当）；自动化场景改用 `env:` 或 `file:`。
- **breaking**：`find-child` 输出从单个对象/`null` 改为匹配数组（无匹配输出 `[]`），不做静默选择。
- `docs/PROJECT_DISCOVERY.md` 剥离全部时效性状态，转为只记录定位、证据与技术判断的永恒设计文档。
- `docs/development.md` 中 branch protection 配置事实迁移至状态登记处，该文档只保留持久规则。
- `AGENTS.md` 移除状态表，"文档同步要求"与"仓库外状态变更防失步"整合升级为文档治理一节。
