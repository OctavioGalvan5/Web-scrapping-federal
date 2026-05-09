import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from datetime import datetime, timedelta
import google.generativeai as genai
from bs4 import BeautifulSoup
import pdfplumber
import os
from dias_habiles_calculator import calcular_fecha_vencimiento
from solve_recaptcha import solve_recaptcha

def descargar_y_extraer_pdf(url_pdf):
    """Función que funciona correctamente para descargar y extraer PDFs"""
    nombre_pdf = "temp_document.pdf"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        resp = requests.get(url_pdf, headers=headers, timeout=60, stream=True)
        resp.raise_for_status()
        with open(nombre_pdf, 'wb') as f:
             for chunk in resp.iter_content(chunk_size=8192):
                 f.write(chunk)
        print(f"PDF descargado: {url_pdf}")
        texto_completo_pdf = ''
        
        try:
            with pdfplumber.open(nombre_pdf) as pdf:
                print(f"  Procesando {len(pdf.pages)} páginas del PDF...")
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        texto_completo_pdf += page_text + "\n"

            if texto_completo_pdf.strip():
                print(f"  ✅ Texto extraído exitosamente del PDF")
                return texto_completo_pdf
            else:
                 print(f"  ⚠️ PDF {url_pdf} no contenía texto extraíble.")
        except Exception as pdf_e:
            print(f"  ❌ Error procesando el PDF '{nombre_pdf}' con pdfplumber: {pdf_e}")
    except requests.exceptions.RequestException as req_e:
        print(f"❌ Error descargando PDF desde {url_pdf}: {req_e}")
    except Exception as e:
        print(f"❌ Error general en descargar_y_extraer_pdf para {url_pdf}: {e}")
    finally:
        if os.path.exists(nombre_pdf):
            try:
                os.remove(nombre_pdf)
            except Exception as del_e:
                print(f"Error eliminando archivo temporal '{nombre_pdf}': {del_e}")

def extraer_info_pagina(driver, tabla_id, textos_extraidos):
    """
    Extrae información de una página específica de actuaciones
    """
    try:
        tabla = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, tabla_id))
        )
        
        filas = tabla.find_elements(By.TAG_NAME, "tr")
        
        for fila in filas[1:]:  # Saltar header
            try:
                celdas = fila.find_elements(By.TAG_NAME, "td")
                if len(celdas) >= 4:
                    fecha = celdas[0].text.strip()
                    tipo = celdas[1].text.strip()
                    descripcion = celdas[2].text.strip()
                    
                    # Buscar enlaces de PDF
                    enlaces_pdf = celdas[3].find_elements(By.CSS_SELECTOR, "a[href*='.pdf']")
                    
                    for enlace in enlaces_pdf:
                        href = enlace.get_attribute("href")
                        if href and ".pdf" in href:
                            print(f"Descargando PDF: {href}")
                            texto_pdf = descargar_y_extraer_pdf(href)
                            if texto_pdf:
                                textos_extraidos.append({
                                    'fecha': fecha,
                                    'tipo': tipo,
                                    'descripcion': descripcion,
                                    'texto_pdf': texto_pdf,
                                    'url_pdf': href
                                })
                                
            except Exception as e:
                print(f"Error procesando fila: {e}")
                continue
                
    except Exception as e:
        print(f"Error extrayendo información de página: {e}")

