import flet as ft
from flet_webview import WebView
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
import boto3
import json
from fpdf import FPDF
import datetime

# ----------------------------------------------------------------------
# 1. CONFIGURACIÓ DE CONEXIÓ
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
# 2. CLASE CHATTAB (AWS Bedrock Agent + Exportació PDF)
# ----------------------------------------------------------------------
class ChatTab:
    def __init__(self, page: ft.Page):
        self.page = page
        self.messages_for_pdf = [] 
        try:
            self.session = boto3.Session(profile_name="projecte1")
            self.agent_client = self.session.client("bedrock-agent-runtime", region_name="us-east-1")
        except Exception as e:
            print(f"Error de configuració AWS: {e}")
            
        self.agent_id = "BEBBVC6EFW"
        self.agent_alias_id = "TSTALIASID"
        self.session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

        self.chat_history = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        self.user_input = ft.TextField(
            hint_text="Pregunta a l'agent d'IA sobre la FP...",
            expand=True, on_submit=self.send_message, height=45, text_size=14
        )

    def send_message(self, e):
        if not self.user_input.value: return
        user_text = self.user_input.value
        self.messages_for_pdf.append(f"Tu: {user_text}")
        self.chat_history.controls.append(
            ft.Row([ft.Container(content=ft.Text(user_text, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLUE_900, padding=10, border_radius=15)], alignment=ft.MainAxisAlignment.END)
        )
        prompt_actual = user_text
        self.user_input.value = ""
        self.page.update()

        try:
            response = self.agent_client.invoke_agent(
                agentId=self.agent_id, agentAliasId=self.agent_alias_id,
                sessionId=self.session_id, inputText=prompt_actual
            )
            full_response = ""
            for event in response.get("completion", []):
                if "chunk" in event:
                    full_response += event["chunk"]["bytes"].decode("utf-8")
            self.messages_for_pdf.append(f"IA: {full_response}")
            self.chat_history.controls.append(
                ft.Row([ft.Container(content=ft.Text(full_response, color=ft.Colors.BLACK),
                bgcolor=ft.Colors.GREY_200, padding=10, border_radius=15, width=450)], alignment=ft.MainAxisAlignment.START)
            )
        except Exception as ex:
            self.chat_history.controls.append(ft.Text(f"❌ Error: {ex}", color="red"))
        self.page.update()

    def export_to_pdf(self, e):
        if not self.messages_for_pdf: return
        
        pdf = FPDF()
        pdf.add_page()
        # Capçalera
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(0, 51, 102) # Blau fosc
        pdf.cell(200, 10, txt="Historial Assistent Virtual FP", ln=True, align='C')
        pdf.ln(10)

        # Contingut
        for msg in self.messages_for_pdf:
            if msg.startswith("Tu:"):
                pdf.set_font("Arial", "B", 11)
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.set_font("Arial", size=11)
                pdf.set_text_color(50, 50, 50)
            
            # Neteja de caràcters per a PDF
            safe_msg = msg.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 8, txt=safe_msg)
            pdf.ln(2)
        
        # Guardar fitxer temporal
        name = f"assets/chat_fp.pdf" # El guardem en la carpeta assets si la tens, o directament
        import os
        if not os.path.exists("assets"): os.makedirs("assets")
        
        path = "assets/chat_export.pdf"
        pdf.output(path)
        
        # L'ORDRE CLAU PERQUÈ L'USUARI EL VEJA:
        self.page.launch_url(f"/{path}") # Flet serveix els fitxers d'assets automàticament
        
        self.page.snack_bar = ft.SnackBar(ft.Text("PDF generat i obert!"))
        self.page.snack_bar.open = True
        self.page.update()

    @property
    def content(self):
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Text("Assistent Virtual FP", size=24, weight="bold", expand=True),
                    ft.ElevatedButton("Exportar PDF", icon=ft.Icons.PICTURE_AS_PDF, on_click=self.export_to_pdf, bgcolor=ft.Colors.RED_600, color="white")
                ]),
                ft.Container(content=self.chat_history, expand=True, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=10, padding=10, bgcolor=ft.Colors.WHITE),
                ft.Row([self.user_input, ft.IconButton(ft.Icons.SEND, on_click=self.send_message, icon_color=ft.Colors.BLUE_900)])
            ])
        )

