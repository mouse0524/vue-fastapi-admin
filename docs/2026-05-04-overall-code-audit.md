# 项目整体代码审计报告

审计日期：2026-05-04

审计范围：后端 `app/**`、前端 `web/src/**`、测试 `tests/**`、迁移、Docker/Nginx/依赖配置与核心业务流程。

审计方式：源码级只读审计。审计过程中未修改业务文件，未执行动态渗透测试、依赖漏洞扫描或容器运行时检查。

## 审计结论

当前项目功能完整，后端采用 FastAPI + Tortoise ORM，前端采用 Vue3 + Naive UI，整体适合中小型管理后台和工单系统。但生产安全基线偏弱，主要风险集中在以下方向：

- 硬编码密钥、默认账号和默认弱配置。
- Skill-Know SQL 查询接口存在高风险数据泄露面。
- 工单附件绑定、技术处理和操作日志存在越权风险。
- Skill-Know 缺少行级权限和资源归属模型。
- WebDAV 分享权限边界不清晰。
- 审计日志可能持久化敏感信息。
- 前端富文本 XSS 与 localStorage token 存储形成高危组合。

优先级建议：先修复 Critical/High 安全问题，再处理性能与可维护性重构。

## Critical

| 编号 | 问题 | 位置 | 风险 | 建议 |
|---|---|---|---|---|
| C1 | 硬编码 JWT `SECRET_KEY`、弱默认数据库密码、默认 `DEBUG=True`、宽松 CORS | `app/settings/config.py:13-30` | 仓库泄露后可伪造 JWT；生产未覆盖配置时数据库弱口令、调试信息泄露、跨域攻击面扩大 | `SECRET_KEY`、数据库/Redis 密码必须从环境变量或密钥系统读取；生产启动校验非默认值；轮换现有密钥；`DEBUG=False`；CORS 改白名单 |
| C2 | 生产 Docker Compose 明文写入 MySQL/Redis 密码 | `docker-compose.yml:15-20`、`docker-compose.yml:32-35`、`docker-compose.yml:56-62` | 数据库和 Redis 凭据已提交到仓库，且 Redis 密码暴露在 command/healthcheck | 立即轮换密码；使用 `.env`、Docker secrets 或密钥管理系统；不要在 command 中写明文密码 |
| C3 | 默认超级管理员 `admin/123456` 自动初始化 | `app/core/init_app.py:65-76`，README 也公开默认账号 | 空库部署后自动创建公开凭据的超级管理员，生产若未修改可被直接接管 | 生产禁用固定默认账号；改为一次性初始化向导/环境变量创建；强制首次登录改密 |
| C4 | Skill-Know SQL “只读查询”可绕过表白名单读取任意表 | `app/services/skill_know/search_service.py:22-36` | 当前只检查 SQL 文本包含允许表名，可构造 `SELECT user.* FROM user, sk_skill` 等读取用户、配置、审计日志 | 移除原始 SQL 接口；或使用 SQL AST 严格校验所有 `FROM/JOIN/子查询` 表；强制字段白名单、`LIMIT`、超时、只读账号 |
| C5 | 工单附件绑定存在越权，可绑定他人未绑定附件 | `app/controllers/ticket.py:148-166`、调用点 `203-204`、`441-442` | 如果知道未绑定附件 ID，用户可把他人附件绑定到自己工单并下载 | 删除宽松绑定逻辑；附件绑定必须校验 `ticket_id=None` 且 `uploader_id == 当前用户`；附件 ID 使用不可枚举 UUID |
| C6 | 技术人员可处理任意 `TECH_PROCESSING` 工单 | `app/api/v1/tickets/tickets.py:215-237`、`app/controllers/ticket.py:333-382` | 只校验“技术”角色，未校验 `ticket.tech_id == 当前用户`，任意技术可抢占/驳回/完成他人工单 | 普通技术处理必须校验被指派；管理员代操作走单独接口并记录原因；不要在普通技术动作中无条件重写 `tech_id` |
| C7 | Skill-Know 缺少行级权限和归属字段 | `app/models/admin.py:214-345`、`app/api/v1/skill_know/*.py` | 有 Skill-Know API 权限的用户可读改删全量文档、Skill、提示词、会话 | 增加 `created_by/owner_id/tenant_id/visibility`；接口按当前用户过滤；区分普通用户、知识库管理员、系统管理员 |

## High

