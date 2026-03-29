
import json
import os
import glob
from pathlib import Path
from datetime import datetime
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Union, Dict, Any, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]
    
class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str
    agent_count: int 
    api_key: str
    temperature: float = 0.7
    top_p: float = 1.0
    system_prompt: str = "You are Grok. Use your tools when necessary."

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    url = "https://api.x.ai/v1/responses"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {req.api_key}"
    }

    effort_level = "low" if req.agent_count == 4 else "high"

    system_message = [{"role": "system", "content": req.system_prompt}]
    history_messages = [{"role": msg.role, "content": msg.content} for msg in req.messages]

    payload = {
        "model": req.model,
        "input": system_message + history_messages,
        "tools": [
            {"type": "x_search"},
            {"type": "web_search"}
        ],
        "stream": True,
        "temperature": req.temperature,
        "top_p": req.top_p
    }

    async def generate():
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    await response.aread()
                    yield f"[API Error {response.status_code}]: {response.text}"
                    return

                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):  # ignore comments/keep-alive
                        continue

                    if line.startswith("data: "):
                        if "[DONE]" in line or "response.completed" in line:
                            continue
                        try:
                            data = json.loads(line[6:])
                            if not isinstance(data, dict):
                                continue

                            # New Responses API format (updated March 2026 for Grok 4.20 models)
                            event_type = data.get("type")

                            # === TEXT HANDLER (also broadened) ===
                            if event_type and ("output_text" in event_type.lower() or "text" in event_type.lower()):
                                if "completed" in event_type.lower() or "done" in event_type.lower() or "stop" in event_type.lower() or "end" in event_type.lower():
                                    continue
                                
                                delta = data.get("delta", {}) or data.get("content", {})
                                if isinstance(delta, dict):
                                    delta_text = delta.get("text") or data.get("text", "")
                                elif isinstance(delta, str):
                                    delta_text = delta
                                else:
                                    delta_text = data.get("text", "")

                                if delta_text:
                                    yield json.dumps({"type": "text", "content": delta_text}) + "\n"
                                    continue

                            # Fallbacks for older or simpler formats
                            elif not event_type:
                                if "choices" in data:
                                    choices = data["choices"]
                                    if choices and isinstance(choices, list):
                                        delta = choices[0].get("delta", {})
                                        
                                        if "content" in delta and delta["content"]:
                                            yield json.dumps({"type": "text", "content": delta["content"]}) + "\n"

                                elif "content" in data:
                                    yield json.dumps({"type": "text", "content": data["content"]}) + "\n"
                                elif "text" in data:
                                    yield json.dumps({"type": "text", "content": data["text"]}) + "\n"

                        except json.JSONDecodeError:
                            continue

    return StreamingResponse(generate(), media_type="application/x-ndjson")
# --- Session Management Endpoints ---
class SaveSessionRequest(BaseModel):
    session_id: str
    title: str
    chat_history: List[Dict[str, Any]]

BASE_DIR = Path(__file__).parent
SESSIONS_DIR = BASE_DIR / 'sessions'
SESSIONS_DIR.mkdir(exist_ok=True)

@app.post("/sessions")
async def save_session(req: SaveSessionRequest):
    file_path = SESSIONS_DIR / f"{req.session_id}.json"
    data = {
        "id": req.session_id,
        "title": req.title,
        "updated_at": datetime.now().isoformat(),
        "chat_history": req.chat_history
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"status": "success", "session_id": req.session_id}

@app.get("/sessions")
async def list_sessions():
    sessions = []
    for file_path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append({
                    "id": data.get("id", file_path.stem),
                    "title": data.get("title", "Untitled Chat"),
                    "updated_at": data.get("updated_at", "")
                })
        except Exception:
            pass
    # Sort by updated_at descending
    sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"sessions": sessions}

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    file_path = SESSIONS_DIR / f"{session_id}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "not found"}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    file_path = SESSIONS_DIR / f"{session_id}.json"
    if file_path.exists():
        file_path.unlink()
        return {"status": "success"}
    return {"error": "not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

