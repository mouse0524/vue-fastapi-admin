from pydantic import BaseModel, Field


class AIKbChatIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="用户问题")
    top_k: int = Field(default=5, ge=1, le=20, description="检索片段数量")


class AIKbFeedbackIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="问题")
    answer: str = Field(..., min_length=1, max_length=20000, description="答案")
    score: int = Field(..., ge=1, le=5, description="评分(1-5)")
    comment: str = Field(default="", max_length=2000, description="反馈说明")


class AIKbConfigIn(BaseModel):
    ai_kb_enabled: bool = True
    ai_kb_top_k: int = Field(default=5, ge=1, le=20)
    ai_kb_chunk_size: int = Field(default=800, ge=100, le=8000)
    ai_kb_chunk_overlap: int = Field(default=120, ge=1, le=2000)
    ai_kb_feedback_window: int = Field(default=20, ge=1, le=200)
    ai_kb_auto_reindex_threshold: int = Field(default=5, ge=1, le=100)