| 编号 | 问题 | 位置 | 风险 | 建议 |
|---|---|---|---|---|
| H1 | 审计日志记录请求体和响应体，缺少敏感字段脱敏 | `app/core/middlewares.py:63-88`、`app/core/middlewares.py:198-213` | 密码、验证码、SMTP/WebDAV 密码、LLM API Key、token 可能持久化到 `AuditLog` | 建立字段级脱敏规则；敏感接口排除或只记录摘要；响应体默认不落库；清理历史敏感日志 |
| H2 | JWT 认证未校验用户启用状态，且 401 可能被转成 500 | `app/core/dependency.py:13-28` | 被禁用用户旧 token 仍可访问；`HTTPException(401)` 被宽泛 `except Exception` 转为 500 | 校验 `user.is_active`；显式重新抛出 `HTTPException`；加入 token version/jti 黑名单；缩短 access token |
| H3 | WebDAV/LLM Base URL 缺少 SSRF 防护 | `app/controllers/webdav.py:360-365`、`app/services/skill_know/openai_client.py`、`app/schemas/settings.py` | 可配置 URL 被后端请求，可能访问内网/云 metadata；LLM API Key 和知识内容可外发到攻击者服务 | URL 白名单；禁止 localhost/私网/link-local/metadata IP；DNS 解析后校验；LLM provider 白名单 |
| H4 | Skill-Know 文档/Skill 列表和搜索返回完整内容及绝对路径 | `app/services/skill_know/document_service.py:71-90`、`160-162`、`app/services/skill_know/utils.py:43-51` | 搜索/列表可批量泄露文档全文、服务器文件路径、内部知识 | 列表/搜索只返回摘要；详情按权限返回内容；永不返回绝对路径；下载用授权 opaque ID |
| H5 | WebDAV 分享创建未校验目标路径是否存在、是否为文件、是否可分享 | `app/controllers/webdav.py:372-407` | 用户可构造任意 WebDAV 路径生成分享，后端使用系统 WebDAV 凭据下载 | 创建分享前 `PROPFIND/HEAD` 校验；服务端提取真实文件名；引入目录 ACL；敏感目录禁止分享 |
| H6 | WebDAV 公开下载路由同时挂到 `/public/webdav` 和 `/webdav` | `app/api/v1/__init__.py:24-36` | 公开接口出现在非 public 前缀下，权限边界和网关策略容易误判 | 公开下载仅保留 `/api/v1/public/webdav/...`；删除 `/api/v1/webdav` 下 public router 挂载 |
| H7 | 工单操作日志接口缺少工单归属/角色权限校验 | `app/api/v1/tickets/tickets.py:309-313` | 普通用户可通过枚举 `ticket_id` 查看他人工单流转日志、审核/技术备注 | 复用工单详情权限；普通用户仅自己，技术仅指派，客服/管理员全量 |
| H8 | Skill-Know 会话无用户归属，可查看/删除所有对话 | `app/models/admin.py:300-321`、`app/services/skill_know/chat_service.py`、`app/api/v1/skill_know/chat.py` | 用户问题、模型回复、检索上下文和时间线可能互相泄露 | 会话/消息增加 `user_id`；创建和查询按当前用户过滤；管理员查看另设审计接口 |
| H9 | 前端 token 存储在 localStorage | `web/src/utils/auth/token.js:3-14` | 一旦出现 XSS，攻击者可直接读取 token 冒用账号 | 改为 `HttpOnly + Secure + SameSite` Cookie；缩短 token 生命周期；配合 CSP 和 token 轮换 |
| H10 | 自研 HTML sanitizer 与富文本编辑器存在 XSS 绕过风险 | `web/src/utils/common/sanitize.js:1-51`、`web/src/components/editor/RichTextEditor.vue:55-72` | 允许 `style`、`class`、`data:image/*`，Quill 直接 `innerHTML` 输入/输出，存在存储型 XSS 链路 | 使用 DOMPurify/成熟库；禁用 `style` 和 SVG data URI；Quill 输入、输出、提交前都净化；后端也净化 |
| H11 | Nginx 缺少 HTTPS 和安全响应头 | `deploy/web.conf:1-13` | 管理后台登录和 token 可能明文传输；缺少点击劫持、MIME sniffing、CSP 防护 | 生产强制 HTTPS；添加 HSTS、CSP、X-Frame-Options/frame-ancestors、nosniff、Referrer-Policy |
| H12 | OpenAPI 默认公开 | `app/__init__.py:27-33` | 暴露接口路径、参数和认证结构，降低攻击枚举成本 | 生产关闭 `/docs`、`/redoc`、`/openapi.json`，或加认证/IP 白名单 |

## Medium

