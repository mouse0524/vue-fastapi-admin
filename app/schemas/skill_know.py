from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    SkillKnowDocumentStatus,
    SkillKnowMessageRole,
    SkillKnowPromptCategory,
    SkillKnowSkillCategory,
    SkillKnowSkillType,
)


class SkillKnowFolderIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    parent_id: int | None = None
    sort_order: int = 0


class SkillKnowFolderUpdate(BaseModel):
    folder_id: int
    name: str | None = None
    description: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None


class SkillKnowSupportSolutionLevel(BaseModel):
    level: int = Field(..., ge=1, le=3)
    title: str
    steps: list[str] = Field(default_factory=list)


class SkillKnowSupportProfile(BaseModel):
    product_type: str | None = None
    product_module: str | None = None
    issue_category: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    affected_versions: list[str] = Field(default_factory=list)
    severity: str | None = None
    solution_levels: list[SkillKnowSupportSolutionLevel] = Field(default_factory=list)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    match_policy: dict[str, Any] = Field(default_factory=dict)


class SkillKnowSkillIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    category: SkillKnowSkillCategory = SkillKnowSkillCategory.PROMPT
    abstract: str | None = None
    overview: str | None = None
    content: str = Field(..., min_length=1)
    trigger_keywords: list[str] = Field(default_factory=list)
    trigger_intents: list[str] = Field(default_factory=list)
    always_apply: bool = False
    folder_id: int | None = None
    priority: int = 100
    config: dict[str, Any] = Field(default_factory=dict)
    support: SkillKnowSupportProfile | None = None


class SkillKnowSkillUpdate(BaseModel):
    skill_id: int
    name: str | None = None
    description: str | None = None
    category: SkillKnowSkillCategory | None = None
    abstract: str | None = None
    overview: str | None = None
    content: str | None = None
    trigger_keywords: list[str] | None = None
    trigger_intents: list[str] | None = None
    always_apply: bool | None = None
    folder_id: int | None = None
    priority: int | None = None
    is_active: bool | None = None
    config: dict[str, Any] | None = None
    support: SkillKnowSupportProfile | None = None


class SkillKnowMoveIn(BaseModel):
    target_id: int
    folder_id: int | None = None


class SkillKnowSearchIn(BaseModel):
    query: str = Field(..., min_length=1)
    category: SkillKnowSkillCategory | None = None
    type: SkillKnowSkillType | None = None
    limit: int = Field(default=20, ge=1, le=100)


class SkillKnowSupportMatchIn(BaseModel):
    query: str = Field(..., min_length=1)
    product_type: str | None = None
    product_module: str | None = None
    issue_category: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class SkillKnowSupportEvaluateSkillIn(BaseModel):
    skill_id: int


class SkillKnowDocumentUpdate(BaseModel):
    document_id: int
    title: str | None = None
    description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    folder_id: int | None = None


class SkillKnowConvertIn(BaseModel):
    document_id: int
    use_llm: bool = True
    auto_activate: bool = True
    folder_id: int | None = None


class SkillKnowBatchConvertIn(BaseModel):
    document_ids: list[int]
    use_llm: bool = True
    folder_id: int | None = None


class SkillKnowPromptUpdate(BaseModel):
    content: str | None = None
    is_active: bool | None = None


class SkillKnowQuickSetupIn(BaseModel):
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_chat_model: str = "gpt-4o-mini"
    llm_embedding_model: str = "text-embedding-3-small"


class SkillKnowTestConnectionIn(BaseModel):
    llm_api_key: str = Field(..., min_length=1)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_chat_model: str = "gpt-4o-mini"
    llm_embedding_model: str = "text-embedding-3-small"


class SkillKnowChatIn(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: int | None = None
    use_tools: bool = True


class SkillKnowSqlIn(BaseModel):
    query: str = Field(..., min_length=1)


class SkillKnowFolderOut(BaseModel):
    id: int
    uuid: str
    name: str
    description: str | None
    parent_id: int | None
    sort_order: int
    is_system: bool
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    children: list["SkillKnowFolderOut"] = Field(default_factory=list)


class SkillKnowSkillOut(BaseModel):
    id: int
    uuid: str
    uri: str | None
    name: str
    description: str
    type: SkillKnowSkillType
    category: SkillKnowSkillCategory
    abstract: str | None
    overview: str | None
    content: str
    trigger_keywords: list[str]
    trigger_intents: list[str]
    always_apply: bool
    version: str
    author: str | None
    is_active: bool
    source_document_id: int | None
    folder_id: int | None
    priority: int
    config: dict[str, Any]
    is_editable: bool
    is_deletable: bool
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None


class SkillKnowDocumentOut(BaseModel):
    id: int
    uuid: str
    uri: str | None
    title: str
    description: str | None
    filename: str
    file_path: str
    file_size: int
    file_type: str
    abstract: str | None
    overview: str | None
    content: str | None
    content_hash: str | None
    status: SkillKnowDocumentStatus
    error_message: str | None
    category: str | None
    tags: list[str]
    folder_id: int | None
    skill_id: int | None
    is_converted: bool
    converted_at: datetime | str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None


class SkillKnowPromptOut(BaseModel):
    id: int
    key: str
    category: SkillKnowPromptCategory
    name: str
    description: str | None
    content: str
    variables: list[str]
    is_active: bool
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None


class SkillKnowMessageOut(BaseModel):
    id: int
    uuid: str
    conversation_id: int
    role: SkillKnowMessageRole
    content: str
    tool_calls: list | None
    timeline: list
    latency_ms: int | None
    created_at: datetime | str | None = None


class SkillKnowConversationOut(BaseModel):
    id: int
    uuid: str
    title: str | None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    messages: list[SkillKnowMessageOut] = Field(default_factory=list)


SkillKnowFolderOut.model_rebuild()
