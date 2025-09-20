from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, Document
from app.auth import hash_password

async def create_user(db: AsyncSession, email: str, password: str):
    hashed = hash_password(password)
    user = User(email=email, hashed_password=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def create_document(db: AsyncSession, filename: str, user_id: int):
    doc = Document(filename=filename, user_id=user_id)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc
