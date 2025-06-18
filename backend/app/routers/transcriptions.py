import aiohttp
import io
import os
import tempfile
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import update
from app.database import get_db
from app.models.audio_files import AudioFile
from app.models.transcripts import Transcript
from app.models.tasks import Task, TaskStatus
from pydantic import BaseModel
from app.routers.websocket_manager import websocket_manager
from app.utils.post_processing import format_transcription, convert_html_to_word_template
from app.services.transcriber import transcribe_audio
from app.utils.onedrive_utils import onedrive_integration
from fastapi import UploadFile
from pydub import AudioSegment

router = APIRouter()

class TranscriptUpdateRequest(BaseModel):
    transcript_text: str

class OneDriveUploadRequest(BaseModel):
    action: str = "save"  # "save" per salvare su OneDrive

# Recupera una trascrizione
@router.get("/transcriptions/{transcript_id}")
def get_transcription(transcript_id: int, db: Session = Depends(get_db)):
    result = db.execute(select(Transcript).filter(Transcript.id == transcript_id))
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Trascrizione non trovata")

    return {
        "transcript_id": transcription.id,
        "transcript_text": transcription.transcript_text,
        "audio_id": transcription.audio_id,
        "created_at": transcription.created_at, 
        "segments": transcription.segments
    }

# Salva automaticamente le modifiche alla trascrizione
@router.put("/transcriptions/{transcript_id}")
def update_transcription(transcript_id: int, request: TranscriptUpdateRequest, db: Session = Depends(get_db)):
    result = db.execute(select(Transcript).filter(Transcript.id == transcript_id))
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Trascrizione non trovata")

    stmt = update(Transcript).where(Transcript.id == transcript_id).values(transcript_text=request.transcript_text)
    db.execute(stmt)
    db.commit()
    websocket_manager.send_notification("Modifiche salvate")
    return {"message": "Trascrizione aggiornata con successo!"}

# API che esegue la trascrizione
@router.post("/start-transcription/{audio_file_id}")
def start_transcription_endpoint(audio_file_id: int, db: Session = Depends(get_db)):
    try:
        # Cerca il file audio nel database
        result = db.execute(select(AudioFile).filter(AudioFile.id == audio_file_id))
        audio_file = result.scalar_one_or_none()

        if not audio_file:
            print(f"❌ File audio con ID {audio_file_id} non trovato nel database.")
            raise HTTPException(status_code=404, detail="File audio non trovato")
        
        # Conversione in .mp3 mono 16kHz
        original = AudioSegment.from_file(io.BytesIO(audio_file.file_data))
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            original.set_channels(1).set_frame_rate(16000).export(temp_file.name, format="mp3")
            temp_path = temp_file.name

        # Trascrizione con API OpenAI
        result_json = transcribe_audio(temp_path)
        print(f"result json ----> {result_json}")
        os.remove(temp_path)

        # Ottieni la trascrizione grezza
        raw_transcription = result_json.get("transcription")
        segments = result_json.get("segments")
        if not raw_transcription:
            raise HTTPException(status_code=500, detail="Trascrizione non trovata nella risposta")

        # Formatta la trascrizione
        formatted_segments = segments
        formatted_transcription = format_transcription(raw_transcription)

        # Salva la trascrizione nel DB
        new_transcript = Transcript(
            audio_id=audio_file.id,
            transcript_text=formatted_transcription,
            segments=formatted_segments,
            created_at=datetime.utcnow()
        )
        db.add(new_transcript)
        db.commit()
        db.refresh(new_transcript)

        return {
            "message": "Trascrizione completata con successo!",
            "transcript_id": new_transcript.id,
            "audio_file_id": audio_file.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante la trascrizione: {str(e)}")

# API che converte la trascrizione in word e gestisce download/OneDrive
@router.post("/transcriptions/{transcript_id}/word")
async def manage_word_file(
    transcript_id: int, 
    action: str = Query("download", description="'download' per scaricare, 'onedrive' per salvare su OneDrive"),
    db: Session = Depends(get_db)
):
    """Genera un file Word dalla trascrizione e lo scarica o salva su OneDrive."""
    
    result = db.execute(select(Transcript).filter(Transcript.id == transcript_id))
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Trascrizione non trovata")

    try:
        if action == "download":
            # Comportamento originale - download diretto
            doc = convert_html_to_word_template(transcription.transcript_text)
            
            file_stream = io.BytesIO()
            doc.save(file_stream)
            file_stream.seek(0)

            return StreamingResponse(
                io.BytesIO(file_stream.getvalue()), 
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename=trascrizione_{transcript_id}.docx"}
            )
            
        elif action == "onedrive":
            # Nuovo comportamento - salvataggio su OneDrive
            result = await onedrive_integration.save_transcription_to_onedrive(
                transcript_text=transcription.transcript_text,
                transcript_id=transcript_id
            )
            
            if result["success"]:
                # Invia notifica WebSocket
                await websocket_manager.send_notification("Trascrizione salvata su OneDrive")
                
                response_data = {
                    "message": "Trascrizione salvata su OneDrive con successo",
                    "onedrive_file_id": result["file_id"],
                    "filename": result["name"],
                    "folder_path": result["folder_path"]
                }
                
                # Aggiungi link condivisibile se disponibile
                if result.get("web_url"):
                    response_data["web_url"] = result["web_url"]
                
                return response_data
            else:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Errore nel salvataggio su OneDrive: {result['error']}"
                )
        else:
            raise HTTPException(status_code=400, detail="Azione non valida. Usa 'download' o 'onedrive'.")
            
    except Exception as e:
        if action == "onedrive":
            await websocket_manager.send_notification("Errore nel salvataggio su OneDrive")
        raise HTTPException(status_code=500, detail=f"Errore nell'elaborazione: {str(e)}")

# NUOVO: Endpoint specifico per salvare su OneDrive (alternativo)
@router.post("/transcriptions/{transcript_id}/save-onedrive")
async def save_transcription_onedrive(transcript_id: int, db: Session = Depends(get_db)):
    """Endpoint dedicato per salvare la trascrizione su OneDrive"""
    
    result = db.execute(select(Transcript).filter(Transcript.id == transcript_id))
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Trascrizione non trovata")

    try:
        # Salva su OneDrive
        upload_result = await onedrive_integration.save_transcription_to_onedrive(
            transcript_text=transcription.transcript_text,
            transcript_id=transcript_id
        )
        
        if upload_result["success"]:
            await websocket_manager.send_notification("Trascrizione salvata su OneDrive")
            
            return {
                "message": "Trascrizione salvata su OneDrive con successo",
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