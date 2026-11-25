# token 与 endpoint 配置

## token source 格式

`trilium_etapi.py` 只接受位置引用，不接受字面 token。

| 格式 | 含义 | 示例 |
|---|---|---|
| `win-cred:<target>` | Windows 凭据管理器 Generic Credential 的精确目标名 | `win-cred:My-Trilium-ETAPI` |
| `file:<path>` | UTF-8 token 文件路径 | `file:C:\secure\trilium-token.txt` |
| `env:<name>` | 环境变量名 | `env:TRILIUM_TOKEN` |
| `stdin` | 从标准输入读取一次 token | 适合受控自动化 |

也可以通过环境变量指定位置本身：

```bash
export TRILIUM_TOKEN_SOURCE='win-cred:My-Trilium-ETAPI'
```

注意：`TRILIUM_TOKEN_SOURCE` 存的是“位置”，不是 token。不要把 token 值放进这个变量。

## 为什么不允许字面 token

字面 token 容易进入：

- shell history
- 进程命令行
- agent 对话记录
- CI 日志和 artifact
- git 提交或笔记正文

因此 CLI 故意不提供 `--token` 参数，也会拒绝不符合位置格式的输入。

## ETAPI endpoint 解析顺序

helper 按以下顺序寻找 ETAPI：

1. 显式 `--base-url`
2. 环境变量 `TRILIUM_ETAPI_URL`
3. Trilium `healthcheck-url` 文件（仅接受 loopback 地址）
4. 常见本地端口探测：`37840`、`37740`、`8080`

如果 healthcheck 文件指向非 loopback 地址，helper 会拒绝自动使用，避免把 token 发到未明确授权的主机；确有远程/反向代理需求时必须显式使用 `--base-url` 或 `TRILIUM_ETAPI_URL`。

显式指定示例：

```bash
python scripts/trilium_etapi.py \
  --token-source 'win-cred:My-Trilium-ETAPI' \
  --base-url 'http://127.0.0.1:37840/etapi' \
  app-info
```

`--base-url` 可以接受以下形式并自动归一化：

```text
http://127.0.0.1:37840
http://127.0.0.1:37840/etapi
http://127.0.0.1:37840/api/health-check
```

## Trilium desktop 的 healthcheck-url

Windows 桌面版常见路径：

```text
%APPDATA%\trilium-data\healthcheck-url
```

文件内容通常类似：

```text
http://127.0.0.1:37840/api/health-check
```

helper 会把它转换为：

```text
http://127.0.0.1:37840/etapi
```

Linux/macOS 路径因安装方式不同而变化，可用 `TRILIUM_HEALTHCHECK_URL_FILE` 显式指定文件位置。

## Network access 与 ETAPI

TriliumNext 桌面版即使关闭浏览器/LAN 访问，本机 ETAPI 集成通常仍可使用。不要因为 `/api/health-check` 或浏览器访问返回 403 就立即开启 Network access；先用有效 token 调用 `/etapi/app-info` 判断。

## 常用环境变量

| 变量 | 用途 |
|---|---|
| `TRILIUM_TOKEN_SOURCE` | token 位置，例如 `win-cred:NAME` |
| `TRILIUM_ETAPI_URL` | 显式 ETAPI base URL |
| `TRILIUM_HEALTHCHECK_URL_FILE` | 显式 healthcheck-url 文件路径 |

这些变量都不应该包含真实 token；唯一例外是你显式选择用 `env:<name>` 方式存放 token，例如 `TRILIUM_TOKEN`。
