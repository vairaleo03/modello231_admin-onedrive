from fastapi import FastAPI
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ping, audio, transcriptions, summaries, users, prompts, clients
from app.routers.websocket_manager import router as websocket_router, websocket_manager
from app.routers import onedrive_management

load_dotenv()

origins = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in origins.split(",") if origin.strip()]

app = FastAPI(
    title="Modello231 API",
    description="API per trascrizione e verbalizzazione conforme al D.Lgs. 231/2001",
    version="2.1.0"
) 

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print(f"✅ CORS attivi per: {allowed_origins}")

# Router esistenti
app.include_router(ping.router)
app.include_router(audio.router)
app.include_router(transcriptions.router)
app.include_router(summaries.router)
app.include_router(users.router)
app.include_router(websocket_router)
app.include_router(prompts.router)
app.include_router(onedrive_management.router)

# NUOVO: Router gestione clienti
app.include_router(clients.router)

# Health check endpoint aggiornato
@app.get("/")
async def root():
    return {
        "message": "Modello231 API - Sistema di trascrizione e verbalizzazione",
        "version": "2.1.0",
        "features": [
            "Trascrizione audio con OpenAI Whisper",
            "Generazione verbali con AI",
            "Gestione clienti con estrazione dati AI",
            "Integrazione OneDrive ottimizzata",
            "Sistema di cache ottimizzato"
        ],
        "new_features": [
            "Gestione completa clienti",
            "Estrazione automatica dati con AI",
            "OneDrive ottimizzato per documenti clienti"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Modello231 API",
        "version": "2.1.0",
        "components": {
            "database": "PostgreSQL",
            "ai_transcription": "OpenAI Whisper",
            "ai_summarization": "Google Gemini",
            "ai_data_extraction": "Google Gemini",
            "cloud_storage": "Microsoft OneDrive",
            "websockets": "FastAPI WebSocket",
            "client_management": "Active"
        }
    }