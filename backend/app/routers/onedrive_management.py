from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.onedrive_utils import onedrive_integration, OneDriveIntegration
from app.services.onedrive_service import onedrive_service
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

router = APIRouter(prefix="/onedrive", tags=["OneDrive Management"])

class ClienteInfoRequest(BaseModel):
    ragione_sociale: str
    cliente_id: Optional[int] = None

class UploadFileRequest(BaseModel):
    file_type: str = "documento"
    cliente_info: Optional[Dict[str, Any]] = None

# Endpoint per creare informazioni cliente standardizzate
@router.post("/cliente/create-info")
async def create_cliente_info(request: ClienteInfoRequest):
    """Crea informazioni cliente standardizzate per OneDrive"""
    try:
        cliente_info = OneDriveIntegration.create_cliente_info(
            ragione_sociale=request.ragione_sociale,
            cliente_id=request.cliente_id
        )
        
        return {
            "success": True,
            "cliente_info": cliente_info,
            "message": "Informazioni cliente create con successo"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella creazione info cliente: {str(e)}")

# Endpoint per ottenere informazioni sulla struttura cartelle
@router.get("/folder-structure")
async def get_folder_structure():
    """Ottiene informazioni sulla struttura cartelle OneDrive"""
    try:
        structure_info = await OneDriveIntegration.get_folder_structure_info()
        
        return {
            "success": True,
            "structure_info": structure_info,
            "message": "Informazioni struttura ottenute con successo"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nell'ottenere struttura: {str(e)}")

# Endpoint per pulire la cache cartelle
@router.post("/clear-cache")
async def clear_folder_cache():
    """Pulisce la cache delle cartelle OneDrive"""
    try:
        await OneDriveIntegration.clear_folder_cache()
        
        return {
            "success": True,
            "message": "Cache cartelle pulita con successo"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella pulizia cache: {str(e)}")

# Endpoint per testare la creazione di cartelle per cliente
@router.post("/test-folder-creation")
async def test_folder_creation(request: ClienteInfoRequest):
    """Testa la creazione di cartelle per un cliente specifico"""
    try:
        cliente_info = OneDriveIntegration.create_cliente_info(
            ragione_sociale=request.ragione_sociale,
            cliente_id=request.cliente_id
        )
        
        # Testa la generazione del percorso per diversi tipi di file
        test_results = {}
        file_types = ["audio", "trascrizione", "verbale", "documento"]
        
        for file_type in file_types:
            folder_path = onedrive_service._generate_folder_path(file_type, cliente_info)
            test_results[file_type] = folder_path
        
        return {
            "success": True,
            "cliente_info": cliente_info,
            "folder_paths": test_results,
            "message": "Test creazione cartelle completato"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel test: {str(e)}")

# Endpoint per simulare upload con cliente
@router.post("/simulate-upload")
async def simulate_upload(
    file_type: str = Query("documento", description="Tipo di file da simulare"),
    ragione_sociale: str = Query(..., description="Ragione sociale del cliente"),
    cliente_id: Optional[int] = Query(None, description="ID del cliente")
):
    """Simula un upload per testare la struttura cartelle senza caricare file reali"""
    try:
        # Crea info cliente
        cliente_info = OneDriveIntegration.create_cliente_info(ragione_sociale, cliente_id)
        
        # Genera percorso cartella
        folder_path = onedrive_service._generate_folder_path(file_type, cliente_info)
        
        # Testa la creazione cartelle (senza upload file)
        folder_id = await onedrive_service._ensure_folder_exists(folder_path)
        
        return {
            "success": True,
            "cliente_info": cliente_info,
            "folder_path": folder_path,
            "folder_id": folder_id,
            "message": f"Cartelle create/verificate per {ragione_sociale}",
            "file_type": file_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella simulazione: {str(e)}")

# Endpoint per ottenere la struttura completa di un cliente
@router.get("/cliente/{ragione_sociale}/structure")
async def get_cliente_structure(ragione_sociale: str, cliente_id: Optional[int] = None):
    """Ottiene la struttura cartelle completa per un cliente"""
    try:
        cliente_info = OneDriveIntegration.create_cliente_info(ragione_sociale, cliente_id)
        
        # Genera tutte le possibili cartelle per il cliente
        file_types = ["audio", "trascrizione", "verbale", "documento"]
        structure = {}
        
        for file_type in file_types:
            folder_path = onedrive_service._generate_folder_path(file_type, cliente_info)
            structure[file_type] = {
                "folder_path": folder_path,
                "exists_in_cache": folder_path in onedrive_service.get_folder_cache_info()
            }
        
        return {
            "success": True,
            "cliente_info": cliente_info,
            "folder_structure": structure,
            "cache_info": {
                "total_cached_folders": len(onedrive_service.get_folder_cache_info()),
                "cliente_folders_in_cache": sum(1 for path in onedrive_service.get_folder_cache_info().keys() 
                                               if ragione_sociale.replace(" ", "_") in path)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nell'ottenere struttura cliente: {str(e)}")

# Endpoint per health check del servizio OneDrive
@router.get("/health")
async def onedrive_health_check():
    """Controlla lo stato del servizio OneDrive"""
    try:
        # Testa connessione base
        token = await onedrive_service._get_access_token()
        drive_id = await onedrive_service._get_drive_id()
        
        cache_info = onedrive_service.get_folder_cache_info()
        
        return {
            "success": True,
            "status": "healthy",
            "service": "OneDrive Microsoft Graph",
            "has_token": bool(token),
            "has_drive_id": bool(drive_id),
            "cache_size": len(cache_info),
            "message": "Servizio OneDrive operativo"
        }
    except Exception as e:
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e),
            "message": "Errore nel servizio OneDrive"
        }