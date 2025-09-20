from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app import models, schemas, config
import httpx
import uuid

router = APIRouter(prefix="/documents", tags=["documents"])

async def get_db():
    async with async_session() as session:
        yield session

async def upload_to_supabase(file: UploadFile):
    filename = f"{uuid.uuid4()}_{file.filename}"
    url = f"{config.settings.SUPABASE_URL}/storage/v1/object/{config.settings.SUPABASE_BUCKET}/{filename}"
    headers = {"apikey": config.settings.SUPABASE_KEY, "Authorization": f"Bearer {config.settings.SUPABASE_KEY}"}
    content = await file.read()
    async with httpx.AsyncClient() as client:
        res = await client.put(url, headers=headers, content=content)
    if res.status_code not in [200, 201]:
        raise HTTPException(status_code=500, detail="Supabase upload failed")
    return filename

@router.post("/", response_model=schemas.DocumentOut)
async def upload_pdf(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    storage_path = await upload_to_supabase(file)
    doc = models.Document(filename=file.filename, storage_path=storage_path)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc
