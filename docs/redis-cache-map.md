# Redis Cache Map

本文档记录当前项目已落地的 Redis 缓存点，包含 key、TTL、读写位置与失效策略。

## 1) Public Config

- key: `config:public:v1`
- TTL: `300s`
- read: `app/controllers/system_setting.py:get_public_config`
- write: `app/controllers/system_setting.py:get_public_config`
- invalidate:
  - `app/controllers/system_setting.py:update`
  - `app/controllers/system_setting.py:upload_logo`

## 2) Workbench Stats

- key: `stats:workbench:global:v1`
- TTL: `60s`
- read/write: `app/api/v1/base/base.py:get_workbench_stats`
- invalidate: 无主动失效（短 TTL 自然过期）

## 3) User Menu Permission

- key: `perm:menu:user:{user_id}:v1`
- TTL: `600s`
- read/write: `app/api/v1/base/base.py:get_user_menu`
- invalidate:
  - `app/controllers/user.py:update_roles -> clear_permission_cache`
  - `app/api/v1/users/users.py:update_user/delete_user`
  - `app/controllers/role.py:update_roles -> clear_permission_cache_by_role`

## 4) User API Permission

- key: `perm:api:user:{user_id}:v1`
- TTL: `600s`
- read/write: `app/api/v1/base/base.py:get_user_api`
- invalidate:
  - `app/controllers/user.py:update_roles -> clear_permission_cache`
  - `app/api/v1/users/users.py:update_user/delete_user`
  - `app/controllers/role.py:update_roles -> clear_permission_cache_by_role`

## 5) Notice Inbox Top 10

- key: `notice:inbox10:user:{user_id}`
- TTL: `300s`
- read/write: `app/controllers/notice.py:inbox`（仅 `page=1,page_size=10`）
- invalidate:
  - `app/controllers/notice.py:create_notice`（所有收件人）
  - `app/controllers/notice.py:read_one`
  - `app/controllers/notice.py:read_all`

## 6) Notice Unread Count

- key: `notice:unread:user:{user_id}`
- TTL: `300s`
- read/write: `app/controllers/notice.py:unread_count`
- invalidate:
  - `app/controllers/notice.py:create_notice`（所有收件人）
  - `app/controllers/notice.py:read_one`
  - `app/controllers/notice.py:read_all`

## 7) Role Dictionary

- key: `dict:roles:v1`
- TTL: `600s`
- read/write: `app/api/v1/roles/roles.py:list_role`
  - 仅在 `page=1 && page_size>=9999 && role_name 为空` 走缓存
- invalidate:
  - `app/api/v1/roles/roles.py:create_role/update_role/delete_role`
  - `app/controllers/role.py:update_roles`

## 8) Dept Dictionary

- key: `dict:depts:v1`
- TTL: `600s`
- read/write: `app/api/v1/depts/depts.py:list_dept`
  - 仅在 `name 为空` 走缓存
- invalidate:
  - `app/controllers/dept.py:create_dept/update_dept/delete_dept`

## 9) User Basic Info

- key: `user:basic:{user_id}`
- TTL: `600s`
- read/write: `app/controllers/user.py:get_user_basic`
- used by: `app/api/v1/base/base.py:get_userinfo`
- invalidate:
  - `app/api/v1/users/users.py:update_user/delete_user`

---

## Key Naming Convention

- 推荐格式：`{domain}:{entity}:{scope}:{id}:v{version}`
- 本项目中已统一使用 `:v1` 后缀用于后续平滑升级。

## Failure Strategy

- 所有缓存读写均应包裹 `try/except`，Redis 异常时自动降级数据库。
- 优先保证业务可用性，再追求缓存命中率。
