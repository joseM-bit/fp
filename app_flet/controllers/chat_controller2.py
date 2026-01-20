from services.chat_service import send_message
from models.fp_models import Targeta

def processar_pregunta(user_text):
    resposta = send_message(user_text)

    if resposta.get("success"):
        dades = resposta.get("data", [])
        missatge_backend = resposta.get("message") # El text de "Indica localitat..."
        
        # CAS 1: El backend ens envia un missatge de text (perquè falten filtres o no hi ha dades)
        if missatge_backend:
            return missatge_backend
        
        # CAS 2: No hi ha dades i tampoc hi ha missatge (cas de seguretat)
        if not dades:
            return "No he trobat resultats per a aquesta consulta. Prova a especificar una altra zona."

        # CAS 3: Hi ha dades, comprovem el format
        primer_item = dades[0]
        if "centre" in primer_item or "grau" in primer_item: # "centre" és la clau que usa el teu SQL
            return [Targeta.from_json(item) for item in dades]
        
        return "He trobat dades, però el format no és l'esperat."
    
    return resposta.get("message", "S'ha produït un error en la comunicació.")