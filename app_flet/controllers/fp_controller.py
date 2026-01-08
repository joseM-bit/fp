from services.api_service import get_filtres, cercar_oferta, get_comarques_per_provincia, get_localitats_per_comarca
from models.fp_models import Centre, Filtres

def obtenir_tots_els_filtres():
    """Retorna un objecte Filtres amb les llistes per als dropdowns"""
    json_data = get_filtres()
    if json_data.get("success"):
        return Filtres.from_json(json_data)
    return Filtres([], [], [], [])

def executar_cerca_oferta(provincia=None, comarca=None, localitat=None, grau=None):
    """Retorna una llista d'objectes Centre segons els filtres"""
    json_data = cercar_oferta(provincia, comarca, localitat, grau)
    
    if json_data.get("success"):
        # Convertim cada diccionari de la llista 'data' en un objecte Centre
        return [Centre.from_json(item) for item in json_data.get("data", [])]
    return []

def obtenir_cicles_per_grau(grau):
    """Retorna una llista de noms de cicles filtrats per grau"""
    # Podem reutilitzar la funció de cerca o crear un endpoint específic
    json_data = cercar_oferta(grau=grau) 
    if json_data.get("success"):
        # Extraiem noms únics de cicles
        cicles = sorted(list(set([item.get("nom_cicle") for item in json_data.get("data", [])])))
        return cicles
    return []

def obtenir_comarques(provincia=None):
    """
    Retorna la llista de comarques filtrada per província demanant-ho a l'API.
    """
    if not provincia or provincia == "Totes":
        # Si no hi ha província, retorna totes les comarques amb la funció get_filtres
        json_data = get_filtres()
        return json_data.get("data", {}).get("comarques", [])
    
    comarques = get_comarques_per_provincia(provincia)
    
    return comarques

def obtenir_localitats(comarca=None):
    """
    Retorna la llista de comarques filtrada per província demanant-ho a l'API.
    """
    if not comarca or comarca == "Totes":
        # Si no hi ha comarca, retorna totes les localitats amb la funció get_filtres
        json_data = get_filtres()
        return json_data.get("data", {}).get("localitats", [])
    
    localitats = get_localitats_per_comarca(comarca)
    
    return localitats