def extraer_info_pagina(driver, tabla_id, textos):
     # (Misma función que en la versión anterior)
    try:
        tabla = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, tabla_id))
        )
        filas = tabla.find_elements(By.TAG_NAME, "tr")
        print(f"Procesando tabla: {tabla_id}. Filas encontradas: {len(filas)}")
        for i, fila in enumerate(filas):
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if celdas:
                # datos = [celda.text for celda in celdas] # Extraer texto de celdas puede ser útil para debug
                enlaces = fila.find_elements(By.TAG_NAME, "a")
                for enlace in enlaces:
                    href = enlace.get_attribute("href")
                    if href and ("download=true" in href or ".pdf" in href.lower()):
                        print(f"    Encontrado enlace PDF: {href}")
                        descargar_y_extraer_pdf(href, textos)
    except Exception as e:
        print(f"Error extrayendo datos de la tabla '{tabla_id}': {e}")
