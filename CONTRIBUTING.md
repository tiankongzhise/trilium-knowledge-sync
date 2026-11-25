# Contributing

## 开发原则

1. **单一来源**：运行时必须以 `skill/trilium-knowledge-sync/` 为唯一入口，不能复制出第二份 skill。
2. **安全优先**：token 规则是硬约束，不允许为了便利而放宽。
3. **标准库优先**：`trilium_etapi.py` 当前只使用 Python 标准库；新增依赖必须有明确收益并更新安装/CI 文档。
4. **幂等可验证**：所有写入路径都应尽量支持重复执行且可核验。
5. **文档归属**：每条事实只写在其归属文档；归属见 `AGENTS.md` 文档地图，行为变化涉及的归属文档必须同 PR 更新。

## 开发流程

```bash
# 1. 修改代码/文档
# 2. 运行全部本地验证
python tools/verify.py

# 3. Windows 上再验证安装行为
powershell -NoProfile -File install.ps1 -WhatIf
```

## 测试要求

- 修改 `trilium_etapi.py`：必须更新或新增 `tests/` 中的单元测试。
- 修改安装脚本：至少在 CI 或本机用临时 HOME/APPDATA 验证链接行为。
- 修改 SKILL.md 的 token 规则：`tools/validate_repo.py` 中的硬性文案检查必须通过。

## Commit / PR

- **禁止直接在 `main` 上提交或 push。** 所有变更必须从最新 `main` 创建 topic branch。
- 推荐分支名：`<type>/<short-topic>`，例如 `fix/token-source-parsing`、`docs/installation`。
- Commit message 聚焦“为什么”，不要只写“update”。
- 不提交真实 token、用户笔记内容、导出的知识库数据或本机隐私路径。
- 不 push 到远端，除非仓库 owner 明确要求。
- PR 必须等待 CI 全部成功后再合并；本地验证通过不能替代远端 CI。
- 紧急修复也只能压缩审查/验证流程，不能绕过分支、PR 和 CI。
