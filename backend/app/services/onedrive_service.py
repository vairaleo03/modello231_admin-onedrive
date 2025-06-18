import os
import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import tempfile
from dotenv import load_dotenv

load_dotenv()

class OneDriveService:
    def __init__(self):
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET") 
        self.tenant_id = os.getenv("MICROSOFT_TENANT_ID")
        self.onedrive_user_email = os.getenv("ONEDRIVE_USER_EMAIL")
        
        if not all([self.client_id, self.client_secret, self.tenant_id, self.onedrive_user_email]):
            raise ValueError("❌ Configurazione Microsoft Graph incompleta nel file .env")
        
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self._access_token = None
        self._token_expires_at = None
        self._user_drive_id = None
        
        # NUOVO: Cache per cartelle già create
        self._folder_cache = {}

    async def _get_access_token(self) -> str:
        """Ottiene un nuovo access token usando Client Credentials Flow"""
        if self._access_token and self._token_expires_at and datetime.now() < self._token_expires_at:
            return self._access_token

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data)
            
            if response.status_code != 200:
                raise Exception(f"❌ Errore nell'ottenere token: {response.text}")
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # Buffer di 5 minuti
            
            print(f"✅ Token OneDrive ottenuto, scade alle: {self._token_expires_at}")
            return self._access_token

    async def _get_drive_id(self) -> str:
        """Ottiene l'ID del drive dell'utente OneDrive"""
        if self._user_drive_id:
            return self._user_drive_id

        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Prima otteniamo l'ID utente
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                f"{self.base_url}/users/{self.onedrive_user_email}",
                headers=headers
            )
            
            if user_response.status_code != 200:
                raise Exception(f"❌ Errore nel trovare utente: {user_response.text}")
            
            user_data = user_response.json()
            user_id = user_data["id"]
            
            # Poi otteniamo il drive
            drive_response = await client.get(
                f"{self.base_url}/users/{user_id}/drive",
                headers=headers
            )
            
            if drive_response.status_code != 200:
                raise Exception(f"❌ Errore nell'ottenere drive: {drive_response.text}")
            
            drive_data = drive_response.json()
            self._user_drive_id = drive_data["id"]
            
            print(f"✅ Drive OneDrive trovato: {self._user_drive_id}")
            return self._user_drive_id

    async def _ensure_folder_exists(self, folder_path: str) -> str:
        """
        Crea la struttura di cartelle se non esiste e restituisce l'ID dell'ultima cartella.
        MIGLIORATO: Usa cache per evitare creazioni duplicate
        """
        # Controlla cache
        if folder_path in self._folder_cache:
            print(f"✅ Cartella trovata in cache: {folder_path}")
            return self._folder_cache[folder_path]

        token = await self._get_access_token()
        drive_id = await self._get_drive_id()
        headers = {"Authorization": f"Bearer {token}"}

        # Parti del percorso (es: "Modello231/Cliente_XYZ/Audio/2025/01-Gennaio")
        path_parts = folder_path.strip("/").split("/")
        current_parent_id = None  # None significa root del drive
        current_path = ""
        
        async with httpx.AsyncClient() as client:
            for i, folder_name in enumerate(path_parts):
                current_path = "/".join(path_parts[:i+1])
                
                # Controlla cache per percorso parziale
                if current_path in self._folder_cache:
                    current_parent_id = self._folder_cache[current_path]
                    continue
                
                # Cerca se la cartella esiste già
                if current_parent_id:
                    search_url = f"{self.base_url}/drives/{drive_id}/items/{current_parent_id}/children"
                else:
                    search_url = f"{self.base_url}/drives/{drive_id}/root/children"
                
                params = {"$filter": f"name eq '{folder_name}' and folder ne null"}
                response = await client.get(search_url, headers=headers, params=params)
                
                if response.status_code == 200:
                    items = response.json().get("value", [])
                    if items:
                        # Cartella esiste già
                        current_parent_id = items[0]["id"]
                        self._folder_cache[current_path] = current_parent_id
                        print(f"✅ Cartella esistente trovata: {folder_name}")
                        continue
                
                # Cartella non esiste, creala
                print(f"📁 Creazione cartella: {folder_name}")
                create_data = {
                    "name": folder_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "replace"  # Evita conflitti
                }
                
                if current_parent_id:
                    create_url = f"{self.base_url}/drives/{drive_id}/items/{current_parent_id}/children"
                else:
                    create_url = f"{self.base_url}/drives/{drive_id}/root/children"
                
                create_response = await client.post(
                    create_url,
                    headers={**headers, "Content-Type": "application/json"},
                    json=create_data
                )
                
                if create_response.status_code not in [200, 201]:
                    raise Exception(f"❌ Errore nella creazione cartella {folder_name}: {create_response.text}")
                
                created_folder = create_response.json()
                current_parent_id = created_folder["id"]
                
                # Salva in cache
                self._folder_cache[current_path] = current_parent_id
                print(f"✅ Cartella creata: {folder_name}")
        
        # Salva il percorso completo in cache
        self._folder_cache[folder_path] = current_parent_id
        return current_parent_id

    def _generate_folder_path(self, file_type: str, cliente_info: Optional[Dict] = None) -> str:
        """
        MIGLIORATO: Genera il percorso della cartella basato su cliente, tipo e data
        
        Args:
            file_type: Tipo di file ('audio', 'trascrizione', 'verbale', 'documento')
            cliente_info: Dict con informazioni cliente (es: {'nome': 'Azienda XYZ', 'id': 123})
        
        Returns:
            Percorso cartella formato: Modello231/[Cliente]/Tipo/Anno/Mese
        """
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m-%B")  # es: "01-Gennaio"
        
        type_mapping = {
            "audio": "Audio",
            "trascrizione": "Trascrizioni", 
            "verbale": "Verbali",
            "documento": "Documenti"
        }
        
        folder_type = type_mapping.get(file_type, "Altri")
        
        # NUOVO: Struttura con cliente
        if cliente_info:
            cliente_nome = cliente_info.get('nome', 'Cliente_Sconosciuto')
            # Sanitizza il nome cliente per filesystem
            cliente_nome_safe = "".join(c for c in cliente_nome if c.isalnum() or c in (' ', '-', '_')).strip()
            cliente_nome_safe = cliente_nome_safe.replace(' ', '_')
            
            return f"Modello231/{cliente_nome_safe}/{folder_type}/{year}/{month}"
        else:
            # Struttura senza cliente (per retrocompatibilità)
            return f"Modello231/{folder_type}/{year}/{month}"

    async def upload_file(self, 
                         file_content: bytes, 
                         filename: str, 
                         file_type: str = "documento",
                         cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        MIGLIORATO: Carica un file su OneDrive con supporto per cliente
        
        Args:
            file_content: Contenuto del file in bytes
            filename: Nome del file
            file_type: Tipo di file ('audio', 'trascrizione', 'verbale', 'documento')
            cliente_info: Dict con informazioni cliente opzionali
        
        Returns:
            Dict con informazioni del file caricato
        """
        try:
            token = await self._get_access_token()
            drive_id = await self._get_drive_id()
            headers = {"Authorization": f"Bearer {token}"}

            # Genera percorso cartella con supporto cliente
            folder_path = self._generate_folder_path(file_type, cliente_info)
            folder_id = await self._ensure_folder_exists(folder_path)

            # Upload del file
            upload_url = f"{self.base_url}/drives/{drive_id}/items/{folder_id}:/{filename}:/content"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.put(
                    upload_url,
                    headers={**headers, "Content-Type": "application/octet-stream"},
                    content=file_content
                )
                
                if response.status_code not in [200, 201]:
                    raise Exception(f"❌ Errore upload: {response.text}")
                
                file_data = response.json()
                
                return {
                    "success": True,
                    "file_id": file_data["id"],
                    "name": file_data["name"],
                    "size": file_data["size"],
                    "web_url": file_data.get("webUrl"),
                    "folder_path": folder_path,
                    "created_datetime": file_data["createdDateTime"],
                    "cliente_info": cliente_info  # NUOVO: Info cliente utilizzate
                }
                
        except Exception as e:
            print(f"❌ Errore OneDrive upload: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def upload_from_path(self, 
                              file_path: str, 
                              file_type: str = "documento",
                              cliente_info: Optional[Dict] = None) -> Dict[str, Any]:
        """MIGLIORATO: Carica un file dal percorso locale con supporto cliente"""
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            filename = Path(file_path).name
            return await self.upload_file(file_content, filename, file_type, cliente_info)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore nella lettura file: {str(e)}"
            }

    async def create_shareable_link(self, file_id: str, permission_type: str = "view") -> Optional[str]:
        """Crea un link condivisibile per il file"""
        try:
            token = await self._get_access_token()
            drive_id = await self._get_drive_id()
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            create_link_data = {
                "type": permission_type,  # "view" o "edit"
                "scope": "organization"  # Solo la tua organizzazione
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/drives/{drive_id}/items/{file_id}/createLink",
                    headers=headers,
                    json=create_link_data
                )
                
                if response.status_code == 200:
                    link_data = response.json()
                    return link_data.get("link", {}).get("webUrl")
                    
        except Exception as e:
            print(f"❌ Errore creazione link: {str(e)}")
            
        return None

    # NUOVO: Metodi per gestione cache
    def clear_folder_cache(self):
        """Pulisce la cache delle cartelle"""
        self._folder_cache.clear()
        print("🗑️ Cache cartelle OneDrive pulita")

    def get_folder_cache_info(self) -> Dict[str, str]:
        """Restituisce informazioni sulla cache delle cartelle"""
        return self._folder_cache.copy()

    # NUOVO: Metodo per ottenere struttura cliente standardizzata
    def format_cliente_info(self, ragione_sociale: str, cliente_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Formatta le informazioni del cliente per l'uso con OneDrive
        
        Args:
            ragione_sociale: Nome/ragione sociale del cliente
            cliente_id: ID del cliente (opzionale)
            
        Returns:
            Dict con informazioni formattate
        """
        return {
            "nome": ragione_sociale,
            "id": cliente_id,
            "timestamp": datetime.now().isoformat()
        }

# Istanza globale del servizio
onedrive_service = OneDriveService()