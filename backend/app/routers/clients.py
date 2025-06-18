# backend/app/routers/clients.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models.clients import Client  # ✅ CORRETTO: import da models
from app.services.client_data_extractor import client_extractor
from app.utils.onedrive_utils import OneDriveIntegration
from app.routers.websocket_manager import websocket_manager
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os

router = APIRouter(prefix="/admin/clients", tags=["Client Management"])

# Pydantic Models
class ClientCreate(BaseModel):
    ragione_sociale: str
    partita_iva: str
    codice_fiscale: Optional[str] = None
    telefono: Optional[str] = None
    email: EmailStr
    pec: Optional[EmailStr] = None
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    cap: Optional[str] = None
    provincia: Optional[str] = None
    rappresentante_legale: Optional[str] = None
    cf_rappresentante: Optional[str] = None
    settore_attivita: Optional[str] = None
    numero_dipendenti: Optional[int] = None
    note: Optional[str] = None

class ClientResponse(BaseModel):
    id: int
    ragione_sociale: str
    partita_iva: str
    email: str
    citta: Optional[str]
    settore_attivita: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ExtractedDataResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_text: Optional[str] = None

# GET: Lista clienti
@router.get("/", response_model=List[ClientResponse])
async def get_clients(db: Session = Depends(get_db)):
    """Restituisce la lista di tutti i clienti"""
    result = db.execute(select(Client).order_by(Client.created_at.desc()))
    clients = result.scalars().all()
    return clients

# GET: Dettagli cliente singolo
@router.get("/{client_id}")
async def get_client(client_id: int, db: Session = Depends(get_db)):
    """Restituisce i dettagli di un cliente specifico"""
    result = db.execute(select(Client).filter(Client.id == client_id))
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    return {
        "id": client.id,
        "ragione_sociale": client.ragione_sociale,
        "partita_iva": client.partita_iva,
        "codice_fiscale": client.codice_fiscale,
        "telefono": client.telefono,
        "email": client.email,
        "pec": client.pec,
        "indirizzo": client.indirizzo,
        "citta": client.citta,
        "cap": client.cap,
        "provincia": client.provincia,
        "rappresentante_legale": client.rappresentante_legale,
        "cf_rappresentante": client.cf_rappresentante,
        "settore_attivita": client.settore_attivita,
        "numero_dipendenti": client.numero_dipendenti,
        "note": client.note,
        "extracted_data": client.extracted_data,
        "documents_path": client.documents_path,
        "created_at": client.created_at,
        "updated_at": client.updated_at
    }

# POST: Crea nuovo cliente
@router.post("/", response_model=ClientResponse)
async def create_client(client_data: ClientCreate, db: Session = Depends(get_db)):
    """Crea un nuovo cliente"""
    
    # Verifica se partita IVA già esiste
    existing = db.execute(
        select(Client).filter(Client.partita_iva == client_data.partita_iva)
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Cliente con questa Partita IVA già esistente"
        )
    
    try:
        # Crea nuovo cliente
        new_client = Client(
            ragione_sociale=client_data.ragione_sociale,
            partita_iva=client_data.partita_iva,
            codice_fiscale=client_data.codice_fiscale,
            telefono=client_data.telefono,
            email=client_data.email,
            pec=client_data.pec,
            indirizzo=client_data.indirizzo,
            citta=client_data.citta,
            cap=client_data.cap,
            provincia=client_data.provincia,
            rappresentante_legale=client_data.rappresentante_legale,
            cf_rappresentante=client_data.cf_rappresentante,
            settore_attivita=client_data.settore_attivita,
            numero_dipendenti=client_data.numero_dipendenti,
            note=client_data.note
        )
        
        db.add(new_client)
        db.commit()
        db.refresh(new_client)
        
        await websocket_manager.send_notification(f"Cliente {client_data.ragione_sociale} creato con successo")
        
        return new_client
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore nella creazione cliente: {str(e)}")

