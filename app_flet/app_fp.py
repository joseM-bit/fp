import flet as ft
from flet_webview import WebView
import pandas as pd
from controllers.fp_controller import obtenir_tots_els_filtres, executar_cerca_oferta, obtenir_comarques, obtenir_localitats_de_comarca, obtenir_localitats_de_provincia

class FpApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Orientat FP - Comunitat Valenciana"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        # Referències per a actualització dinàmica
        self.map_container = ft.Ref[ft.Container]()
        self.results_col = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        
        # Carreguem filtres inicials (Node.js/Python Controller)
        self.filtres_globals = obtenir_tots_els_filtres()
        
        self.setup_ui()

    def setup_ui(self):
        # --- DROPDOWNS ---
        self.drop_provincia = ft.Dropdown(
            label="Província", width=180,
            options=[ft.dropdown.Option("Totes")] + [ft.dropdown.Option(p) for p in self.filtres_globals.provincies],
            on_change=self.actualitzar_comarques
        )
        self.drop_comarca = ft.Dropdown(
            label="Comarca", width=220,
            options=[ft.dropdown.Option("Totes")] + [ft.dropdown.Option(c) for c in self.filtres_globals.comarques],
            on_change=self.actualitzar_localitats
        )
        self.drop_localitat = ft.Dropdown(
            label="Localitat", width=220,
            options=[ft.dropdown.Option("Totes")] + [ft.dropdown.Option(l) for l in self.filtres_globals.localitats]
        )
        self.drop_grau = ft.Dropdown(
            label="Grau", width=180,
            options=[ft.dropdown.Option("Tots")] + [ft.dropdown.Option(g) for g in self.filtres_globals.graus]
        )
        """self.drop_cicles = ft.Dropdown(
            label="Cicle", width=300, 
            options=[ft.dropdown.Option("Tots")] + [ft.dropdown.Option(c) for c in self.filtres_globals.cicles]
        ))"""

        # --- CONFIGURACIÓ INICIAL DEL MAPA (WebView) ---
        # URL inicial: Centrat a la CV
        url_cv = "https://www.openstreetmap.org/export/embed.html?bbox=-1.5,37.8,0.5,40.5&layer=mapnik"
        self.map_widget = WebView(url_cv, expand=True)

        # --- LAYOUT ---
        self.page.add(
            ft.Container(
                padding=20,
                expand=True,
                content=ft.Column([
                    ft.Text("Busca el teu Cicle Formatiu", size=32, weight="bold", color=ft.Colors.BLUE_900),
                    
                    # Barra superior de filtres
                    ft.Container(
                        padding=15, bgcolor=ft.Colors.BLUE_GREY_50, border_radius=10,
                        content=ft.Row([
                            self.drop_provincia, self.drop_comarca, 
                            self.drop_localitat, self.drop_grau,
                            ft.IconButton(
                                icon=ft.Icons.SEARCH, bgcolor=ft.Colors.BLUE_700,
                                icon_color="white", on_click=self.handle_search
                            )
                        ], wrap=True)
                    ),

                    # Secció de contingut (Llista + Mapa)
                    ft.Row([
                        # Esquerra: Resultats
                        ft.Container(
                            content=self.results_col,
                            width=450, expand=False
                        ),
                        # Dreta: El Mapa amb WebView
                        ft.Container(
                            ref=self.map_container,
                            expand=True,
                            border=ft.border.all(1, ft.Colors.BLUE_GREY_200),
                            border_radius=15,
                            content=self.map_widget # Aquí carreguem el WebView
                        )
                    ], expand=True, spacing=20)
                ])
            )
        )

    # --- LÒGICA DE FILTRES DEPENDENTS ---
    def actualitzar_comarques(self, e):
        prov_triada = self.drop_provincia.value
        # Ara aquesta funció demana només el que necessita
        noves_comarques = obtenir_comarques(prov_triada)
        
        self.drop_comarca.options = [ft.dropdown.Option("Totes")]
        for c in noves_comarques:
            self.drop_comarca.options.append(ft.dropdown.Option(c))
        
        self.drop_comarca.value = "Totes"
        self.actualitzar_localitats(e)

    def actualitzar_localitats(self, e):
        comarca_sel = self.drop_comarca.value
        provincia_sel = self.drop_provincia.value
        
        # 1. Cas: Cap filtre seleccionat (Tot a "Totes")
        if comarca_sel == "Totes" and provincia_sel == "Totes":
            noves_localitats = self.filtres_globals.localitats
            
        # 2. Cas: Només tenim la Província (Comarca és "Totes")
        elif comarca_sel == "Totes":
            noves_localitats = obtenir_localitats_de_provincia(provincia_sel)
            
        # 3. Cas: Tenim una Comarca específica
        else:
            noves_localitats = obtenir_localitats_de_comarca(comarca_sel)

        # Actualització visual
        self.drop_localitat.options = [ft.dropdown.Option("Totes")]
        for localitat in noves_localitats:
            self.drop_localitat.options.append(ft.dropdown.Option(localitat))
        
        self.drop_localitat.value = "Totes"
        self.page.update()

    # --- GESTIÓ DE CERCA I TARGETES ---
    def handle_search(self, e):
        self.results_col.controls.clear()
        self.page.update()

        resultats = executar_cerca_oferta(
            provincia=self.drop_provincia.value if self.drop_provincia.value != "Totes" else None,
            comarca=self.drop_comarca.value if self.drop_comarca.value != "Totes" else None,
            localitat=self.drop_localitat.value if self.drop_localitat.value != "Totes" else None,
            grau=self.drop_grau.value if self.drop_grau.value != "Tots" else None
        )

        for centre in resultats:
            self.results_col.controls.append(self.crear_card(centre))
        self.page.update()

    def crear_card(self, centre):
        return ft.Card(
            content=ft.Container(
                padding=10,
                on_click=lambda _: self.actualitzar_mapa_centre(centre),
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.SCHOOL),
                        title=ft.Text(centre.nom, weight="bold", size=14),
                        subtitle=ft.Text(f"{centre.nom_cicle}\n{centre.localitat}", size=12)
                    ),
                ])
            )
        )

    # --- LÒGICA DEL MAPA (Igual que el teu fitxer original) ---
    def actualitzar_mapa_centre(self, centre):
        # Necessitem lat/lon. Si el teu backend ja les torna:
        lat = getattr(centre, 'latitud', 39.46)
        lon = getattr(centre, 'longitud', -0.37)
        
        delta = 0.01 # Zoom per a un centre sol
        bbox = f"{lon-delta}%2C{lat-delta}%2C{lon+delta}%2C{lat+delta}"
        marker = f"&marker={lat}%2C{lon}"
        
        new_url = f"https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik{marker}"
        
        # Substituïm el contingut del contenidor amb un nou WebView (més robust en Flet)
        self.map_container.current.content = WebView(new_url, expand=True)
        self.page.update()

if __name__ == "__main__":
    ft.app(target=FpApp)