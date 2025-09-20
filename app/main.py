from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app import models, schemas, auth, config

DATABASE_URL = config.settings.DATABASE_URL
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(title="Phase 1: User Management")

# Startup: create tables
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# -----------------------------
# Register
# -----------------------------
@app.post("/register", response_model=schemas.UserOut)
async def register(user: schemas.UserCreate):
    async with async_session() as session:
        stmt = select(models.User).where(models.User.email == user.email)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already exists")
        hashed = auth.hash_password(user.password)
        db_user = models.User(email=user.email, hashed_password=hashed)
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        return db_user

# -----------------------------
# Login
# -----------------------------
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    async with async_session() as session:
        stmt = select(models.User).where(models.User.email == form_data.username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user or not auth.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        token = auth.create_access_token({"sub": user.email})
        return {"access_token": token, "token_type": "bearer"}
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.config import settings
from app import models, schemas, crud, auth

app = FastAPI(title="HOGN23 Phase 1 Backend")

# Async Engine
engine = create_async_engine(settings.DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Startup: create tables
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# Dependency
async def get_db():
    async with async_session() as session:
        yield session

# Routes
@app.post("/register", response_model=schemas.UserRead)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await crud.create_user(db, user.email, user.password)
    return new_user

@app.post("/login")
async def login(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user_by_email(db, user.email)
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.create_access_token({"sub": db_user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/documents", response_model=schemas.DocumentRead)
async def upload_doc(doc: schemas.DocumentCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_document(db, doc.filename, doc.user_id)
