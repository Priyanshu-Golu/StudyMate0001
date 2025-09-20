from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_milvus import Milvus
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredEmailLoader,
    WebBaseLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tempfile
import os
import bs4
from typing import List

# This file seems to contain multiple disconnected snippets.
# I've reorganized it into functional components.

# --- Vector Store Setup ---
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import os
import shutil
from . import services

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain


router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)

# Directory to store uploaded files temporarily
UPLOAD_DIRECTORY = "/tmp/rag_uploads"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    context: list[str]


DB_FILE = tempfile.NamedTemporaryFile(prefix="milvus_", suffix=".db", delete=False).name
EMBEDDINGS_MODEL = GoogleGenerativeAIEmbeddings(model="models/"gemini-embedding-001")
VECTOR_DB_INSTANCE = None

def get_vector_db():
    """Initializes and returns a singleton Milvus vector database instance."""
    global VECTOR_DB_INSTANCE
    if VECTOR_DB_INSTANCE is None:
        print(f"The vector database will be saved to {DB_FILE}")
        VECTOR_DB_INSTANCE = Milvus(
            embedding_function=EMBEDDINGS_MODEL,
            connection_args={"uri": DB_FILE},
            auto_id=True,
            index_params={"index_type": "AUTOINDEX"},
        )
    return VECTOR_DB_INSTANCE



@router.post("/process/")
async def process_document(filename: str) -> int:
    """Loads a document from a file, splits it into chunks, and adds it to the vector store."""
    documents = []
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File not found: {filename}")

    file_extension = os.path.splitext(filename)[1]
    if file_extension == ".pdf":
        loader = PyPDFLoader(filename)
    elif file_extension == ".docx":
        loader = Docx2txtLoader(filename)
    elif file_extension == ".eml":
        loader = UnstructuredEmailLoader(filename)
    elif file_extension == ".txt":
        loader = TextLoader(filename)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

    documents.extend(loader.lazy_load())

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)

    for i, text in enumerate(texts):
        text.metadata["doc_id"] = i + 1

    vector_db = get_vector_db()
    ids = vector_db.add_documents(texts)
    return len(ids)



MODEL = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.4)

@router.post("/query/", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Asks a question to the RAG system and gets an answer.
    """
    try:
        response = await services.answer_question(request.query)
        context_docs = [doc.page_content for doc in response.get("context", [])]
        return {"answer": response.get("answer"), "context": context_docs}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred during query: {e}"
        )

@router.get("/answer/")

async def get_rag_answer(query: str) -> dict:
    """
    Builds and invokes a RAG chain to answer a question based on the vector store.
    """
    vector_db = get_vector_db()
    if vector_db is None:
        raise RuntimeError("Vector database is not initialized. Please upload a document first.")

    # Create a prompt for question-answering with the retrieved context
    prompt_template = ChatPromptTemplate.from_template("""Answer the following question based only on the provided context:

<context>
{context}
</context>

Question: {input}""")
    
    # Assemble the retrieval-augmented generation chain
    combine_docs_chain = create_stuff_documents_chain(
        llm=MODEL,
        prompt=prompt_template,
    )
    
    rag_chain = create_retrieval_chain(
        retriever=vector_db.as_retriever(),
        combine_docs_chain=combine_docs_chain,
    )
    
    # The 'invoke' method can be blocking, for a truly async API, consider 'ainvoke'
    output = await rag_chain.ainvoke({"input": query})
    return output


if __name__ == "__main__":
