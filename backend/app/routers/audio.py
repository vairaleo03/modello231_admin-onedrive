from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session 
from sqlalchemy.future import select
from app.models.audio_files import AudioFile
from app.database import get_db
from app.models import *
from app.routers.websocket_manager import websocket_manager
from app.utils.onedrive_utils import onedrive_integration
import uuid
import asyncio

router = APIRouter()

# API che permette il caricamento di un file audio e il salvataggio a DB - RIMOSSO PARAMETRO ONEDRIVE
@router.post("/audio/upload")
async def upload_audio(
    audio_file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """Carica file audio nel database - SALVATAGGIO ONEDRIVE RIMOSSO"""
    
    if not audio_file:
        print("Nessun file ricevuto")
        raise HTTPException(status_code=400, detail="Nessun file ricevuto")
    
    print(f"Nome del file ricevuto: {audio_file.filename}")
    
    try:
        file_content = audio_file.file.read()  
        print(f"📦 Dimensione del file: {len(file_content)} byte")

        # Crea un nuovo record nel database
        new_audio = AudioFile(file_name=audio_file.filename, file_data=file_content)
        db.add(new_audio)
        db.commit()
        db.refresh(new_audio)

        job_id = str(uuid.uuid4())  
        print(f"🆔 Job ID generato: {job_id}")
        
        response_data = {
            "audio_file_id": new_audio.id, 
            "job_id": job_id, 
            "message": "File caricato con successo!"
        }

        # RIMOSSO: Salvataggio automatico OneDrive
        await websocket_manager.send_notification("File salvato con successo")

        return response_data

    except Exception as e:
        print(f"Errore durante l'upload: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante l'upload: {str(e)}")

# Endpoint specifico per salvare file audio esistente su OneDrive
@router.post("/audio/{audio_id}/save-onedrive")
async def save_audio_onedrive(audio_id: int, db: Session = Depends(get_db)):
    """Salva un file audio esistente su OneDrive"""
    
    result = db.execute(select(AudioFile).filter(AudioFile.id == audio_id))
    audio_file = result.scalar_one_or_none()
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="File audio non trovato")
    
    try:
        await websocket_manager.send_notification("Salvataggio su OneDrive in corso...")
        
        onedrive_result = await onedrive_integration.save_audio_to_onedrive(
            audio_data=audio_file.file_data,
            filename=audio_file.file_name
        )
        
        if onedrive_result["success"]:
            await websocket_manager.send_notification("File audio salvato su OneDrive")
            
            return {
                "message": "File audio salvato su OneDrive con successo",
                "file_info": {
                    "file_id": onedrive_result["file_id"],
                    "filename": onedrive_result["name"],
                    "size": onedrive_result["size"],
                    "folder_path": onedrive_result["folder_path"],
                    "web_url": onedrive_result.get("web_url")
                }
            }
        else:
            await websocket_manager.send_notification("Errore nel salvataggio su OneDrive")
            raise HTTPException(
                status_code=500,
                detail=f"Errore nel salvataggio su OneDrive: {onedrive_result['error']}"
            )
            
    except Exception as e:
        await websocket_manager.send_notification("Errore nel salvataggio su OneDrive")
        raise HTTPException(status_code=500, detail=f"Errore: {str(e)}")

# API per ottenere la lista dei file audio caricati
@router.get("/audio")
def get_audio_files(db: Session = Depends(get_db)):
    """Restituisce ID, nome file e data di caricamento"""
    result = db.execute(select(AudioFile))
    audio_files = result.scalars().all()

    return [
        {"id": file.id, "file_name": file.file_name, "uploaded_at": file.uploaded_at}
        for file in audio_files
    ]

# Endpoint per ottenere dettagli file audio
@router.get("/audio/{audio_id}")
def get_audio_file_details(audio_id: int, db: Session = Depends(get_db)):
    """Ottiene i dettagli di un file audio specifico"""
    result = db.execute(select(AudioFile).filter(AudioFile.id == audio_id))
    audio_file = result.scalar_one_or_none()
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="File audio non trovato")
    
    return {
        "id": audio_file.id,
        "file_name": audio_file.file_name,
        "file_size": len(audio_file.file_data),
        "uploaded_at": audio_file.uploaded_at
    }

# Endpoint per eliminare file audio
@router.delete("/audio/{audio_id}")
async def delete_audio_file(audio_id: int, db: Session = Depends(get_db)):
    """Elimina un file audio dal database"""
    result = db.execute(select(AudioFile).filter(AudioFile.id == audio_id))
    audio_file = result.scalar_one_or_none()
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="File audio non trovato")
    
    try:
        db.delete(audio_file)
        db.commit()
        
        await websocket_manager.send_notification("File audio eliminato")
        
        return {"message": "File audio eliminato con successo"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore nell'eliminazione: {str(e)}")