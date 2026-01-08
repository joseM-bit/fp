import requests
import urllib.parse

BASE_URL = "http://localhost:3000/api/fp"

def get_filtres():
    """Obté les dades per a omplir els dropdowns (províncies, comarques, localitats i graus)"""
    try:
        response = requests.get(f"{BASE_URL}/filtres")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error en get_filtres: {e}")
        return {"success": False, "data": {"provincies": [], "comarques": [], "localitats": [], "graus": []}}

def get_cicles():
    """Obté la llista completa de cicles per al dropdown de cicles"""
    try:
         response = requests.get(f"{BASE_URL}/cicles")
         response.raise_for_status()
         return response.json()
    except requests.RequestException as e:
        print(f"Error en get_cicles: {e}")
        return {"success": False, "data": []}


def cercar_oferta(provincia=None, comarca=None, localitat=None, grau=None):
    """Envia els filtres seleccionats al servidor i rep els resultats de la cerca"""
    try:
        # Construïm el cos de la petició només amb els camps que l'usuari ha triat
        payload = {}
        if provincia: payload["provincia"] = provincia
        if comarca: payload["comarca"] = comarca
        if localitat: payload["localitat"] = localitat
        if grau: payload["grau"] = grau

        response = requests.post(f"{BASE_URL}/cercar", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error en cercar_oferta: {e}")
        return {"success": False, "data": []}

def get_detalls_centre(codi_centre):
    """Obté tota la informació d'un centre específic mitjançant el seu codi"""
    try:
        response = requests.get(f"{BASE_URL}/centre/{codi_centre}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error en get_detalls_centre: {e}")
        return {"success": False, "error": str(e)}

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

    com_encoded = urllib.parse.quote(comarca)
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