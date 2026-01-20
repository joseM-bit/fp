import requests

BASE_URL = "http://localhost:3000/api/fp"


def send_message(message):
    try:
        response = requests.post(f"{BASE_URL}/chat", json={"message": message}, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {"success": False, "message": "Error en el servidor"}
    except Exception as e:
        return {"success": False, "message": str(e)}