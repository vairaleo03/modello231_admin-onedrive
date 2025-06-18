from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.prompts import Prompt

router = APIRouter(prefix="/api/prompts", tags=["Prompts"])

# GET: Recupera un prompt per ID
@router.get("/{prompt_id}")
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt non trovato")
    return {
        "id": prompt.id,
        "name": prompt.name,
        "content": prompt.prompt
    }

# PUT: Aggiorna un prompt esistente
@router.put("/{prompt_id}")
def update_prompt(prompt_id: int, data: dict, db: Session = Depends(get_db)):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt non trovato")
    
    prompt.prompt = data.get("content", prompt.prompt)
    db.commit()
    db.refresh(prompt)
    return {
        "message": "Prompt aggiornato con successo",
        "id": prompt.id,
        "content": prompt.prompt
    }
