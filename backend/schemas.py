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
    memory_type: str | None = None
    source_ref: str | None = None


class ChatResponse(BaseModel):
    answer: str
    memory_types: list[str]  # which memory type(s) the router picked (the Phase 6 proof point)
    sources: list[ChatSource]
    memory_update: dict | None = None
    message_id: int | None = None  # id to fetch this exchange's context trace (Phase 7)


class TokenBreakdown(BaseModel):
    system: int
    history: int
    context: int
    total: int


class RetrievedItemTrace(BaseModel):
    memory_type: str | None = None
    score: float
    tokens: int
    kept: bool
    preview: str


class ContextTraceOut(BaseModel):
    message_id: int
    token_budget: int
    tokens: TokenBreakdown
    history_messages_available: int
    history_messages_kept: int
    kept_count: int
    dropped_count: int
    retrieved: list[RetrievedItemTrace]


class MemoryCreate(BaseModel):
    memory_type: str  # one of: document, code, decision, workflow, conversation
    content: str
    source_ref: str | None = None
    project_id: int  # memories are scoped to a project


class MemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    memory_type: str
    content: str
    source_ref: str | None = None
    project_id: int | None = None
    created_at: datetime


class MemorySearchRequest(BaseModel):
    memory_type: str
    query: str
    top_k: int = 5
    project_id: int | None = None


class MemorySearchResult(BaseModel):
    memory_id: int | None = None
    memory_type: str
    content: str
    source_ref: str | None = None
    score: float


class MemorySearchResponse(BaseModel):
    results: list[MemorySearchResult]


class GitIngestRequest(BaseModel):
    repo_path: str  # path to a local git repo on the server's filesystem
    max_commits: int | None = None  # only ingest the N most recent commits
    branch: str | None = None  # ref to walk (default: current branch)


class GitCommitIngested(BaseModel):
    sha: str
    short_sha: str
    subject: str
    files_changed: int
    code_chunks: int
    stored_as_decision: bool


class GitIngestResponse(BaseModel):
    repo_path: str
    branch: str | None = None
    commits_processed: int
    code_chunks_stored: int
    decision_entries_stored: int
    commits: list[GitCommitIngested]


class EvalQuestionResult(BaseModel):
    question: str
    expected: str
    predicted: list[str]
    correct: bool


class EvalPerType(BaseModel):
    memory_type: str
    total: int
    correct: int
    accuracy: float


class EvalResponse(BaseModel):
    version: str
    total: int
    correct: int
    accuracy: float
    per_type: list[EvalPerType]
    results: list[EvalQuestionResult]
