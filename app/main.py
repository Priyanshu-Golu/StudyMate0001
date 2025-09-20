from fastapi import FastAPI
from app.database import engine, Base
from app.routes import auth, pdf
from app.RAG import rag

app = FastAPI()

app.include_router(auth.router)
app.include_router(pdf.router)
app.include_router(rag.router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
