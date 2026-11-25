# Test Plan

## 测试层级

| 层级 | 范围 | 自动化状态 |
|---|---|---|
| 仓库结构校验 | 必要文件、SKILL frontmatter、安全硬规则、文档链接 | 自动化 |
| Python 单元测试 | token source、endpoint、HTTP client、upsert、verification | 自动化 |
| mock ETAPI 集成测试 | CLI 子进程端到端 create/upsert/update/readback | 自动化 |
| 安装脚本 smoke test | 临时 HOME/APPDATA 中 install/reinstall/uninstall | CI 自动化 |
| PowerShell/Bash 语法 | `install.ps1`、`install.sh` | CI 自动化 |
| 真实 Trilium 验证 | 用户本机 token + 真实 ETAPI | 手动/受控验证 |

## 本地命令

```bash
python tools/validate_repo.py
python -m unittest discover -s tests -v
bash -n install.sh
python -m py_compile skill/trilium-knowledge-sync/scripts/trilium_etapi.py
```

Windows PowerShell：

```powershell
$errors = $null
[void][System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw .\install.ps1), [ref]$errors)
if ($errors.Count) { $errors; exit 1 }
```

## 单元测试重点

### token source

- env/file/stdin 正常读取
- 字面 token 被拒绝
- 空位置、空变量、空白 token 被拒绝
- Windows credential blob UTF-16LE/UTF-8 解码
- `win-cred` 不要求或尝试变体名

### endpoint discovery

- root URL、healthcheck URL、ETAPI URL 归一化
- 非 http/https 被拒绝
- 自定义反向代理 path 保留
- 端口探测未识别 Trilium 形状前不发送 token

### HTTP client

- Authorization header 使用 Bearer token
- 错误 detail 中的 token 被 redaction
- noteId URL encoding
- HTTPError/URLError 错误边界

### upsert

- 不存在则 create
- 内容相同则 unchanged
- 内容不同则 update
- type/MIME 不一致时 patch
- deleted child 不作为更新目标
- 写入后重新读取正文和父关系

## mock ETAPI 集成测试

`tests/test_mock_etapi_integration.py` 启动本机临时 HTTP server，覆盖：

- `app-info`
- `upsert-note` create → unchanged → updated
- `find-child`
- `list-children`
- `get-content --output`
- 错误 token 不出现在 stdout/stderr

该测试不需要真实 Trilium，也不使用真实 token。

## 安装脚本测试

必须在临时 HOME/APPDATA/USERPROFILE 下执行，不能污染真实技能库。

验证点：

1. 首次 install 创建链接。
2. 第二次 install 识别 already linked。
3. uninstall 只移除链接。
4. 源 `skill/trilium-knowledge-sync/SKILL.md` 仍存在。
5. Windows 使用 junction；Linux/macOS 使用 symlink。

## 真实 Trilium 手动验证

只有在用户当前对话明确 token 位置后执行：

1. `app-info` 返回 Trilium 版本。
2. 在测试父笔记下 upsert 一篇小 Markdown。
3. 第二次 upsert 应返回 unchanged。
4. 修改源文件后第三次 upsert 应返回 updated。
5. 在 Trilium UI 检查 type/MIME、正文和层级。
6. 验证完成后是否删除测试笔记由用户决定；helper 不提供删除命令。

## 发布前冒烟

- CI 全绿。
- `quick_validate.py` 或等价 skill validator 通过。
- CHANGELOG 已更新。
- tag 版本与 release artifact 命名正确。
- 压缩包不包含 token、临时文件、`__pycache__` 或本机隐私路径。
