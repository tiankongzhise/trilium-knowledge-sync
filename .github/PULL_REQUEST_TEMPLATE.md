## 变更目的

<!-- 说明为什么需要这个变更，而不仅是改了什么 -->

## 变更范围

- [ ] SKILL.md 行为规则
- [ ] `trilium_etapi.py`
- [ ] 安装脚本
- [ ] 文档
- [ ] 测试
- [ ] CI/CD

## 验证

请勾选或填写已执行的验证：

- [ ] `python tools/validate_repo.py`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `bash -n install.sh`
- [ ] PowerShell 语法检查（Windows）
- [ ] 临时 HOME/APPDATA 安装 smoke test
- [ ] 其他：

## 安全检查

- [ ] 本 PR 来自 topic branch，不包含直接推送到 `main` 的变更
- [ ] 我会等 CI 全部成功后再合并，不会用本地验证替代远端 CI
- [ ] 没有提交 token、凭据、真实笔记内容或本机隐私路径
- [ ] 没有新增字面 token 参数
- [ ] 没有引入直接写 SQLite 的默认路径
- [ ] 文档已同步更新
