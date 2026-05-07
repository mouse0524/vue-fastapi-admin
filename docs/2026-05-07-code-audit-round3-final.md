# 2026-05-07 代码审计终版报告（第三轮）

本报告为第三轮复核结果，覆盖：

- 第一轮发现的问题
- 第二轮/第三轮修复闭环
- 当前仍存在的遗留风险
- 验证证据与后续建议

---

## 1. 审计范围

- 后端：`app/`（认证鉴权、权限、上传下载、审计日志、异常处理、配置）
- 前端：`web/src/`（系统设置、请求拦截、HTML 渲染、配置一致性）
- 部署：`Dockerfile`、`docker-compose*.yml`、`deploy/web.conf`、`.dockerignore`
- 测试：`tests/`

---

## 2. 修复闭环（已完成）

### 2.1 认证与密钥安全

1) 默认弱口令超级管理员移除

- 修复前：初始化默认 `admin / 123456`
- 修复后：首个超级管理员必须通过环境变量提供强密码
- 证据：`app/core/init_app.py:68`

2) SECRET_KEY 强制必填

- 修复前：允许硬编码或自动回退
- 修复后：`SECRET_KEY` 缺失即启动失败
- 证据：`app/settings/config.py:26`、`app/settings/config.py:131`

3) JWT Claim 强化（iss/aud/iat/jti）

- 修复前：仅基本 payload 与 exp
- 修复后：签发与校验都要求 `iss/aud/iat/jti`
- 证据：
  - `app/schemas/login.py:18`
  - `app/api/v1/base/base.py:87`
  - `app/core/dependency.py:15`

### 2.2 权限与访问控制

4) 工单附件绑定越权修复

- 修复前：存在宽松回退绑定，可能绑定非本人附件
- 修复后：仅允许 `ticket_id=None 且 uploader_id 在 owner_ids 内` 的附件绑定；不足即拒绝
- 证据：`app/controllers/ticket.py:152`

5) 工单操作日志接口补权限校验

- 修复前：`/ticket/actions` 可被越权查看
- 修复后：复用工单访问判定 `_can_access_ticket`
- 证据：`app/api/v1/tickets/tickets.py:313`

6) 工作台统计按角色隔离

- 修复前：登录用户可看到全局统计
- 修复后：普通用户/技术只看个人维度，全局指标仅管理员/客服可见
- 证据：`app/api/v1/base/base.py:183`

### 2.3 注入、日志与信息泄露

7) Skill-Know SQL 搜索默认关闭且按配置注册路由

- 修复前：`/skill-know/search/sql` 始终暴露（仅靠逻辑拒绝）
- 修复后：默认不注册 SQL 路由；即使启用也保留服务端校验
- 证据：
  - `app/api/v1/skill_know/__init__.py:20`
  - `app/api/v1/skill_know/search.py:7`
  - `app/services/skill_know/search_service.py:29`

8) 审计日志敏感字段脱敏

- 修复前：请求体/响应体可能含密码、验证码、密钥
- 修复后：统一敏感 key 递归脱敏为 `******`
- 证据：`app/core/middlewares.py:62`

9) 异常信息生产收敛

- 修复前：大量内部异常直接回给前端
- 修复后：根据 `DEBUG` 控制，生产返回通用错误
- 证据：`app/core/exceptions.py:22`

### 2.4 配置与部署安全

10) CORS 默认收紧

- 修复前：`*` + credentials
- 修复后：本地白名单 + 限制 methods/headers
- 证据：`app/settings/config.py:14`

11) OpenAPI/Docs 默认关闭

- 修复前：默认对外可访问
- 修复后：受 `OPENAPI_ENABLED` 控制，默认关闭
- 证据：`app/__init__.py:32`

12) compose 明文凭据改为环境变量必填

- 修复前：数据库/Redis/初始管理密码明文
- 修复后：通过 `${VAR:?required}` 强制注入
- 证据：`docker-compose.yml:15`

13) Nginx 增加安全头与代理转发头

- 修复前：无安全响应头
- 修复后：增加 CSP、XFO、nosniff、Referrer-Policy、Permissions-Policy
- 证据：`deploy/web.conf:4`

14) Docker 构建面收敛

- 修复前：`.dockerignore` 几乎无效
- 修复后：忽略 venv/git/cache/log/env 等噪音
- 证据：`.dockerignore:1`

15) 前端无效配置清理

- 修复前：系统设置页提交后端未接收的 `ai_kb_*` 字段
- 修复后：已移除无效字段，补齐 WebDAV 配置项可见性；Logo accept 与后端一致（去掉 svg）
- 证据：
  - `web/src/views/system/settings/index.vue:36`
  - `web/src/views/system/settings/index.vue:457`
  - `web/src/views/system/settings/index.vue:653`

---

## 3. 验证结果

### 3.1 自动化测试

- 后端测试：`python -m pytest`
- 结果：`17 passed`
- 说明：新增安全测试覆盖脱敏与 SQL 默认禁用
- 证据：`tests/test_security_controls.py:1`

### 3.2 前端构建与 lint

- `pnpm run build`：通过
- 定向 lint（本次修改文件）通过
- 全仓 lint：仍存在大量历史格式/规则问题（非本次变更引入）

---

## 4. 当前遗留风险（未完全闭环）

### 4.1 JWT 撤销机制仍缺失（中风险）

- 现状：虽已补 claims 校验，但尚无 `jti` 黑名单/token 版本撤销
- 风险：被盗 token 在有效期内仍可继续使用
- 建议：引入 Redis 黑名单或用户 token_version 机制

### 4.2 Docker 非 root 运行需环境联调确认（中风险）

- 现状：已切 `USER app`、Nginx 改 8080，compose 映射 `80:8080`
- 风险：不同宿主环境下 Nginx pid/目录权限可能仍有差异
- 建议：在目标环境做一次容器启动与健康检查联调

### 4.3 全仓前端 lint 存量较多（低风险，工程治理项）

- 现状：大量 Prettier 与规则历史欠账
- 风险：影响代码质量门禁，但不属于本次安全漏洞本身
- 建议：拆分为独立“风格治理”任务，分目录分批修复

---

## 5. 建议的最终收尾动作

1) 增加 JWT 撤销机制（高优先）
2) 在目标环境做 Docker 非 root 联调（高优先）
3) 增加 CI 安全扫描：`pip-audit` / `pnpm audit`（中优先）
4) 启动前端 lint 历史债清理（中优先）

---

## 6. 审计结论

本轮已完成主要高危项修复，关键攻击面（默认弱口令、SQL 搜索暴露、附件越权、明文敏感信息落库、生产配置过宽）已显著收敛。当前剩余问题以“体系增强与工程治理”为主，可进入收尾阶段。
