from pydantic import BaseModel, Field


class WebDavListIn(BaseModel):
    path: str = Field(default="/", description="目录路径")


class WebDavMkdirIn(BaseModel):
    path: str = Field(default="/", description="父目录路径")
    name: str = Field(..., min_length=1, max_length=120, description="目录名")


class WebDavDeleteIn(BaseModel):
    path: str = Field(..., min_length=1, description="待删除路径")


class WebDavShareCreateIn(BaseModel):
    file_path: str = Field(..., min_length=1, description="文件路径")
    file_name: str = Field(..., min_length=1, description="文件名")
    expire_hours: int | None = Field(default=None, description="分享有效时长(小时)")


class WebDavShareDeleteIn(BaseModel):
    id: int = Field(..., description="分享记录ID")
