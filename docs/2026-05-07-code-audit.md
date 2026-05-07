# 2026-05-07 代码审计报告

本报告基于当前仓库的只读代码审计结果整理，覆盖安全风险、重复代码、无用配置、依赖与部署配置问题。审计范围包括 FastAPI 后端、Vue 前端、Docker/Nginx 部署配置、依赖清单与部分测试/文档结构。

## 一、审计结论摘要

项目整体为 `FastAPI + Tortoise ORM + Vue 3 + Vite + Nginx/Docker` 架构。主要风险集中在以下方面：

- 生产敏感配置硬编码：JWT 密钥、数据库密码、Redis 密码等存在于源码或 compose 文件中。
- 默认超级管理员弱口令：首次初始化会创建 `admin / 123456`。
- SQL 自由查询入口：`Skill-Know` 存在直接执行用户输入 SQL 的接口。
- 工单附件绑定存在所有权绕过：未绑定附件可被宽松绑定到其他工单。
- CORS、DEBUG、OpenAPI、Nginx 安全头等生产安全配置偏弱。
- 审计日志可能记录密码、验证码、API Key、WebDAV/SMTP 密码等敏感信息。
- 前端存在 `localStorage` token、HTML sanitizer 自研实现、依赖偏旧等风险。
- 后端依赖、系统设置、Docker 配置、前端 API 模块存在重复和无用配置。

建议优先处理 Critical/High 项，再进行配置收敛和代码结构治理。

## 二、Critical 风险

### 1. 硬编码生产密钥、数据库密码、Redis 密码

- 分类：`A02: Cryptographic Failures`
- 位置：`app/settings/config.py:24`
- 位置：`docker-compose.yml:16`
- 位置：`docker-compose.yml:20`
- 位置：`docker-compose.yml:32`
- 位置：`docker-compose.yml:35`
- 位置：`docker-compose.yml:56`
- 位置：`docker-compose.yml:62`
- 位置：`docker-compose.dev.yml:16`
- 位置：`docker-compose.dev.yml:20`

问题：`SECRET_KEY` 固定在源码中，MySQL/Redis 密码也在仓库配置中明文存在。

风险：泄露后可伪造 JWT、连接数据库、访问 Redis，甚至复用到其他环境。

修复方案：

- 将 `SECRET_KEY`、数据库密码、Redis 密码全部改为环境变量注入。
- 仓库只保留 `.env.example`，真实 `.env` 不提交。
- 生产环境立即轮换现有 JWT 密钥、MySQL 用户密码、Redis 密码。
- `SECRET_KEY` 缺失时启动失败，禁止默认值兜底。

### 2. 默认初始化超级管理员 `admin / 123456`

- 分类：`A05: Security Misconfiguration`
- 位置：`app/core/init_app.py:65-76`

问题：系统首次启动时，如果没有用户，会自动创建弱口令超级管理员。

风险：首次部署未及时修改密码时，任何人都可能接管系统。验证码和登录锁定无法抵消默认凭据风险。

修复方案：

- 禁止生产自动创建弱口令超级管理员。
- 初始管理员密码从环境变量读取，并强制满足强密码策略。
- 或改为运维手动执行初始化命令创建管理员。
- 首次登录强制改密，并记录默认账号是否仍未变更。

### 3. `Skill-Know` SQL 搜索直接执行用户 SQL

- 分类：`A03: Injection`
- 位置：`app/api/v1/skill_know/search.py:15-17`
- 位置：`app/services/skill_know/search_service.py:27-41`

问题：接口只检查 `SELECT`、分号、部分关键字和表名包含，然后直接执行用户输入 SQL。

风险：攻击者可利用复杂 `SELECT`、函数、子查询、注释、大小写/空白变体、`UNION`、`INFORMATION_SCHEMA`、大结果集等方式绕过或拖垮数据库。即使限定只读，也可能造成数据泄露和拒绝服务。

修复方案：