def procesar_expediente_con_paginacion(driver, numero_expediente, año):
    """
    Procesa un expediente extrayendo información de todas las páginas disponibles
    """
    textos_extraidos = []
    
    try:
        print("Extrayendo actuaciones recientes...")
        extraer_info_pagina(driver, "expediente:action-table", textos_extraidos)
        
        # Paginación de actuaciones recientes
        pagina_actual = 1
        tabla_reciente = None
        
        try:
            tabla_reciente = driver.find_element(By.ID, "expediente:action-table")
        except:
            pass

        while tabla_reciente:
            try:
                paginador = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.pagination"))
                )
                siguiente_li = paginador.find_element(By.CSS_SELECTOR, "li.active + li:not(.disabled)")
                siguiente_link = siguiente_li.find_element(By.TAG_NAME, "a")
                pagina_actual += 1
                print(f"Navegando a página {pagina_actual} de recientes...")
                
                driver.execute_script("arguments[0].click();", siguiente_link)
                WebDriverWait(driver, 15).until(EC.staleness_of(tabla_reciente))
                WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located((By.ID, "expediente:action-table"))
                )
                time.sleep(2)
                
                extraer_info_pagina(driver, "expediente:action-table", textos_extraidos)
                tabla_reciente = driver.find_element(By.ID, "expediente:action-table")
                
            except Exception:
                print("Fin de paginación reciente.")
                break

        try:
            print("Intentando acceder a actuaciones históricas...")
            hist_btn_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#expediente\\:btnActuacionesHistoricas > a"))
            )
            driver.execute_script("arguments[0].click();", hist_btn_link)
            print("Accediendo a históricas...")
            
            WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.ID, "expediente:action-historic-table"))
            )
            time.sleep(3)
            
            print("Extrayendo actuaciones históricas...")
            extraer_info_pagina(driver, "expediente:action-historic-table", textos_extraidos)
            
            # Paginación de actuaciones históricas
            pagina_hist_actual = 1
            tabla_historica = None
            
            try:
                tabla_historica = driver.find_element(By.ID, "expediente:action-historic-table")
            except:
                pass

            while tabla_historica:
                try:
                    paginador_hist = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.ui-paginator-bottom"))
                    )
                    siguiente_link_hist = paginador_hist.find_element(
                        By.CSS_SELECTOR, "span.ui-paginator-next:not(.ui-state-disabled)"
                    )
                    pagina_hist_actual += 1
                    print(f"Navegando a página {pagina_hist_actual} de históricas...")
                    
                    driver.execute_script("arguments[0].click();", siguiente_link_hist)
                    WebDriverWait(driver, 15).until(EC.staleness_of(tabla_historica))
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located((By.ID, "expediente:action-historic-table"))
                    )
                    time.sleep(3)
                    
                    extraer_info_pagina(driver, "expediente:action-historic-table", textos_extraidos)
                    tabla_historica = driver.find_element(By.ID, "expediente:action-historic-table")
                    
                except Exception:
                    print("Fin de paginación histórica.")
                    break
                    
        except Exception as e_hist:
            print(f"Actuaciones históricas no disponibles o error: {e_hist}")

    except Exception as e:
        print(f"Error procesando expediente {numero_expediente}/{año}: {e}")
    
    return textos_extraidos

