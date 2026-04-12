from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.security import hash_password
from app.models.models import (
    User, Customer, Ticket, Comment,
    RoleEnum, TicketStatusEnum,
)
from app.schemas.schemas import (
    UserOut, UserUpdate, CustomerOut, CustomerCreate, CustomerUpdate,
    DashboardStats,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Dashboard ─────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    total_tickets = await db.scalar(select(func.count(Ticket.id))) or 0
    open_tickets = await db.scalar(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatusEnum.open)
    ) or 0
    in_progress = await db.scalar(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatusEnum.in_progress)
    ) or 0
    resolved = await db.scalar(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatusEnum.resolved)
    ) or 0
    closed = await db.scalar(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatusEnum.closed)
    ) or 0
    total_customers = await db.scalar(select(func.count(Customer.id))) or 0
    total_users = await db.scalar(select(func.count(User.id))) or 0

    return DashboardStats(
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress,
        resolved_tickets=resolved,
        closed_tickets=closed,
        total_customers=total_customers,
        total_users=total_users,
    )


# ── User Management ───────────────────────────────────

@router.get("/users", response_model=list[UserOut])
async def list_users(
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    query = select(User)
    if role:
        try:
            query = query.where(User.role == RoleEnum(role))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid role filter")
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_in.model_dump(exclude_unset=True)
    if "role" in update_data:
        try:
            user.role = RoleEnum(update_data["role"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid role")
    if "email" in update_data:
        user.email = update_data["email"]
    if "full_name" in update_data:
        user.full_name = update_data["full_name"]
    if "is_active" in update_data:
        user.is_active = update_data["is_active"]

    await db.flush()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.flush()


# ── Customer Management ───────────────────────────────

@router.post("/customers", response_model=CustomerOut, status_code=201)
async def create_customer(
    cust_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    existing = await db.execute(
        select(Customer).where(Customer.email == cust_in.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Customer email already exists")

    customer = Customer(**cust_in.model_dump())
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.get("/customers", response_model=list[CustomerOut])
async def list_customers(
    is_active: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    query = select(Customer)
    if is_active is not None:
        query = query.where(Customer.is_active == is_active)
    query = query.order_by(Customer.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/customers/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: int,
    cust_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = cust_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    await db.flush()
    await db.refresh(customer)
    return customer


@router.delete("/customers/{customer_id}", status_code=204)
async def deactivate_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.is_active = False
    await db.flush()
