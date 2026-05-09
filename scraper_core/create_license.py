#!/usr/bin/env python3
"""
Script para crear licencias en Firebase (solo para administradores)
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os

def create_license(machine_id, user_email):
    """
    Crea una licencia en Firebase
    
    Args:
        machine_id (str): ID de la máquina
        user_email (str): Email del usuario
    """
    try:
        # Inicializar Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase_config.json")
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        # Crear documento de licencia
        license_data = {
            'machine_id': machine_id,
            'user_email': user_email,
            'active': True,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # Guardar en Firebase
        doc_ref = db.collection('licenses').add(license_data)
        
        print(f"✅ Licencia creada exitosamente")
        print(f"   ID Máquina: {machine_id}")
        print(f"   Usuario: {user_email}")
        print(f"   ID Documento: {doc_ref[1].id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando licencia: {e}")
        return False

def main():
    """Función principal"""
    print("🔧 CREADOR DE LICENCIAS")
    print("=" * 40)
    
    if not os.path.exists("firebase_config.json"):
        print("❌ Error: No se encontró firebase_config.json")
        return
    
    print("Ingrese los datos para crear la licencia:")
    
    machine_id = input("🔑 ID de máquina: ").strip()
    if not machine_id:
        print("❌ Error: ID de máquina requerido")
        return
    
    user_email = input("📧 Email del usuario: ").strip()
    if not user_email:
        print("❌ Error: Email requerido")
        return
    
    if create_license(machine_id, user_email):
        print("\n🎉 ¡Licencia creada correctamente!")
    else:
        print("\n❌ Error creando la licencia")

if __name__ == "__main__":
    main()
