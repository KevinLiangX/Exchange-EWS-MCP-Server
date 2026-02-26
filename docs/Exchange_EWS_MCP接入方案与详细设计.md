# Exchange(EWS) MCP Server 接入方案与详细设计

## 1. 文档信息

- 文档版本: v3.0 (Python 化及全量功能进化版)
- 编写日期: 2026-02-26
- 适用场景: 提供标准 FastMCP (Model Context Protocol) Server，深度适配公司 Exchange 邮箱 (EWS)
- 目标读者: 服务端开发、AI/Agent 开发者、测试、运维、安全合规

---

## 2. 背景与目标

### 2.1 现状与背景

当前客户端（Electron）已经包含具备对话能力的 AI Agent，并且能够通过 MCP (Model Context Protocol) 调用大模型外部工具。
现有公司的邮箱配置使用的是 EWS (Exchange Web Services) 端点：
- 内部/外部 URL: `https://mail.pactera.com/ews/exchange.asmx`

我们需要提供一个**纯粹的 EWS MCP Server**，将 EWS 的能力深度封装为标准的 MCP 工具（Tools），使得 AI Agent 可以通过自然语言对话的方式，直接获取邮件、管理附件、进行总结、回复、发送等操作，而无需开发专门的传统 UI。

### 2.2 业务目标

1. 提供一个独立的 Python MCP Server 进程，依托 FastMCP 框架，通过标准输入输出 (stdio) 或 HTTP/SSE 方式与现有的 AI 客户端通信。
2. 彻底封装 EWS 核心能力为 15 个标准的 MCP Tools（读取、搜索、发送、回复、移动、附件解析、批量操作等）。
3. 支持大模型 Agent 通过对话直接调用这些工具，实现“对话即纯粹的邮件办公管家”。
4. 确保敏感操作具备防重发（幂等锁）机制，保障系统执行的稳定性。

---

## 3. 总体架构设计

### 3.1 核心组件架构

```mermaid
flowchart LR
  A["AI 客户端 (已有对话UI)"] -->|"指令/意图"| B["AI Agent (大模型)"]
  
  subgraph MCP Client (客户端对接层)
    B -->|stdio (本地子进程)| C1
    B -->|HTTP/SSE (远程网络)| C1
  end
  
  subgraph EWS MCP Server (Python FastMCP)
    direction TB
    C1["FastMCP Protocol 层 (工具注册、路由适配)"]
    C2["幂等防重中间件 (Idempotency Lock)"]
    C3["exchangelib Adapter (对象转换与 EWS 交互)"]
    C4["配置与认证管理器 (dotenv)"]
    C1 --> C2 --> C3
    C4 --> C3
  end

  C3 -->|"SOAP/XML"| D["公司 Exchange Server (EWS)"]
```

### 3.2 模块职责

1. **FastMCP Protocol 层**: 使用官方的 `mcp` Python SDK 对外暴露预定义的 Tools。核心设计为**双协议支持**：
   - **`stdio` 模式**: 面向基础的桌面端，作为子进程被拉起，无需暴露本地端口。
   - **`SSE` 模式**: 面向未来架构迁移，基于 Starlette/Uvicorn 提供跨域 Server-Sent Events 调用。
2. **幂等防重中间件**: 拦截写操作，基于幂等键防止网络超时导致大模型重复发送邮件。
3. **配置与认证管理器**: 通过环境变量（`.env` 或运行时注入）安全接收凭据，快速初始化 `exchangelib` 单例账号。
4. **EWS Adapter**: 底层基于成熟的 `exchangelib` 库，把 MCP 的 JSON 请求转换并拼凑为复杂的 EWS SOAP 报文。并在邮件发信工具中嵌入通用的 HTML 及签名（Signature）样式处理器。

---

## 4. MCP 工具集定义 (15 个核心 Tools)

### 4.1 基础与高级查询类 (Read-Only)

#### 1. `list_messages(folder_name, limit, fetch_body)`
- **功能**: 列出指定文件夹下的最新邮件列表。

#### 2. `search_messages(query, folder_name, limit, fetch_body)`
- **功能**: 使用 Exchange 原生查询语法（AQS）搜索匹配条件的邮件，如 'subject:Project'。

#### 3. `get_message_details(message_id)`
- **功能**: 获取某封邮件的元信息、文本正文、HTML 原始内容数据。

#### 4. `get_conversation_thread(message_id, limit)`
- **功能**: 向上穿透，拉取属于同一讨论组（ConversationId 相同）的所有上下文历史邮件，为 LLM 总结提供全部语料。

