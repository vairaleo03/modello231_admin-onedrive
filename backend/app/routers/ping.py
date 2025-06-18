from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

class PingRequest(BaseModel):
    user_id: str
    email: str | None = None
    full_name: str | None = None

@router.post("/ping")
async def ping(data: PingRequest, request: Request):
    print(f"🔐 Accesso da utente {data.user_id} ({data.email})")
    return {"message": f"accesso eseguito per {data.user_id}"}
