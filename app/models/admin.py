from tortoise import fields

from app.schemas.menus import MenuType

from .base import BaseModel, TimestampMixin
from .enums import MethodType, PartnerRegisterStatus, RegisterType, TicketActionType, TicketStatus


class User(BaseModel, TimestampMixin):
    username = fields.CharField(max_length=20, unique=True, description="用户名称", index=True)
    alias = fields.CharField(max_length=30, null=True, description="用户姓名", index=True)
    company_name = fields.CharField(max_length=120, null=True, description="公司名称", index=True)
    hardware_id = fields.CharField(max_length=80, null=True, unique=True, description="产品硬件ID", index=True)
    email = fields.CharField(max_length=255, unique=True, description="邮箱", index=True)
    phone = fields.CharField(max_length=20, null=True, unique=True, description="电话", index=True)
    password = fields.CharField(max_length=128, null=True, description="密码")
    is_active = fields.BooleanField(default=True, description="是否激活", index=True)
    is_superuser = fields.BooleanField(default=False, description="是否为超级管理员", index=True)
    last_login = fields.DatetimeField(null=True, description="最后登录时间", index=True)
    roles = fields.ManyToManyField("models.Role", related_name="user_roles")
    dept_id = fields.IntField(null=True, description="部门ID", index=True)

    class Meta:
        table = "user"


class Role(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, unique=True, description="角色名称", index=True)
    desc = fields.CharField(max_length=500, null=True, description="角色描述")
    menus = fields.ManyToManyField("models.Menu", related_name="role_menus")
    apis = fields.ManyToManyField("models.Api", related_name="role_apis")

    class Meta:
        table = "role"


class Api(BaseModel, TimestampMixin):
    path = fields.CharField(max_length=100, description="API路径", index=True)
    method = fields.CharEnumField(MethodType, description="请求方法", index=True)
    summary = fields.CharField(max_length=500, description="请求简介", index=True)
    tags = fields.CharField(max_length=100, description="API标签", index=True)

    class Meta:
        table = "api"


class Menu(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, description="菜单名称", index=True)
    remark = fields.JSONField(null=True, description="保留字段")
    menu_type = fields.CharEnumField(MenuType, null=True, description="菜单类型")
    icon = fields.CharField(max_length=100, null=True, description="菜单图标")
    path = fields.CharField(max_length=100, description="菜单路径", index=True)
    order = fields.IntField(default=0, description="排序", index=True)
    parent_id = fields.IntField(default=0, description="父菜单ID", index=True)
    is_hidden = fields.BooleanField(default=False, description="是否隐藏")
    component = fields.CharField(max_length=100, description="组件")
    keepalive = fields.BooleanField(default=True, description="存活")
    redirect = fields.CharField(max_length=100, null=True, description="重定向")

    class Meta:
        table = "menu"


class Dept(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, unique=True, description="部门名称", index=True)
    desc = fields.CharField(max_length=500, null=True, description="备注")
    is_deleted = fields.BooleanField(default=False, description="软删除标记", index=True)
    order = fields.IntField(default=0, description="排序", index=True)
    parent_id = fields.IntField(default=0, max_length=10, description="父部门ID", index=True)

    class Meta:
        table = "dept"


class DeptClosure(BaseModel, TimestampMixin):
    ancestor = fields.IntField(description="父代", index=True)
    descendant = fields.IntField(description="子代", index=True)
    level = fields.IntField(default=0, description="深度", index=True)


class AuditLog(BaseModel, TimestampMixin):
    user_id = fields.IntField(description="用户ID", index=True)
    username = fields.CharField(max_length=64, default="", description="用户名称", index=True)
    module = fields.CharField(max_length=64, default="", description="功能模块", index=True)
    summary = fields.CharField(max_length=128, default="", description="请求描述", index=True)
    method = fields.CharField(max_length=10, default="", description="请求方法", index=True)
    path = fields.CharField(max_length=255, default="", description="请求路径", index=True)
    status = fields.IntField(default=-1, description="状态码", index=True)
    response_time = fields.IntField(default=0, description="响应时间(单位ms)", index=True)
    request_args = fields.JSONField(null=True, description="请求参数")
    response_body = fields.JSONField(null=True, description="返回数据")


class Ticket(BaseModel, TimestampMixin):
    ticket_no = fields.CharField(max_length=40, unique=True, description="工单编号", index=True)
    company_name = fields.CharField(max_length=120, description="公司名称")
    contact_name = fields.CharField(max_length=60, description="联系人")
    email = fields.CharField(max_length=255, description="邮箱", index=True)
    phone = fields.CharField(max_length=20, description="手机号", index=True)
    category = fields.CharField(max_length=60, description="问题分类", index=True)
    title = fields.CharField(max_length=200, description="问题标题", index=True)
    description = fields.TextField(description="问题描述")
    status = fields.CharEnumField(TicketStatus, default=TicketStatus.PENDING_REVIEW, index=True)
    submitter_id = fields.BigIntField(description="提交人ID", index=True)
    reviewer_id = fields.BigIntField(null=True, description="客服审核人ID", index=True)
    tech_id = fields.BigIntField(null=True, description="技术处理人ID", index=True)
    reject_reason = fields.TextField(null=True, description="驳回原因")
    finished_at = fields.DatetimeField(null=True, description="完成时间", index=True)

    class Meta:
        table = "ticket"


