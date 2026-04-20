from pydantic import BaseModel, EmailStr, Field


class SendVerifyCodeIn(BaseModel):
    email: EmailStr = Field(..., description="邮箱")
    captcha_id: str = Field(..., description="验证码ID")
    captcha_code: str = Field(..., description="图形验证码")