- 不暴露自由 SQL。
- 改为白名单查询 API：固定表、固定字段、固定过滤条件、固定排序、强制 `LIMIT`。
- 如必须保留 SQL，应使用 SQL AST 解析器做严格白名单，并限制查询时间、结果行数、字段列表和数据库账号权限。
- 该接口只允许管理员角色使用，且单独加审计和限流。

### 4. 工单附件绑定存在所有权绕过

- 分类：`A01: Broken Access Control`
- 位置：`app/controllers/ticket.py:148-166`

问题：`_bind_attachments` 先按 `uploader_id` 严格绑定，若数量不足，会把剩余未绑定附件在不校验所有者的情况下绑定到当前工单。

风险：攻击者如果猜到未绑定附件 ID，可能把他人的临时附件绑定进自己的工单，进而获得下载入口或造成数据错乱。

修复方案：

- 删除 `remaining_ids` 的宽松绑定逻辑。
- 所有附件绑定必须满足 `id__in=attachment_ids`、`ticket_id=None`、`uploader_id__in=owner_ids`。
- 如果绑定数量不足，直接拒绝并返回非法附件 ID。
- 附件 ID 建议使用不可预测 UUID，或上传后返回短期绑定 token，而不是递增 ID。

## 三、High 风险

### 1. CORS 全开放且允许凭据

- 分类：`A05: Security Misconfiguration`
- 位置：`app/settings/config.py:13-16`
- 位置：`app/core/init_app.py:30-38`

问题：`allow_origins=["*"]`、`allow_credentials=True`、方法和请求头全开放。

风险：扩大跨站调用面，后续如果改用 cookie 会直接变成高危配置。

修复方案：生产环境只允许明确域名，例如 `https://your-domain.com`。不要在生产使用 `*`。按需开放方法和 header。

### 2. 生产默认 `DEBUG=True`，OpenAPI 始终暴露

- 分类：`A05: Security Misconfiguration`
- 位置：`app/settings/config.py:19`
- 位置：`app/__init__.py:27-34`

问题：日志级别默认 DEBUG，`/openapi.json` 和默认 docs 路径可被访问。

风险：接口结构、字段、认证 header 名称和内部模块会暴露。

修复方案：生产 `DEBUG=False`。生产环境禁用或鉴权保护 `/docs`、`/redoc`、`/openapi.json`。

### 3. 审计日志可能保存敏感信息

- 分类：`A09: Security Logging and Monitoring Failures`
- 位置：`app/core/middlewares.py:63-88`
- 位置：`app/core/middlewares.py:90-139`
- 位置：`app/core/middlewares.py:210-213`

问题：审计日志会记录 POST/PUT/PATCH 请求体，并记录非 GET 的响应体。除 `/api/v1/base/access_token` 外，重置密码、邮箱验证码、系统设置、WebDAV 配置、SMTP 配置、LLM API Key、用户信息等都可能进入 `AuditLog`。

修复方案：

- 引入敏感字段脱敏清单：`password`、`old_password`、`new_password`、`token`、`secret`、`captcha_code`、`email_code`、`smtp_password`、`webdav_password`、`api_key` 等。
- 响应体也应按字段脱敏或默认不保存。
- 审计日志查看接口增加更细粒度权限，并设置保留周期。

### 4. `/ticket/actions` 未校验工单归属

- 分类：`A01: Broken Access Control`
- 位置：`app/api/v1/tickets/tickets.py:309-313`

问题：接口只依赖路由级权限，没有像 `/ticket/get` 一样校验当前用户是否能查看该工单。

风险：只要用户拥有 `GET /api/v1/ticket/actions` 权限，就可能枚举其他工单操作日志。

修复方案：复用 `/ticket/get` 的权限判断。非管理员/客服只能看自己提交或指派给自己的工单。

### 5. `base/workbench_stats` 对所有登录用户泄露全局统计

- 分类：`A01: Broken Access Control`
- 位置：`app/api/v1/base/base.py:189-236`

问题：只要登录即可获取全局工单总数、待审注册数、用户总数、审计日志数等运营信息。

风险：普通用户可获取不必要的全局运营数据。

修复方案：按角色返回差异化统计。普通用户只返回自己的工单统计；技术只返回分配给自己的工单；客服/管理员才返回全局统计。

