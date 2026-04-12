from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None
    role: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


# ── User ──────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    full_name: str
    role: str = "customer"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Customer ──────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class CustomerOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    company: str | None
    notes: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Ticket ────────────────────────────────────────────

class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    priority: str = "medium"
    customer_id: int | None = None


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    assigned_to: int | None = None


class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    category: str | None
    ai_category: str | None
    ai_confidence: float | None
    ai_analysis: str | None
    customer_id: int | None
    created_by: int
    assigned_to: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketWithDetails(TicketOut):
    creator_name: str | None = None
    assignee_name: str | None = None
    customer_name: str | None = None
    comment_count: int = 0


# ── Comment ───────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str = Field(min_length=1)
    is_internal: bool = False


class CommentOut(BaseModel):
    id: int
    ticket_id: int
    user_id: int
    content: str
    is_internal: bool
    created_at: datetime
    author_name: str | None = None

    model_config = {"from_attributes": True}


# ── AI Classification ─────────────────────────────────

class ClassificationResult(BaseModel):
    category: str
    confidence: float
    priority: str | None = None
    analysis: str | None = None


# ── Dashboard / Stats ─────────────────────────────────

class DashboardStats(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    total_customers: int
    total_users: int
    avg_resolution_hours: float | None = None