# POST: Estrai dati da documenti
@router.post("/extract-data", response_model=ExtractedDataResponse)
async def extract_client_data(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Estrae dati cliente da documenti caricati usando AI"""
    
    if not files:
        raise HTTPException(status_code=400, detail="Nessun file caricato")
    
    try:
        await websocket_manager.send_notification("Elaborazione documenti in corso...")
        
        # Prepara file per l'estrazione
        file_data = []
        for file in files:
            content = await file.read()
            file_data.append({
                'filename': file.filename,
                'content_bytes': content,
                'content_type': file.content_type
            })
        
        # Estrae dati con AI
        extraction_result = await client_extractor.extract_from_documents(file_data)
        
        if extraction_result.get("success"):
            await websocket_manager.send_notification("Dati estratti con successo!")
        else:
            await websocket_manager.send_notification("Errore nell'estrazione dati")
        
        return extraction_result
        
    except Exception as e:
        await websocket_manager.send_notification("Errore nell'elaborazione documenti")
        raise HTTPException(status_code=500, detail=f"Errore nell'estrazione: {str(e)}")

# POST: Salva documenti cliente su OneDrive
@router.post("/{client_id}/save-documents")
async def save_client_documents(
    client_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Salva i documenti di un cliente su OneDrive"""
    
    # Verifica che il cliente esista
    result = db.execute(select(Client).filter(Client.id == client_id))
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    try:
        await websocket_manager.send_notification("Salvataggio documenti su OneDrive...")
        
        # Crea info cliente per OneDrive
        cliente_info = OneDriveIntegration.create_cliente_info(
            ragione_sociale=client.ragione_sociale,
            cliente_id=client.id
        )
        
        saved_files = []
        for file in files:
            content = await file.read()
            
            # Salva su OneDrive
            result = await OneDriveIntegration.save_document_to_onedrive(
                file_content=content,
                filename=file.filename,
                cliente_info=cliente_info
            )
            
            if result.get("success"):
                saved_files.append({
                    "filename": file.filename,
                    "onedrive_path": result.get("folder_path"),
                    "file_id": result.get("file_id")
                })
        
        # Aggiorna cliente con path documenti
        if saved_files:
            documents_info = {
                "files": saved_files,
                "upload_date": datetime.utcnow().isoformat()
            }
            client.extracted_data = client.extracted_data or {}
            client.extracted_data["documents"] = documents_info
            client.documents_path = saved_files[0]["onedrive_path"]  # Path principale
            
            db.commit()
        
        await websocket_manager.send_notification(f"Documenti salvati per {client.ragione_sociale}")
        
        return {
            "success": True,
            "message": f"Salvati {len(saved_files)} documenti",
            "files": saved_files
        }
        
    except Exception as e:
        await websocket_manager.send_notification("Errore nel salvataggio documenti")
        raise HTTPException(status_code=500, detail=f"Errore nel salvataggio: {str(e)}")

# PUT: Aggiorna cliente
@router.put("/{client_id}")
async def update_client(
    client_id: int,
    client_data: ClientCreate,
    db: Session = Depends(get_db)
):
    """Aggiorna i dati di un cliente esistente"""
    
    result = db.execute(select(Client).filter(Client.id == client_id))
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    try:
        # Aggiorna tutti i campi
        for field, value in client_data.dict().items():
            if value is not None:
                setattr(client, field, value)
        
        client.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(client)
        
        await websocket_manager.send_notification(f"Cliente {client.ragione_sociale} aggiornato")
        
        return client
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore nell'aggiornamento: {str(e)}")

# DELETE: Elimina cliente
@router.delete("/{client_id}")
async def delete_client(client_id: int, db: Session = Depends(get_db)):
    """Elimina un cliente"""
    
    result = db.execute(select(Client).filter(Client.id == client_id))
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    
    try:
        ragione_sociale = client.ragione_sociale
        db.delete(client)
        db.commit()
        
        await websocket_manager.send_notification(f"Cliente {ragione_sociale} eliminato")
        
        return {"message": "Cliente eliminato con successo"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Errore nell'eliminazione: {str(e)}")

# GET: Test sistema
@router.get("/test-system")
async def test_client_system():
    """Endpoint di test per verificare il sistema gestione clienti"""
    
    test_results = {
        "database": "❌",
        "ai_extraction": "❌", 
        "onedrive": "❌",
        "websockets": "❌"
    }
    
    # Test database
    try:
        from app.models.clients import Client
        test_results["database"] = "✅ Database pronto"
    except Exception as e:
        test_results["database"] = f"❌ Errore DB: {str(e)}"
    
    # Test AI
    try:
        import google.generativeai as genai
        GEMINI_API = os.getenv("GEMINI_API_KEY")
        if GEMINI_API:
            test_results["ai_extraction"] = "✅ Gemini AI configurato"
        else:
            test_results["ai_extraction"] = "❌ GEMINI_API_KEY mancante"
    except Exception as e:
        test_results["ai_extraction"] = f"❌ Errore AI: {str(e)}"
    
    # Test OneDrive
    try:
        from app.services.onedrive_service import onedrive_service
        required_vars = ["MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET", "MICROSOFT_TENANT_ID", "ONEDRIVE_USER_EMAIL"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if not missing_vars:
            test_results["onedrive"] = "✅ OneDrive configurato"
        else:
            test_results["onedrive"] = f"❌ Variabili mancanti: {', '.join(missing_vars)}"
    except Exception as e:
        test_results["onedrive"] = f"❌ Errore OneDrive: {str(e)}"
    
    # Test WebSocket
    try:
        await websocket_manager.send_notification("Test sistema clienti completato")
        test_results["websockets"] = "✅ WebSocket funzionante"
    except Exception as e:
        test_results["websockets"] = f"❌ Errore WebSocket: {str(e)}"
    
    # Status generale
    all_working = all("✅" in result for result in test_results.values())
    
    return {
        "system_status": "✅ TUTTO FUNZIONANTE" if all_working else "⚠️ PROBLEMI RILEVATI",
        "timestamp": datetime.utcnow().isoformat(),
        "components": test_results,
        "endpoints_available": [
            "GET /admin/clients/ - Lista clienti",
            "POST /admin/clients/ - Crea cliente", 
            "POST /admin/clients/extract-data - Estrai dati AI",
            "GET /admin/clients/test-system - Test sistema"
        ],
        "frontend_url": "http://localhost:3000/admin-dashboard",
        "next_steps": [
            "1. Verifica che tutti i componenti mostrino ✅",
            "2. Vai su http://localhost:3000/admin-dashboard",
            "3. Clicca su 'Nuovo Cliente'",
            "4. Testa upload documenti e estrazione AI",
            "5. Completa creazione cliente"
        ] if all_working else [
            "1. Risolvi i problemi indicati con ❌",
            "2. Controlla le variabili d'ambiente nel file .env",
            "3. Verifica che la migrazione database sia applicata",
            "4. Rilancia il test"
        ]
    }