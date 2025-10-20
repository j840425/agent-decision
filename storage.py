# storage.py
import json
from datetime import datetime
from models import UserProfile
from config import config
from google.cloud import storage as gcs
import os

class StorageManager:
    """Maneja la persistencia del perfil del usuario en Cloud Storage"""
    
    def __init__(self):
        self.bucket_name = config.STORAGE_BUCKET
        self.file_name = "user_profile.json"
        
        # Si estamos en local, usar JSON local
        if config.IS_LOCAL:
            self.local_mode = True
            self.local_path = config.USER_PROFILE_PATH
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.local_mode = False
            self.client = gcs.Client(project=config.GOOGLE_CLOUD_PROJECT)
            self.bucket = self.client.bucket(self.bucket_name)
            self.blob = self.bucket.blob(self.file_name)
    
    def profile_exists(self) -> bool:
        """Verifica si existe un perfil completo"""
        try:
            profile = self.load_profile()
            # Verificar si tiene AL MENOS UN campo completado (más flexible)
            has_data = (
                profile.edad is not None or
                profile.ocupacion is not None or
                profile.estado_civil is not None or
                len(profile.additional_context) > 0
            )
            return has_data
        except Exception:
            return False
    
    def load_profile(self) -> UserProfile:
        """Carga el perfil del usuario"""
        if self.local_mode:
            return self._load_local()
        else:
            return self._load_cloud()
    
    def _load_local(self) -> UserProfile:
        """Carga desde archivo local"""
        try:
            if not self.local_path.exists():
                return UserProfile()
            
            with open(self.local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'created_at' in data:
                    data['created_at'] = datetime.fromisoformat(data['created_at'])
                if 'updated_at' in data:
                    data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                return UserProfile(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            return UserProfile()
    
    def _load_cloud(self) -> UserProfile:
        """Carga desde Cloud Storage"""
        try:
            if not self.blob.exists():
                return UserProfile()
            
            content = self.blob.download_as_text()
            data = json.loads(content)
            
            if 'created_at' in data:
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'updated_at' in data:
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            
            return UserProfile(**data)
        except Exception as e:
            print(f"Error cargando desde Cloud Storage: {e}")
            return UserProfile()
    
    def save_profile(self, profile: UserProfile):
        """Guarda el perfil del usuario"""
        profile.updated_at = datetime.now()
        
        data = profile.model_dump()
        data['created_at'] = profile.created_at.isoformat()
        data['updated_at'] = profile.updated_at.isoformat()
        
        if self.local_mode:
            self._save_local(data)
        else:
            self._save_cloud(data)
    
    def _save_local(self, data: dict):
        """Guarda en archivo local"""
        with open(self.local_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_cloud(self, data: dict):
        """Guarda en Cloud Storage"""
        try:
            content = json.dumps(data, indent=2, ensure_ascii=False)
            self.blob.upload_from_string(content, content_type='application/json')
        except Exception as e:
            print(f"Error guardando en Cloud Storage: {e}")
    
    def update_field(self, field_name: str, value: any):
        """Actualiza un campo específico del perfil"""
        profile = self.load_profile()
        if hasattr(profile, field_name):
            setattr(profile, field_name, value)
            self.save_profile(profile)
        else:
            profile.additional_context[field_name] = value
            self.save_profile(profile)
    
    def clear_profile(self):
        """Borra el perfil actual"""
        self.save_profile(UserProfile())

# Instancia global
storage = StorageManager()