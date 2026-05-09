#!/usr/bin/env python3
"""
Launcher Simple con Verificación de Licencias
"""

import sys
import subprocess
import importlib.util
import os
from simple_license_checker import verify_license, get_current_machine_id

def check_python_version():
    """Verifica que la versión de Python sea compatible"""
    if sys.version_info < (3, 7):
        print("❌ Error: Se requiere Python 3.7 o superior")
        print(f"   Versión actual: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} - Compatible")
    return True

def check_and_install_dependencies():
    """Verifica e instala las dependencias necesarias"""
    dependencies = [
        ('selenium', 'selenium'),
        ('webdriver_manager', 'webdriver-manager'),
        ('pandas', 'pandas'),
        ('openpyxl', 'openpyxl'),
        ('bs4', 'beautifulsoup4'),
        ('requests', 'requests'),
        ('google.generativeai', 'google-generativeai'),
        ('pdfplumber', 'pdfplumber'),
        ('PIL', 'Pillow'),
        ('pytesseract', 'pytesseract'),
        ('tkinter', None),  # tkinter viene con Python
        ('firebase_admin', 'firebase-admin'),  # Para licencias
    ]
    
    missing_deps = []
    
    print("🔍 Verificando dependencias...")
    
    for module_name, pip_name in dependencies:
        if module_name == 'tkinter':
            try:
                import tkinter
                print(f"   ✅ {module_name} - Disponible")
            except ImportError:
                print(f"   ❌ {module_name} - No disponible")
                missing_deps.append(('tkinter', None))
        else:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                print(f"   ❌ {module_name} - No instalado")
                missing_deps.append((module_name, pip_name))
            else:
                print(f"   ✅ {module_name} - Instalado")
    
    # Instalar dependencias faltantes
    if missing_deps:
        print(f"\n📦 Instalando {len(missing_deps)} dependencias faltantes...")
        
        for module_name, pip_name in missing_deps:
            if pip_name:
                try:
                    print(f"   📥 Instalando {pip_name}...")
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", pip_name
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"   ✅ {pip_name} instalado correctamente")
                except subprocess.CalledProcessError as e:
                    print(f"   ❌ Error instalando {pip_name}: {e}")
                    return False
            else:
                print(f"   ⚠️ {module_name} requiere instalación manual")
        
        print("✅ Todas las dependencias han sido instaladas")
    else:
        print("✅ Todas las dependencias están disponibles")
    
    return True

def check_firebase_config():
    """Verifica que existe la configuración de Firebase"""
    config_file = "firebase_config.json"
    
    if not os.path.exists(config_file):
        print(f"\n❌ Error: No se encontró {config_file}")
        print("💡 Para configurar Firebase:")
        print("   1. Ve a https://console.firebase.google.com/")
        print("   2. Crea un proyecto")
        print("   3. Ve a Configuración → Cuentas de servicio")
        print("   4. Genera una clave privada")
        print("   5. Descarga el JSON y renómbralo a 'firebase_config.json'")
        return False
    
    print(f"✅ Configuración Firebase encontrada")
    return True

def launch_gui():
    """Lanza la interfaz gráfica"""
    print("\n🚀 Iniciando interfaz gráfica...")
    
    try:
        from interfaz_scraper_ia import main
        main()
        
    except ImportError as e:
        print(f"❌ Error importando la interfaz: {e}")
        return False
    except Exception as e:
        print(f"❌ Error ejecutando la interfaz: {e}")
        return False
    
    return True

def main():
    """Función principal del launcher"""
    print("🔍 LAUNCHER - Scraper de Expedientes con Licencia")
    print("=" * 70)
    
    
    print("\n🔐 VERIFICANDO LICENCIA...")
    print("=" * 50)
    
    # Mostrar ID de máquina
    machine_id = get_current_machine_id()
    print(f"🔑 ID de esta máquina: {machine_id}")
    
    # Verificar licencia
    if verify_license():
        print("✅ LICENCIA VÁLIDA - Acceso permitido")
        print("=" * 50)
        
        # Lanzar aplicación
        if not launch_gui():
            print("\n❌ Error: No se pudo iniciar la interfaz gráfica")
            return
        
    else:
        print("❌ LICENCIA INVÁLIDA - Acceso denegado")
        print("=" * 50)
        print("💡 Contacte al administrador para obtener una licencia")
        print(f"   Proporcione este ID de máquina: {machine_id}")
        return
    
    print("\n👋 ¡Gracias por usar el Scraper de Expedientes!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