| 编号 | 问题 | 位置 | 风险 | 建议 |
|---|---|---|---|---|
| M1 | WebDAV 上传完整文件读入内存 | `app/controllers/webdav.py:296-320` | 多并发大文件上传可导致内存放大或 DoS | 流式上传；限制并发、用户/IP 频率；检查 `Content-Length` |
| M2 | Skill-Know 文档上传仅按扩展名校验且一次性读入内存 | `app/services/skill_know/document_service.py:28-41`、`55-68` | 伪造文件类型、解析器资源消耗、内存压力 | magic/MIME 校验；流式落盘；解析进后台任务；PDF 页数/docx 解压大小/文本长度限制 |
| M3 | 知识包导入缺少大小、结构和条目数量限制 | `app/api/v1/skill_know/pack.py`、`app/services/skill_know/pack_service.py:30-74` | 大 JSON 或大量 Skill/Relation 导入造成内存/数据库 DoS，脏数据进入知识库 | 限制文件大小、条目数、字段长度；Pydantic schema 校验；后台任务和配额 |
| M4 | 批量上传任务使用进程内全局字典 | `app/api/v1/skill_know/upload.py` | 无 TTL/容量限制；多 worker 状态不一致；task_id 泄露可查他人任务 | 使用 Redis/DB 并设置 TTL；绑定用户 ID；限制单用户并发 |
| M5 | 异常处理可能返回内部异常细节 | `app/core/exceptions.py` | SQL、路径、模型字段、请求参数可能暴露给前端 | 客户端返回通用错误；详细错误仅写日志并脱敏 |
| M6 | WebDAV 分享码熵偏低 | `app/controllers/webdav.py:392-397` | 约 48 bit 分享码长期偏弱，公开下载可被分布式猜测 | 使用至少 128 bit 随机 code；增加下载次数限制、分享密码、成功/失败审计 |
| M7 | 密码找回存在账号枚举风险 | `app/api/v1/base/base.py` | 未注册邮箱返回差异信息，可枚举账号；缺少邮箱/IP 频控 | 统一返回“如邮箱存在已发送”；增加邮箱/IP/账号限流 |
| M8 | 多个分页参数缺少上限 | `app/api/v1/tickets/tickets.py:93-106`、`app/api/v1/partner/partner.py`、部分系统列表 | 超大 `page_size` 可拖慢数据库和序列化 | 全局统一 `page>=1`、`page_size<=100`；深分页限制或游标分页 |
| M9 | 工单状态机不一致，技术驳回后编辑可能绕过客服复审 | `app/controllers/ticket.py:402-453`、`455-469` | `update_ticket` 和 `resubmit_ticket` 对 `TECH_REJECTED` 流转不一致 | 建立集中状态机；明确技术驳回后是否客服复审；接口复用同一迁移逻辑 |
| M10 | 工单富文本后端正则清洗不完整 | `app/controllers/ticket.py:97-114` 及备注/描述写入点 | 正则难覆盖 SVG、style、data URL、编码绕过，可能存储型 XSS | 使用 bleach/nh3 等白名单 sanitizer；URL 协议白名单；前端展示再净化 |
| M11 | 注册审核存在并发竞态 | `app/controllers/partner.py` | 并发注册/审核可能重复申请、重复创建用户或状态不一致 | 注册和审核使用事务；条件更新 `WHERE status=pending`；唯一约束异常友好处理 |
| M12 | 注册申请列表返回完整个人信息 | `app/api/v1/partner/partner.py` | 公司、联系人、邮箱、手机号、硬件 ID 暴露面较大 | 列表脱敏，详情按权限展示；访问审计 |
| M13 | 前端 SSE 流式对话错误处理不足 | `web/src/views/skill-know/chat/index.vue:31-49` | `resp.ok`/`resp.body` 未检查，单条 JSON parse 无容错，401 不统一登出 | 检查响应状态；逐条 try/catch；AbortController；限制 timeline 长度 |
| M14 | 前端响应拦截器直接展示后端 `msg` | `web/src/utils/http/interceptors.js` | 后端内部错误、路径、SQL 信息可能展示给普通用户 | 生产展示通用文案；业务码 401 统一登出；详细错误仅日志 |
| M15 | 文件上传前端缺少统一大小/类型/数量校验 | `web/src/api/index.js`、工单和 Skill-Know 上传页面 | 依赖 `accept`，可绕过；公开上传更易被滥用 | 抽统一上传校验；后端重新校验；公开上传加验证码/限流 |
| M16 | Docker 生产暴露 MySQL/Redis 到宿主机 | `docker-compose.yml:42-43`、`57-58` | 如果防火墙不严，数据库/Redis 可被扫描爆破 | 生产移除 `ports`；仅内部网络访问；运维用 VPN/SSH tunnel |
| M17 | 依赖较旧且缺少安全审计流程 | `pyproject.toml:6`、`web/package.json`、`web/pnpm-lock.yaml` | `quill@1.3.7`、旧 Vite/插件、Python 依赖需核对 CVE；开发工具混入运行依赖 | 建立 `pip-audit`/`pnpm audit`/Renovate；升级富文本和构建链；拆分运行/开发依赖 |

