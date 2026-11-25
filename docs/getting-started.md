# 上手指南

本指南帮助你在本机安装并让 agent 使用 `trilium-knowledge-sync`。

## 前置条件

- Trilium Notes / TriliumNext 桌面版或服务器版
- Trilium 已启动，并且知道本机 ETAPI 地址（桌面版通常在本机回环地址）
- Python 3.9+（helper 只使用标准库）
- Windows PowerShell 5.1+ / PowerShell 7+，或 Git Bash / Linux / macOS shell

## 第一步：创建 ETAPI token

1. 打开 Trilium Notes
2. 进入 **Options / 选项 → ETAPI**
3. 点击 **Create new ETAPI token**
4. 输入一个可识别用途的名称，例如 `trilium-knowledge-sync`
5. 立即复制 token；Trilium 只显示这一次

> 不要把 token 发到聊天、issue、git 提交、CI 日志或 Trilium 笔记中。

## 第二步：选择 token 存放方式

skill 不直接接受 token 值，只接受“位置”。推荐顺序如下。

### 方式 A：Windows 凭据管理器（推荐 Windows 桌面）

在 Windows 凭据管理器中创建 Generic Credential：

- 目标名：例如 `My-Trilium-ETAPI`
- 用户名：任意非敏感标识
- 密码：ETAPI token

之后对 agent 明确说：

```text
token 在 Windows 凭据管理器，精确目标名是 My-Trilium-ETAPI
```

注意目标名精确匹配，空格也有意义。

### 方式 B：本地 token 文件

把 token 保存到权限受控的 UTF-8 文本文件，例如：

```text
C:\secure\trilium-token.txt
```

之后对 agent 明确说：

```text
token 位置是文件 C:\secure\trilium-token.txt
```

不要把该文件放进 git 仓库或同步目录。

### 方式 C：环境变量

在当前 shell 或受控 runner 中设置：

```bash
export TRILIUM_TOKEN='<token>'
```

之后对 agent 明确说：

```text
token 在环境变量 TRILIUM_TOKEN 中
```

`setx` 会持久化到用户环境，除非明确需要，否则不建议。

## 第三步：安装 skill

Windows PowerShell：

```powershell
cd C:\path\to\trilium-knowledge-sync
.\install.ps1
```

Git Bash：

```bash
cd /path/to/trilium-knowledge-sync
./install.sh
```

安装成功后，多个 agent 的技能目录会出现 `trilium-knowledge-sync`，但它们是链接，不是副本。

验证链接：

```powershell
Get-Item "$env:APPDATA\devin\skills\trilium-knowledge-sync" | Format-List FullName,LinkType,Target
```

## 第四步：让 agent 执行同步

示例请求：

```text
把 C:\Users\me\Desktop\research.md 写入 Trilium 知识库。
放在“知识库/调研”下面，保留 Markdown 原文，并创建一个索引页。
token 在 Windows 凭据管理器，精确目标名是 My-Trilium-ETAPI。
```

如果你没有明确 token 位置，agent 必须先问你；这是刻意设计的安全行为。

## 第五步：验证

agent 完成后应报告：

- Trilium 层级路径
- 新建/更新笔记标题与 noteId
- hash / type / MIME / 父子关系验证结果

你也可以直接在 Trilium 中打开对应笔记检查渲染效果。
