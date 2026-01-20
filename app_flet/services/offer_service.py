import requests
import urllib.parse

BASE_URL = "http://localhost:3000/api/fp"


def get_cicles_filtrats(provincia=None, comarca=None, localitat=None, familia=None, grau=None):
    """Envia els filtres seleccionats al servidor i retorna la llista de titulacions de FP que compleixen els filtres."""
    payload = {
        "provincia": provincia,
        "comarca": comarca,
        "localitat": localitat,
        "familia": familia,
        "grau": grau
    }
    try:
        response = requests.post(f"{BASE_URL}/cicles", json=payload)
        return response.json()
    except:
        return {"success": False}

def get_cursos_filtrats(provincia=None, comarca=None, localitat=None, familia=None, grau=None):
    """Envia els filtres seleccionats al servidor i retorna la llista de cursos d'especialització que compleixen els filtres."""
    payload = {
        "provincia": provincia,
        "comarca": comarca,
        "localitat": localitat,
        "familia": familia,
        "grau": grau
    }
    try:
        response = requests.post(f"{BASE_URL}/cursos", json=payload)
        return response.json()
    except:
        return {"success": False}


def cercar_oferta(tipus, pagina, provincia=None, comarca=None, localitat=None, familia=None, grau=None, id_cicle=None):
    """Envia els filtres seleccionats al servidor i retorna l'oferta de centres que cumplixen els filtres."""
    payload = {
        "tipus": tipus,
        "pagina": pagina,
        "provincia": provincia,
        "comarca": comarca,
        "localitat": localitat,
        "familia": familia,
        "grau": grau,
        "id_cicle": id_cicle
    }
    try:
        response = requests.post(f"{BASE_URL}/cercar", json=payload)
        return response.json()
    except:
        return {"success": False}

# No té ús de moment
def get_detalls_centre(codi_centre):
    """Obté tota la informació d'un centre específic mitjançant el seu codi"""
    try:
        response = requests.get(f"{BASE_URL}/centre/{codi_centre}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error en get_detalls_centre: {e}")
        return {"success": False, "error": str(e)}

