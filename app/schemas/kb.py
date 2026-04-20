from pydantic import BaseModel, Field


class KbSpaceCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, description="知识空间名称")
    desc: str | None = Field(default=None, description="空间描述")
    is_public: bool = Field(default=False, description="是否公开")
    status: bool = Field(default=True, description="状态")


class KbSpaceUpdateIn(BaseModel):
    id: int = Field(..., description="空间ID")
    name: str | None = Field(default=None, min_length=1, max_length=120, description="知识空间名称")
    desc: str | None = Field(default=None, description="空间描述")
    is_public: bool | None = Field(default=None, description="是否公开")
    status: bool | None = Field(default=None, description="状态")


class KbDocumentCreateIn(BaseModel):
    space_id: int = Field(..., description="空间ID")
    title: str = Field(..., min_length=1, max_length=255, description="文档标题")
    source_type: str = Field(default="manual", description="来源类型")
    source_url: str | None = Field(default=None, description="来源URL")
    content: str = Field(..., min_length=1, description="文档正文")


class KbSessionCreateIn(BaseModel):
    space_id: int = Field(..., description="空间ID")
    title: str | None = Field(default=None, description="会话标题")


class KbAskIn(BaseModel):
    space_id: int = Field(..., description="空间ID")
    question: str = Field(..., min_length=1, description="提问内容")
    session_id: int | None = Field(default=None, description="会话ID")


class KbFeedbackCreateIn(BaseModel):
    message_id: int = Field(..., description="回答消息ID")
    rating: str = Field(..., description="评价(up/down)")
    comment: str | None = Field(default=None, description="反馈内容")


class KbDocumentDeleteIn(BaseModel):
    id: int = Field(..., description="文档ID")
