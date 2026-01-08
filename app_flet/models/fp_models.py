class Centre:
    def __init__(self, nom, localitat, comarca, provincia, nom_cicle, grau):
        self.nom = nom
        self.localitat = localitat
        self.comarca = comarca
        self.provincia = provincia
        self.nom_cicle = nom_cicle
        self.grau = grau

    @staticmethod
    def from_json(json_data):
        return Centre(
            nom=json_data.get("centre"),
            localitat=json_data.get("localitat"),
            comarca=json_data.get("comarca"),
            provincia=json_data.get("provincia"),
            nom_cicle=json_data.get("nom_cicle"),
            grau=json_data.get("grau")
        )

class Filtres:
    def __init__(self, provincies, comarques, localitats, graus):
        self.provincies = provincies
        self.comarques = comarques
        self.localitats = localitats
        self.graus = graus

    @staticmethod
    def from_json(json_data):
        d = json_data.get("data", {})
        return Filtres(
            provincies=d.get("provincies", []),
            comarques=d.get("comarques", []),
            localitats=d.get("localitats", []),
            graus=d.get("graus", [])
        )