# backend/app/services/client_data_extractor.py
import google.generativeai as genai
import os
import base64
import json
from typing import Dict, List, Optional
from PIL import Image
import io
import PyPDF2
import docx
from dotenv import load_dotenv

load_dotenv()
GEMINI_API = os.getenv("GEMINI_API_KEY")

class ClientDataExtractor:
    def __init__(self):
        genai.configure(api_key=GEMINI_API)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    async def extract_from_documents(self, files: List[Dict]) -> Dict:
        """
        Estrae dati cliente da una lista di documenti
        files: Lista di dict con {filename, content_bytes, content_type}
        """
        extracted_texts = []
        
        for file_info in files:
            try:
                text = await self._extract_text_from_file(
                    file_info['content_bytes'], 
                    file_info['content_type'],
                    file_info['filename']
                )
                if text:
                    extracted_texts.append(f"=== {file_info['filename']} ===\n{text}\n")
            except Exception as e:
                print(f"Errore estrazione {file_info['filename']}: {e}")
                continue
        
        if not extracted_texts:
            return {"error": "Nessun testo estratto dai documenti"}
        
        # Unisce tutti i testi estratti
        combined_text = "\n".join(extracted_texts)
        
        # Estrae i dati usando Gemini
        return await self._extract_client_data_with_ai(combined_text)
    
    async def _extract_text_from_file(self, content_bytes: bytes, content_type: str, filename: str) -> str:
        """Estrae testo da diversi tipi di file"""
        
        try:
            if content_type.startswith('image/'):
                return await self._extract_from_image(content_bytes)
            elif content_type == 'application/pdf':
                return self._extract_from_pdf(content_bytes)
            elif content_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
                return self._extract_from_docx(content_bytes)
            elif content_type.startswith('text/'):
                return content_bytes.decode('utf-8')
            else:
                print(f"Tipo file non supportato: {content_type}")
                return ""
        except Exception as e:
            print(f"Errore estrazione testo da {filename}: {e}")
            return ""
    
    async def _extract_from_image(self, content_bytes: bytes) -> str:
        """Estrae testo da immagine usando Gemini Vision"""
        try:
            # Converte l'immagine per Gemini
            image = Image.open(io.BytesIO(content_bytes))
            
            prompt = """
            Estrai tutto il testo visibile in questa immagine.
            Se contiene informazioni aziendali, concentrati su:
            - Ragione sociale
            - Partita IVA
            - Codice fiscale
            - Indirizzo
            - Telefono
            - Email
            - Rappresentante legale
            - Settore di attività
            
            Restituisci il testo estratto in modo strutturato.
            """
            
            response = self.model.generate_content([prompt, image])
            return response.text
            
        except Exception as e:
            print(f"Errore estrazione immagine: {e}")
            return ""
    
    def _extract_from_pdf(self, content_bytes: bytes) -> str:
        """Estrae testo da PDF"""
        try:
            pdf_file = io.BytesIO(content_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text
        except Exception as e:
            print(f"Errore estrazione PDF: {e}")
            return ""
    
    def _extract_from_docx(self, content_bytes: bytes) -> str:
        """Estrae testo da documento Word"""
        try:
            doc_file = io.BytesIO(content_bytes)
            doc = docx.Document(doc_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text
        except Exception as e:
            print(f"Errore estrazione DOCX: {e}")
            return ""
    
    async def _extract_client_data_with_ai(self, text: str) -> Dict:
        """Usa Gemini per estrarre dati strutturati dal testo"""
        
        prompt = f"""
        Analizza il seguente testo estratto da documenti aziendali e estrai le informazioni del cliente.
        
        TESTO DA ANALIZZARE:
        {text}
        
        Estrai le seguenti informazioni se presenti:
        - ragione_sociale (nome completo dell'azienda)
        - partita_iva (11 cifre)
        - codice_fiscale (16 caratteri per persone fisiche o 11 per aziende)
        - telefono
        - email
        - pec (email certificata)
        - indirizzo (via, numero civico)
        - citta
        - cap (5 cifre)
        - provincia (2 lettere)
        - rappresentante_legale (nome e cognome)
        - cf_rappresentante (codice fiscale del rappresentante)
        - settore_attivita
        - numero_dipendenti (solo numero)
        
        IMPORTANTE:
        - Restituisci SOLO un JSON valido
        - Se un campo non è presente, usa null
        - Non aggiungere testo prima o dopo il JSON
        - Verifica che partita_iva contenga solo numeri
        - Verifica che cap contenga solo numeri
        - Pulisci i dati da caratteri speciali non necessari
        
        Esempio formato risposta:
        {{
            "ragione_sociale": "AZIENDA ESEMPIO S.R.L.",
            "partita_iva": "12345678901",
            "codice_fiscale": "12345678901",
            "telefono": "080-1234567",
            "email": "info@esempio.it",
            "pec": "esempio@pec.it",
            "indirizzo": "Via Roma, 123",
            "citta": "Bari",
            "cap": "70100",
            "provincia": "BA",
            "rappresentante_legale": "Mario Rossi",
            "cf_rappresentante": "RSSMRA80A01F205X",
            "settore_attivita": "Servizi",
            "numero_dipendenti": 25
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            # Pulisce la risposta per ottenere solo il JSON
            response_text = response.text.strip()
            
            # Rimuove eventuali markdown code blocks
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            extracted_data = json.loads(response_text)
            
            # Validazione base
            validated_data = self._validate_extracted_data(extracted_data)
            
            return {
                "success": True,
                "data": validated_data,
                "raw_text": text[:1000] + "..." if len(text) > 1000 else text
            }
            
        except json.JSONDecodeError as e:
            print(f"Errore parsing JSON: {e}")
            print(f"Risposta AI: {response.text}")
            return {
                "success": False,
                "error": "Errore nel parsing dei dati estratti",
                "raw_response": response.text
            }
        except Exception as e:
            print(f"Errore estrazione AI: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_extracted_data(self, data: Dict) -> Dict:
        """Valida e pulisce i dati estratti"""
        
        validated = {}
        
        # Validazioni specifiche
        if data.get('partita_iva'):
            piva = str(data['partita_iva']).replace('-', '').replace(' ', '')
            if piva.isdigit() and len(piva) == 11:
                validated['partita_iva'] = piva
        
        if data.get('cap'):
            cap = str(data['cap']).replace('-', '').replace(' ', '')
            if cap.isdigit() and len(cap) == 5:
                validated['cap'] = cap
        
        if data.get('numero_dipendenti'):
            try:
                validated['numero_dipendenti'] = int(data['numero_dipendenti'])
            except (ValueError, TypeError):
                pass
        
        # Copia gli altri campi pulendoli
        string_fields = [
            'ragione_sociale', 'codice_fiscale', 'telefono', 'email', 'pec',
            'indirizzo', 'citta', 'provincia', 'rappresentante_legale',
            'cf_rappresentante', 'settore_attivita'
        ]
        
        for field in string_fields:
            if data.get(field) and str(data[field]).strip():
                validated[field] = str(data[field]).strip()
        
        return validated

# Istanza globale
client_extractor = ClientDataExtractor()