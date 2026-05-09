from datetime import datetime, timedelta
import calendar

# Feriados nacionales de Argentina 2025 (puedes actualizar cada año)
FERIADOS_2025 = [
    "01/01/2025",  # Año Nuevo
    "03/03/2025",  # Carnaval
    "04/03/2025",  # Carnaval
    "24/03/2025",  # Día Nacional de la Memoria por la Verdad y la Justicia
    "02/04/2025",  # Día del Veterano y de los Caídos en la Guerra de Malvinas
    "18/04/2025",  # Viernes Santo
    "01/05/2025",  # Día del Trabajador
    "25/05/2025",  # Día de la Revolución de Mayo
    "16/06/2025",  # Paso a la Inmortalidad del General Don Martín Miguel de Güemes
    "20/06/2025",  # Paso a la Inmortalidad del General Don Manuel Belgrano
    "09/07/2025",  # Día de la Independencia
    "17/08/2025",  # Paso a la Inmortalidad del General Don José de San Martín
    "12/10/2025",  # Día del Respeto a la Diversidad Cultural
    "20/11/2025",  # Día de la Soberanía Nacional
    "08/12/2025",  # Inmaculada Concepción de María
    "25/12/2025",  # Navidad
]

def es_dia_habil(fecha):
    """
    Determina si una fecha es día hábil (no sábado, domingo ni feriado)
    """
    # Convertir a datetime si es string
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, "%d/%m/%Y")
    
    # Verificar si es fin de semana
    if fecha.weekday() >= 5:  # 5=sábado, 6=domingo
        return False
    
    # Verificar si es feriado
    fecha_str = fecha.strftime("%d/%m/%Y")
    if fecha_str in FERIADOS_2025:
        return False
    
    return True

def agregar_dias_habiles(fecha_inicio, dias_habiles):
    """
    Agrega una cantidad específica de días hábiles a una fecha
    """
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.strptime(fecha_inicio, "%d/%m/%Y")
    
    fecha_actual = fecha_inicio
    dias_agregados = 0
    
    while dias_agregados < dias_habiles:
        fecha_actual += timedelta(days=1)
        
        if es_dia_habil(fecha_actual):
            dias_agregados += 1
    
    return fecha_actual

def agregar_dias_corridos(fecha_inicio, dias_corridos):
    """
    Agrega una cantidad específica de días corridos a una fecha
    """
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.strptime(fecha_inicio, "%d/%m/%Y")
    
    fecha_final = fecha_inicio + timedelta(days=dias_corridos)
    return fecha_final

def calcular_fecha_vencimiento(fecha_documento, dias_plazo, tipo_dias="habiles"):
    """
    Calcula la fecha de vencimiento basada en la fecha del documento y el plazo
    
    Args:
        fecha_documento (str): Fecha del documento en formato DD/MM/YYYY
        dias_plazo (int): Número de días del plazo
        tipo_dias (str): "habiles" o "corridos"
    
    Returns:
        str: Fecha de vencimiento en formato DD/MM/YYYY
    """
    try:
        print(f"📅 Calculando vencimiento:")
        print(f"   Fecha documento: {fecha_documento}")
        print(f"   Plazo: {dias_plazo} días {tipo_dias}")
        
        # Convertir fecha de string a datetime
        if isinstance(fecha_documento, str):
            # Intentar diferentes formatos de fecha
            formatos_fecha = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
            fecha_inicio = None
            
            for formato in formatos_fecha:
                try:
                    fecha_inicio = datetime.strptime(fecha_documento, formato)
                    break
                except ValueError:
                    continue
            
            if fecha_inicio is None:
                print(f"❌ No se pudo parsear la fecha: {fecha_documento}")
                return None
        else:
            fecha_inicio = fecha_documento
        
        # Calcular fecha de vencimiento según el tipo
        if tipo_dias.lower() == "habiles":
            fecha_vencimiento = agregar_dias_habiles(fecha_inicio, dias_plazo)
        else:  # días corridos
            fecha_vencimiento = agregar_dias_corridos(fecha_inicio, dias_plazo)
        
        resultado = fecha_vencimiento.strftime("%d/%m/%Y")
        print(f"   ✅ Fecha vencimiento: {resultado}")
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error calculando vencimiento: {str(e)}")
        return None

def obtener_dias_hasta_vencimiento(fecha_vencimiento):
    """
    Calcula cuántos días faltan hasta el vencimiento
    """
    try:
        if isinstance(fecha_vencimiento, str):
            fecha_venc = datetime.strptime(fecha_vencimiento, "%d/%m/%Y")
        else:
            fecha_venc = fecha_vencimiento
        
        fecha_actual = datetime.now()
        diferencia = fecha_venc - fecha_actual
        
        return diferencia.days
        
    except Exception as e:
        print(f"❌ Error calculando días hasta vencimiento: {str(e)}")
        return None

def es_vencimiento_proximo(fecha_vencimiento, dias_alerta=5):
    """
    Determina si un vencimiento está próximo (dentro de X días)
    """
    dias_restantes = obtener_dias_hasta_vencimiento(fecha_vencimiento)
    
    if dias_restantes is None:
        return False
    
    return 0 <= dias_restantes <= dias_alerta

# Función de prueba
if __name__ == "__main__":
    # Ejemplo de uso
    fecha_doc = "18/08/2025"
    dias = 5
    tipo = "habiles"
    
    print("🧪 PRUEBA DE CÁLCULO DE VENCIMIENTOS")
    print("=" * 50)
    
    resultado = calcular_fecha_vencimiento(fecha_doc, dias, tipo)
    print(f"Resultado: {resultado}")
    
    if resultado:
        dias_restantes = obtener_dias_hasta_vencimiento(resultado)
        print(f"Días hasta vencimiento: {dias_restantes}")
        
        es_proximo = es_vencimiento_proximo(resultado, 10)
        print(f"¿Es vencimiento próximo? {es_proximo}")
