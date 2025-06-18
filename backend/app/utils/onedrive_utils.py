import io
import os
import tempfile
from typing import Dict, Any, Optional, Union
from docx import Document
from datetime import datetime
from app.services.onedrive_service import onedrive_service

class OneDriveFileManager:
    """MIGLIORATO: Gestisce l'upload di vari tipi di file su OneDrive con supporto cliente"""
    
    @staticmethod
    async def upload_word_document(doc: Document, 
                                  base_filename: str, 
                                  file_type: str = "documento",
                                  cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        MIGLIORATO: Carica un documento Word su OneDrive con supporto cliente
        
        Args:
            doc: Documento Word (docx.Document)
            base_filename: Nome base del file (senza estensione)
            file_type: Tipo di file ('trascrizione', 'verbale', 'documento')
            cliente_info: Informazioni cliente opzionali
        
        Returns:
            Risultato dell'upload
        """
        try:
            # Crea un file temporaneo in memoria
            file_stream = io.BytesIO()
            doc.save(file_stream)
            file_stream.seek(0)
            
            # Genera nome file unico con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base_filename}_{timestamp}.docx"
            
            # Upload su OneDrive con supporto cliente
            result = await onedrive_service.upload_file(
                file_content=file_stream.getvalue(),
                filename=filename,
                file_type=file_type,
                cliente_info=cliente_info
            )
            
            file_stream.close()
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore upload documento Word: {str(e)}"
            }

    @staticmethod
    async def upload_audio_file(audio_data: bytes, 
                               original_filename: str,
                               cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        MIGLIORATO: Carica un file audio su OneDrive con supporto cliente
        
        Args:
            audio_data: Dati audio in bytes
            original_filename: Nome originale del file
            cliente_info: Informazioni cliente opzionali
        
        Returns:
            Risultato dell'upload
        """
        try:
            # Genera nome file unico mantenendo estensione originale
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_without_ext = os.path.splitext(original_filename)[0]
            extension = os.path.splitext(original_filename)[1]
            filename = f"{name_without_ext}_{timestamp}{extension}"
            
            result = await onedrive_service.upload_file(
                file_content=audio_data,
                filename=filename,
                file_type="audio",
                cliente_info=cliente_info
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore upload file audio: {str(e)}"
            }

    @staticmethod
    async def upload_transcription_docx(doc: Document, 
                                       transcript_id: int,
                                       cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """MIGLIORATO: Carica una trascrizione come documento Word con supporto cliente"""
        filename = f"trascrizione_{transcript_id}"
        return await OneDriveFileManager.upload_word_document(
            doc, filename, "trascrizione", cliente_info
        )

    @staticmethod
    async def upload_verbale_docx(doc_path: str, 
                                 summary_id: int,
                                 cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        MIGLIORATO: Carica un verbale su OneDrive dal percorso temporaneo con supporto cliente
        
        Args:
            doc_path: Percorso del file docx temporaneo
            summary_id: ID del riassunto/verbale
            cliente_info: Informazioni cliente opzionali
        
        Returns:
            Risultato dell'upload
        """
        try:
            with open(doc_path, "rb") as f:
                file_content = f.read()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"verbale_odv_{summary_id}_{timestamp}.docx"
            
            result = await onedrive_service.upload_file(
                file_content=file_content,
                filename=filename,
                file_type="verbale",
                cliente_info=cliente_info
            )
            
            # Rimuovi il file temporaneo
            try:
                os.remove(doc_path)
            except:
                pass
                
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore upload verbale: {str(e)}"
            }

    @staticmethod
    async def upload_text_as_docx(text_content: str, 
                                 filename: str, 
                                 file_type: str = "documento",
                                 cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        MIGLIORATO: Converte testo in documento Word e lo carica su OneDrive con supporto cliente
        
        Args:
            text_content: Contenuto testuale
            filename: Nome base del file
            file_type: Tipo di file
            cliente_info: Informazioni cliente opzionali
        
        Returns:
            Risultato dell'upload
        """
        try:
            # Crea documento Word dal testo
            doc = Document()
            
            # Aggiungi il testo diviso in paragrafi
            paragraphs = text_content.split('\n')
            for paragraph_text in paragraphs:
                if paragraph_text.strip():
                    doc.add_paragraph(paragraph_text.strip())
            
            return await OneDriveFileManager.upload_word_document(
                doc, filename, file_type, cliente_info
            )
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore conversione testo: {str(e)}"
            }

class OneDriveIntegration:
    """MIGLIORATO: Classe principale per l'integrazione OneDrive nell'app con supporto cliente"""
    
    @staticmethod
    async def save_transcription_to_onedrive(transcript_text: str, 
                                           transcript_id: int,
                                           cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """MIGLIORATO: Salva una trascrizione su OneDrive con supporto cliente"""
        return await OneDriveFileManager.upload_text_as_docx(
            text_content=transcript_text,
            filename=f"trascrizione_{transcript_id}",
            file_type="trascrizione",
            cliente_info=cliente_info
        )
    
    @staticmethod
    async def save_document_to_onedrive(
        file_content: bytes, 
        filename: str,
        cliente_info: Optional[Dict] = None,
        document_type: str = "documento"
    ) -> Dict[str, Any]:
        """
        Salva un documento generico su OneDrive
        Wrapper semplificato per documenti clienti
        """
        return await OneDriveClientManager.save_document_to_onedrive(
            file_content, filename, cliente_info, document_type
        )
    
    @staticmethod
    async def save_summary_to_onedrive(summary_text: str, 
                                     summary_id: int,
                                     cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """MIGLIORATO: Salva un riassunto/verbale su OneDrive con supporto cliente"""
        return await OneDriveFileManager.upload_text_as_docx(
            text_content=summary_text,
            filename=f"verbale_odv_{summary_id}",
            file_type="verbale",
            cliente_info=cliente_info
        )
    
    @staticmethod
    async def save_audio_to_onedrive(audio_data: bytes, 
                                   filename: str,
                                   cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """MIGLIORATO: Salva un file audio su OneDrive con supporto cliente"""
        return await OneDriveFileManager.upload_audio_file(
            audio_data, filename, cliente_info
        )
    
    @staticmethod
    async def create_file_link(file_id: str) -> Optional[str]:
        """Crea un link condivisibile per un file"""
        return await onedrive_service.create_shareable_link(file_id, "view")

    # NUOVO: Metodi per gestione cliente
    @staticmethod
    def create_cliente_info(ragione_sociale: str, cliente_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Crea dizionario informazioni cliente standardizzato
        
        Args:
            ragione_sociale: Nome/ragione sociale del cliente
            cliente_id: ID del cliente opzionale
            
        Returns:
            Dict con informazioni cliente formattate
        """
        return onedrive_service.format_cliente_info(ragione_sociale, cliente_id)

    @staticmethod
    async def get_folder_structure_info() -> Dict[str, Any]:
        """
        Restituisce informazioni sulla struttura cartelle OneDrive
        
        Returns:
            Dict con informazioni su cache e struttura
        """
        return {
            "cache_info": onedrive_service.get_folder_cache_info(),
            "cache_size": len(onedrive_service.get_folder_cache_info()),
            "base_structure": "Modello231/{Cliente}/{Tipo}/{Anno}/{Mese}"
        }

    @staticmethod
    async def clear_folder_cache():
        """Pulisce la cache delle cartelle OneDrive"""
        onedrive_service.clear_folder_cache()

# NUOVO: Classe helper per gestione clienti
class ClienteHelper:
    """Helper per la gestione delle informazioni cliente nell'integrazione OneDrive"""
    
    @staticmethod
    def extract_from_session(session_data: Dict) -> Optional[Dict]:
        """
        Estrae informazioni cliente dalla sessione utente
        
        Args:
            session_data: Dati di sessione dell'utente
            
        Returns:
            Dict con informazioni cliente o None
        """
        # Placeholder per futura implementazione con dati sessione reali
        cliente_id = session_data.get("cliente_id")
        ragione_sociale = session_data.get("ragione_sociale")
        
        if ragione_sociale:
            return OneDriveIntegration.create_cliente_info(ragione_sociale, cliente_id)
        
        return None
    
    @staticmethod
    def extract_from_filename(filename: str) -> Optional[Dict]:
        """
        Tenta di estrarre informazioni cliente dal nome file
        
        Args:
            filename: Nome del file
            
        Returns:
            Dict con informazioni cliente o None
        """
        # Logica per estrarre cliente dal filename se contiene pattern specifici
        # Es: "cliente_xyz_audio.mp3" -> {"nome": "Cliente_XYZ"}
        
        if "_" in filename:
            parts = filename.split("_")
            if len(parts) >= 2 and parts[0].lower() == "cliente":
                return OneDriveIntegration.create_cliente_info(f"Cliente_{parts[1].title()}")
        
        return None

class OneDriveClientManager:
    """Gestione specializzata documenti clienti su OneDrive"""
    
    @staticmethod
    async def save_document_to_onedrive(
        file_content: bytes, 
        filename: str,
        cliente_info: Dict,
        document_type: str = "documento"
    ) -> Dict[str, Any]:
        """
        Salva un documento cliente su OneDrive con struttura ottimizzata
        
        Args:
            file_content: Contenuto del file
            filename: Nome del file
            cliente_info: Dict con info cliente
            document_type: Tipo documento ('documento', 'contratto', 'certificato', etc.)
        """
        try:
            # Genera percorso specifico per documenti cliente
            folder_path = OneDriveClientManager._generate_client_document_path(
                cliente_info, document_type
            )
            
            result = await onedrive_service.upload_file(
                file_content=file_content,
                filename=filename,
                file_type="documento",
                cliente_info=cliente_info
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "file_id": result["file_id"],
                    "name": result["name"],
                    "size": result["size"],
                    "folder_path": result["folder_path"],
                    "web_url": result.get("web_url"),
                    "document_type": document_type
                }
            else:
                return result
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore salvataggio documento: {str(e)}"
            }
    
    @staticmethod
    def _generate_client_document_path(cliente_info: Dict, document_type: str) -> str:
        """
        Genera percorso ottimizzato per documenti cliente
        Struttura: Modello231/Clienti/{RagioneSociale}/Documenti/{TipoDocumento}
        """
        from datetime import datetime
        
        ragione_sociale = cliente_info.get('nome', 'Cliente_Sconosciuto')
        ragione_sociale_safe = "".join(c for c in ragione_sociale if c.isalnum() or c in (' ', '-', '_')).strip()
        ragione_sociale_safe = ragione_sociale_safe.replace(' ', '_')
        
        # Mappa tipi documento
        type_mapping = {
            "documento": "Documenti_Generali",
            "contratto": "Contratti",
            "certificato": "Certificati",
            "fattura": "Fatture",
            "privacy": "Privacy_GDPR",
            "sicurezza": "Sicurezza_Lavoro",
            "anagrafica": "Anagrafica",
            "altro": "Altri_Documenti"
        }
        
        folder_type = type_mapping.get(document_type.lower(), "Documenti_Generali")
        year = datetime.now().strftime("%Y")
        
        return f"Modello231/Clienti/{ragione_sociale_safe}/Documenti/{folder_type}/{year}"
    
    @staticmethod
    async def get_client_documents(cliente_info: Dict) -> Dict[str, Any]:
        """Recupera lista documenti di un cliente da OneDrive"""
        try:
            # Implementazione futura per recuperare lista files
            # Per ora restituisce info struttura
            ragione_sociale = cliente_info.get('nome', 'Cliente_Sconosciuto')
            ragione_sociale_safe = ragione_sociale.replace(' ', '_')
            
            base_path = f"Modello231/Clienti/{ragione_sociale_safe}/Documenti"
            
            return {
                "success": True,
                "client": ragione_sociale,
                "base_path": base_path,
                "message": "Struttura cartelle preparata per il cliente"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore recupero documenti: {str(e)}"
            }

# Istanza globale per facilitare l'uso
onedrive_integration = OneDriveIntegration()