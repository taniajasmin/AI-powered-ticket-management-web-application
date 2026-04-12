from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.models import (
    User, Ticket, Comment, Customer,
    TicketStatusEnum, TicketPriorityEnum, TicketCategoryEnum, RoleEnum,
)
from app.schemas.schemas import (
    TicketCreate, TicketUpdate, TicketOut, TicketWithDetails,
    CommentCreate, CommentOut,
)
from app.services.ai_classifier import classify_ticket

router = APIRouter(prefix="/tickets", tags=["Tickets"])


EAGER_LOAD_OPTIONS = [
    selectinload(Ticket.creator),
    selectinload(Ticket.assignee),
    selectinload(Ticket.customer),
    selectinload(Ticket.comments),
]


def _ticket_to_out(ticket: Ticket) -> TicketWithDetails:
    return TicketWithDetails(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value if ticket.status else None,
        priority=ticket.priority.value if ticket.priority else None,
        category=ticket.category.value if ticket.category else None,
        ai_category=ticket.ai_category,
        ai_confidence=ticket.ai_confidence,
        ai_analysis=ticket.ai_analysis,
        customer_id=ticket.customer_id,
        created_by=ticket.created_by,
        assigned_to=ticket.assigned_to,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        creator_name=ticket.creator.full_name if ticket.creator else None,
        assignee_name=ticket.assignee.full_name if ticket.assignee else None,
        customer_name=ticket.customer.name if ticket.customer else None,
        comment_count=len(ticket.comments) if ticket.comments else 0,
    )


async def _get_ticket_eager(db: AsyncSession, ticket_id: int) -> Ticket | None:
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id).options(*EAGER_LOAD_OPTIONS)
    )
    return result.scalar_one_or_none()


@router.post("", response_model=TicketWithDetails, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_in: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if ticket_in.customer_id:
        cust = await db.get(Customer, ticket_in.customer_id)
        if not cust:
            raise HTTPException(status_code=404, detail="Customer not found")

    try:
        priority = TicketPriorityEnum(ticket_in.priority)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid priority")

    ticket = Ticket(
        title=ticket_in.title,
        description=ticket_in.description,
        priority=priority,
        customer_id=ticket_in.customer_id,
        created_by=current_user.id,
    )
    db.add(ticket)
    await db.flush()

    # AI classification
    classification = await classify_ticket(ticket.title, ticket.description)
    if classification:
        ticket.ai_category = classification.category
        ticket.ai_confidence = classification.confidence
        ticket.ai_analysis = classification.analysis
        try:
            ticket.category = TicketCategoryEnum(classification.category)
        except ValueError:
            ticket.category = TicketCategoryEnum.general
        if classification.priority:
            try:
                ticket.priority = TicketPriorityEnum(classification.priority)
            except ValueError:
                pass

    await db.flush()

    # Re-fetch with eager loads
    ticket = await _get_ticket_eager(db, ticket.id)
    return _ticket_to_out(ticket)


@router.get("", response_model=list[TicketWithDetails])
async def list_tickets(
    status_filter: str | None = Query(None, alias="status"),
    priority_filter: str | None = Query(None, alias="priority"),
    category_filter: str | None = Query(None, alias="category"),
    assigned_to_filter: int | None = Query(None, alias="assigned_to"),
    customer_id_filter: int | None = Query(None, alias="customer_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Ticket).options(*EAGER_LOAD_OPTIONS)

    if current_user.role == RoleEnum.customer:
        query = query.where(Ticket.created_by == current_user.id)

    if status_filter:
        try:
            query = query.where(Ticket.status == TicketStatusEnum(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status filter")
    if priority_filter:
        try:
            query = query.where(Ticket.priority == TicketPriorityEnum(priority_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid priority filter")
    if category_filter:
        try:
            query = query.where(Ticket.category == TicketCategoryEnum(category_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category filter")
    if assigned_to_filter is not None:
        query = query.where(Ticket.assigned_to == assigned_to_filter)
    if customer_id_filter is not None:
        query = query.where(Ticket.customer_id == customer_id_filter)

    query = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    tickets = result.scalars().all()
    return [_ticket_to_out(t) for t in tickets]


@router.get("/stats")
async def ticket_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status_counts = {}
    for s in TicketStatusEnum:
        q = select(func.count(Ticket.id)).where(Ticket.status == s)
        if current_user.role == RoleEnum.customer:
            q = q.where(Ticket.created_by == current_user.id)
        count = await db.scalar(q)
        status_counts[s.value] = count or 0

    total_q = select(func.count(Ticket.id))
    if current_user.role == RoleEnum.customer:
        total_q = total_q.where(Ticket.created_by == current_user.id)
    total = await db.scalar(total_q) or 0

    return {"total": total, "by_status": status_counts}


@router.get("/{ticket_id}", response_model=TicketWithDetails)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await _get_ticket_eager(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if current_user.role == RoleEnum.customer and ticket.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this ticket")

    return _ticket_to_out(ticket)


@router.patch("/{ticket_id}", response_model=TicketWithDetails)
async def update_ticket(
    ticket_id: int,
    ticket_in: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    ticket = await _get_ticket_eager(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    update_data = ticket_in.model_dump(exclude_unset=True)
    if "status" in update_data:
        try:
            ticket.status = TicketStatusEnum(update_data["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if "priority" in update_data:
        try:
            ticket.priority = TicketPriorityEnum(update_data["priority"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid priority")
    if "category" in update_data:
        try:
            ticket.category = TicketCategoryEnum(update_data["category"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")
    if "title" in update_data:
        ticket.title = update_data["title"]
    if "description" in update_data:
        ticket.description = update_data["description"]
    if "assigned_to" in update_data:
        if update_data["assigned_to"] is not None:
            assignee = await db.get(User, update_data["assigned_to"])
            if not assignee:
                raise HTTPException(status_code=404, detail="Assignee user not found")
        ticket.assigned_to = update_data["assigned_to"]

    await db.flush()
    # Re-fetch to get fresh relationships
    ticket = await _get_ticket_eager(db, ticket_id)
    return _ticket_to_out(ticket)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await db.delete(ticket)


# ── Comments ──────────────────────────────────────────

@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def add_comment(
    ticket_id: int,
    comment_in: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if comment_in.is_internal and current_user.role == RoleEnum.customer:
        raise HTTPException(status_code=403, detail="Customers cannot add internal comments")

    comment = Comment(
        ticket_id=ticket_id,
        user_id=current_user.id,
        content=comment_in.content,
        is_internal=comment_in.is_internal,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    return CommentOut(
        id=comment.id,
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        content=comment.content,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
        author_name=current_user.full_name,
    )


@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
async def list_comments(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    result = await db.execute(
        select(Comment)
        .where(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at.asc())
    )
    comments = result.scalars().all()

    out = []
    for c in comments:
        user = await db.get(User, c.user_id)
        if c.is_internal and current_user.role == RoleEnum.customer:
            continue
        out.append(CommentOut(
            id=c.id,
            ticket_id=c.ticket_id,
            user_id=c.user_id,
            content=c.content,
            is_internal=c.is_internal,
            created_at=c.created_at,
            author_name=user.full_name if user else "Unknown",
        ))
    return out