### 4.2 附件深度解析类 (Read-Only)

#### 5. `list_attachments(message_id)`
- **功能**: 获取某封邮件下所有附件的基本信息（文件名、大小、类型）。

#### 6. `get_attachment_content(message_id, attachment_name)`
- **功能**: 深度提取核心附件里的纯文本给大模型提供决策支持。
- **支持格式**: 原生支持解析 `.pdf` (pypdf), `.docx` (python-docx), `.xlsx` (openpyxl) 以及所有纯文本格式 (`.txt`, `.csv`, `.md`, `.json`, `.html`)。

### 4.3 交互与状态管理类 (Write-Action)

#### 7. `mark_as_read(message_id, is_read)`
- **功能**: 标记单封邮件为已读/未读。

#### 8. `move_message(message_id, destination_folder)`
- **功能**: 移动单封邮件到指定文件夹（如 inbox, deleteditems）。

#### 9. `delete_message(message_id, hard_delete)`
- **功能**: 移动邮件到回收站；或直接执行物理硬删除。

#### 10. `batch_mark_as_read(message_ids, is_read)`
- **功能**: 批量已读（通过 EWS bulk_update 提升性能）。

#### 11. `batch_move_messages(message_ids, destination_folder)`
- **功能**: 批量移动（通过 EWS bulk_move 提升性能）。

### 4.4 高危发信类 (Write-High-Risk)

*所有发信类接口强制要求提供 `idempotency_key` (防重机制) 参数。*

#### 12. `send_email(to_recipients, subject, body, idempotency_key, cc_recipients, use_signature)`
- **功能**: 新建并发送邮件。正文支持 Markdown 到 HTML 的精美转换注入。

#### 13. `reply_email(message_id, body, reply_all, idempotency_key, use_signature)`
- **功能**: 针对特定邮件进行单回或全员回复。

#### 14. `forward_email(message_id, to_recipients, idempotency_key, body_prefix, ...)`
- **功能**: 转发指定邮件。

#### 15. `save_draft(...)`
- **功能**: 仅保存草稿至草稿箱，不进行真实发送。

---

## 5. 关键技术选型

1. **开发语言**: Python 3.12+ (使用 `uv` 管理包与虚拟环境)
2. **MCP SDK**: 官方 `mcp` 包 (基于 FastMCP 范式，以极其简洁的方式暴露装饰器路由)。
3. **EWS 底层库**: `exchangelib`。Python 生态最全面、最强悍的 EWS 交互框架，完美支持 NTLM 认证、时区处理、大批量操作（bulk_update）和高级 AQS 搜索。
4. **附件解析栈**:
   - `pypdf`: 纯 Python，用于高效提取 PDF 页面文本。
   - `python-docx`: 解析 Word 段落与表格单元。
   - `openpyxl`: 解析 Excel 的多表（Sheet）以及二维数据阵列。
5. **异常防御与高可用**: 内存级防并发字典锁。为发件相关的工具自动上锁（idempotency_key），即使模型发出多次调用甚至同时执行，依然能阻断并发。

---

## 6. 认证与安全设计

### 6.1 凭据传递机制 (环境变量注入)
1. **`stdio` 模式 (高度隔离推荐)**:
   - 极度建议在主客户端的 `mcpServers` 注册配置中利用 `env` 字段，动态将 `EWS_USERNAME` 和 `EWS_PASSWORD` 这种机密注入成为启动参数。系统或大模型都不会直接触碰到真实的密码原文。
2. **`SSE` 服务端模式**:
   - 采用标准且隔离良好的外层 `.env` 和 Docker/Runner 级别环境变量注入。

### 6.2 幂等性设计保障
大模型偶尔会由于模型内部等待时长过高或上游网络超时，产生反复执行同一发信指令的行为。
为了阻止同一封信被发两次：
1. 发信工具（Send, Reply, Forward）全要求传入大模型生成的具有唯一性的 `idempotency_key` 格式串（如 UUID）。
2. Server 接到请求时，针对此 Key 加并发锁。如果短期内已经成功则直接抛弃并返回伪装好的 `success`；如果在处理中（Pending）立刻报错阻塞后进入队列，以此避免发送行为错乱。

---

## 7. 异常处理与映射机制

MCP Server 会主动捕获下层的 HTTP Timeout 和各种底层的 EWS 报错 `ErrorXXX`。统一捕获 `try...except Exception as e` 并将报错原由转换为含有 `success: false` 和明确报错指导字符串（string）交还给 Agent。模型通常非常聪明，能基于异常字符串自己反思，并在下次发送正确参数，最终向真实的人类汇报执行详情。
