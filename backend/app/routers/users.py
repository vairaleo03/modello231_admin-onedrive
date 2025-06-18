from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
import httpx
import os
router = APIRouter()

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")

class RoleAssignment(BaseModel):
    user_id: str
    role: str

@router.post("/user/assign-role")
async def assign_role(payload: RoleAssignment, authorization: str = Header(None)):
    headers = {
        "Authorization": f"Bearer {CLERK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "public_metadata": {
            "role": payload.role
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"https://api.clerk.com/v1/users/{payload.user_id}",
            json=data,
            headers=headers
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return {"status": "ok", "message": f"Ruolo '{payload.role}' assegnato a {payload.user_id}"}