### 6. MySQL 和 Redis 端口直接映射到宿主机

- 分类：`A05: Network Exposure`
- 位置：`docker-compose.yml:42-43`
- 位置：`docker-compose.yml:57-58`
- 位置：`docker-compose.dev.yml:53-54`
- 位置：`docker-compose.dev.yml:68-69`

问题：数据库和 Redis 暴露到宿主端口。

风险：若宿主安全组/防火墙配置不严，可能被外部探测或暴力破解。

修复方案：生产环境删除 MySQL/Redis 的 `ports`，只使用 Docker 内部网络。如需运维访问，绑定到 `127.0.0.1` 或通过堡垒机/VPN。

### 7. Nginx 未配置 HTTPS 和安全响应头

- 分类：`A05: Missing Security Headers`
- 位置：`deploy/web.conf:1-13`

问题：缺少 HSTS、CSP、X-Frame-Options、X-Content-Type-Options、Referrer-Policy、Permissions-Policy。

风险：站点可能受点击劫持、MIME sniffing、弱 CSP 等影响。

修复方案：在 Nginx 添加安全头；生产强制 HTTPS；为 `/api/` 添加 `proxy_set_header Host`、`X-Real-IP`、`X-Forwarded-For`、`X-Forwarded-Proto`。

## 四、Medium 风险

### 1. 前端 HTML 净化为自研实现，允许 `style` 属性

- 分类：`A07: XSS`
- 位置：`web/src/utils/common/sanitize.js:1-52`
- 位置：`web/src/views/ticket/components/TicketDetailModal.vue:194`
- 位置：`web/src/views/ticket/components/TicketDetailModal.vue:258`
- 位置：`web/src/views/system/notice/index.vue:136`
- 位置：`web/src/views/system/notice/index.vue:187`

问题：自研 sanitizer 容易漏掉边界，当前允许 `style`、`target`、`class`，并允许 `data:image/*`。

修复方案：使用成熟库 `DOMPurify`，按业务配置白名单。默认禁止 `style`，`target="_blank"` 自动补 `rel="noopener noreferrer"`。

### 2. 后端富文本清洗使用正则，不足以作为安全边界

- 分类：`A07: XSS`
- 位置：`app/controllers/ticket.py:97-114`

问题：正则处理 HTML 容易漏掉编码、嵌套、畸形标签、SVG/MathML、CSS 等绕过。

修复方案：后端使用 `bleach` 或等价 HTML sanitizer，明确允许标签和属性。

### 3. 前端 JWT 存储在 `localStorage`

- 分类：`A02: Token Handling`
- 位置：`web/src/utils/auth/token.js:1-15`
- 位置：`web/src/utils/http/interceptors.js:11-14`

问题：token 存在 `localStorage`，请求时通过 `token` header 发送。

风险：一旦发生 XSS，攻击者可直接读取 `access_token` 并复用。当前 token 有效期为 7 天，窗口较长。

修复方案：优先改为 `HttpOnly + Secure + SameSite=Lax/Strict` cookie 存储会话，配合 CSRF 防护。短期内至少缩短 access token 有效期，并引入 refresh token 和服务端撤销机制。

### 4. JWT 缺少 issuer/audience/jti，且过期时间较长

- 分类：`A02: JWT`
- 位置：`app/settings/config.py:26`
- 位置：`app/utils/jwt_utils.py:7-10`
- 位置：`app/core/dependency.py:13-28`

问题：7 天 access token 被盗后可长期使用；没有 `issuer/audience/jti` 不利于跨服务隔离和撤销。

修复方案：access token 缩短到 15-60 分钟；增加 refresh token；验证 `iss`、`aud`、`exp`、`iat`、`jti`。用户改密、禁用、角色变更后使旧 token 失效。

### 5. 异常响应暴露内部异常细节

- 分类：`A05: Information Disclosure`
- 位置：`app/core/exceptions.py:17-23`
- 位置：`app/core/exceptions.py:26-32`
- 位置：`app/core/exceptions.py:41-50`

