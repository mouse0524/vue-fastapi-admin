from pydantic import BaseModel, Field


class CaptchaOut(BaseModel):
    captcha_id: str = Field(..., description="验证码ID")
    image_base64: str = Field(..., description="验证码图片base64")


class CaptchaVerifyIn(BaseModel):
    captcha_id: str = Field(..., description="验证码ID")
    captcha_code: str = Field(..., description="验证码")
