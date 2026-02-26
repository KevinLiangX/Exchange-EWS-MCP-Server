# Exchange EWS MCP Server

一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的服务端应用，旨在让 AI Agents (如 Cursor, Cline, Claude 桌面端等) 能够通过自然语言**安全、无缝地访问和管理**基于 EWS（Exchange Web Services) 的企业邮箱。

本项目原生集成了对 NTLM 认证的支持，提供了“即插即用”的邮箱读写、附件解析能力，并通过内置的并发锁 (Idempotency Key) 机制为所有高风险的邮件发送动作提供了防脑裂、防超发重发阻断能力。

## 🌟 核心功能地图 (15 Tools)

当前基于 Python `FastMCP` 框架重构，共计暴露了 15 个强力工具供大模型使用：

### 1. 邮件与线程检索 (Read Tools)
*   `list_messages`: 列出指名文件夹（Inbox，Sent等）下的最新邮件列表。
*   `search_messages`: 使用 Exchange 原生 AQS 检索语法全局搜索匹配关键词的邮件。
*   `get_message_details`: 获取某封邮件的详细发件人、往来人员及原文。
*   **[Pro]** `get_conversation_thread`: 自动溯源，拉取当前同属一个会话讨论组（Thread）的全部历史邮件。

### 2. 深度附件解析 (Attachment Tools)
*   `list_attachments`: 一键呈现某封邮件上的全部附件清单元数据。
*   **[Pro]** `get_attachment_content`: 打破“只能读正文”的局限，让 AI 直接深入提取阅读附件内的纯文本数据。
    * *原生支持:* `.pdf`, `.docx`, `.xlsx`, `.md`, `.json`, `.csv`, `.txt`, `.html`

### 3. 高效状态与归档管理 (Management Tools)
*   `mark_as_read` / `batch_mark_as_read`: 单条或批量标记邮件已读/未读状态。
*   `move_message` / `batch_move_messages`: 单条或批量将邮件归档、移入垃圾箱等操作。
*   `delete_message`: 软删除（移至废件箱）或彻底硬删除。

### 4. 高危发信操作 (Send Tools)
*所有发信操作强制要求 Agent 携带由它生成的防重 `idempotency_key` 锁，确保系统稳定性。*
*   `send_email`: 支持 Markdown 渲染，附带签名与收件人发出新邮件。
*   `reply_email`: 针对某封特定邮件执行“单回”或“回复全部”。
*   `forward_email`: 追加引言语并转发。
*   `save_draft`: 仅将内容写入“草稿箱”。

---

## 🛠 环境与依赖准备

本项目推荐使用现代的 `uv` 工具链进行 Python 环境的管理：

1. **Python 3.12+** 环境。
2. 安装 **uv** (极速 Python 依赖管理工具)。
3. 在项目根目录执行以下命令，自动初始化虚拟环境并安装所需的全部依赖（包括 `exchangelib`, `pypdf`, `python-docx`, `openpyxl` 等）：
   ```bash
   uv sync
   ```

---

## 🔧 配置指南 (环境变量)

MCP Server 的核心控制依赖于标准的系统环境变量注入。你可以将其写入克隆目录下的 `.env` 文件中，**或者更推荐在 AI 客户端 (Cursor / Cline) 的 MCP env 配置栏内**进行隔离注入，避免密码明文落盘。

```env
# 你的 EWS 接入完整地址 (必填)
EWS_ENDPOINT=https://mail.example.com/EWS/Exchange.asmx

# 登录域 (选填)
EWS_DOMAIN=MYCORPDOMAIN

# 用户名和密码 (必填)
EWS_USERNAME=your.name@example.com
EWS_PASSWORD=your_real_password_here

# 指定 EWS 的客户端声明兼容版本 (默认 Exchange2013)
EWS_EXCHANGE_VERSION=Exchange2016

# 放行自签发证书、绕过 SSL 验证报错。0 为关闭验证。（必填）
NODE_TLS_REJECT_UNAUTHORIZED=0

# MCP 运行协议模式：stdio (默认) / sse / http
MCP_MODE=stdio

# SSE 与 HTTP 模式下的暴露端口，默认 3101
MCP_PORT=3101

# (选填) 自动装配进每封发送邮件末尾的默认签名 (支持 Markdown 渲染)
EWS_EMAIL_SIGNATURE="---\n**此致**\n*张三* | 测试开发中心\n[公司主站](https://www.example.com)"
```

