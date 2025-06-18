# backend/app/models/clients.py
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.database import Base
from datetime import datetime

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    ragione_sociale = Column(String(255), nullable=False)
    partita_iva = Column(String(11), unique=True, nullable=False)
    codice_fiscale = Column(String(16), nullable=True)
    telefono = Column(String(20), nullable=True)
    email = Column(String(255), nullable=False)
    pec = Column(String(255), nullable=True)
    indirizzo = Column(String(255), nullable=True)
    citta = Column(String(100), nullable=True)
    cap = Column(String(5), nullable=True)
    provincia = Column(String(2), nullable=True)
    rappresentante_legale = Column(String(255), nullable=True)
    cf_rappresentante = Column(String(16), nullable=True)
    settore_attivita = Column(String(100), nullable=True)
    numero_dipendenti = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    
    # Dati estratti con AI
    extracted_data = Column(JSON, nullable=True)
    documents_path = Column(String(500), nullable=True)  # Path OneDrive documenti
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)