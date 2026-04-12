"""
Seed the database with initial data: admin user, sample customers, and tickets.

Run with: python -m app.seed
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session, init_db
from app.core.security import hash_password
from app.models.models import (
    User, Customer, Ticket, Comment,
    RoleEnum, TicketStatusEnum, TicketPriorityEnum, TicketCategoryEnum,
)
from app.services.ai_classifier import _keyword_classify


async def seed():
    await init_db()

    async with async_session() as session:
        # ── Users ──────────────────────────────────────
        users_data = [
            {
                "email": "admin@ticketapp.com",
                "username": "admin",
                "full_name": "System Admin",
                "role": RoleEnum.admin,
                "password": "admin123",
            },
            {
                "email": "john@example.com",
                "username": "john_doe",
                "full_name": "John Doe",
                "role": RoleEnum.customer,
                "password": "customer123",
            },
            {
                "email": "jane@example.com",
                "username": "jane_smith",
                "full_name": "Jane Smith",
                "role": RoleEnum.customer,
                "password": "customer123",
            },
        ]

        users: list[User] = []
        for u in users_data:
            user = User(
                email=u["email"],
                username=u["username"],
                full_name=u["full_name"],
                role=u["role"],
                hashed_password=hash_password(u["password"]),
            )
            session.add(user)
            users.append(user)

        await session.flush()

        # ── Customers ──────────────────────────────────
        customers_data = [
            {"name": "Acme Corp", "email": "support@acmecorp.com", "company": "Acme Corp", "phone": "+1-555-0100"},
            {"name": "Globex Inc", "email": "help@globex.com", "company": "Globex Inc", "phone": "+1-555-0200"},
            {"name": "Wayne Enterprises", "email": "it@wayne-ent.com", "company": "Wayne Enterprises", "phone": "+1-555-0300"},
        ]

        customers: list[Customer] = []
        for c in customers_data:
            customer = Customer(**c)
            session.add(customer)
            customers.append(customer)

        await session.flush()

        # ── Tickets with AI classification ─────────────
        tickets_data = [
            {
                "title": "Payment failed on checkout",
                "description": "I tried to pay for my subscription but the payment was declined. My card is valid and has sufficient funds. Invoice #INV-2024-001.",
                "created_by": users[1].id,
                "customer_id": customers[0].id,
                "status": TicketStatusEnum.open,
            },
            {
                "title": "Cannot login to my account",
                "description": "I've been trying to reset my password for the past hour but the reset email never arrives. I've checked my spam folder.",
                "created_by": users[2].id,
                "customer_id": customers[1].id,
                "status": TicketStatusEnum.in_progress,
                "assigned_to": users[0].id,
            },
            {
                "title": "Feature request: Dark mode",
                "description": "Would like to suggest adding a dark mode option to the dashboard. It would be great for users who work at night.",
                "created_by": users[1].id,
                "customer_id": customers[0].id,
                "status": TicketStatusEnum.open,
            },
            {
                "title": "Server timeout errors",
                "description": "Getting constant 504 timeout errors on the production server since the last update. This is urgent and blocking our entire team.",
                "created_by": users[2].id,
                "customer_id": customers[2].id,
                "status": TicketStatusEnum.in_progress,
                "assigned_to": users[0].id,
            },
            {
                "title": "Billing discrepancy on last invoice",
                "description": "My last invoice shows a charge of $150 but my plan is $99/month. I think there's been a billing error.",
                "created_by": users[1].id,
                "customer_id": customers[1].id,
                "status": TicketStatusEnum.resolved,
                "assigned_to": users[0].id,
            },
            {
                "title": "Security concern about data handling",
                "description": "I noticed that the application sends unencrypted data over HTTP in some endpoints. This is a potential security vulnerability.",
                "created_by": users[2].id,
                "customer_id": customers[2].id,
                "status": TicketStatusEnum.open,
            },
        ]

        for t in tickets_data:
            classification = _keyword_classify(t["title"], t["description"])
            ticket = Ticket(
                title=t["title"],
                description=t["description"],
                status=t.get("status", TicketStatusEnum.open),
                priority=TicketPriorityEnum(
                    classification.priority if classification.priority else "medium"
                ),
                category=TicketCategoryEnum(
                    classification.category if classification.category in [e.value for e in TicketCategoryEnum] else "general"
                ),
                ai_category=classification.category,
                ai_confidence=classification.confidence,
                ai_analysis=classification.analysis,
                created_by=t["created_by"],
                customer_id=t.get("customer_id"),
                assigned_to=t.get("assigned_to"),
            )
            session.add(ticket)
            await session.flush()

            # Add a comment to some tickets
            if t["status"] in (TicketStatusEnum.in_progress, TicketStatusEnum.resolved):
                comment = Comment(
                    ticket_id=ticket.id,
                    user_id=t.get("assigned_to", users[0].id),
                    content="Looking into this issue. Will update shortly." if t["status"] == TicketStatusEnum.in_progress else "Issue has been resolved. Please confirm.",
                    is_internal=False,
                )
                session.add(comment)

        await session.commit()
        print("Database seeded successfully!")
        print()
        print("Default accounts:")
        print("  Admin:    admin / admin123")
        print("  Customer: john_doe / customer123")
        print("  Customer: jane_smith / customer123")


if __name__ == "__main__":
    asyncio.run(seed())
