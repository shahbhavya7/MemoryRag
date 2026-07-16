from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ProjectBase(BaseModel):
    name: str
    description: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChatBase(BaseModel):
    title: str


class ChatCreate(ChatBase):
    pass


class ChatUpdate(ChatBase):
    pass


class ChatOut(ChatBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    created_at: datetime


class DocumentUploadOut(BaseModel):
    source_filename: str
    chunks_created: int


class DocumentSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class DocumentSearchResult(BaseModel):
    text: str
    score: float
    metadata: dict


class DocumentSearchResponse(BaseModel):
    results: list[DocumentSearchResult]


class ChatRequest(BaseModel):
    project_id: int
    message: str
    top_k: int = 4


class ChatSource(BaseModel):
    text: str
    score: float
    source_filename: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