# ----------------------------------------------------------------------
# 3. CLASE TABCONTENT (Cercador Millorat)
# ----------------------------------------------------------------------
class TabContent:
    def __init__(self, title, page, map_ref):
        self.page = page
        self.title = title
        self.map_ref = map_ref
        self.is_esp = "Especialización" in title or "Especialització" in title

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

    def update_comarcas(self, e):
        filtros = {"provincia": self.dd_prov.value} if self.dd_prov.value != "TODAS" else None
        comarcas = get_db_list("comarca", "centre", filtros)
        self.dd_comarca.options = [ft.dropdown.Option("TODAS")] + [ft.dropdown.Option(c) for c in comarcas]
        self.dd_comarca.value = "TODAS"
        self.update_localidades(None)

    def update_localidades(self, e):
        query = "SELECT DISTINCT c.localitat FROM centre c JOIN oferta o ON c.codi = o.codcen WHERE 1=1"
        params = {}
        if self.dd_prov.value != "TODAS": query += " AND c.provincia = :prov"; params["prov"] = self.dd_prov.value
        if self.dd_comarca.value != "TODAS": query += " AND c.comarca = :com"; params["com"] = self.dd_comarca.value
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
            locs = df['localitat'].tolist()
        self.dd_loc.options = [ft.dropdown.Option("TODAS")] + [ft.dropdown.Option(l) for l in locs]
        self.dd_loc.value = "TODAS"
        self.update_academic_after_loc(None)

    def update_academic_after_loc(self, e):
        self.update_grados_disponibles(None)
        self.update_ciclos(None)

    def update_grados_disponibles(self, e):
        query = "SELECT DISTINCT t.grau FROM titulacio t JOIN oferta o ON t.id = o.id_titulacio JOIN centre c ON o.codcen = c.codi WHERE 1=1"
        params = {}
        if self.dd_loc.value != "TODAS": query += " AND c.localitat = :loc"; params["loc"] = self.dd_loc.value
        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(text(query), conn, params=params)
                grados_raw = df['grau'].tolist()
                
                # --- LÒGICA DE FILTRATGE PER PESTANYA ---
                if self.is_esp:
                    # Només Cursos d'Especialització (CE)
                    grados = [g for g in grados_raw if any(x in str(g).upper() for x in ["CE ", "ESPECIALIZA", "CURSO DE ESP"])]
                else:
                    # Bàsica, Mitjà i Superior (Exclou CE)
                    grados = [g for g in grados_raw if not any(x in str(g).upper() for x in ["CE ", "ESPECIALIZA"])]
                
                self.dd_grado.options = [ft.dropdown.Option("TODOS")] + [ft.dropdown.Option(g) for g in grados]
                self.dd_grado.value = "TODOS"
        except: pass
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
        if self.dd_loc.value != "TODAS": query += " AND c.localitat = :loc"; params["loc"] = self.dd_loc.value
        if self.dd_grado.value != "TODOS": query += " AND t.grau = :grau"; params["grau"] = self.dd_grado.value
        if self.dd_familia.value != "TODAS": query += " AND t.familia = :fam"; params["fam"] = self.dd_familia.value
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
            ciclos = df['nom_cicle'].tolist()
            self.dd_ciclo.options = [ft.dropdown.Option("TODOS")] + [ft.dropdown.Option(c) for c in ciclos]
            self.dd_ciclo.value = "TODOS"
        self.page.update()

    def do_search(self, e):
        query = """
            SELECT c.nom, t.nom_cicle, c.localitat, c.latitud, c.longitud, t.grau,
                   o.regim_formatiu, o.torn, t.familia, c.titular,
                   c.direccio, c.telefon, c.correu, c.web
            FROM oferta o 
            JOIN centre c ON o.codcen = c.codi 
            JOIN titulacio t ON o.id_titulacio = t.id
            WHERE 1=1
        """
        params = {}
        f_map = {'p': (self.dd_prov.value, 'c.provincia'), 'com': (self.dd_comarca.value, 'c.comarca'), 
                 'l': (self.dd_loc.value, 'c.localitat'), 'g': (self.dd_grado.value, 't.grau'),
                 'f': (self.dd_familia.value, 't.familia'), 'cic': (self.dd_ciclo.value, 't.nom_cicle')}
        for k, (v, col) in f_map.items():
            if v and "TOD" not in str(v).upper(): query += f" AND {col} = :{k}"; params[k] = v

        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(text(query), conn, params=params)
            
            if not df.empty:
                # Aplicar filtre final segons pestanya
                mask_ce = df['grau'].str.contains("ESPECIALIZA|CE |CURSO DE ESP", case=False, na=False)
                df = df[mask_ce] if self.is_esp else df[~mask_ce]

            self.results_col.controls.clear()
            self.counter.value = f"Resultats: {len(df)}"

            if df.empty:
                self.results_col.controls.append(ft.Text("No s'han trobat centres amb aquests filtres.", italic=True))
            else:
                for _, row in df.iterrows():
                    v_reg, v_tit = str(row['regim_formatiu']).upper(), str(row['titular']).upper()
                    if any(x in v_reg or x in v_tit for x in ["PÚBLIC", "PUBLIC", "GENERALITAT"]):
                        c_sem, label = ft.Colors.GREEN_600, "PÚBLIC"
                    elif "CONCERT" in v_reg or "CONCERT" in v_tit:
                        c_sem, label = ft.Colors.AMBER_500, "CONCERTAT"
                    else:
                        c_sem, label = ft.Colors.RED_600, "PRIVAT"

                    web_raw = str(row['web']).strip()
                    url_v = None
                    if web_raw.lower() not in ["none", "nan", "", "0.0.0.0", "null", "0"]:
                        url_v = web_raw if web_raw.startswith("http") else f"http://{web_raw}"

                    self.results_col.controls.append(
            ft.Card(
                elevation=3,
                content=ft.Container(
                    padding=15,
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.SCHOOL, color=ft.Colors.BLUE_800 if "SUPERIOR" in str(row['grau']).upper() else ft.Colors.ORANGE_800),
                            ft.Text(row['nom'], weight="bold", expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Container(content=ft.Text(label, size=9, color="white", weight="bold"), bgcolor=c_sem, padding=5, border_radius=5)
                        ]),
                        # AFEDIM LA FAMÍLIA PROFESSIONAL AQUÍ
                        ft.Row([
                            ft.Icon(ft.Icons.FOLDER_OPEN, size=14, color=ft.Colors.GREY_700),
                            ft.Text(f"Família: {row['familia']}", size=12, italic=True, color=ft.Colors.GREY_700)
                        ]),
                        ft.Text(row['nom_cicle'], size=13, weight="w500"),
                        ft.Row([ft.Icon(ft.Icons.LOCATION_ON, size=16), ft.Text(f"{row['direccio']}, {row['localitat']}", size=11, expand=True)]),
                        ft.Divider(height=1),
                        ft.Row([
                            ft.TextButton("WEB", icon=ft.Icons.LANGUAGE, on_click=lambda e, u=url_v: self.page.launch_url(u) if u else None, visible=bool(url_v)),
                            ft.ElevatedButton("MAPA", icon=ft.Icons.MAP, on_click=lambda _, r=row: self.update_map(r))
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ])
                )
            )
        )
        except Exception as ex: print(ex)
        self.page.update()

    def update_map(self, row):
        lat, lon = row['latitud'], row['longitud']
        url = f"https://www.openstreetmap.org/export/embed.html?bbox={lon-0.005}%2C{lat-0.005}%2C{lon+0.005}%2C{lat+0.005}&layer=mapnik&marker={lat}%2C{lon}"
        self.map_ref.current.content = WebView(url, expand=True)
        self.page.update()

