## 变更目的

<!-- 说明为什么需要这个变更，而不仅是改了什么 -->

## 变更范围

- [ ] SKILL.md 行为规则
- [ ] `trilium_etapi.py`
- [ ] 安装脚本
- [ ] 文档
- [ ] 测试
- [ ] CI/CD

## 文档治理核对

- [ ] 本 PR 涉及的事实域，其归属文档已更新（归属唯一，见 `AGENTS.md` 文档地图）
- [ ] 已检索仓内无所改事实的第二处抄录；发现的抄录已删除或改为引用
- [ ] 若涉及状态变化：`docs/PROJECT_STATE.md` 已在本 PR 内更新，其他文档无状态性陈述
- [ ] 若涉及远端配置变更（branch protection/ruleset/webhook/可见性等）：登记处已与变更同批交付

## 验证

请勾选或填写已执行的验证：

- [ ] `python tools/verify.py`
- [ ] 临时 HOME/APPDATA 安装 smoke test
- [ ] 其他：

## 安全检查

- [ ] 本 PR 来自 topic branch，不包含直接推送到 `main` 的变更
- [ ] 我会等 CI 全部成功后再合并，不会用本地验证替代远端 CI
- [ ] 没有提交 token、凭据、真实笔记内容或本机隐私路径
- [ ] 没有新增字面 token 参数