问题：`DoesNotExist`、`IntegrityError`、`RequestValidationError`、`ResponseValidationError` 把异常内容返回给客户端。

风险：可能泄露模型名、字段、查询参数、校验结构。

修复方案：生产环境返回通用错误信息，详细异常只写日志。按 `settings.DEBUG` 控制是否暴露细节。

### 6. `WebDAV` 连接测试存在 SSRF 风险

- 分类：`A04: Insecure Design`
- 位置：`app/controllers/system_setting.py:191-233`

问题：管理员可配置任意 `webdav_base_url` 并由服务器发起请求。

风险：管理员账号被盗后，该功能可被用于探测内网服务。

修复方案：限制协议仅 `https`，禁止内网 IP、localhost、link-local、metadata 地址；或维护允许域名白名单。

### 7. WebDAV 上传把完整文件读入内存

- 分类：`A05: Resource Exhaustion`
- 位置：`app/controllers/webdav.py:308-320`

问题：上传时累积 `chunks` 后 `b"".join(chunks)`，完整文件进入内存。

风险：多个并发大文件会造成内存压力。

修复方案：使用流式上传，避免完整文件驻留内存。对上传接口增加并发限制和速率限制。

### 8. 前端依赖偏旧且存在已知高风险候选

- 分类：`A06: Vulnerable Components`
- 位置：`web/package.json:20`
- 位置：`web/package.json:27`
- 位置：`web/package.json:43-44`

问题：`axios ^1.4.0`、`quill ^1.3.7`、`vite ^4.4.6` 偏旧。`quill 1.x` 历史上与 XSS 风险相关，Vite 4 也经历多次安全修复。

修复方案：升级到当前安全版本，例如 `axios` 最新 1.x、`quill` 2.x 或替换编辑器、Vite 5/6/7 视项目兼容性推进。

审计限制：`npm audit` 因无 `package-lock.json` 失败；`pnpm audit` 因当前 registry `npmmirror` audit endpoint 不存在失败。建议临时切换官方 registry 执行审计。

## 五、Low 风险

### 1. 容器以 root 运行，镜像安装了不必要工具

- 分类：`A05: Docker Hardening`
- 位置：`Dockerfile:13-38`
- 位置：`Dockerfile:26`

问题：生产镜像安装 `vim`、`curl`、`procps`、`net-tools`、数据库客户端等，且默认 root 运行。

修复方案：生产镜像使用非 root 用户；去掉调试工具；分离构建依赖和运行依赖；增加 `read_only`、`cap_drop`、资源限制。

### 2. 生产构建使用镜像源并未锁定所有依赖来源

- 分类：`A05: Supply Chain`
- 位置：`Dockerfile:8`
- 位置：`Dockerfile:28`

问题：依赖供应链信任集中在镜像源，且 Python 依赖包含 `markitdown[all]>=0.1.1` 这样的非精确版本。

修复方案：生产使用锁文件和 hash 校验；`requirements.txt` 全部精确 pin；CI 中增加 `pip-audit`、`pnpm audit` 或 SCA 工具。

### 3. 前端 `.env*` 已提交

- 分类：`A05: Public Config Hygiene`
- 位置：`web/.env`
- 位置：`web/.env.production`

说明：当前未看到密钥，仅是公开配置，风险较低。

修复方案：保留非敏感配置可以接受；若后续加入任何 token/key，必须改用 `.env.example` 并忽略真实 `.env`。

## 六、重复代码与无用配置

### 1. Python 依赖维护源重复，且内容不一致

- 严重级别：High
- 位置：`pyproject.toml:6`
- 位置：`requirements.txt:1-68`

问题：后端依赖同时维护在 `pyproject.toml` 和 `requirements.txt`，Docker 实际使用 `requirements.txt`，但 `pyproject.toml` 里还有更多包和重复项，例如 `uvloop==0.21.0` 出现两次，且包含 `pyproject-toml>=0.1.0` 这类 `requirements.txt` 没有的依赖。

风险：本地、CI、Docker、IDE 解析依赖可能不一致，导致本地可跑、容器不可跑，或安全扫描结果不一致。