---

## 🚀 启动与客户端接入方案

### 方式一：StdIO 模式 (最推荐、最安全的桌面端 AI 接入方式)

这种模式下，你的 IDE 或 Agent 会直接拉起一个子进程与此 Server 通信。端口不暴露，最安全。

**Cursor / Cline 配置大纲范例：**
```json
{
  "mcpServers": {
    "EmailExchange": {
      "command": "uv",
      "args": [
        "--directory", "/你电脑上本项目的绝对路径/",
        "run",
        "main.py"
      ],
      "env": {
        "MCP_MODE": "stdio",
        "EWS_ENDPOINT": "https://mail.example.com/EWS/Exchange.asmx",
        "EWS_DOMAIN": "YOURDOMAIN",
        "EWS_USERNAME": "your.name@example.com",
        "EWS_PASSWORD": "你的密码写在这里",
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```
*提示：通过 `env` 注入，你的 `.env` 文件甚至可以是完全空白的。*

### 方式二：SSE (Server-Sent Events) 模式

如果你要把这个邮箱管家作为一项独立的云端服务跑在内网主机上，并接受异地 Agent Client 的请求，请采用此模式。

1. **先启动 Python 服务端**：
   在带有全量 `.env` 变量配置的目录下执行：
   ```bash
   MCP_MODE=sse MCP_PORT=3101 uv run main.py
   ```
   > 将看到日志：`INFO: Uvicorn running on http://0.0.0.0:3101`

2. **远程客户端配置 SSE URL 接入**：
   ```json
   {
     "mcpServers": {
       "EmailExchange": {
         "type": "sse",
         "url": "http://192.168.x.x:3101/sse"
       }
     }
   }
   ```

### 方式三：零环境依赖的单文件二进制包 (推荐分发)

如果你需要把服务器脱离源码和 Python 环境，发给其他并不懂代码的实施人员或提供给第三方对接。可以通过本项目自带的 PyInstaller 脚本将其一键打包为单体可执行文件：

1. **自己打包**: 
   ```bash
   uv add --dev pyinstaller
   uv run pyinstaller --onefile --clean --name ews-mcp-server main.py
   ```
   随后会在 `dist/` 文件夹下生成一个 `ews-mcp-server` 的可执行文件（在 Win 上为 `.exe`）。

2. **跨平台全自动打包 (CI/CD)**:
   本项目已内置 GitHub Actions （位于 `.github/workflows/build-binaries.yml`）。
   当你往 Git 推送 `v1.x.x` 的 tag 时，或者手动点击运行 Workflow，**云端会自动并发打包出适配 macOS、Ubuntu 和 Windows 11 的独立二进制程序包**！之后可以在 GitHub 的 Actions 或 Releases 页面直接下载对应系统的执行包。

**脱离源码对接示例**:
获取到如 `ews-mcp-server.exe` 放至电脑角落后，在 Cursor 中的配置更为极简：
```json
{
  "mcpServers": {
    "EmailExchange": {
      "command": "C:\\path\\to\\ews-mcp-server.exe",
      "args": [],
      "env": {
        "MCP_MODE": "stdio",
        "EWS_ENDPOINT": "...",
        "EWS_USERNAME": "...",
        "EWS_PASSWORD": "..."
      }
    }
  }
}
```

---

## 📚 更多详细设计资料


本项目的相关演进思路与 Python 全系组件的系统调用时序可参考进阶阅读：

👉 **[查看《Exchange_EWS_MCP接入方案与详细设计.md》](./docs/Exchange_EWS_MCP接入方案与详细设计.md)**
