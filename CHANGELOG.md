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
