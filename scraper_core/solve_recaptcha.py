import requests
import time
import json

def solve_recaptcha(api_key, sitekey, pageurl):
    if not api_key or api_key == "TU_CLAVE_2CAPTCHA":
        print("Error: API Key de 2Captcha no proporcionada.")
        return None
    s = requests.Session()
    captcha_url = "http://2captcha.com/in.php"
    data = {
        "key": api_key,
        "method": "userrecaptcha",
        "googlekey": sitekey,
        "pageurl": pageurl,
        "json": 1
    }
    try:
        response = s.post(captcha_url, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get("status") != 1:
            print(f"Error al enviar CAPTCHA a 2captcha: {result.get('request')}")
            return None
        captcha_id = result.get("request")
        print(f"Captcha enviado a 2captcha, ID: {captcha_id}. Esperando solución...")

        fetch_url = "http://2captcha.com/res.php"
        params = {"key": api_key, "action": "get", "id": captcha_id, "json": 1}
        start_time = time.time()
        timeout_2captcha = 180

        while (time.time() - start_time) < timeout_2captcha:
            time.sleep(10)
            res = s.get(fetch_url, params=params, timeout=30)
            res.raise_for_status()
            result2 = res.json()
            if result2.get("status") == 1:
                solution = result2.get("request")
                print(f"Captcha resuelto por 2captcha: {solution[:15]}...")
                return solution
            elif result2.get("request") == "CAPCHA_NOT_READY":
                print("Captcha aún no está listo...")
                continue
            else:
                print(f"Error obteniendo solución de 2captcha: {result2.get('request')}")
                return None
        print("Timeout esperando la solución del CAPTCHA.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Error de conexión con 2captcha: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decodificando respuesta JSON de 2captcha: {e}")
        return None
