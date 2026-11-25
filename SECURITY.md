# Security Policy

## 支持范围

本项目是一个本地 agent skill 与 ETAPI helper，不直接暴露网络服务。安全问题主要包括：

- Trilium ETAPI token 泄露
- 错误读取非用户指定的凭据
- 非授权写入、覆盖或删除知识库内容
- 安装脚本误删非链接目录
- CI/CD artifact 意外包含 secret

## 报告安全问题

如果漏洞涉及本机私密数据，请不要在公开 issue 中披露细节、token、笔记内容或凭据位置。先私下联系仓库维护者，并在问题修复后再公开技术细节。

## 凭据处理要求

- 不接受字面 token 参数或聊天中的 token 值。
- 只读取用户当次明确指定的 token 位置。
- 不批量扫描 Windows 凭据管理器、浏览器、SSH、云 CLI 或其他 secret store。
- 不把 token 写入日志、笔记、测试 fixture、CI artifact 或 git 历史。
- 若 token 已泄露，应立即在 Trilium 中删除/吊销并重新创建。

## 数据写入边界

- 默认只能创建或按精确标题更新目标任务范围内的笔记。
- 不默认删除、移动、覆盖非本任务创建的笔记。
- 批量删除、重建知识库、直接 SQLite 写入都属于高风险操作，必须单独明确授权。
