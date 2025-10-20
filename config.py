# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Google Cloud
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    GOOGLE_CLOUD_REGION = os.getenv("GOOGLE_CLOUD_REGION")
    VERTEX_AI_MODEL = os.getenv("VERTEX_AI_MODEL")

    # Tavily API
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") 
    
    # Cloud Storage (para producción)
    STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", f"{GOOGLE_CLOUD_PROJECT}-decision-agent")
    
    # Detectar si estamos en local o en Cloud Run
    IS_LOCAL = os.getenv("K_SERVICE") is None
    
    # RUTA ABSOLUTA: Basada en la ubicación de config.py
    BASE_DIR = Path(__file__).resolve().parent  
    DATA_DIR = BASE_DIR / "data"  
    USER_PROFILE_PATH = DATA_DIR / "user_profile.json"
    
    MAX_TREE_DEPTH = int(os.getenv("MAX_TREE_DEPTH", "4"))
    
    # Crear directorio data si no existe (solo local)
    if IS_LOCAL:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # LLM Settings
    TEMPERATURE = 0.7
    MAX_OUTPUT_TOKENS = 8192

    AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.1"))
    AGENT_MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "3"))
    AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))
    
    # Google Search Grounding
    USE_GROUNDING = True
    
    @classmethod
    def validate(cls):
        """Valida que la configuración esté completa"""
        if not cls.GOOGLE_CLOUD_PROJECT:
            raise ValueError("GOOGLE_CLOUD_PROJECT no está configurado en .env")
        return True

config = Config()