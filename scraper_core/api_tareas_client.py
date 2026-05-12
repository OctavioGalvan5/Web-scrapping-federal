import requests
import json
import logging

logger = logging.getLogger(__name__)

class TareasFederalClient:
    def __init__(self, api_key, base_url="https://tareasfederal.cajadeabogadossalta.org"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.endpoint = f"{self.base_url}/api/tasks"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def crear_tarea(self, title, due_date, description="", priority="Normal", assignee_ids=None, area_id=None):
        """
        Crea una tarea en la API de Tareas Federal.
        
        :param title: Titulo de la tarea (ej: Numero de expediente)
        :param due_date: Fecha limite (YYYY-MM-DD)
        :param description: Descripcion de la tarea (ej: Caratula)
        :param priority: Normal, Media o Urgente
        :param assignee_ids: Lista de IDs de usuarios asignados
        :param area_id: ID del area (opcional)
        :return: dict con la respuesta de la API o None si hubo error
        """
        payload = {
            "title": title,
            "due_date": due_date,
            "description": description,
            "priority": priority
        }
        
        if assignee_ids:
            payload["assignee_ids"] = assignee_ids
            
        if area_id:
            payload["area_id"] = area_id

        try:
            response = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=30)
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Error al crear tarea: {response.status_code} - {response.text}")
                return {"error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Excepcion al conectar con API Tareas: {e}")
            return {"error": str(e)}

    def test_connection(self):
        # La API no tiene un endpoint de ping explicito segun el instructivo, 
        # pero podriamos intentar una peticion mal formada o simplemente confiar en crear_tarea.
        pass
