import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import httpx
from app.routers.websocket_manager import websocket_manager

# Configurazione logging
logger = logging.getLogger("onedrive_middleware")
logging.basicConfig(level=logging.INFO)

class OneDriveError(Exception):
    """Eccezione base per errori OneDrive"""
    def __init__(self, message: str, error_code: str = None, retry_after: int = None):
        self.message = message
        self.error_code = error_code
        self.retry_after = retry_after
        super().__init__(self.message)

class OneDriveAuthError(OneDriveError):
    """Errore di autenticazione OneDrive"""
    pass

class OneDriveQuotaError(OneDriveError):
    """Errore di quota OneDrive"""
    pass

class OneDriveRateLimitError(OneDriveError):
    """Errore di rate limiting OneDrive"""
    pass

class OneDriveFileNotFoundError(OneDriveError):
    """File non trovato su OneDrive"""
    pass

class OneDriveErrorHandler:
    """Gestione centralizzata degli errori OneDrive"""
    
    ERROR_MAPPING = {
        400: "Richiesta non valida",
        401: "Token di accesso non valido o scaduto",
        403: "Accesso negato - controllare i permessi",
        404: "File o cartella non trovato",
        409: "Conflitto - file già esistente",
        412: "Condizione prerequisito fallita",
        413: "File troppo grande",
        429: "Troppe richieste - limite raggiunto",
        500: "Errore interno di OneDrive",
        502: "OneDrive temporaneamente non disponibile",
        503: "Servizio OneDrive non disponibile",
        507: "Spazio di archiviazione insufficiente"
    }

    @staticmethod
    def parse_graph_error(response: httpx.Response) -> OneDriveError:
        """Analizza la risposta di errore di Microsoft Graph"""
        status_code = response.status_code
        
        try:
            error_data = response.json()
            error_info = error_data.get("error", {})
            error_code = error_info.get("code", "Unknown")
            error_message = error_info.get("message", OneDriveErrorHandler.ERROR_MAPPING.get(status_code, "Errore sconosciuto"))
        except:
            error_code = "ParseError"
            error_message = OneDriveErrorHandler.ERROR_MAPPING.get(status_code, f"Errore HTTP {status_code}")

        # Gestione retry-after per rate limiting
        retry_after = None
        if status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))

        # Crea eccezione specifica
        if status_code == 401:
            return OneDriveAuthError(error_message, error_code)
        elif status_code == 429:
            return OneDriveRateLimitError(error_message, error_code, retry_after)
        elif status_code == 507:
            return OneDriveQuotaError(error_message, error_code)
        elif status_code == 404:
            return OneDriveFileNotFoundError(error_message, error_code)
        else:
            return OneDriveError(error_message, error_code)

    @staticmethod
    async def send_error_notification(error: OneDriveError, context: str = ""):
        """Invia notifica di errore via WebSocket"""
        message = f"OneDrive {context}: {error.message}"
        try:
            await websocket_manager.send_notification(message)
        except:
            logger.error(f"Impossibile inviare notifica WebSocket: {message}")

class OneDriveRetryHandler:
    """Gestione retry automatici per OneDrive"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def execute_with_retry(self, 
                               operation: Callable, 
                               *args, 
                               context: str = "",
                               **kwargs) -> Any:
        """Esegue un'operazione con retry automatico"""
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await operation(*args, **kwargs)
                
            except OneDriveRateLimitError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = e.retry_after or (self.base_delay * (2 ** attempt))
                    logger.warning(f"Rate limit hit, retry in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                
            except OneDriveAuthError as e:
                # Non riprovare per errori di autenticazione
                logger.error(f"Authentication error in {context}: {e.message}")
                await OneDriveErrorHandler.send_error_notification(e, context)
                raise
                
            except OneDriveQuotaError as e:
                # Non riprovare per errori di quota
                logger.error(f"Quota error in {context}: {e.message}")
                await OneDriveErrorHandler.send_error_notification(e, context)
                raise
                
            except OneDriveError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"OneDrive error, retry in {delay}s (attempt {attempt + 1}): {e.message}")
                    await asyncio.sleep(delay)
                    continue
                    
            except Exception as e:
                # Errori generici
                last_exception = OneDriveError(f"Errore imprevisto: {str(e)}")
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Unexpected error, retry in {delay}s (attempt {attempt + 1}): {str(e)}")
                    await asyncio.sleep(delay)
                    continue
        
        # Tutti i retry falliti
        logger.error(f"All retries failed for {context}: {last_exception.message}")
        await OneDriveErrorHandler.send_error_notification(last_exception, context)
        raise last_exception

def onedrive_error_handler(context: str = ""):
    """Decoratore per gestione errori OneDrive"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as e:
                error = OneDriveErrorHandler.parse_graph_error(e.response)
                logger.error(f"OneDrive error in {context or func.__name__}: {error.message}")
                await OneDriveErrorHandler.send_error_notification(error, context or func.__name__)
                raise error
            except OneDriveError:
                # Rilancia errori OneDrive già gestiti
                raise
            except Exception as e:
                error = OneDriveError(f"Errore imprevisto: {str(e)}")
                logger.error(f"Unexpected error in {context or func.__name__}: {str(e)}")
                await OneDriveErrorHandler.send_error_notification(error, context or func.__name__)
                raise error
        return wrapper
    return decorator

def onedrive_retry(max_retries: int = 3, base_delay: float = 1.0, context: str = ""):
    """Decoratore per retry automatici OneDrive"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_handler = OneDriveRetryHandler(max_retries, base_delay)
            return await retry_handler.execute_with_retry(
                func, *args, context=context or func.__name__, **kwargs
            )
        return wrapper
    return decorator

class OneDriveHealthCheck:
    """Controllo dello stato di salute di OneDrive"""
    
    def __init__(self):
        self.last_check = None
        self.is_healthy = True
        self.last_error = None

    async def check_health(self, onedrive_service) -> Dict[str, Any]:
        """Verifica lo stato di OneDrive"""
        try:
            # Test semplice per verificare connettività
            token = await onedrive_service._get_access_token()
            drive_id = await onedrive_service._get_drive_id()
            
            self.last_check = datetime.now()
            self.is_healthy = True
            self.last_error = None
            
            return {
                "healthy": True,
                "last_check": self.last_check.isoformat(),
                "service": "OneDrive",
                "status": "operational"
            }
            
        except Exception as e:
            self.last_check = datetime.now()
            self.is_healthy = False
            self.last_error = str(e)
            
            return {
                "healthy": False,
                "last_check": self.last_check.isoformat(),
                "service": "OneDrive",
                "status": "error",
                "error": self.last_error
            }

# Istanza globale per health check
onedrive_health = OneDriveHealthCheck()

# Configurazione logging specifico per OneDrive
def setup_onedrive_logging():
    """Configura logging specifico per OneDrive"""
    onedrive_logger = logging.getLogger("onedrive_middleware")
    onedrive_logger.setLevel(logging.INFO)
    
    if not onedrive_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        onedrive_logger.addHandler(handler)
    
    return onedrive_logger

# Inizializza logging
setup_onedrive_logging()