# ----------------------------------------------------------------------
# 4. FUNCIÓ PRINCIPAL
# ----------------------------------------------------------------------
def main(page: ft.Page):
    page.title = "Projecte Ferran - FP GVA"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    map_container_ref = ft.Ref[ft.Container]()
    map_view = ft.Container(ref=map_container_ref, expand=True, bgcolor=ft.Colors.GREY_100, 
                           alignment=ft.alignment.center, content=ft.Text("Selecciona un centre"))

    tab_std = TabContent("Estàndard (Bàsica/Mitjà/Superior)", page, map_container_ref)
    tab_esp = TabContent("Especialització (Màsters FP)", page, map_container_ref)
    tab_chat = ChatTab(page)

    page.add(ft.Row([
        ft.Column([
            ft.Tabs(tabs=[
                ft.Tab(text="Estàndard", icon=ft.Icons.SCHOOL, content=tab_std.content), 
                ft.Tab(text="Especialització", icon=ft.Icons.STAR, content=tab_esp.content),
                ft.Tab(text="Agent IA", icon=ft.Icons.AUTO_AWESOME, content=tab_chat.content) 
            ], expand=True)
        ], expand=2),
        ft.VerticalDivider(width=1),
        ft.Column([map_view], expand=3)
    ], expand=True))

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER,assets_dir="assets")