def procesar_expediente(driver, numero_expediente, año):
    """
    Función principal para procesar un expediente individual
    """
    print(f"\n--- Procesando expediente {numero_expediente}/{año} ---")
    
    try:
        # Navegar al expediente
        url_expediente = f"https://scw.pjn.gov.ar/scw/home.seam?expediente={numero_expediente}&anio={año}"
        driver.get(url_expediente)
        
        # Resolver CAPTCHA si es necesario
        if resolver_captcha_si_necesario(driver):
            print("CAPTCHA resuelto exitosamente")
        
        # Esperar a que cargue la página del expediente
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "expediente:action-table"))
        )
        
        textos_extraidos = procesar_expediente_con_paginacion(driver, numero_expediente, año)
        
        # Procesar expedientes vinculados
        expedientes_vinculados = obtener_expedientes_vinculados(driver)
        
        for exp_vinculado in expedientes_vinculados:
            print(f"Procesando expediente vinculado: {exp_vinculado}")
            try:
                # Navegar al expediente vinculado
                url_vinculado = f"https://scw.pjn.gov.ar/scw/home.seam?expediente={exp_vinculado['numero']}&anio={exp_vinculado['año']}"
                driver.get(url_vinculado)
                
                # Resolver CAPTCHA si es necesario
                resolver_captcha_si_necesario(driver)
                
                # Esperar a que cargue
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "expediente:action-table"))
                )
                
                textos_vinculados = procesar_expediente_con_paginacion(driver, exp_vinculado['numero'], exp_vinculado['año'])
                textos_extraidos.extend(textos_vinculados)
                
            except Exception as e:
                print(f"Error procesando expediente vinculado {exp_vinculado}: {e}")
                continue
        
        # Analizar textos con IA
        vencimientos_encontrados = []
        for texto_info in textos_extraidos:
            try:
                vencimientos = analizar_texto_con_gemini(texto_info['texto_pdf'])
                if vencimientos:
                    for vencimiento in vencimientos:
                        vencimientos_encontrados.append({
                            'expediente': f"{numero_expediente}/{año}",
                            'fecha_actuacion': texto_info['fecha'],
                            'tipo_actuacion': texto_info['tipo'],
                            'descripcion': texto_info['descripcion'],
                            'url_pdf': texto_info['url_pdf'],
                            'plazo_detectado': vencimiento['plazo'],
                            'fecha_vencimiento': vencimiento['fecha_vencimiento'],
                            'dias_restantes': vencimiento['dias_restantes'],
                            'tipo_dias': vencimiento['tipo_dias']
                        })
            except Exception as e:
                print(f"Error analizando texto: {e}")
                continue
        
        return vencimientos_encontrados
        
    except Exception as e:
        print(f"Error procesando expediente {numero_expediente}/{año}: {e}")
        return []

