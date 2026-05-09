def descargar_y_extraer_pdf(url_pdf, textos):
    # (Misma función que en la versión anterior, con manejo de Tesseract opcional)
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
        imagen_extraida = False
        try:
            with pdfplumber.open(nombre_pdf) as pdf:
                print(f"  Procesando {len(pdf.pages)} páginas del PDF...")
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        texto_completo_pdf += page_text + "\n"
                    # Solo intentar OCR si hay texto nulo O muy corto Y Tesseract está configurado
                    elif (not page_text or len(page_text.strip()) < 10) and pytesseract.pytesseract.tesseract_cmd and os.path.exists(pytesseract.pytesseract.tesseract_cmd):
                        print(f"  Página {i+1}: Texto escaso/nulo, intentando OCR...")
                        try:
                            pil_image = page.to_image(resolution=300).original
                            ocr_text = pytesseract.image_to_string(pil_image, lang="spa")
                            if ocr_text and ocr_text.strip():
                                texto_completo_pdf += ocr_text + "\n"
                                print(f"    [OCR aplicado con éxito en pág {i+1}]")
                                imagen_extraida = True
                            else:
                                 print(f"    [OCR no devolvió texto en pág {i+1}]")
                        except pytesseract.TesseractNotFoundError:
                             print("    ERROR: Tesseract no encontrado durante OCR. Verifica la ruta.")
                        except Exception as ocr_e:
                             print(f"    Error durante OCR en pág {i+1}: {ocr_e}")
                    elif (not page_text or len(page_text.strip()) < 10):
                        print(f"  Página {i+1}: Texto escaso/nulo, pero Tesseract no está configurado. Saltando OCR.")

            if texto_completo_pdf.strip():
                textos.append(texto_completo_pdf)
            else:
                 print(f"  PDF {url_pdf} no contenía texto extraíble (o Tesseract no pudo procesarlo).")
        except Exception as pdf_e:
            print(f"  Error procesando el PDF '{nombre_pdf}' con pdfplumber: {pdf_e}")
    except requests.exceptions.RequestException as req_e:
        print(f"Error descargando PDF desde {url_pdf}: {req_e}")
    except Exception as e:
        print(f"Error general en descargar_y_extraer_pdf para {url_pdf}: {e}")
    finally:
        if os.path.exists(nombre_pdf):
            try:
                os.remove(nombre_pdf)
            except Exception as del_e:
                print(f"Error eliminando archivo temporal '{nombre_pdf}': {del_e}")
