import flet as ft
from flet_webview import WebView
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse

# ----------------------------------------------------------------------
# 1. CONFIGURACIÓN DE CONEXIÓN
# ----------------------------------------------------------------------
password = urllib.parse.quote_plus("root") 
engine = create_engine(f"mysql+mysqlconnector://root:{password}@localhost/fpdb")

def get_db_list(column, table, filters=None):
    query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL AND {column} != ''"
    params = {}
    if filters:
        for k, v in filters.items():
            if v and "TOT" not in str(v).upper():
                query += f" AND {k} = :{k}"
                params[k] = v
    query += f" ORDER BY {column} ASC"
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
            return df[column].tolist()
    except Exception as e:
        print(f"Error SQL: {e}")
        return []

# ----------------------------------------------------------------------
# 2. CLASE DE INTERFAZ
# ----------------------------------------------------------------------
class TabContent:
    def __init__(self, title, page, map_ref):
        self.page = page
        self.title = title
        self.map_ref = map_ref
        self.is_esp = "Especialización" in title

        # Dropdowns - Definición y Eventos
        self.dd_prov = ft.Dropdown(label="Provincia", expand=True, on_change=self.update_comarcas)
        self.dd_comarca = ft.Dropdown(label="Comarca", expand=True, on_change=self.update_localidades)
        self.dd_loc = ft.Dropdown(label="Localidad", expand=True, on_change=self.update_academic_after_loc)
        
        self.dd_grado = ft.Dropdown(label="Grado", expand=True, on_change=self.update_academic_filters)
        self.dd_familia = ft.Dropdown(label="Familia", expand=True, on_change=self.update_ciclos)
        self.dd_ciclo = ft.Dropdown(label="Ciclo", expand=True)

        self.results_col = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)
        self.counter = ft.Text("Resultados: 0", weight="bold", size=16)

        self.load_initial_data()

        self.content = ft.Column([
            ft.Text(f"Buscador {title}", size=22, weight="bold", color=ft.Colors.BLUE_900),
            ft.Container(
                bgcolor=ft.Colors.BLUE_GREY_50, padding=20, border_radius=15,
                content=ft.Column([
                    ft.Row([self.dd_prov, self.dd_comarca, self.dd_loc]),
                    ft.Row([self.dd_grado, self.dd_familia, self.dd_ciclo]),
                    ft.ElevatedButton("BUSCAR", icon=ft.Icons.SEARCH, on_click=self.do_search, height=50, expand=True)
                ])
            ),
            self.counter,
            self.results_col
        ], expand=True)

    def load_initial_data(self):
        provincias = get_db_list("provincia", "centre")
        self.dd_prov.options = [ft.dropdown.Option("TODAS")] + [ft.dropdown.Option(p) for p in provincias]
        self.dd_prov.value = "TODAS"
        self.update_comarcas(None)

    # --- FLUJO GEOGRÁFICO ---

    def update_comarcas(self, e):
        filtros = {"provincia": self.dd_prov.value} if self.dd_prov.value != "TODAS" else None
        comarcas = get_db_list("comarca", "centre", filtros)
        self.dd_comarca.options = [ft.dropdown.Option("TODAS")] + [ft.dropdown.Option(c) for c in comarcas]
        self.dd_comarca.value = "TODAS"
        self.update_localidades(None)

    def update_localidades(self, e):
        query = "SELECT DISTINCT c.localitat FROM centre c JOIN oferta o ON c.codi = o.codcen WHERE 1=1"
        params = {}
        if self.dd_prov.value != "TODAS":
            query += " AND c.provincia = :prov"; params["prov"] = self.dd_prov.value
        if self.dd_comarca.value != "TODAS":
            query += " AND c.comarca = :com"; params["com"] = self.dd_comarca.value
        
        with engine.connect() as conn:
            locs = pd.read_sql_query(text(query), conn, params=params)['localitat'].tolist()
        
        self.dd_loc.options = [ft.dropdown.Option("TODAS")] + [ft.dropdown.Option(l) for l in locs]
        self.dd_loc.value = "TODAS"
        self.update_academic_after_loc(None)

    # --- FLUJO ACADÉMICO ---

    def update_academic_after_loc(self, e):
        self.update_grados_disponibles(None)
        self.update_ciclos(None)

    def update_grados_disponibles(self, e):
        query = """
            SELECT DISTINCT t.grau FROM titulacio t 
            JOIN oferta o ON t.id = o.id_titulacio 
            JOIN centre c ON o.codcen = c.codi WHERE 1=1
        """
        params = {}
        if self.dd_loc.value != "TODAS":
            query += " AND c.localitat = :loc"; params["loc"] = self.dd_loc.value
        
        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(text(query), conn, params=params)
                grados_raw = df['grau'].tolist()
                
                if self.is_esp:
                    # CE que NO son básicos
                    grados = [g for g in grados_raw if ("CE " in g or "ESPECIALIZACI" in g.upper()) and "BÁSICO" not in g.upper()]
                else:
                    # Estándar: Incluye Básico, Medio, Superior y Básica 2ª Oportunidad (OPORTUNIDAD)
                    grados = [g for g in grados_raw if not ("CE " in g or "ESPECIALIZACI" in g.upper()) or "BÁSICO" in g.upper() or "OPORTUNIDAD" in g.upper()]

                self.dd_grado.options = [ft.dropdown.Option("TODOS")] + [ft.dropdown.Option(g) for g in grados]
                self.dd_grado.value = "TODOS"
        except Exception as ex: print(f"Error Grados: {ex}")
        self.page.update()

    def update_academic_filters(self, e):
        filtros = {"grau": self.dd_grado.value} if self.dd_grado.value != "TODOS" else None
        familias = get_db_list("familia", "titulacio", filtros)
        self.dd_familia.options = [ft.dropdown.Option("TODAS")] + [ft.dropdown.Option(f) for f in familias]
        self.dd_familia.value = "TODAS"
        self.update_ciclos(None)

    def update_ciclos(self, e):
        query = "SELECT DISTINCT t.nom_cicle FROM titulacio t JOIN oferta o ON t.id = o.id_titulacio JOIN centre c ON o.codcen = c.codi WHERE 1=1"
        params = {}
        if self.dd_loc.value != "TODAS":
            query += " AND c.localitat = :loc"; params["loc"] = self.dd_loc.value
        if self.dd_grado.value != "TODOS":
            query += " AND t.grau = :grau"; params["grau"] = self.dd_grado.value
        if self.dd_familia.value != "TODAS":
            query += " AND t.familia = :fam"; params["fam"] = self.dd_familia.value
            
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
            ciclos = df['nom_cicle'].tolist()
            self.dd_ciclo.options = [ft.dropdown.Option("TODOS")] + [ft.dropdown.Option(c) for c in ciclos]
            self.dd_ciclo.value = "TODOS"
        self.page.update()

    # --- BÚSQUEDA Y MAPA ---

    def do_search(self, e):
        query = """
            SELECT c.nom, t.nom_cicle, c.localitat, c.latitud, c.longitud, t.grau
            FROM oferta o JOIN centre c ON o.codcen = c.codi JOIN titulacio t ON o.id_titulacio = t.id
            WHERE 1=1
        """
        params = {}
        f_map = {'p':(self.dd_prov.value,'c.provincia'), 'com':(self.dd_comarca.value,'c.comarca'), 
                 'l':(self.dd_loc.value,'c.localitat'), 'g':(self.dd_grado.value,'t.grau'),
                 'f':(self.dd_familia.value, 't.familia'), 'cic':(self.dd_ciclo.value, 't.nom_cicle')}
        
        for k, (v, col) in f_map.items():
            if v and "TOD" not in str(v).upper():
                query += f" AND {col} = :{k}"; params[k] = v

        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)

        mask_ce = df['grau'].str.contains("ESPECIALIZACI|CURSO|CE ", case=False, na=False)
        # Excepción para que Básica 2 siempre sea estándar
        mask_basica = df['grau'].str.contains("BÁSICO|OPORTUNIDAD", case=False, na=False)
        
        if self.is_esp:
            df = df[mask_ce & ~mask_basica]
        else:
            df = df[~mask_ce | mask_basica]

        self.results_col.controls.clear()
        self.counter.value = f"Resultados: {len(df)}"
        for _, row in df.iterrows():
            self.results_col.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.SCHOOL),
                    title=ft.Text(row['nom'], weight="bold"),
                    subtitle=ft.Text(f"{row['nom_cicle']} ({row['localitat']})"),
                    on_click=lambda _, r=row: self.update_map(r)
                )
            )
        self.page.update()

    def update_map(self, row):
        lat, lon = row['latitud'], row['longitud']
        url = f"https://www.openstreetmap.org/export/embed.html?bbox={lon-0.005}%2C{lat-0.005}%2C{lon+0.005}%2C{lat+0.005}&layer=mapnik&marker={lat}%2C{lon}"
        self.map_ref.current.content = WebView(url, expand=True)
        self.page.update()

# ----------------------------------------------------------------------
# 3. MAIN
# ----------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "FP GVA - Buscador"
    map_container_ref = ft.Ref[ft.Container]()
    map_view = ft.Container(ref=map_container_ref, expand=True, bgcolor=ft.Colors.GREY_100, alignment=ft.alignment.center)

    tab_std = TabContent("FP Estándar", page, map_container_ref)
    tab_esp = TabContent("Especialización", page, map_container_ref)

    page.add(ft.Row([
        ft.Column([ft.Tabs(tabs=[ft.Tab(text="Estándar", content=tab_std.content), 
                                ft.Tab(text="Especialización", content=tab_esp.content)], expand=True)], expand=2),
        ft.VerticalDivider(), map_view
    ], expand=True))

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER)