# -*- coding: utf-8 -*-
"""
Extractor de datos HTML para expedientes - Reemplazo de descarga de PDFs
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import time
import re

def extraer_datos_basicos_expediente(driver):
    """
    Extrae los datos básicos del expediente del HTML
    """
    datos_expediente = {
        'expediente': 'No disponible',
        'jurisdiccion': 'No disponible', 
        'dependencia': 'No disponible',
        'situacion_actual': 'No disponible',
        'caratula': 'No disponible'
    }
    
    try:
        print("📄 Extrayendo datos básicos del expediente...")
        
        # Esperar a que cargue el contenido principal
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ui-fieldset-content"))
        )
        
        # Obtener el HTML de la página
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Buscar el contenedor principal
        fieldset_content = soup.find('div', class_='ui-fieldset-content')
        
        if fieldset_content:
            # Extraer cada campo usando los labels
            labels_map = {
                'Expediente:': 'expediente',
                'Jurisdicción:': 'jurisdiccion', 
                'Dependencia:': 'dependencia',
                'Sit. Actual:': 'situacion_actual',
                'Carátula:': 'caratula'
            }
            
            for label_text, key in labels_map.items():
                try:
                    # Buscar el label
                    label = fieldset_content.find('label', string=label_text)
                    if label:
                        # Encontrar el contenedor padre y buscar el span con el valor
                        form_group = label.find_parent('div', class_='form-group')
                        if form_group:
                            # Buscar el span con el valor (puede tener diferentes clases)
                            value_span = form_group.find('span', style=lambda x: x and 'color:#000000' in x)
                            if not value_span:
                                value_span = form_group.find('span', class_='form_control')
                            
                            if value_span:
                                datos_expediente[key] = value_span.get_text(strip=True)
                                print(f"   ✅ {label_text} {datos_expediente[key]}")
                            else:
                                print(f"   ⚠️ No se encontró valor para {label_text}")
                        else:
                            print(f"   ⚠️ No se encontró form-group para {label_text}")
                    else:
                        print(f"   ⚠️ No se encontró label {label_text}")
                        
                except Exception as e:
                    print(f"   ❌ Error extrayendo {label_text}: {e}")
                    continue
        else:
            print("   ❌ No se encontró el contenedor ui-fieldset-content")
            
    except Exception as e:
        print(f"❌ Error general extrayendo datos básicos: {e}")
    
    return datos_expediente

def hacer_click_intervinientes_y_extraer(driver):
    """
    Hace clic en la pestaña Intervinientes y extrae los datos de la tabla
    """
    datos_intervinientes = {
        'actor_nombre': 'No disponible',
        'letrado_apoderado': 'No disponible',
        'tomo_folio': 'No disponible',
        'cuit_cuil': 'No disponible'
    }
    
    try:
        print("👥 Haciendo clic en pestaña Intervinientes...")
        
        # Buscar y hacer clic en la pestaña Intervinientes
        tab_intervinientes = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'rf-tab-lbl') and text()='Intervinientes']"))
        )
        
        driver.execute_script("arguments[0].click();", tab_intervinientes)
        print("   ✅ Clic en Intervinientes realizado")
        
        # Esperar a que cargue la tabla
        time.sleep(3)
        
        # Esperar a que aparezca la tabla de participantes
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//tbody[contains(@id, 'participantsTable')]"))
        )
        
        print("   📋 Tabla de participantes cargada, extrayendo datos...")
        
        # Obtener el HTML actualizado
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Buscar todas las tablas de participantes
        participant_tables = soup.find_all('tbody', id=lambda x: x and 'participantsTable' in x and ':tb' in x)
        
        for table in participant_tables:
            try:
                # Buscar la fila principal
                main_row = table.find('tr', class_='rf-dt-r')
                if main_row:
                    cells = main_row.find_all('td', class_='rf-dt-c')
                    
                    if len(cells) >= 2:
                        # Primera celda debería contener el tipo (ACTOR, DEMANDADO, etc.)
                        tipo_span = cells[0].find('span', class_='font-strong')
                        if tipo_span and 'ACTOR' in tipo_span.get_text(strip=True).upper():
                            
                            # Segunda celda contiene el nombre del actor
                            nombre_span = cells[1].find('span', class_='font-strong')
                            if nombre_span:
                                datos_intervinientes['actor_nombre'] = nombre_span.get_text(strip=True)
                                print(f"   ✅ Actor encontrado: {datos_intervinientes['actor_nombre']}")
                            
                            # Buscar la tabla anidada con los datos del letrado
                            nested_table = table.find('tbody', class_='rf-cst')
                            if nested_table:
                                letrado_row = nested_table.find('tr', class_='rf-cst-r')
                                if letrado_row:
                                    letrado_cells = letrado_row.find_all('td', class_='rf-cst-c')
                                    
                                    if len(letrado_cells) >= 4:
                                        # Verificar que la primera celda dice "LETRADO APODERADO"
                                        if 'LETRADO APODERADO' in letrado_cells[0].get_text(strip=True).upper():
                                            datos_intervinientes['letrado_apoderado'] = letrado_cells[1].get_text(strip=True)
                                            datos_intervinientes['tomo_folio'] = letrado_cells[2].get_text(strip=True)
                                            datos_intervinientes['cuit_cuil'] = letrado_cells[3].get_text(strip=True)
                                            
                                            print(f"   ✅ Letrado Apoderado: {datos_intervinientes['letrado_apoderado']}")
                                            print(f"   ✅ Tomo/Folio: {datos_intervinientes['tomo_folio']}")
                                            print(f"   ✅ CUIT/CUIL: {datos_intervinientes['cuit_cuil']}")
                                            
                                            break  # Salir del loop una vez encontrado el actor
                            
            except Exception as e:
                print(f"   ⚠️ Error procesando tabla de participante: {e}")
                continue
                
    except TimeoutException:
        print("   ❌ Timeout: No se pudo encontrar la pestaña Intervinientes")
    except Exception as e:
        print(f"   ❌ Error general en intervinientes: {e}")
    
    return datos_intervinientes

def combinar_datos_expediente(datos_basicos, datos_intervinientes):
    """
    Combina todos los datos extraídos en un solo diccionario
    """
    datos_completos = {
        **datos_basicos,
        **datos_intervinientes,
        'fecha_extraccion': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return datos_completos

def crear_prompt_para_ia(datos_expediente):
    """
    Crea el prompt para enviar a la IA con los datos extraídos
    """
    prompt = f"""
**Rol:** Eres un asistente legal experto especializado en análisis de expedientes judiciales argentinos.

**Tarea:** Analizar y limpiar los siguientes datos de un expediente judicial, devolviendo la información en formato JSON estructurado.

**Datos del Expediente:**
- Expediente: {datos_expediente.get('expediente', 'No disponible')}
- Jurisdicción: {datos_expediente.get('jurisdiccion', 'No disponible')}
- Dependencia: {datos_expediente.get('dependencia', 'No disponible')}
- Situación Actual: {datos_expediente.get('situacion_actual', 'No disponible')}
- Carátula: {datos_expediente.get('caratula', 'No disponible')}
- Actor: {datos_expediente.get('actor_nombre', 'No disponible')}
- Letrado Apoderado: {datos_expediente.get('letrado_apoderado', 'No disponible')}
- Tomo/Folio: {datos_expediente.get('tomo_folio', 'No disponible')}
- CUIT/CUIL: {datos_expediente.get('cuit_cuil', 'No disponible')}

**Instrucciones:**
1. Limpia y normaliza todos los datos
2. Extrae información relevante de la carátula (tipo de proceso, partes, etc.)
3. Identifica el tipo de juzgado y jurisdicción
4. Normaliza nombres y datos personales
5. Devuelve ÚNICAMENTE un JSON válido con la siguiente estructura:

{{
    "expediente_numero": "número limpio del expediente",
    "jurisdiccion_normalizada": "jurisdicción limpia",
    "juzgado": "nombre del juzgado normalizado",
    "secretaria": "secretaría si está disponible",
    "situacion_actual": "situación normalizada",
    "tipo_proceso": "tipo de proceso extraído de la carátula",
    "actor_principal": "nombre del actor principal limpio",
    "demandado_principal": "demandado extraído de la carátula",
    "objeto_demanda": "objeto de la demanda",
    "letrado_actor": "nombre del letrado limpio",
    "matricula_letrado": "tomo y folio del letrado",
    "cuit_cuil_letrado": "CUIT/CUIL del letrado limpio",
    "observaciones": "cualquier observación relevante"
}}

Responde ÚNICAMENTE con el JSON, sin texto adicional.
"""
    
    return prompt

def procesar_respuesta_ia_json(respuesta_ia):
    """
    Procesa la respuesta JSON de la IA y la valida
    """
    try:
        # Limpiar la respuesta por si tiene texto adicional
        respuesta_limpia = respuesta_ia.strip()
        
        # Buscar el JSON en la respuesta
        inicio_json = respuesta_limpia.find('{')
        fin_json = respuesta_limpia.rfind('}') + 1
        
        if inicio_json != -1 and fin_json != -1:
            json_str = respuesta_limpia[inicio_json:fin_json]
            datos_json = json.loads(json_str)
            
            print("✅ JSON procesado correctamente")
            return datos_json
        else:
            print("❌ No se encontró JSON válido en la respuesta")
            return None
            
    except json.JSONDecodeError as e:
        print(f"❌ Error decodificando JSON: {e}")
        print(f"Respuesta recibida: {respuesta_ia[:200]}...")
        return None
    except Exception as e:
        print(f"❌ Error procesando respuesta de IA: {e}")
        return None

def guardar_datos_en_excel_analizados(datos_json, numero_expediente, ano_expediente):
    """
    Guarda los datos JSON en el Excel de expedientes analizados
    """
    try:
        import pandas as pd
        import os
        from datetime import datetime
        
        archivo_salida = 'expedientes_analizados.xlsx'
        
        # Crear el registro para Excel
        registro = {
            'Número': numero_expediente,
            'Año': ano_expediente,
            'Expediente_Completo': datos_json.get('expediente_numero', ''),
            'Jurisdicción': datos_json.get('jurisdiccion_normalizada', ''),
            'Juzgado': datos_json.get('juzgado', ''),
            'Secretaría': datos_json.get('secretaria', ''),
            'Situación_Actual': datos_json.get('situacion_actual', ''),
            'Tipo_Proceso': datos_json.get('tipo_proceso', ''),
            'Actor_Principal': datos_json.get('actor_principal', ''),
            'Demandado_Principal': datos_json.get('demandado_principal', ''),
            'Objeto_Demanda': datos_json.get('objeto_demanda', ''),
            'Letrado_Actor': datos_json.get('letrado_actor', ''),
            'Matrícula_Letrado': datos_json.get('matricula_letrado', ''),
            'CUIT_CUIL_Letrado': datos_json.get('cuit_cuil_letrado', ''),
            'Observaciones': datos_json.get('observaciones', ''),
            'Estado_Análisis': 'Completado - Datos HTML',
            'Fecha_Procesamiento': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Crear DataFrame
        df_nuevo = pd.DataFrame([registro])
        
        # Verificar si el archivo existe
        if os.path.exists(archivo_salida):
            # Cargar datos existentes
            df_existente = pd.read_excel(archivo_salida)
            
            # Verificar duplicados
            expediente_completo = f"{numero_expediente}/{ano_expediente}"
            duplicado = df_existente[
                (df_existente['Número'].astype(str) == str(numero_expediente)) &
                (df_existente['Año'].astype(str) == str(ano_expediente))
            ]
            
            if not duplicado.empty:
                print(f"⚠️ Expediente {expediente_completo} ya existe, actualizando...")
                # Actualizar registro existente
                df_existente.loc[
                    (df_existente['Número'].astype(str) == str(numero_expediente)) &
                    (df_existente['Año'].astype(str) == str(ano_expediente))
                ] = registro
                df_final = df_existente
            else:
                # Agregar nuevo registro
                df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
        else:
            # Crear archivo nuevo
            df_final = df_nuevo
        
        # Guardar archivo
        df_final.to_excel(archivo_salida, index=False)
        print(f"✅ Datos guardados en {archivo_salida}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error guardando en Excel: {e}")
        return False
