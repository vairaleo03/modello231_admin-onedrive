from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import update
from app.database import get_db
from app.models.verbs import Verbs
from pydantic import BaseModel
from app.routers.websocket_manager import websocket_manager
from app.models.transcripts import Transcript
from app.services.summarizer import generate_summary
from app.utils.post_processing import parse_odv_summary, fill_odv_template, parse_to_tiptap_json, estrai_sezioni_verbale
from app.utils.onedrive_utils import onedrive_integration, OneDriveFileManager
from datetime import datetime
import tempfile
import os

router = APIRouter()

class SummaryUpdateRequest(BaseModel):
    summary_text: str

class VerbaleFields(BaseModel):
    VERIFICA: str
    NUMERO_VERBALE: int
    LUOGO_RIUNIONE: str
    DATA_RIUNIONE: str
    ORARIO_INIZIO: str
    ORARIO_FINE: str

# API che genera il riassunto della trascrizione
@router.post("/summary/start/{transcript_id}")
def summarize_transcription(transcript_id: int, db: Session = Depends(get_db)):
    try: 
        result = db.execute(select(Transcript).filter(Transcript.id == transcript_id))
        transcript = result.scalar_one_or_none()

        if not transcript:
            print(f"Trascrizione con ID {transcript_id} non trovata nel database.")
            raise HTTPException(status_code=404, detail="Trascrizione non trovata")

        if not transcript.transcript_text:
            raise HTTPException(status_code=400, detail="Testo della trascrizione mancante")

        summary = generate_summary(transcript.transcript_text)
                
        try:
            new_verbs = Verbs(
                transcript_id=transcript_id,
                verbs_text=summary,
                created_at=datetime.utcnow()
            )

            db.add(new_verbs)
            db.commit()
            db.refresh(new_verbs)
        except Exception as e:
            print(f"❌ Errore durante il processo: {e}")

        return new_verbs.id
    
    except Exception as e:
        print(f"❌ Eccezione nell'endpoint summary/start/ : {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante il riassunto: {str(e)}")

# API che recupera un riassunto
@router.get("/summary/{summary_id}")
def get_summary(summary_id: int, db: Session = Depends(get_db)):
    result = db.execute(select(Verbs).filter(Verbs.id == summary_id))
    summary = result.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Riassunto non trovato")

    summary_parsed = parse_to_tiptap_json(summary.verbs_text)
    return {
        "summary_id": summary.id,
        "transcript_id": summary.transcript_id,
        "summary_text": summary_parsed,
        "created_at": summary.created_at
    }

# API che Salva automaticamente le modifiche al riassunto
@router.put("/summary/{summary_id}")
async def update_transcription(summary_id: int, request: SummaryUpdateRequest, db: Session = Depends(get_db)):
    result = db.execute(select(Verbs).filter(Verbs.id == summary_id))
    summary = result.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Riassunto non trovato")

    stmt = update(Verbs).where(Verbs.id == summary_id).values(verbs_text=request.summary_text)
    db.execute(stmt)
    db.commit()
    await websocket_manager.send_notification("Modifiche salvate")
    return {"message": "Riassunto aggiornato con successo!"}