## Low

| 编号 | 问题 | 位置 | 风险 | 建议 |
|---|---|---|---|---|
| L1 | 权限控制依赖 method/path 与数据库 API 记录完全匹配 | `app/core/dependency.py:31-46` | 新增接口权限表不同步时可能误拒绝或误授权；每次请求加载角色 API 有性能压力 | 使用声明式 permission code/scope；启动时校验路由和权限表；缓存权限并在角色变更失效 |
| L2 | 输入字段长度约束不统一 | 多个 `app/schemas/*.py` | 超长输入可导致日志、邮件、LLM prompt、前端渲染膨胀 | 外部输入统一加 `max_length`、列表数量、dict 深度限制 |
| L3 | Skill-Know 删除文档只删数据库不删物理文件 | `app/services/skill_know/document_service.py:102-106` | 已删除文档仍残留磁盘，造成存储膨胀和潜在泄露 | 删除时校验路径并删除文件；或实现软删除归档和定期清理 |
| L4 | Skill-Know 允许 `.doc`，但解析逻辑实际按 docx | `app/services/skill_know/document_service.py:32-34`、`document_parser.py` | 合法 `.doc` 上传会处理失败 | 不支持则移除 `.doc`；支持则用隔离转换服务 |
| L5 | WebDAV 目录缓存 TTL 较长 | `app/controllers/webdav.py` | 外部 WebDAV 变更后列表陈旧，可能误分享或展示旧文件 | 缩短 TTL；增加手动刷新；分享创建前实时校验 |
| L6 | 前端 `api/index.js` 过大，领域边界弱 | `web/src/api/index.js` | Auth、系统、工单、Skill-Know、WebDAV 混在单文件，维护成本高 | 拆分为 `authApi`、`ticketApi`、`systemApi`、`skillKnowApi` |
| L7 | 工单上传/预览逻辑重复且 object URL 未统一释放 | `web/src/views/ticket/submit/index.vue`、`my/index.vue` | 内存泄漏，修复不一致 | 抽 `useTicketAttachmentUpload`；删除/重置/卸载时 `URL.revokeObjectURL` |
| L8 | `htmlToPlainText` 用正则去标签 | `web/src/utils/common/sanitize.js:54-59` | 容易被误用为安全净化 | 明确仅用于展示/复制；如需纯文本用 DOMParser `textContent` |

## 关键流程审查

### 工单流程

发现附件绑定越权、技术处理越权、操作日志越权、状态机不一致、分页无限制、富文本净化不足。工单是当前最需要立即加测试和权限服务抽象的业务域。

### 注册审核流程

基础角色限制存在，但注册/审核并发控制不足，列表个人信息缺少脱敏。建议补事务和条件更新。

### WebDAV 流程

分享创建边界不足，公开路由挂载混淆，分享码偏短，上传内存放大。建议先修分享权限和路由，再做流式上传。

### Skill-Know 流程

最大风险是 SQL 接口、行级权限缺失、内容/路径过度返回、上传解析 DoS、会话无归属、LLM Base URL SSRF/外发风险。建议把 Skill-Know 从“管理员全局工具”改为带 owner/visibility 的权限模型。

### 前端流程

localStorage token 与富文本 XSS 形成高危组合。建议优先改 token 承载方式、引入成熟 sanitizer、加 CSP。

### 部署流程

默认生产配置不满足安全基线。建议先轮换凭据、关闭默认账号风险、收紧 CORS/DEBUG/OpenAPI、配置 HTTPS 和安全头。

## 代码质量与可维护性

### 代码规范

后端整体模块划分清晰，FastAPI Controller/Schema/Model 层基本分离；但权限判断分散在 API 与 Controller，状态流转散落，容易产生不一致。

### 注释完整性

多数业务逻辑自解释，但关键安全逻辑缺少注释和测试，例如附件绑定 fallback、WebDAV 分享校验边界、SQL 白名单策略。

### 命名合理性

整体命名可读；部分通用函数如 `get_ticket`、`sql`、`sanitizeHtml` 容易掩盖安全语义，建议命名中体现权限/安全边界，如 `get_ticket_unchecked`、`unsafe_sql_query` 或移除。

### 重复率