class TicketAttachment(BaseModel, TimestampMixin):
    ticket_id = fields.BigIntField(null=True, description="工单ID", index=True)
    origin_name = fields.CharField(max_length=255, description="原始文件名")
    file_path = fields.CharField(max_length=500, description="文件相对路径")
    file_size = fields.BigIntField(default=0, description="文件大小")
    mime_type = fields.CharField(max_length=100, default="application/octet-stream", description="MIME类型")
    uploader_id = fields.BigIntField(description="上传人ID", index=True)

    class Meta:
        table = "ticket_attachment"


class TicketActionLog(BaseModel, TimestampMixin):
    ticket_id = fields.BigIntField(description="工单ID", index=True)
    action = fields.CharEnumField(TicketActionType, description="动作类型", index=True)
    from_status = fields.CharEnumField(TicketStatus, null=True, description="变更前状态", index=True)
    to_status = fields.CharEnumField(TicketStatus, description="变更后状态", index=True)
    operator_id = fields.BigIntField(description="操作人ID", index=True)
    comment = fields.TextField(null=True, description="备注")

    class Meta:
        table = "ticket_action_log"


class PartnerRegistration(BaseModel, TimestampMixin):
    register_type = fields.CharEnumField(RegisterType, default=RegisterType.CHANNEL, description="注册类型", index=True)
    company_name = fields.CharField(max_length=120, description="公司名称")
    contact_name = fields.CharField(max_length=60, description="联系人")
    email = fields.CharField(max_length=255, description="邮箱", index=True)
    phone = fields.CharField(max_length=20, description="手机号", index=True)
    username = fields.CharField(max_length=20, description="用户名", index=True)
    hardware_id = fields.CharField(max_length=80, null=True, description="产品硬件ID", index=True)
    password_hash = fields.CharField(max_length=128, description="密码哈希")
    status = fields.CharEnumField(PartnerRegisterStatus, default=PartnerRegisterStatus.PENDING, index=True)
    reviewer_id = fields.BigIntField(null=True, description="审核人ID", index=True)
    review_comment = fields.CharField(max_length=500, null=True, description="审核备注")
    reviewed_at = fields.DatetimeField(null=True, description="审核时间", index=True)

    class Meta:
        table = "partner_registration"


class SystemSetting(BaseModel, TimestampMixin):
    site_title = fields.CharField(max_length=120, default="Vue FastAPI Admin", description="网站标题")
    site_logo = fields.CharField(max_length=500, null=True, description="网站Logo")
    allow_partner_register = fields.BooleanField(default=True, description="是否开放代理商注册")
    ticket_categories = fields.JSONField(default=["登录问题", "权限问题", "系统异常", "其他"], description="工单分类")

    smtp_host = fields.CharField(max_length=120, null=True, description="SMTP主机")
    smtp_port = fields.IntField(default=465, description="SMTP端口")
    smtp_username = fields.CharField(max_length=120, null=True, description="SMTP用户名")
    smtp_password = fields.CharField(max_length=200, null=True, description="SMTP密码")
    smtp_sender = fields.CharField(max_length=120, null=True, description="发件邮箱")
    smtp_sender_name = fields.CharField(max_length=120, default="系统通知", description="发件人名称")
    smtp_use_tls = fields.BooleanField(default=False, description="是否使用TLS")
    smtp_use_ssl = fields.BooleanField(default=True, description="是否使用SSL")

    email_verify_subject = fields.CharField(max_length=200, default="代理商注册验证码", description="验证邮件主题")
    email_verify_is_html = fields.BooleanField(default=True, description="验证码邮件是否HTML")
    email_verify_template = fields.TextField(
        default="您好，您的验证码是：{code}，{minutes}分钟内有效。",
        description="验证邮件模板",
    )
    register_review_approve_subject = fields.CharField(
        max_length=200,
        default="注册审核结果通知",
        description="注册审核通过邮件主题",
    )
    register_review_approve_is_html = fields.BooleanField(default=True, description="注册审核通过模板是否HTML")
    register_review_approve_template = fields.TextField(
        default="您好，{contact_name}，您的{register_type}注册申请已审核通过，现可使用邮箱登录系统。",
        description="注册审核通过邮件模板",
    )
    register_review_reject_subject = fields.CharField(
        max_length=200,
        default="注册审核结果通知",
        description="注册审核驳回邮件主题",
    )
    register_review_reject_is_html = fields.BooleanField(default=True, description="注册审核驳回模板是否HTML")
    register_review_reject_template = fields.TextField(
        default="您好，{contact_name}，您的{register_type}注册申请已驳回。驳回理由：{reason}",
        description="注册审核驳回邮件模板",
    )

    webdav_enabled = fields.BooleanField(default=False, description="是否启用WebDAV", index=True)
    webdav_base_url = fields.CharField(max_length=500, null=True, description="WebDAV基础地址")
    webdav_username = fields.CharField(max_length=120, null=True, description="WebDAV用户名")
    webdav_password = fields.CharField(max_length=255, null=True, description="WebDAV密码")
    webdav_share_default_expire_hours = fields.IntField(default=168, description="WebDAV默认分享有效时长(小时)")
    webdav_signature_secret = fields.CharField(max_length=255, null=True, description="WebDAV签名密钥")

    class Meta:
        table = "system_setting"


class WebDavShareLink(BaseModel, TimestampMixin):
    code = fields.CharField(max_length=32, unique=True, description="分享码", index=True)
    file_path = fields.CharField(max_length=1000, description="文件路径")
    file_name = fields.CharField(max_length=255, description="文件名")
    expire_time = fields.DatetimeField(description="过期时间", index=True)
    is_active = fields.BooleanField(default=True, description="是否生效", index=True)
    created_by = fields.BigIntField(description="创建人ID", index=True)

    class Meta:
        table = "webdav_share_link"