# Download di un riassunto come docx con opzione OneDrive
@router.post("/summary/{summary_id}/word")
async def download_summary_word(
    summary_id: int, 
    fields: VerbaleFields, 
    action: str = Query("download", description="'download' per scaricare, 'onedrive' per salvare su OneDrive"),
    db: Session = Depends(get_db)
):
    """Genera verbale Word e lo scarica o salva su OneDrive"""
    
    # Recupero riassunto dal DB
    result = db.execute(select(Verbs).filter_by(id=summary_id))
    summary = result.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Riassunto non trovato")
    
    try:
        sections = estrai_sezioni_verbale(summary.verbs_text)

        extra_fields = {
            "DATA_RIUNIONE": datetime.strptime(fields.DATA_RIUNIONE, "%Y-%m-%d").strftime("%d/%m/%Y"),
            "ORARIO_INIZIO": fields.ORARIO_INIZIO,
            "ORARIO_FINE": fields.ORARIO_FINE,
            "LUOGO_RIUNIONE": fields.LUOGO_RIUNIONE,
            "DATA_REDAZIONE": datetime.utcnow().strftime("%d/%m/%Y"),
            "NUMERO_VERBALE": str(fields.NUMERO_VERBALE),
            "VERIFICA": fields.VERIFICA
        }

        if action == "download":
            # Comportamento originale - download diretto
            filename = f"verbale_odv_{summary_id}.docx"
            filepath = f"/tmp/{filename}"
            fill_odv_template(sections, filepath, extra_fields)

            return FileResponse(
                path=filepath,
                filename=filename,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
        elif action == "onedrive":
            # Nuovo comportamento - salvataggio su OneDrive
            filename = f"verbale_odv_{summary_id}.docx"
            filepath = f"/tmp/{filename}"
            fill_odv_template(sections, filepath, extra_fields)
            
            # Carica su OneDrive
            upload_result = await OneDriveFileManager.upload_verbale_docx(filepath, summary_id)
            
            if upload_result["success"]:
                await websocket_manager.send_notification("Verbale salvato su OneDrive")
                
                response_data = {
                    "message": "Verbale salvato su OneDrive con successo",
                    "file_info": {
                        "file_id": upload_result["file_id"],
                        "filename": upload_result["name"],
                        "size": upload_result["size"],
                        "folder_path": upload_result["folder_path"],
                        "web_url": upload_result.get("web_url")
                    }
                }
                
                return response_data
            else:
                await websocket_manager.send_notification("Errore nel salvataggio su OneDrive")
                raise HTTPException(
                    status_code=500,
                    detail=f"Errore nel salvataggio su OneDrive: {upload_result['error']}"
                )
        else:
            raise HTTPException(status_code=400, detail="Azione non valida. Usa 'download' o 'onedrive'.")
            
    except Exception as e:
        if action == "onedrive":
            await websocket_manager.send_notification("Errore nel salvataggio su OneDrive")
        raise HTTPException(status_code=500, detail=f"Errore nell'elaborazione: {str(e)}")

# NUOVO: Endpoint specifico per salvare riassunto su OneDrive (senza template)
@router.post("/summary/{summary_id}/save-onedrive")
async def save_summary_onedrive(summary_id: int, db: Session = Depends(get_db)):
    """Endpoint dedicato per salvare il riassunto su OneDrive come testo semplice"""
    
    result = db.execute(select(Verbs).filter(Verbs.id == summary_id))
    summary = result.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Riassunto non trovato")

    try:
        # Salva su OneDrive
        upload_result = await onedrive_integration.save_summary_to_onedrive(
            summary_text=summary.verbs_text,
            summary_id=summary_id
        )
        
        if upload_result["success"]:
            await websocket_manager.send_notification("Verbale salvato su OneDrive")
            
            return {
                "message": "Verbale salvato su OneDrive con successo",
                "file_info": {
                    "file_id": upload_result["file_id"],
                    "filename": upload_result["name"],
                    "size": upload_result["size"],
                    "folder_path": upload_result["folder_path"],
                    "web_url": upload_result.get("web_url")
                }
            }
        else:
            await websocket_manager.send_notification("Errore nel salvataggio su OneDrive")
            raise HTTPException(
                status_code=500,
                detail=f"Errore nel salvataggio su OneDrive: {upload_result['error']}"
            )
            
    except Exception as e:
        await websocket_manager.send_notification("Errore nel salvataggio su OneDrive")
        raise HTTPException(status_code=500, detail=f"Errore: {str(e)}")

# NUOVO: Endpoint per salvare verbale formattato su OneDrive
@router.post("/summary/{summary_id}/save-formatted-onedrive")
async def save_formatted_summary_onedrive(
    summary_id: int, 
    fields: VerbaleFields, 
    db: Session = Depends(get_db)
):
    """Salva il verbale formattato su OneDrive senza scaricare"""
    
    result = db.execute(select(Verbs).filter_by(id=summary_id))
    summary = result.scalar_one_or_none()

    if not summary:
        raise HTTPException(status_code=404, detail="Riassunto non trovato")

    try:
        sections = estrai_sezioni_verbale(summary.verbs_text)

        extra_fields = {
            "DATA_RIUNIONE": datetime.strptime(fields.DATA_RIUNIONE, "%Y-%m-%d").strftime("%d/%m/%Y"),
            "ORARIO_INIZIO": fields.ORARIO_INIZIO,
            "ORARIO_FINE": fields.ORARIO_FINE,
            "LUOGO_RIUNIONE": fields.LUOGO_RIUNIONE,
            "DATA_REDAZIONE": datetime.utcnow().strftime("%d/%m/%Y"),
            "NUMERO_VERBALE": str(fields.NUMERO_VERBALE),
            "VERIFICA": fields.VERIFICA
        }

        # Crea file temporaneo
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            filepath = temp_file.name

        fill_odv_template(sections, filepath, extra_fields)
        
        # Carica su OneDrive
        upload_result = await OneDriveFileManager.upload_verbale_docx(filepath, summary_id)
        
        if upload_result["success"]:
            await websocket_manager.send_notification("Verbale formattato salvato su OneDrive")
            
            return {
                "message": "Verbale formattato salvato su OneDrive con successo",
                "file_info": {
                    "file_id": upload_result["file_id"],
                    "filename": upload_result["name"],
                    "size": upload_result["size"],
                    "folder_path": upload_result["folder_path"],
                    "web_url": upload_result.get("web_url")
                }
            }
        else:
            await websocket_manager.send_notification("Errore nel salvataggio su OneDrive")
            raise HTTPException(
                status_code=500,
                detail=f"Errore nel salvataggio su OneDrive: {upload_result['error']}"
            )
            
    except Exception as e:
        await websocket_manager.send_notification("Errore nel salvataggio su OneDrive")
        raise HTTPException(status_code=500, detail=f"Errore: {str(e)}")