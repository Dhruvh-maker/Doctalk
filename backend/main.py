import os
from typing import List, Optional
import io
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from mistralai.client import Mistral
from supabase import create_client

load_dotenv()

app = FastAPI(title="DocTalk API")

# CORS middleware — allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))


# ---------------------------------------------------------------------------
# Helper: process_pdf
# ---------------------------------------------------------------------------
async def process_pdf(file: UploadFile) -> int:
    """
    Extracts text from a PDF, splits into 500-word chunks, embeds each chunk
    with Mistral, and stores them in the Supabase documents table.
    Returns the total number of chunks stored.
    """
    contents = await file.read()
    reader = PdfReader(io.BytesIO(contents))

    # Extract all text
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + " "

    # Split into 500-word chunks
    words = full_text.split()
    chunks = []
    for i in range(0, len(words), 500):
        chunk = " ".join(words[i : i + 500])
        chunks.append(chunk)

    # Embed and store chunks in batches of 50 to avoid API limits
    batch_size = 50
    total_stored = 0

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]
        
        # Embed the batch
        result = mistral_client.embeddings.create(
            model="mistral-embed", inputs=batch_chunks
        )
        
        # Insert the batch into Supabase
        rows = []
        for j, chunk in enumerate(batch_chunks):
            rows.append(
                {
                    "content": chunk,
                    "embedding": result.data[j].embedding,
                    "filename": file.filename,
                }
            )
            
        if rows:
            supabase.table("documents").insert(rows).execute()
            total_stored += len(rows)

    return total_stored


# ---------------------------------------------------------------------------
# Helper: answer_question
# ---------------------------------------------------------------------------
async def answer_question(question: str, filename: str, history: list = []) -> str:
    """
    Embeds the question, retrieves the 3 most similar chunks from Supabase,
    builds a messages list with history, and returns Mistral's answer.
    """
    # Embed the question
    q_result = mistral_client.embeddings.create(
        model="mistral-embed", inputs=[question]
    )
    question_embedding = q_result.data[0].embedding

    # Retrieve matching chunks
    match_response = supabase.rpc(
        "match_documents",
        {
            "query_embedding": question_embedding, 
            "match_count": 3,
            "filter_filename": filename
        },
    ).execute()

    chunks = [doc["content"] for doc in match_response.data]
    context = "\n\n".join(chunks)

    # Build messages list with system prompt, context, history, and question
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that answers questions "
                "based on the provided document context. "
                "Always refer to the context when answering."
            ),
        },
        {
            "role": "user",
            "content": f"Here is the relevant context from the document:\n\n{context}",
        },
    ]

    # Append conversation history
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Append current question
    messages.append({"role": "user", "content": question})

    chat_response = mistral_client.chat.complete(
        model="mistral-small-latest",
        messages=messages,
    )

    return chat_response.choices[0].message.content


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: List[HistoryMessage] = []
    session_id: str = ""
    filename: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        chunk_count = await process_pdf(file)
        return {"status": "success", "chunks": chunk_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        history_dicts = [{"role": m.role, "content": m.content} for m in request.history]
        answer = await answer_question(request.question, request.filename, history_dicts)

        # Save to chat_history if session_id is provided
        if request.session_id:
            supabase.table("chat_history").insert(
                {"session_id": request.session_id, "role": "user", "content": request.question}
            ).execute()
            supabase.table("chat_history").insert(
                {"session_id": request.session_id, "role": "assistant", "content": answer}
            ).execute()

        return {"answer": answer}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    try:
        result = (
            supabase.table("chat_history")
            .select("role, content")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return {"history": result.data}
    except Exception as e:
        return {"status": "error", "message": str(e)}
