#!/usr/bin/env python3
"""
Sistema Simple de Verificación de Licencias con Firebase
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
import hashlib
import platform
import uuid

class SimpleLicenseChecker:
    def __init__(self):
        self.db = None
        self.machine_id = self._get_machine_id()
        self._init_firebase()
    
    def _init_firebase(self):
        """Inicializa Firebase"""
        try:
            config_file = "firebase_config.json"
            
            if not os.path.exists(config_file):
                print(f"❌ Error: No se encontró {config_file}")
                return False
            
            if not firebase_admin._apps:
                cred = credentials.Certificate(config_file)
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            print("✅ Firebase conectado")
            return True
            
        except Exception as e:
            print(f"❌ Error conectando Firebase: {e}")
            return False
    
    def _get_machine_id(self):
        """Genera ID único de la máquina"""
        try:
            # Información del sistema
            system_info = f"{platform.node()}-{platform.machine()}-{platform.processor()}"
            
            # Crear hash único
            machine_id = hashlib.md5(system_info.encode()).hexdigest()[:12]
            return machine_id
            
        except:
            # Fallback
            return str(uuid.getnode())[:12]
    
    def check_license(self):
        """
        Verifica si la licencia es válida
        Returns: True si es válida, False si no
        """
        if not self.db:
            print("❌ Error: Firebase no disponible")
            return False
        
        try:
            # Buscar licencia para esta máquina
            licenses_ref = self.db.collection('licenses')
            query = licenses_ref.where('machine_id', '==', self.machine_id).where('active', '==', True)
            
            licenses = list(query.stream())
            
            if not licenses:
                print(f"❌ No se encontró licencia válida para esta máquina")
                print(f"   ID de máquina: {self.machine_id}")
                return False
            
            license_data = licenses[0].to_dict()
            
            print(f"✅ Licencia válida encontrada")
            print(f"   Usuario: {license_data.get('user_email', 'N/A')}")
            print(f"   ID Máquina: {self.machine_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error verificando licencia: {e}")
            return False
    
    def get_machine_id(self):
        """Retorna el ID de la máquina actual"""
        return self.machine_id

# Función simple para usar en el launcher
def verify_license():
    """
    Función simple para verificar licencia
    Returns: True si es válida, False si no
    """
    checker = SimpleLicenseChecker()
    return checker.check_license()

def get_current_machine_id():
    """
    Obtiene el ID de la máquina actual
    """
    checker = SimpleLicenseChecker()
    return checker.get_machine_id()

if __name__ == "__main__":
    print("🔐 VERIFICADOR SIMPLE DE LICENCIAS")
    print("=" * 50)
    
    checker = SimpleLicenseChecker()
    print(f"ID de esta máquina: {checker.get_machine_id()}")
    
    if checker.check_license():
        print("✅ Licencia válida - Acceso permitido")
    else:
        print("❌ Licencia inválida - Acceso denegado")