修复方案：选一个依赖源作为事实来源。建议使用 `pyproject.toml + uv.lock`，Docker 改为按锁文件安装；或反过来删除/弱化 `pyproject.toml` 的 `dependencies`，只保留工具配置。避免手工双写。

### 2. 前端系统设置页存在一批 `ai_kb_*` 表单字段，但后端设置模型不接收

- 严重级别：High
- 位置：`web/src/views/system/settings/index.vue:96-111`
- 位置：`web/src/views/system/settings/index.vue:258-260`
- 位置：`web/src/views/system/settings/index.vue:309-312`
- 位置：`app/schemas/settings.py:6-64`
- 位置：`app/controllers/system_setting.py:244-303`

问题：前端 `form` 和校验规则包含 `ai_kb_enabled`、`ai_kb_openai_base_url`、`ai_kb_openai_api_key`、`ai_kb_chat_model`、`ai_kb_embedding_model` 等字段，但 `SystemSettingUpdateIn` 不定义这些字段，`system_setting_controller.update()` 也没有处理这些 key。Pydantic 默认会忽略额外字段，因此这些配置保存时很可能被静默丢弃。

风险：用户以为保存了 AI 知识库配置，实际后端没有持久化；造成配置失效和排障困难。

修复方案：如果这些配置应归 `Skill-Know` 快速设置，则从系统设置页移除 `ai_kb_*` 字段，统一走 `skill_know_config_service`。如果系统设置页需要承载这些配置，则补齐后端 schema、默认值、存储映射和读取回显。

### 3. Docker 生产构建上下文过大，`.dockerignore` 基本无效

- 严重级别：High
- 位置：`.dockerignore:1`
- 位置：`Dockerfile:16`

问题：`.dockerignore` 只忽略 `web/node_modules`，但仓库包含 `venv`、`.git`、`__pycache__`、测试缓存、文档、历史审计文件等。`Dockerfile` 使用 `ADD . .` 会把大量无关内容复制进镜像上下文/镜像层。

风险：镜像变大、构建变慢，还可能把 `.git`、本地虚拟环境、缓存文件、临时文件带入生产镜像。

修复方案：补充忽略项：`.git`、`venv`、`__pycache__`、`.pytest_cache`、`tests/__pycache__`、`*.pyc`、`web/node_modules`、`web/dist`、日志、临时文件、本地 `.env*`。同时把 `ADD . .` 改成精确 `COPY app requirements.txt pyproject.toml migrations run.py deploy ...`。

### 4. `_get_client_ip` 重复实现

- 严重级别：Medium
- 位置：`app/api/v1/base/base.py:30-40`
- 位置：`app/api/v1/webdav/webdav.py:22-32`

问题：两处逻辑完全同类，都根据 `TRUST_PROXY_HEADERS` 读取 `x-forwarded-for`、`x-real-ip`，否则读 `request.client.host`。

风险：后续修改代理信任策略时容易只改一处，导致登录安全和 WebDAV 下载限流行为不一致。

修复方案：抽到公共工具，例如 `app/utils/request.py:get_client_ip(request)`，两个入口复用。

### 5. 上传文件逻辑重复，且校验策略不统一

- 严重级别：Medium
- 位置：`app/controllers/ticket.py:499-584`
- 位置：`app/controllers/system_setting.py:347-416`
- 位置：`app/services/skill_know/document_service.py:35-99`
- 位置：`app/controllers/webdav.py:296-333`

问题：多处都做文件名、扩展名、目录、大小、写入、删除清理，但实现分散。工单和 Logo 有 magic 头校验，Skill-Know 文档只按扩展名和大小读取，WebDAV 直接读入内存后上传。

风险：安全策略不一致，后续修复文件上传漏洞时容易漏掉某类入口。

修复方案：抽公共上传服务或最少抽公共函数：扩展名规范化、大小限制、magic 校验、临时文件写入、路径安全校验、清理逻辑。按业务传入允许类型和是否需要 magic 校验。

### 6. HTML 清洗逻辑前后端重复且实现不一致

