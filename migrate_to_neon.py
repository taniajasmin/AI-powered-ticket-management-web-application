import asyncio
import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from sqlalchemy.orm import make_transient

from app.models.models import Base, User, Customer, Ticket, Comment

load_dotenv()

async def migrate():
    print("Starting migration...")
    
    # 1. Setup SQLite (Source)
    sqlite_url = "sqlite+aiosqlite:///./ticket_system.db"
    source_engine = create_async_engine(sqlite_url, echo=False)
    SourceSession = async_sessionmaker(source_engine, expire_on_commit=False, autoflush=False)
    
    # 2. Setup Postgres (Target)
    neon_url = os.getenv("DATABASE_URL")
    if not neon_url:
        print("ERROR: DATABASE_URL not found in .env")
        return
        
    print(f"Connecting to Neon Postgres...")
    
    # Translate URL
    if neon_url.startswith("postgres://"):
        neon_url = neon_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif neon_url.startswith("postgresql://") and not neon_url.startswith("postgresql+asyncpg://"):
        neon_url = neon_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
    if "postgresql+asyncpg" in neon_url and "sslmode=" in neon_url:
        neon_url = neon_url.replace("sslmode=", "ssl=")

    target_engine = create_async_engine(neon_url, echo=False)
    TargetSession = async_sessionmaker(target_engine, expire_on_commit=False, autoflush=False)
    
    # 3. Create tables in Neon
    print("Creating tables in Neon...")
    async with target_engine.begin() as conn:
        # Drop all tables first just in case
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    # 4. Migrate Data
    async with SourceSession() as source_db, TargetSession() as target_db:
        
        # Migrate Users
        print("Migrating users...")
        result = await source_db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            make_transient(u)
            target_db.add(u)
        await target_db.flush()
        
        # Migrate Customers
        print("Migrating customers...")
        result = await source_db.execute(select(Customer))
        customers = result.scalars().all()
        for c in customers:
            make_transient(c)
            target_db.add(c)
        await target_db.flush()
        
        # Migrate Tickets
        print("Migrating tickets...")
        result = await source_db.execute(select(Ticket))
        tickets = result.scalars().all()
        for t in tickets:
            make_transient(t)
            target_db.add(t)
        await target_db.flush()
        
        # Migrate Comments
        print("Migrating comments...")
        result = await source_db.execute(select(Comment))
        comments = result.scalars().all()
        for c in comments:
            make_transient(c)
            target_db.add(c)
        await target_db.flush()

        # Fix Postgres auto-increment sequences
        print("Updating Primary Key auto-increment sequences...")
        tables = ['users', 'customers', 'tickets', 'comments']
        for table in tables:
            query = text(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id)+1 FROM {table}), 1), false);")
            await target_db.execute(query)
            
        await target_db.commit()
        
    print("Migration completely successful!")
    await source_engine.dispose()
    await target_engine.dispose()

if __name__ == "__main__":
    if not os.path.exists("./ticket_system.db"):
        print("Error: No local ticket_system.db found to migrate.")
    else:
        asyncio.run(migrate())
