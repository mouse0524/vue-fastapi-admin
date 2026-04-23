from pydantic import BaseModel, Field, field_validator


class SystemSettingUpdateIn(BaseModel):
    site_title: str = Field(..., description="网站标题")
    site_logo: str | None = Field(default=None, description="网站Logo")
    allow_partner_register: bool = Field(default=True, description="是否开放代理商注册")
    ticket_attachment_extensions: list[str] = Field(default_factory=list, description="工单附件允许上传类型")
    ticket_project_phases: list[str] = Field(default_factory=list, description="工单项目阶段")
    ticket_categories: list[str] = Field(default_factory=list, description="工单分类")
    ticket_root_causes: list[str] = Field(default_factory=list, description="工单问题根因")
    ticket_description_templates: list[str] = Field(default_factory=list, description="工单问题描述模板")
    role_home_pages: list[dict] = Field(default_factory=list, description="角色默认首页配置")
    login_security_enabled: bool = Field(default=True, description="是否启用登录安全策略")
    login_account_ip_fail_limit: int = Field(default=5, description="账号+IP失败锁定阈值")
    login_account_ip_lock_minutes: int = Field(default=60, description="账号+IP锁定时长(分钟)")
    login_ip_fail_limit: int = Field(default=20, description="IP失败锁定阈值")
    login_ip_lock_minutes: int = Field(default=60, description="IP锁定时长(分钟)")
    login_fail_window_minutes: int = Field(default=60, description="登录失败统计窗口(分钟)")
    login_generic_error_enabled: bool = Field(default=True, description="是否启用统一登录错误提示")

    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str | None = None
    smtp_sender_name: str = "系统通知"
    smtp_use_tls: bool = False
    smtp_use_ssl: bool = True

    email_verify_subject: str = "代理商注册验证码"
    email_verify_is_html: bool = True
    email_verify_template: str = "您好，您的验证码是：{code}，{minutes}分钟内有效。"
    register_review_approve_subject: str = "注册审核结果通知"
    register_review_approve_is_html: bool = True
    register_review_approve_template: str = (
        "您好，{contact_name}，您的{register_type}注册申请已审核通过，现可使用邮箱登录系统。"
    )
    register_review_reject_subject: str = "注册审核结果通知"
    register_review_reject_is_html: bool = True
    register_review_reject_template: str = "您好，{contact_name}，您的{register_type}注册申请已驳回。驳回理由：{reason}"

    webdav_enabled: bool = False
    webdav_base_url: str | None = None
    webdav_username: str | None = None
    webdav_password: str | None = None
    webdav_share_default_expire_hours: int = 168
    webdav_signature_secret: str | None = None

    llm_provider: str = "openai"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "mock-rag-v1"
    llm_timeout_seconds: int = 20

    @field_validator("ticket_attachment_extensions")
    @classmethod
    def validate_attachment_extensions(cls, value: list[str]):
        items = []
        for item in value:
            normalized = str(item or "").strip().lower().lstrip(".")
            if normalized:
                items.append(normalized)
        if not items:
            raise ValueError("允许上传类型至少保留一项")
        return items

    @field_validator("ticket_root_causes", "ticket_description_templates")
    @classmethod
    def validate_required_ticket_items(cls, value: list[str], info):
        field_name = "问题根因" if info.field_name == "ticket_root_causes" else "问题描述模板"
        items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if not items:
            raise ValueError(f"{field_name}至少保留一项")
        return items

    @field_validator("role_home_pages")
    @classmethod
    def validate_role_home_pages(cls, value: list[dict]):
        cleaned = []
        seen_roles: set[str] = set()
        for item in value:
            if not isinstance(item, dict):
                continue
            role_name = str(item.get("role_name") or "").strip()
            path = str(item.get("path") or "").strip()
            if role_name and path:
                if role_name in seen_roles:
                    raise ValueError(f"角色默认首页存在重复配置：{role_name}")
                seen_roles.add(role_name)
                cleaned.append({"role_name": role_name, "path": path})
        return cleaned

    @field_validator(
        "login_account_ip_fail_limit",
        "login_account_ip_lock_minutes",
        "login_ip_fail_limit",
        "login_ip_lock_minutes",
        "login_fail_window_minutes",
    )
    @classmethod
    def validate_positive_security_numbers(cls, value: int, info):
        if value < 1:
            raise ValueError(f"{info.field_name} 必须大于等于 1")
        return value


class PublicSiteConfigOut(BaseModel):
    site_title: str
    site_logo: str | None = None
    allow_partner_register: bool
    ticket_attachment_extensions: list[str]
    ticket_project_phases: list[str]
    ticket_categories: list[str]
    ticket_description_templates: list[str]
    role_home_pages: list[dict]
    login_security_enabled: bool
    login_account_ip_fail_limit: int
    login_account_ip_lock_minutes: int
    login_ip_fail_limit: int
    login_ip_lock_minutes: int
    login_fail_window_minutes: int
    login_generic_error_enabled: bool


class WebDavTestIn(BaseModel):
    webdav_enabled: bool = True
    webdav_base_url: str | None = None
    webdav_username: str | None = None
    webdav_password: str | None = None