class VencimientosAnalyzer:
    def __init__(self, gemini_api_key, captcha_api_key, headless=True):
        self.gemini_api_key = gemini_api_key
        self.captcha_api_key = captcha_api_key
        self.headless = headless
        self.driver = None
        
        # Configurar Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
    def inicializar_driver(self):
        """Inicializa el driver de Chrome"""
        print("🔧 Inicializando navegador...")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
    
    def navegar_a_expediente(self, numero_expediente, año_expediente):
        """Navega a un expediente específico usando el flujo correcto del PJN"""
        print(f"🔍 Navegando a expediente {numero_expediente}/{año_expediente}")
        
        try:
            # Abrir página
            self.driver.get("https://scw.pjn.gov.ar/scw/home.seam")
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.ID, "formPublica:numero")))
            print("Página de consulta cargada.")
            time.sleep(1)

            # Ingresar datos
            self.driver.find_element(By.ID, "formPublica:numero").send_keys(numero_expediente)
            self.driver.find_element(By.ID, "formPublica:anio").send_keys(año_expediente)
            Select(self.driver.find_element(By.ID, "formPublica:camaraNumAni")).select_by_value("24")
            print(f"Datos del expediente {numero_expediente}/{año_expediente} ingresados.")
            time.sleep(1)

            # Resolver CAPTCHA
            sitekey = "6LcTJ1kUAAAAAJT1Xqu3gzANPfCbQG0nke9O5b6K"
            captcha_solution = solve_recaptcha(self.captcha_api_key, sitekey, self.driver.current_url)
            if not captcha_solution:
                print("❌ Error: Falló la resolución del CAPTCHA. Saltando expediente.")
                return False

            # Inyectar solución y buscar
            print("Inyectando solución del CAPTCHA...")
            self.driver.execute_script(f"document.getElementById('g-recaptcha-response').innerHTML = arguments[0];", captcha_solution)
            time.sleep(1)
            print("Haciendo clic en buscar...")
            buscar_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "formPublica:buscarPorNumeroButton")))
            buscar_button.click()
            print("Esperando resultados...")
            time.sleep(5)

            try:
                messages_element = WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.ui-messages-error-summary, div.ui-messages-info-summary")))
                msg = messages_element.text
                print(f"Mensaje encontrado: {msg}")
                if "Expediente inexistente" in msg or "no se registran actuaciones" in msg:
                    print(f"❌ Expediente {numero_expediente}/{año_expediente} no encontrado o sin actuaciones.")
                    return False
            except Exception:
                print("No se encontraron mensajes de error/info. Procediendo a extraer datos.")
                pass
            
            print(f"✅ Expediente {numero_expediente}/{año_expediente} cargado")
            return True
            
        except Exception as e:
            print(f"❌ Error navegando a expediente: {str(e)}")
            return False
    
    def extraer_documentos_tabla_principal(self):
        """Extrae documentos de la tabla principal usando la función que funciona"""
        print("📄 Extrayendo documentos de tabla principal...")
        
        textos_extraidos = []
        
        try:
            print("Extrayendo actuaciones recientes...")
            extraer_info_pagina(self.driver, "expediente:action-table", textos_extraidos)
            
        except Exception as e:
            print(f"❌ Error extrayendo documentos principales: {str(e)}")
        
        return textos_extraidos
    
    def procesar_expedientes_vinculados(self):
        """Procesa la pestaña de expedientes vinculados - VERSIÓN CORREGIDA"""
        print("🔗 Procesando expedientes vinculados...")
        
        documentos_vinculados = []
        
        try:
            # Hacer clic en pestaña "Vinculados"
            vinculados_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@class='rf-tab-lbl' and text()='Vinculados']"))
            )
            vinculados_tab.click()
            print("✅ Clic en pestaña Vinculados realizado")
            
            # Esperar a que cargue el contenido
            time.sleep(3)
            
            # Verificar si hay tabla de vinculados
            try:
                tabla_vinculados = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "expediente:connectedTable"))
                )
                print("📋 Tabla de vinculados encontrada")
            except TimeoutException:
                print("ℹ️ No se encontró tabla de vinculados - posiblemente no hay expedientes vinculados")
                return documentos_vinculados
            
            tbody_vinculados = tabla_vinculados.find_element(By.TAG_NAME, "tbody")
            filas_vinculados = tbody_vinculados.find_elements(By.TAG_NAME, "tr")
            
            print(f"📋 Encontradas {len(filas_vinculados)} filas de expedientes vinculados")
            
            for i, fila in enumerate(filas_vinculados, 1):
                try:
                    # Buscar el botón de visualizar
                    boton_ver = None
                    try:
                        boton_ver = fila.find_element(By.XPATH, ".//a[@class='btn btn-default' and contains(@onclick, 'jsf.util.chain')]")
                        print(f"✅ Encontrado botón de visualizar en vinculado {i}")
                    except NoSuchElementException:
                        print(f"⚠️ No se encontró botón de visualizar en vinculado {i}")
                        continue
                    
                    # Extraer información del expediente vinculado
                    celdas = fila.find_elements(By.TAG_NAME, "td")
                    if len(celdas) >= 4:
                        numero_vinculado = celdas[0].text.strip()
                        print(f"🔍 Procesando vinculado {i}: {numero_vinculado}")
                        
                        # Hacer clic en el botón
                        print(f"Haciendo clic en botón de vinculado {i}...")
                        self.driver.execute_script("arguments[0].click();", boton_ver)
                        
                        print("⏳ Esperando navegación a nueva página...")
                        time.sleep(5)  # Espera más tiempo para la navegación
                        
                        try:
                            WebDriverWait(self.driver, 15).until(
                                EC.presence_of_element_located((By.ID, "expediente:action-table"))
                            )
                            print(f"✅ Nueva página cargada para vinculado {i}")
                        except TimeoutException:
                            print(f"⚠️ Timeout esperando tabla en nueva página para vinculado {i}")
                            continue
                        
                        try:
                            print("📄 Extrayendo documentos de la nueva página usando función exitosa...")
                            extraer_info_pagina(self.driver, "expediente:action-table", documentos_vinculados)
                            print(f"✅ Extracción completada para vinculado {i}: {numero_vinculado}")
                            
                        except Exception as e:
                            print(f"❌ Error extrayendo documentos del vinculado {i}: {str(e)}")
                        
                        print("🔙 Navegando de vuelta a página de vinculados...")
                        self.driver.back()
                        time.sleep(3)
                        
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.ID, "expediente:connectedTable"))
                            )
                            print("✅ De vuelta en página de vinculados")
                        except TimeoutException:
                            print("⚠️ Error regresando a página de vinculados")
                            break
                        
                except Exception as e:
                    print(f"❌ Error procesando vinculado {i}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error procesando vinculados: {str(e)}")
        
        print(f"🔗 Procesamiento de vinculados completado. Total documentos: {len(documentos_vinculados)}")
        return documentos_vinculados


    
    def analizar_vencimientos_con_ia(self, textos_documentos):
        """Analiza textos con IA para detectar vencimientos"""
        print("🤖 Analizando vencimientos con IA...")
        
        if not textos_documentos:
            return None
        
        # Combinar todos los textos
        texto_completo = "\n\n".join(texto['texto_pdf'] for texto in textos_documentos)
        
        print("\n" + "="*80)
        print("🔍 DEBUG: TEXTO ENVIADO A GEMINI")
        print("="*80)
        texto_para_analisis = texto_completo  # Limitar para no exceder tokens
        print(f"📝 Longitud del texto: {len(texto_para_analisis)} caracteres")
        print(f"📄 Texto completo a analizar:\n{texto_para_analisis}")
        print("="*80)
        
        prompt = f"""
        Analiza el siguiente texto de documentos judiciales y busca cualquier mención de plazos, términos o vencimientos.

        Busca específicamente:
        - Frases como "por el término de X días"
        - "plazo de X días"
        - "dentro de X días"
        - "en el término de X días"
        - Cualquier referencia a plazos procesales

        Si encuentras un vencimiento:
        1. Extrae la fecha del documento (busca fechas como "Salta, 18 de agosto de 2025")
        2. Extrae el número de días del plazo
        3. Indica si son días hábiles o corridos
        4. Proporciona un resumen del vencimiento

        Este es un ejemplo:

        "Salta, 18 de agosto de 2025.- Proveyendo a la presentación de fecha
        06/08/2025:...Por lo demás, de lo manifestado por la Dra. Ramos en
        relación al pago de la estampilla previsional, córrase vista mediante
        DEOX a la Caja de Seguridad Social para Abogados de Salta, por el
        término de cinco (5) días de recibido la presente, a los fines que hubiera
        lugar. FC"


        Responde en formato JSON:
        {{
            "vencimiento_encontrado": true/false,
            "fecha_documento": "DD/MM/YYYY",
            "dias_plazo": número,
            "tipo_dias": "habiles" o "corridos",
            "descripcion": "descripción del vencimiento",
            "texto_relevante": "fragmento del texto que contiene el vencimiento"
        }}

        TEXTO A ANALIZAR:
        {texto_para_analisis}
        """
        
        print("\n" + "="*80)
        print("📤 DEBUG: PROMPT ENVIADO A GEMINI")
        print("="*80)
        print(prompt)
        print("="*80)
        
        try:
            print("⏳ Enviando consulta a Gemini...")
            response = self.model.generate_content(prompt)
            resultado_texto = response.text
            
            print("\n" + "="*80)
            print("📥 DEBUG: RESPUESTA COMPLETA DE GEMINI")
            print("="*80)
            print(f"📝 Respuesta recibida:\n{resultado_texto}")
            print("="*80)
            
            # Intentar extraer JSON de la respuesta
            import json
            
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{.*\}', resultado_texto, re.DOTALL)
            if json_match:
                json_text = json_match.group()
                print(f"\n🔍 DEBUG: JSON EXTRAÍDO DE LA RESPUESTA:")
                print(f"📄 JSON encontrado: {json_text}")
                
                try:
                    resultado_json = json.loads(json_text)
                    print(f"✅ DEBUG: JSON PARSEADO EXITOSAMENTE:")
                    print(f"📊 Resultado parseado: {resultado_json}")
                    
                    vencimiento_encontrado = resultado_json.get('vencimiento_encontrado', False)
                    print(f"\n🎯 DEBUG: ANÁLISIS DEL RESULTADO:")
                    print(f"   - Vencimiento encontrado: {vencimiento_encontrado}")
                    print(f"   - Fecha documento: {resultado_json.get('fecha_documento', 'N/A')}")
                    print(f"   - Días plazo: {resultado_json.get('dias_plazo', 'N/A')}")
                    print(f"   - Tipo días: {resultado_json.get('tipo_dias', 'N/A')}")
                    print(f"   - Descripción: {resultado_json.get('descripcion', 'N/A')}")
                    print(f"   - Texto relevante: {resultado_json.get('texto_relevante', 'N/A')}")

                    if vencimiento_encontrado:
                        return [{
                            'expediente': f"{textos_documentos[0]['fecha']}/{textos_documentos[0]['tipo']}",
                            'fecha_actuacion': resultado_json.get('fecha_documento', ''),
                            'tipo_actuacion': resultado_json.get('tipo_dias', ''),
                            'descripcion': resultado_json.get('descripcion', ''),
                            'url_pdf': textos_documentos[0]['url_pdf'],
                            'plazo_detectado': resultado_json.get('dias_plazo', ''),
                            'fecha_vencimiento': resultado_json.get('fecha_vencimiento', ''),
                            'dias_restantes': resultado_json.get('dias_restantes', ''),
                            'tipo_dias': resultado_json.get('tipo_dias', '')
                        }]
                    else:
                        return None
                except json.JSONDecodeError as je:
                    print(f"❌ DEBUG: ERROR PARSEANDO JSON: {str(je)}")
                    print(f"📄 JSON problemático: {json_text}")
                    return None
            else:
                print("⚠️ DEBUG: No se pudo extraer JSON de la respuesta de IA")
                print("🔍 DEBUG: Buscando patrones alternativos en la respuesta...")
                
                if "vencimiento_encontrado" in resultado_texto.lower():
                    print("✅ DEBUG: Se encontró mención de 'vencimiento_encontrado' en la respuesta")
                if "días" in resultado_texto.lower() or "dias" in resultado_texto.lower():
                    print("✅ DEBUG: Se encontró mención de 'días' en la respuesta")
                if any(palabra in resultado_texto.lower() for palabra in ["plazo", "término", "termino", "vencimiento"]):
                    print("✅ DEBUG: Se encontraron palabras clave relacionadas con plazos")
                
                return None
                
        except Exception as e:
            print(f"❌ DEBUG: Error analizando con IA: {str(e)}")
            print(f"🔍 DEBUG: Tipo de error: {type(e).__name__}")
            return None
    
    def procesar_expediente_completo(self, numero_expediente, año_expediente):
        """Procesa un expediente completo buscando vencimientos"""
        print(f"\n🔍 PROCESANDO EXPEDIENTE {numero_expediente}/{año_expediente}")
        print("=" * 60)
        
        try:
            # Navegar al expediente
            if not self.navegar_a_expediente(numero_expediente, año_expediente):
                return None
            
            # Extraer documentos de tabla principal
            documentos_principales = self.extraer_documentos_tabla_principal()
            
            # Procesar expedientes vinculados
            documentos_vinculados = self.procesar_expedientes_vinculados()
            
            # Combinar todos los documentos
            todos_documentos = documentos_principales + documentos_vinculados
            
            if not todos_documentos:
                print("⚠️ No se encontraron documentos para analizar")
                return None
            
            print(f"📄 Total documentos encontrados: {len(todos_documentos)}")
            print(f"   - Documentos principales: {len(documentos_principales)}")
            print(f"   - Documentos vinculados: {len(documentos_vinculados)}")
            
            # Analizar con IA
            resultado_vencimiento = self.analizar_vencimientos_con_ia(todos_documentos)
            
            if resultado_vencimiento:
                print("✅ VENCIMIENTO DETECTADO!")
                return resultado_vencimiento
            else:
                print("ℹ️ No se detectaron vencimientos")
                return None
                
        except Exception as e:
            print(f"❌ Error procesando expediente: {str(e)}")
            return None
    
    def cerrar_driver(self):
        """Cierra el driver"""
        if self.driver:
            self.driver.quit()
            print("🔧 Navegador cerrado")