前端上传/预览、后端权限判断、工单状态迁移存在明显重复。建议抽公共服务和 composable。

### 复杂度

`ticket.py`、`webdav.py`、`api/index.js`、`settings/index.vue`、Skill-Know 服务链路较重。建议按权限、状态机、上传、安全净化、外部服务访问拆分基础组件。

### 测试覆盖

当前 `tests/` 只有少量工单和 Skill-Know 支持测试，缺少安全回归测试。应补越权、输入校验、上传、SQL、SSRF、XSS 净化、状态机测试。

## 性能瓶颈

- 文档/WebDAV 上传一次性读入内存，需流式处理。
- 文档解析同步执行在请求链路，需后台任务队列。
- 多个列表接口 `page_size` 无上限，需统一分页约束。
- 工单列表逐个查询用户基本信息，建议一次性批量查用户表。
- Skill-Know 文档列表/搜索返回完整内容，前端过滤大字段会拖慢浏览器和网络。
- Chroma 客户端每次 `_client()` 创建 `PersistentClient`，长期高频检索可能有额外开销，建议复用客户端实例并监控连接/句柄。

## 架构评估

当前架构适合中小型管理后台：FastAPI + Tortoise ORM + Vue3 + Naive UI，业务模块清晰，迭代速度快。

主要架构短板：

- 权限模型缺少行级/资源级授权，当前更偏接口级 RBAC。
- 安全配置缺少生产 profile 和启动时校验。
- 外部服务访问没有统一出口治理，WebDAV/LLM SSRF 风险分散。
- 文件上传没有统一安全上传组件。
- 工单缺少集中状态机。
- Skill-Know 缺少多用户/多租户可见性模型。
- 审计日志缺少脱敏和数据保留策略。

建议建立以下基础能力：

- `PermissionService`：资源级授权矩阵。
- `TicketStateMachine`：统一工单状态流转。
- `SafeUploadService`：大小、MIME、magic、流式、清理、配额。
- `SafeUrlValidator`：外部 URL SSRF 防护。
- `AuditSanitizer`：请求/响应脱敏。
- `ContentSanitizer`：后端 HTML 白名单净化。
- `SecuritySettingsValidator`：生产启动配置检查。

## 整改路线

| 优先级 | 范围 | 建议动作 |
|---|---|---|
| P0 | 密钥与默认账号 | 轮换 JWT/MySQL/Redis 密钥；移除硬编码；禁用生产默认 `admin/123456`；关闭生产 DEBUG/OpenAPI |
| P0 | SQL 与越权 | 禁用或重写 Skill-Know SQL；修复附件绑定越权；修复技术处理越权；修复工单 actions 越权 |
| P0 | Skill-Know 权限 | 增加 owner/visibility；会话、文档、Skill 全部按用户过滤 |
| P1 | XSS 与 token | 引入 DOMPurify/后端 sanitizer；Quill 输入输出净化；token 改 HttpOnly Cookie；加 CSP |
| P1 | SSRF 与外部服务 | WebDAV/LLM Base URL 白名单和私网 IP 禁止；LLM 上下文最小化 |
| P1 | 上传与文件安全 | 流式上传；magic 校验；解析后台化；删除物理文件；知识包 schema/大小限制 |
| P2 | 性能与维护 | 分页上限；批量查询；拆分前端 API；抽权限服务、状态机、上传 composable |
| P2 | 测试与治理 | 增加安全回归测试；引入依赖漏洞扫描；生产安全配置检查；审计日志脱敏测试 |

## 建议新增测试

- 工单附件绑定：用户 A 不能绑定用户 B 未绑定附件。
- 技术处理：非指派技术不能完成/驳回工单。
- 工单操作日志：无关用户不能查看他人工单日志。
- Skill-Know SQL：`user, sk_skill`、`sk_system_config, sk_skill`、`UNION`、函数调用均拒绝。
- Skill-Know 会话：用户不能查看/删除他人会话。
- WebDAV 分享：不存在路径、目录路径、未授权路径不能创建分享。
- 审计日志：password/token/api_key/captcha/smtp/webdav 字段必须脱敏。
- XSS 净化：事件属性、SVG data URI、style、javascript URL 均被清除。
- 上传：伪造扩展名、超大文件、解析失败文件不会残留或泄露路径。

## 审计限制

- 本次为源码级只读审计，未执行依赖漏洞扫描、动态渗透测试、容器运行时检查或数据库实测。
- 未发现独立设计文档，关键流程按 README、代码行为和现有测试推断。
- 生产环境是否覆盖默认配置、是否有网关限流/HTTPS/WAF/安全组保护，需要运维侧进一步确认。