- 严重级别：Medium
- 位置：`app/controllers/ticket.py:97-114`
- 位置：`web/src/utils/common/sanitize.js:1-52`

问题：后端用正则剥离危险标签/属性，前端用 DOMParser 白名单。两套规则不同，可能出现后端认为安全但前端处理不同，或反之。

风险：安全边界不清，XSS 修复难以统一。

修复方案：明确后端存储前清洗 + 前端展示前兜底清洗。后端用成熟库 `bleach`，前端用 `DOMPurify`，并把允许标签/属性作为文档化策略。

### 7. 时间格式化逻辑重复

- 严重级别：Medium
- 位置：`app/models/base.py:21`
- 位置：`app/models/base.py:45`
- 位置：`app/controllers/notice.py:30`
- 位置：`app/controllers/ticket.py:267`

问题：多处直接 `strftime(settings.DATETIME_FORMAT)`。

风险：格式变更、时区处理、空值处理不一致。

修复方案：抽 `format_datetime(value)` 工具函数，统一处理 `None`、时区和字符串返回。

### 8. Docker 生产与开发 compose 重复大量配置

- 严重级别：Medium
- 位置：`docker-compose.yml:1-72`
- 位置：`docker-compose.dev.yml:1-85`

问题：MySQL、Redis、环境变量、密码、healthcheck、volume 大量重复。

风险：修改数据库密码、端口、健康检查时容易遗漏 dev/prod 之一。

修复方案：使用基础 `docker-compose.yml` + `docker-compose.override.yml` 或 `docker-compose.dev.yml` 只覆盖差异项。敏感值统一从 `.env` 注入。

### 9. WebDAV 签名 URL 构造逻辑重复

- 严重级别：Medium
- 位置：`app/api/v1/webdav/webdav.py:52-54`
- 位置：`app/api/v1/webdav/webdav.py:83-85`

问题：创建分享和列表分享都手动 `build_share_signature` + `urlencode` + 拼接下载 URL。

风险：签名参数变化时需要改两处。

修复方案：在 `webdav_controller` 或 API 层抽 `build_share_download_url(code)`。

### 10. 前端 API 封装文件过大

- 严重级别：Medium
- 位置：`web/src/api/index.js:1-200`

问题：用户、角色、菜单、工单、公告、设置、WebDAV、Skill-Know 全部塞在一个对象里，Skill-Know 部分尤其长。

风险：维护成本高，接口命名和权限变更容易冲突。

修复方案：按业务拆分为 `api/base.js`、`api/ticket.js`、`api/settings.js`、`api/webdav.js`、`api/skillKnow.js`，再在 `api/index.js` 聚合导出。

### 11. `settings.KB_DEFAULT_TOP_K` 和 `settings.KB_DEFAULT_MODEL` 未被使用

- 严重级别：Low
- 位置：`app/settings/config.py:120-121`

问题：未发现除定义外的后端引用。

风险：误导维护者，以为知识库默认配置由全局 settings 控制，实际 Skill-Know 使用 `SkillKnowConfigService.DEFAULTS`。

修复方案：删除这两个全局配置，或把 Skill-Know 默认值迁移统一到这里。建议删除，避免双配置源。

### 12. `webdav_signature_ttl` 和 `webdav_max_upload_size` 后端支持，但前端系统设置页未暴露

- 严重级别：Low
- 位置：`app/schemas/settings.py:61-63`
- 位置：`app/controllers/system_setting.py:100-102`
- 位置：`app/controllers/system_setting.py:299-301`
- 位置：`web/src/views/system/settings/index.vue:565-596`

问题：后端有字段和校验，但前端 WebDAV 设置页只展示启用、Base URL、用户名、密码、默认分享时长、签名密钥。

风险：配置只能靠默认值或接口手动提交，运维不可见。

修复方案：如果需要可配置，就在前端补两个输入项；如果不需要用户配置，就从 schema/update mapping 中移除，改为服务端常量或环境变量。

### 13. 前端 Logo 上传允许 `.svg`，后端明确拒绝 SVG

