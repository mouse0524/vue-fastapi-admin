from tortoise import fields

from .base import BaseModel, TimestampMixin


class KbSpace(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=120, unique=True, description="知识空间名称", index=True)
    desc = fields.TextField(null=True, description="空间描述")
    is_public = fields.BooleanField(default=False, description="是否公开", index=True)
    status = fields.BooleanField(default=True, description="状态", index=True)
    owner_id = fields.BigIntField(description="空间负责人", index=True)

    class Meta:
        table = "kb_space"


class KbDocument(BaseModel, TimestampMixin):
    space_id = fields.BigIntField(description="所属空间", index=True)
    title = fields.CharField(max_length=255, description="文档标题", index=True)
    source_type = fields.CharField(max_length=20, default="upload", description="来源类型", index=True)
    source_url = fields.CharField(max_length=500, null=True, description="来源URL")
    file_name = fields.CharField(max_length=255, null=True, description="文件名")
    file_ext = fields.CharField(max_length=20, null=True, description="文件后缀")
    file_size = fields.BigIntField(default=0, description="文件大小")
    file_hash = fields.CharField(max_length=64, null=True, description="文件哈希", index=True)
    storage_path = fields.CharField(max_length=500, null=True, description="存储路径")
    parse_status = fields.CharField(max_length=20, default="pending", description="解析状态", index=True)
    parse_error = fields.TextField(null=True, description="解析错误")
    version = fields.IntField(default=1, description="版本")
    is_deleted = fields.BooleanField(default=False, description="是否删除", index=True)
    created_by = fields.BigIntField(description="创建人", index=True)

    class Meta:
        table = "kb_document"


class KbChunk(BaseModel, TimestampMixin):
    space_id = fields.BigIntField(description="所属空间", index=True)
    document_id = fields.BigIntField(description="文档ID", index=True)
    chunk_index = fields.IntField(default=0, description="分块序号")
    content = fields.TextField(description="分块内容")
    token_count = fields.IntField(default=0, description="token数量")
    metadata_json = fields.JSONField(null=True, description="扩展元数据")
    embedding_id = fields.CharField(max_length=128, null=True, description="向量ID")

    class Meta:
        table = "kb_chunk"


class KbSession(BaseModel, TimestampMixin):
    space_id = fields.BigIntField(description="空间ID", index=True)
    user_id = fields.BigIntField(description="用户ID", index=True)
    title = fields.CharField(max_length=200, null=True, description="会话标题")
    status = fields.CharField(max_length=20, default="active", description="状态", index=True)

    class Meta:
        table = "kb_session"


class KbMessage(BaseModel, TimestampMixin):
    session_id = fields.BigIntField(description="会话ID", index=True)
    role = fields.CharField(max_length=20, description="角色", index=True)
    content = fields.TextField(description="消息内容")
    model_name = fields.CharField(max_length=100, null=True, description="模型名称")
    prompt_tokens = fields.IntField(default=0, description="输入tokens")
    completion_tokens = fields.IntField(default=0, description="输出tokens")
    latency_ms = fields.IntField(default=0, description="耗时ms")
    trace_id = fields.CharField(max_length=64, null=True, description="链路追踪", index=True)

    class Meta:
        table = "kb_message"


class KbCitation(BaseModel, TimestampMixin):
    message_id = fields.BigIntField(description="回答消息ID", index=True)
    document_id = fields.BigIntField(description="文档ID", index=True)
    chunk_id = fields.BigIntField(description="分块ID", index=True)
    score = fields.FloatField(default=0.0, description="召回分值")
    snippet = fields.TextField(description="引用片段")

    class Meta:
        table = "kb_citation"


class KbFeedback(BaseModel, TimestampMixin):
    message_id = fields.BigIntField(description="回答消息ID", index=True)
    user_id = fields.BigIntField(description="反馈人", index=True)
    rating = fields.CharField(max_length=10, description="评价", index=True)
    comment = fields.TextField(null=True, description="反馈内容")
    status = fields.CharField(max_length=20, default="new", description="处理状态", index=True)

    class Meta:
        table = "kb_feedback"


class KbLlmCallLog(BaseModel, TimestampMixin):
    trace_id = fields.CharField(max_length=64, null=True, description="链路追踪", index=True)
    session_id = fields.BigIntField(null=True, description="会话ID", index=True)
    message_id = fields.BigIntField(null=True, description="消息ID", index=True)
    node_name = fields.CharField(max_length=32, default="answer", description="节点名称", index=True)
    provider = fields.CharField(max_length=32, null=True, description="模型提供商", index=True)
    model_code = fields.CharField(max_length=100, null=True, description="模型编码", index=True)
    prompt_tokens = fields.IntField(default=0, description="输入tokens")
    completion_tokens = fields.IntField(default=0, description="输出tokens")
    latency_ms = fields.IntField(default=0, description="耗时ms")
    request_json = fields.JSONField(null=True, description="请求参数")
    response_json = fields.JSONField(null=True, description="响应结果")
    error_code = fields.CharField(max_length=120, null=True, description="错误码", index=True)
    cost_estimate = fields.FloatField(default=0.0, description="成本估算")

    class Meta:
        table = "kb_llm_call_log"
