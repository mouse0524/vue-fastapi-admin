from pydantic import BaseModel, Field


class SystemSettingUpdateIn(BaseModel):
    site_title: str = Field(..., description="网站标题")
    site_logo: str | None = Field(default=None, description="网站Logo")
    allow_partner_register: bool = Field(default=True, description="是否开放代理商注册")
    ticket_categories: list[str] = Field(default_factory=list, description="工单分类")
    ticket_root_causes: list[str] = Field(default_factory=list, description="工单问题根因")

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


class PublicSiteConfigOut(BaseModel):
    site_title: str
    site_logo: str | None = None
    allow_partner_register: bool
    ticket_categories: list[str]


class WebDavTestIn(BaseModel):
    webdav_enabled: bool = True
    webdav_base_url: str | None = None
    webdav_username: str | None = None
    webdav_password: str | None = None
