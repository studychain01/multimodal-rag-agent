import logging
import os
import base64
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from agent import run_agent
from sessions import get_or_create_session, update_session_messages

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="Vulcan OmniPro 220 Support Agent")

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── request/response models ───────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    """If omitted, a new session is created; client should send back the returned session_id."""
    conversation_history: list = []
    """Legacy: used only when the server session has no messages yet (first load / old clients)."""

class ChatResponse(BaseModel):
    blocks: list
    session_id: str

# ── pages directory ───────────────────────────────────────
PAGES_DIR = Path("files/pages")

# ── endpoints ─────────────────────────────────────────────
@app.get("/")
def health_check():
    return {"status": "ok", "agent": "Vulcan OmniPro 220 Support"}

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        sid, session = get_or_create_session(request.session_id)
        history = list(session["messages"])
        if not history and request.conversation_history:
            history = list(request.conversation_history)

        blocks, messages_after = run_agent(
            user_message=request.message,
            conversation_history=history,
            memory_summary=session.get("memory") or "",
        )
        update_session_messages(session, messages_after)

        return JSONResponse(
            content={
                "blocks": blocks.get("blocks", []) if isinstance(blocks, dict) else [],
                "session_id": sid,
            }
        )

    except Exception as e:
        print(f"Agent error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/page/{source}/{page_num}")
async def get_page(source: str, page_num: int):
    
    # validate source
    valid_sources = ["owner-manual", "quick-start-guide", "selection-chart"]
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Invalid source: {source}")
    
    # build path
    image_path = PAGES_DIR / source / f"page_{page_num}.png"
    
    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_num} not found in {source}"
        )
    
    # read and return as base64
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    return JSONResponse(content={
        "source":  source,
        "page":    page_num,
        "data":    image_data,
        "url":     f"/page/{source}/{page_num}"
    })

@app.get("/pages/{source}")
async def list_pages(source: str):
    source_dir = PAGES_DIR / source
    
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail=f"Source {source} not found")
    
    pages = sorted([
        int(p.stem.replace("page_", ""))
        for p in source_dir.glob("page_*.png")
    ])
    
    return {"source": source, "pages": pages, "count": len(pages)}