- 严重级别：Low
- 位置：`web/src/views/system/settings/index.vue:441`
- 位置：`app/controllers/system_setting.py:349-351`
- 位置：`app/controllers/system_setting.py:390-398`

问题：前端 `accept=".jpg,.jpeg,.png,.webp,.svg"`，但后端只允许 `jpg/jpeg/png/webp`，且有拒绝 SVG 的分支。

风险：用户可以选择 SVG，但提交后必定失败，属于无效 UI 配置。

修复方案：从前端 `accept` 移除 `.svg`；后端 `detected_ext == "svg"` 分支可保留作为防御性兜底。

### 14. `pyproject.toml` 中 `uvloop` 重复声明

- 严重级别：Low
- 位置：`pyproject.toml:6`

问题：同一依赖同时有 `uvloop==0.21.0` 和 `uvloop==0.21.0 ; sys_platform != 'win32'`。

风险：依赖解析行为不清晰，Windows 环境可能尝试解析不适配包。

修复方案：只保留带平台条件的声明。

### 15. 开发注释和死代码残留

- 严重级别：Low
- 位置：`app/core/dependency.py:43-44`
- 位置：`web/src/utils/auth/token.js:17-31`
- 位置：`web/src/views/system/role/index.vue:338`
- 位置：`web/src/utils/http/interceptors.js:53`

问题：有调试注释、注释掉的 refresh token 代码、TODO、`console.log`。

风险：不影响运行，但增加阅读噪音，也可能在生产控制台泄漏错误对象。

修复方案：删除无用注释和 `console.log`；TODO 如果是真需求，转成 issue 或补实现。

### 16. `.env.production` 与 `docker-compose.dev.yml` 中 `VITE_BASE_API` 重复配置

- 严重级别：Low
- 位置：`web/.env.production:5`
- 位置：`docker-compose.dev.yml:24`
- 位置：`web/.env.development:8`

问题：同一基础 API 路径在多处定义，当前值一致，但后续调整容易遗漏。

修复方案：保留环境专属 `.env.*`，compose 不重复传 `VITE_BASE_API`，除非确实要覆盖。

## 七、优先修复顺序

1. 立即轮换并移除硬编码密钥/密码，修复默认管理员弱口令。
2. 下线或重构 `Skill-Know SQL只读搜索`，删除自由 SQL 执行。
3. 修复工单附件 `_bind_attachments` 所有权绕过。
4. 对审计日志做敏感字段脱敏，避免密码、验证码、API Key 落库。
5. 收紧生产 CORS、关闭 DEBUG/OpenAPI、补齐 Nginx 安全头。
6. 修复 `/ticket/actions` 和 `workbench_stats` 的数据权限边界。
7. 引入成熟 HTML sanitizer，升级前端高风险依赖，改进 token 存储。
8. 清理无用配置：删除或统一 `KB_DEFAULT_*`、`ai_kb_*`、SVG accept、重复 `uvloop`。
9. 统一配置来源：后端依赖只保留一个事实源，Docker compose 敏感值统一 `.env` 注入。
10. 抽公共工具：`get_client_ip`、文件上传/路径校验、时间格式化、WebDAV 下载 URL 构造。
11. 拆分前端 API 模块，降低 `web/src/api/index.js` 的维护压力。

## 八、验证建议

1. 增加后端权限测试：普通用户无法访问他人工单详情、附件、actions、全局统计。
2. 增加附件绑定测试：用户 A 上传的未绑定附件不能被用户 B 绑定。
3. 增加 SQL 搜索安全测试：非白名单字段、子查询、union、无 limit、大结果集都应被拒绝。
4. 增加日志脱敏测试：请求/响应包含 `password`、`token`、`secret`、`captcha_code` 时审计日志必须显示 `******`。
5. 增加系统设置保存回显测试，确认 `ai_kb_*` 这类字段不会被静默丢弃。
6. 增加 Logo 上传测试，确认前后端允许类型一致。
7. CI 增加依赖审计：前端使用官方 npm registry 跑 `pnpm audit`，后端使用 `pip-audit`。