def analizar_vencimientos_expedientes(gemini_api_key, captcha_api_key, headless=True):
    """Función principal para analizar vencimientos en expedientes"""
    print("🚀 INICIANDO ANÁLISIS DE VENCIMIENTOS")
    print("=" * 60)
    
    # Leer archivo de expedientes
    try:
        df_expedientes = pd.read_excel("expedientes.xlsx")
        print(f"📊 Cargados {len(df_expedientes)} expedientes del Excel")
    except Exception as e:
        print(f"❌ Error cargando expedientes.xlsx: {str(e)}")
        return
    
    analyzer = VencimientosAnalyzer(gemini_api_key, captcha_api_key, headless)
    
    try:
        # Inicializar navegador (sin login ya que usa consulta pública)
        analyzer.inicializar_driver()
        
        # Lista para almacenar expedientes con vencimientos
        expedientes_con_vencimientos = []
        
        # Procesar cada expediente
        for index, row in df_expedientes.iterrows():
            try:
                numero_expediente = str(row.get('Número', '')).strip()
                año_expediente = str(row.get('Año', '')).strip()
                
                if not numero_expediente or not año_expediente:
                    print(f"⚠️ Expediente {index+1}: Datos incompletos")
                    continue
                
                print(f"\n📋 Procesando expediente {index+1}/{len(df_expedientes)}")
                
                # Analizar expediente
                resultado = analyzer.procesar_expediente_completo(numero_expediente, año_expediente)
                
                if resultado:
                    # Agregar información del vencimiento a la fila
                    row_con_vencimiento = row.copy()
                    row_con_vencimiento['Fecha_Vencimiento'] = resultado.get('fecha_vencimiento_calculada', '')
                    row_con_vencimiento['Descripcion_Vencimiento'] = resultado.get('descripcion', '')
                    row_con_vencimiento['Dias_Plazo'] = resultado.get('dias_plazo', '')
                    row_con_vencimiento['Tipo_Dias'] = resultado.get('tipo_dias', '')
                    row_con_vencimiento['Fecha_Documento'] = resultado.get('fecha_documento', '')
                    
                    expedientes_con_vencimientos.append(row_con_vencimiento)
                
                # Pausa entre expedientes
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error procesando expediente {index+1}: {str(e)}")
                continue
        
        # Guardar resultados
        if expedientes_con_vencimientos:
            df_vencimientos = pd.DataFrame(expedientes_con_vencimientos)
            df_vencimientos.to_excel("expedientes_vencimientos.xlsx", index=False)
            
            print(f"\n✅ ANÁLISIS COMPLETADO")
            print(f"📊 Expedientes con vencimientos: {len(expedientes_con_vencimientos)}")
            print(f"💾 Archivo guardado: expedientes_vencimientos.xlsx")
        else:
            print("\nℹ️ No se encontraron expedientes con vencimientos")
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
    finally:
        analyzer.cerrar_driver()

def resolver_captcha_si_necesario(driver):
    # Implementación de la función para resolver CAPTCHA si es necesario
    pass

def obtener_expedientes_vinculados(driver):
    # Implementación de la función para obtener expedientes vinculados
    pass

def analizar_texto_con_gemini(texto_pdf):
    # Implementación de la función para analizar texto con Gemini
    pass

if __name__ == "__main__":
    # Ejemplo de uso
    analizar_vencimientos_expedientes(
        gemini_api_key="tu_api_key",
        captcha_api_key="tu_captcha_key",
        headless=True
    )
