import requests
import urllib.parse

BASE_URL = "http://localhost:3000/api/fp"

def get_filtres(tipus):
    """Obté les dades per a omplir els dropdowns (províncies, comarques, localitats i graus)"""
    try:
        response = requests.get(f"{BASE_URL}/filtres/{tipus}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error en get_filtres: {e}")
        return {"success": False, "data": {"provincies": [], "comarques": [], "localitats": [], "graus": []}}

def get_all_cicles_fp():
    """Obté la llista completa de cicles (objectes JSON) per omplir el dropdown (cicle)"""
    try:
        response = requests.get(f"{BASE_URL}/cicles", timeout=5)
        response.raise_for_status()
        return response.json()
        
    except requests.RequestException as e:
        print(f"Error en get_cicles: {e}")
        return {"success": False, "data": []}

def get_all_cicles_ce():
    """Obté la llista completa de cicles (objectes JSON) per omplir el dropdown (cicle)"""
    try:
        response = requests.get(f"{BASE_URL}/cursos", timeout=5)
        response.raise_for_status()
        return response.json()
        
    except requests.RequestException as e:
        print(f"Error en get_cicles: {e}")
        return {"success": False, "data": []}

def get_comarques_per_provincia(provincia):
    """Obté la llista de comarques d'una provincia determinada"""

    prov_encoded = urllib.parse.quote(provincia)
    url = f"{BASE_URL}/comarques/{prov_encoded}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        result = response.json()
        if result.get("success"):
            return result.get("data", [])
        return []
    except requests.RequestException as e:
        print(f"Error en get_comarques_per_provincia: {e}")
        return {"success": False, "error": str(e)}

def get_localitats_per_comarca(comarca):
    """Obté la llista de localitats d'una comarca determinada"""

    com_encoded = urllib.parse.quote(comarca, safe='')
    url = f"{BASE_URL}/localitats/{com_encoded}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        result = response.json()
        if result.get("success"):
            return result.get("data", [])
        return []
    except requests.RequestException as e:
        print(f"Error en get_localitats_per_comarca: {e}")
        return {"success": False, "error": str(e)}

def get_localitats_per_provincia(provincia):
    """Obté la llista de localitats d'una provincia determinada"""

    prov_encoded = urllib.parse.quote(provincia)
    url = f"{BASE_URL}/toteslocalitats/{prov_encoded}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        result = response.json()
        if result.get("success"):
            return result.get("data", [])
        return []
    except requests.RequestException as e:
        print(f"Error en get_localitats_per_provincia: {e}")
        return {"success": False, "error": str(e)}