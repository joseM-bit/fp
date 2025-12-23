import flet as ft
import pandas as pd
import webbrowser
import numpy as np
import hashlib
from flet import Container, Text, Column, Row, padding 

# ----------------------------------------------------------------------
# 1. CÀRREGA I PREPROCESSAMENT DE DADES DE FP 
# ----------------------------------------------------------------------

# Noms d'arxius
FP_FILE = "oferta_fp_25_26.csv"
ESP_FILE = "oferta_fp_especialitzacio.csv" 

# Columnes finals esperades (9 elements)
FP_COLS = ['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'GRADO', 'FAMILIA', 'CICLO', 'TURNO', 'UNIDADES']
CANONICAL_GRADES = ['BÁSICO', 'BÁSICO 2A OPORTUNIDAD', 'MEDIO', 'SUPERIOR']

# --- MAPA DE ESTANDARITZACIÓ DE PROVÍNCIES ---
PROVINCE_MAP = {
    'ALACANT': 'ALACANT',
    'ALICANTE': 'ALACANT',
    'VALÈNCIA': 'VALÈNCIA',
    'VALENCIA': 'VALÈNCIA', 
    'CASTELLÓ': 'CASTELLÓ',
    'CASTELLO': 'CASTELLÓ',
    'CASTELLÓN': 'CASTELLÓ',
    'VALÈNCIA.': 'VALÈNCIA',
}

# --- DADES DE GEOLOCALITZACIÓ SIMULADES (Coordenades centrals de la província) ---
PROVINCE_CENTER_COORDS = {
    'ALACANT': {'lat': 38.3452, 'lon': -0.4810, 'delta_lat': 0.15, 'delta_lon': 0.2},
    'VALÈNCIA': {'lat': 39.4699, 'lon': -0.3763, 'delta_lat': 0.15, 'delta_lon': 0.15},
    'CASTELLÓ': {'lat': 39.9871, 'lon': -0.0381, 'delta_lat': 0.15, 'delta_lon': 0.2},
}

# Diccionari per guardar coordenades consistents per a cada centre
coords_cache = {}

def get_consistent_coords(row):
    """Retorna coordenades consistents basades en un hash del centre i localitat."""
    key = f"{row['PROVINCIA']}_{row['LOCALIDAD']}_{row['CENTRO']}"
    
    # Si ja hem calculat les coordenades per aquest centre, retornem-les
    if key in coords_cache:
        return pd.Series(coords_cache[key])
    
    # Si no, generem coordenades consistents
    if row['PROVINCIA'] in PROVINCE_CENTER_COORDS:
        # Crear un hash del nom del centre per a generar valors consistents
        hash_str = hashlib.md5(key.encode()).hexdigest()
        
        # Convertir el hash a valors numèrics per a latitud i longitud
        hash_int_lat = int(hash_str[:8], 16)  # Primer 8 caràcters hex per latitud
        hash_int_lon = int(hash_str[8:16], 16)  # Següents 8 caràcters hex per longitud
        
        # Normalitzar els valors entre 0 i 1
        norm_lat = hash_int_lat / 0xFFFFFFFF
        norm_lon = hash_int_lon / 0xFFFFFFFF
        
        base = PROVINCE_CENTER_COORDS[row['PROVINCIA']]
        
        # Generar coordenades dins del rang de la província
        # Utilitzem una distribució més realista: concentració al voltant del centre provincial
        lat = base['lat'] + (norm_lat - 0.5) * base['delta_lat'] * 1.5
        lon = base['lon'] + (norm_lon - 0.5) * base['delta_lon'] * 1.5
        
        # Per a les localitats, ajustem les coordenades perquè centres de la mateixa localitat estiguin a prop
        localidad_hash = hashlib.md5(f"{row['PROVINCIA']}_{row['LOCALIDAD']}".encode()).hexdigest()
        localidad_int = int(localidad_hash[:8], 16)
        norm_localidad = localidad_int / 0xFFFFFFFF
        
        # Ajust més petit per a centres de la mateixa localitat
        localidad_lat_offset = (norm_localidad - 0.5) * base['delta_lat'] * 0.3
        localidad_lon_offset = (norm_localidad - 0.5) * base['delta_lon'] * 0.3
        
        lat += localidad_lat_offset
        lon += localidad_lon_offset
        
        result = {'latitud': lat, 'longitud': lon}
        coords_cache[key] = result
        return pd.Series(result)
    
    return pd.Series({'latitud': 0.0, 'longitud': 0.0})

def standardize_grade(g_upper):
    """Mapeja el text de la columna GRADO a les categories canòniques de FP Estàndard."""
    if pd.isna(g_upper): return None
    g_upper = g_upper.upper().strip()
    if 'BÁSICO 2A OPORT' in g_upper or 'BÁSICO 2ª OPORT' in g_upper: return 'BÁSICO 2A OPORTUNIDAD'
    if 'BÁSICO' in g_upper: return 'BÁSICO'
    if 'MEDIO' in g_upper: return 'MEDIO'
    if 'SUPERIOR' in g_upper: return 'SUPERIOR'
    return None 

def standardize_esp_grade(g_upper):
    """Mapeja el text de la columna GRADO a les categories canòniques de Especialització (Medio/Superior)."""
    if pd.isna(g_upper): return 'ESPECIALIZACIÓN'
    g_upper = g_upper.upper().strip()
    if 'SUPERIOR' in g_upper: return 'SUPERIOR'
    if 'MEDIO' in g_upper: return 'MEDIO'
    return 'ESPECIALIZACIÓN'


def load_and_clean_data():
    """Càrrega i neteja els dos arxius CSV, retornant un dict de DataFrames amb coordenades simulades."""
    data_frames = {}

    # --- Processar oferta_fp_25_26.csv (FP Standard) ---
    try:
        df_fp = pd.read_csv(FP_FILE, header=None, skiprows=lambda x: x < 4, encoding='utf-8')
        
        if df_fp.shape[1] >= 9:
            df_fp = df_fp.iloc[:, :9].copy()
            df_fp.columns = FP_COLS
        elif df_fp.shape[1] >= 8:
            df_fp = df_fp.iloc[:, :8].copy()
            df_fp.columns = ['PROVINCIA', 'LOCALIDAD', 'CENTRO_REGIMEN', 'GRADO_RAW', 'FAMILIA', 'CICLO', 'TURNO', 'UNIDADES']
            df_fp['RÉGIMEN'] = df_fp['CENTRO_REGIMEN'].astype(str).str.split().str[-1]
            df_fp['CENTRO'] = df_fp['CENTRO_REGIMEN'].astype(str).apply(lambda x: ' '.join(x.split()[:-1]))
            df_fp.drop(columns=['CENTRO_REGIMEN'], inplace=True)
            df_fp = df_fp[['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'GRADO_RAW', 'FAMILIA', 'CICLO', 'TURNO', 'UNIDADES']].copy()
            df_fp.columns = FP_COLS
        else:
            raise ValueError(f"L'arxiu {FP_FILE} té menys de 8 columnes.")
        
        df_fp['PROVINCIA'] = df_fp['PROVINCIA'].astype(str).str.strip().str.upper()
        df_fp['PROVINCIA'] = df_fp['PROVINCIA'].apply(lambda x: PROVINCE_MAP.get(x, x))
        df_fp['GRADO'] = df_fp['GRADO'].astype(str).apply(standardize_grade)
        df_fp['RÉGIMEN'] = df_fp['RÉGIMEN'].astype(str).str.split(',').str[0].str.strip().str.upper()
        df_fp = df_fp[df_fp['GRADO'].isin(CANONICAL_GRADES)].copy()
        df_fp['UNIDADES'] = pd.to_numeric(df_fp['UNIDADES'], errors='coerce').fillna(0).astype(int)
        
        for col in ['LOCALIDAD', 'CENTRO', 'FAMILIA', 'CICLO', 'TURNO']:
             df_fp[col] = df_fp[col].astype(str).str.strip().str.upper().replace('NAN', '', regex=False)

        # Aplicar coordenades consistents
        df_fp[['latitud', 'longitud']] = df_fp.apply(get_consistent_coords, axis=1)

        data_frames['FP_STANDARD'] = df_fp
        print(f"✅ Carregat {FP_FILE} amb {len(df_fp)} registres.")
        print(f"   Exemple de coordenades: {df_fp.iloc[0]['CENTRO']} -> {df_fp.iloc[0]['latitud']}, {df_fp.iloc[0]['longitud']}")
    except Exception as e:
        print(f"❌ Error en carregar {FP_FILE}: {e}")
        data_frames['FP_STANDARD'] = pd.DataFrame(columns=FP_COLS + ['latitud', 'longitud'])


    # --- Processar oferta_fp_especialitzacio.csv (Especialització) ---
    try:
        df_esp = pd.read_csv(ESP_FILE, header=None, skiprows=lambda x: x < 3, encoding='utf-8', on_bad_lines='skip')
        
        if df_esp.shape[1] >= 9:
            df_esp = df_esp.iloc[:, :9].copy()
            df_esp.columns = ['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'GRADO', 'FAMILIA', 'CICLO', 'TURNO', 'UNIDADES']
        else:
             raise ValueError(f"L'arxiu {ESP_FILE} té menys de 9 columnes.")

        df_esp['GRADO'] = df_esp['GRADO'].astype(str).apply(standardize_esp_grade)
        df_esp['PROVINCIA'] = df_esp['PROVINCIA'].astype(str).str.strip().str.upper()
        df_esp['PROVINCIA'] = df_esp['PROVINCIA'].apply(lambda x: PROVINCE_MAP.get(x, x))
        df_esp['RÉGIMEN'] = df_esp['RÉGIMEN'].astype(str).str.split(',').str[0].str.strip().str.upper()
        df_esp['UNIDADES'] = pd.to_numeric(df_esp['UNIDADES'], errors='coerce').fillna(0).astype(int)
        for col in ['LOCALIDAD', 'CENTRO', 'FAMILIA', 'CICLO', 'TURNO']:
             df_esp[col] = df_esp[col].astype(str).str.strip().str.upper().replace('NAN', '', regex=False)
        
        df_esp = df_esp[df_esp['GRADO'] != 'ESPECIALIZACIÓN'].copy()
        # Aplicar coordenades consistents
        df_esp[['latitud', 'longitud']] = df_esp.apply(get_consistent_coords, axis=1)

        data_frames['FP_ESPECIALIZACION'] = df_esp
        print(f"✅ Carregat {ESP_FILE} amb {len(df_esp)} registres.")
        print(f"   Exemple de coordenades: {df_esp.iloc[0]['CENTRO']} -> {df_esp.iloc[0]['latitud']}, {df_esp.iloc[0]['longitud']}")
    except Exception as e:
        print(f"❌ Error en carregar {ESP_FILE}: {e}")
        data_frames['FP_ESPECIALIZACION'] = pd.DataFrame(columns=FP_COLS + ['latitud', 'longitud'])

    return data_frames

def get_clean_sorted_list(series):
    """Filtra NaNs, converteix a string i ordena la llista de valors únics."""
    return sorted(series.dropna().astype(str).str.strip().unique().tolist())

data_dict = load_and_clean_data()
fp_standard_df = data_dict['FP_STANDARD']
fp_esp_df = data_dict['FP_ESPECIALIZACION']


# ----------------------------------------------------------------------
# 2. LÒGICA DE MAPES 
# ----------------------------------------------------------------------

def get_osm_url_all_centers(data_subset: pd.DataFrame) -> str:
    """Calcula el centre i el zoom per a l'URL d'OSM amb TOTS els marcadors."""
    default_lat, default_lon = 39.4699, -0.3763 # València
    
    if data_subset.empty:
        lat, lon = default_lat, default_lon
        delta = 0.5  # Zoom per defecte per veure tota la Comunitat
    else:
        # Filtrar coordenades vàlides (no 0,0)
        valid_coords = data_subset[(data_subset['latitud'] != 0.0) & (data_subset['longitud'] != 0.0)]
        
        if len(valid_coords) == 0:
            lat, lon = default_lat, default_lon
            delta = 0.5
        else:
            lat_min, lat_max = valid_coords['latitud'].min(), valid_coords['latitud'].max()
            lon_min, lon_max = valid_coords['longitud'].min(), valid_coords['longitud'].max()
            
            lat = (lat_min + lat_max) / 2
            lon = (lon_min + lon_max) / 2
            
            lat_range = lat_max - lat_min
            lon_range = lon_max - lon_min
            
            # Afegir un marge del 20%
            delta = max(lat_range, lon_range, 0.1) * 1.2

    bbox_str = f"{lon-delta}%2C{lat-delta}%2C{lon+delta}%2C{lat+delta}"
    
    markers = ""
    for _, row in data_subset.head(100).iterrows(): 
        if row['latitud'] != 0.0 and row['longitud'] != 0.0:
            markers += f"&marker={row['latitud']}%2C{row['longitud']}"

    return (f"https://www.openstreetmap.org/export/embed.html?"
            f"bbox={bbox_str}&"
            f"layer=mapnik"
            f"{markers}")

def get_osm_url_single_center(lat: float, lon: float, center_name: str, localidad: str, provincia: str) -> str:
    """Genera URL d'OSM centrada en un sol marcador amb informació."""
    if lat == 0.0 and lon == 0.0:
        # Si no tenim coordenades vàlides, centrem a la província
        if provincia in PROVINCE_CENTER_COORDS:
            base = PROVINCE_CENTER_COORDS[provincia]
            lat, lon = base['lat'], base['lon']
            delta = 0.1
        else:
            lat, lon = 39.4699, -0.3763  # València per defecte
            delta = 0.1
    else:
        delta = 0.01  # Zoom més proper per a un sol centre
    
    bbox_str = f"{lon-delta}%2C{lat-delta}%2C{lon+delta}%2C{lat+delta}"
    
    # Crear un marcador amb etiqueta
    marker = f"&marker={lat}%2C{lon}"
    
    return (f"https://www.openstreetmap.org/export/embed.html?"
            f"bbox={bbox_str}&"
            f"layer=mapnik"
            f"{marker}")

# ----------------------------------------------------------------------
# 3. Lògica i UI de Flet 
# ----------------------------------------------------------------------

def get_regime_style(regime: str):
    regime_upper = regime.upper()
    if 'PÚBLICO' in regime_upper:
        return ft.Colors.BLUE_700, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_700), ft.Icons.SCHOOL
    elif 'PRIVADO' in regime_upper:
        return ft.Colors.RED_700, ft.Colors.with_opacity(0.1, ft.Colors.RED_700), ft.Icons.BUSINESS
    else:
        return ft.Colors.GREY_700, ft.Colors.with_opacity(0.1, ft.Colors.GREY_700), ft.Icons.APARTMENT

class TabContent:
    """Classe que encapsula el contingut d'una pestanya."""
    def __init__(self, page: ft.Page, initial_df: pd.DataFrame, title: str, map_container_ref: ft.Ref):
        self.page = page
        self.initial_df = initial_df
        self.title = title
        self.map_container_ref = map_container_ref
        self.selected_card_index = None
        self.current_filtered_df = pd.DataFrame()
        
        # Preparació de dades específiques de la pestanya
        self.PROVINCES = get_clean_sorted_list(initial_df['PROVINCIA'])
        self.GRADES = get_clean_sorted_list(initial_df['GRADO'])
        self.CYCLES = get_clean_sorted_list(initial_df['CICLO'])
        
        # Controles de UI
        self.results_list_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)
        self.counter_text = ft.Text("Ofertes trobades: 0", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)
        self.total_units_text = ft.Text("Unitats ofertades: 0", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800)
        
        # Dropdowns
        province_options = [ft.dropdown.Option("TOTES LES PROVÍNCIES")] + [ft.dropdown.Option(p) for p in self.PROVINCES]
        self.province_dropdown = ft.Dropdown(options=province_options, label="Província", width=180, value="TOTES LES PROVÍNCIES")
        
        grade_options = [ft.dropdown.Option("TOTS ELS GRAUS")] + [ft.dropdown.Option(g) for g in self.GRADES]
        self.grade_dropdown = ft.Dropdown(options=grade_options, label="Grau (FP)", width=280, value="TOTS ELS GRAUS")

        cycle_options = [ft.dropdown.Option("TOTS ELS CICLES/CURSOS")] + [ft.dropdown.Option(c) for c in self.CYCLES]
        self.cycle_dropdown = ft.Dropdown(options=cycle_options, label="Cicle / Curs", width=400, value="TOTS ELS CICLES/CURSOS")
        
        # Botons
        self.update_button = ft.ElevatedButton(text="🔍 Aplicar Filtres", icon=ft.Icons.SEARCH, on_click=self.update_results, style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, padding=ft.padding.symmetric(horizontal=20, vertical=12), elevation=5), height=45)
        self.clear_button = ft.TextButton(text="Netejar Filtres", icon=ft.Icons.CLEAR_ALL, on_click=self.clear_filters, style=ft.ButtonStyle(color=ft.Colors.GREY_700), height=45)
        
        self.show_all_button = ft.ElevatedButton(
            text="📌 Mostrar tots els centres",
            icon=ft.Icons.MAP,
            on_click=self.show_all_centers,
            style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE),
            height=40
        )
        
        # Assignació de Handlers
        self.province_dropdown.on_change = self.update_cycle_dropdown
        self.grade_dropdown.on_change = self.update_cycle_dropdown
        
        # Construcció de la interfície
        self.filter_section = ft.Container(
            padding=ft.padding.all(15),
            border_radius=10,
            bgcolor=ft.Colors.BLUE_GREY_50,
            content=ft.Column([
                ft.Text(f"Filtres per a {title}", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_800),
                ft.Row([
                    self.province_dropdown,
                    self.grade_dropdown,
                    self.cycle_dropdown,
                    ft.Container(width=20),
                    self.update_button,
                    self.clear_button
                ], vertical_alignment=ft.CrossAxisAlignment.END)
            ], spacing=10)
        )
        
        self.results_section = ft.Column([
            ft.Row([
                self.counter_text,
                ft.Container(width=20),
                self.total_units_text,
                ft.Container(expand=True),
                ft.Text("Fes clic a qualsevol targeta per veure-la al mapa", size=12, color=ft.Colors.GREY_500)
            ]),
            ft.Container(
                content=self.results_list_column,
                height=600,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=10,
                padding=10,
                bgcolor=ft.Colors.WHITE
            )
        ], spacing=10, expand=1)
        
        self.content = ft.Column(
            controls=[self.filter_section, self.results_section],
            expand=True
        )
        
        # Inicialitzar amb dades
        self.initialize_results()
    
    def create_offer_card(self, offer_data: pd.Series, index: int) -> ft.Card:
        """Crea una targeta d'oferta amb interacció de clic."""
        regime_color, bg_color, icon = get_regime_style(offer_data['RÉGIMEN'])
        
        search_query = f"{offer_data['CENTRO']}, {offer_data['LOCALIDAD']}, {offer_data['PROVINCIA']}"
        map_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}" 

        def open_map_external(e):
            e.control.stop_propagation()
            webbrowser.open(map_url)

        def on_card_click(e):
            """Quan es fa clic a la targeta, es selecciona i es centra el mapa."""
            # Desmarcar la targeta prèviament seleccionada
            if self.selected_card_index is not None and self.selected_card_index < len(self.results_list_column.controls):
                old_card = self.results_list_column.controls[self.selected_card_index]
                if hasattr(old_card.content, 'bgcolor'):
                    old_card.content.bgcolor = ft.Colors.WHITE
                    old_card.elevation = 2
                    old_card.content.border = None
            
            # Marcar la nova targeta seleccionada
            self.selected_card_index = index
            e.control.bgcolor = ft.Colors.BLUE_50
            e.control.border = ft.border.all(2, ft.Colors.BLUE_500)
            e.control.elevation = 5
            
            # Centrar el mapa en aquest centre
            self.center_map_on_selected(offer_data)
            
            self.page.update()
        
        grado_text = offer_data['GRADO'].upper() if offer_data['GRADO'] else 'N/A' 
        is_esp_course = 'CURSO' in offer_data['CICLO'].upper()
        
        grado_style_text = grado_text
        if is_esp_course:
            grado_style_text = f"C. ESP. ({grado_text})"
        
        # Informació de coordenades per a debugging
        coords_info = f"Coordenades: {offer_data['latitud']:.4f}, {offer_data['longitud']:.4f}" if offer_data['latitud'] != 0.0 else "Coordenades no disponibles"
        
        # Crear contingut de la targeta
        card_content = ft.Container(
            padding=15,
            bgcolor=ft.Colors.WHITE,
            border_radius=8,
            on_click=on_card_click,
            content=ft.Column([
                ft.Row([
                    ft.Text(offer_data['CICLO'], weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.BLUE_GREY_900, expand=True),
                    ft.Container(
                        content=ft.Text(grado_style_text, size=11, color=regime_color, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.with_opacity(0.1, regime_color), 
                        border_radius=8, 
                        padding=ft.padding.symmetric(horizontal=10, vertical=4)
                    )
                ], spacing=10),
                
                ft.Divider(height=5, color=ft.Colors.GREY_200),
                
                ft.Row([
                    ft.Icon(icon, size=16, color=regime_color),
                    ft.Text(offer_data['CENTRO'], size=13, color=ft.Colors.GREY_800, weight=ft.FontWeight.W_600, expand=True),
                    ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=14, color=ft.Colors.GREY_600),
                    ft.Text(f"{offer_data['LOCALIDAD']} ({offer_data['PROVINCIA']})", size=12, color=ft.Colors.GREY_700)
                ], spacing=8),

                ft.Row([
                    ft.Icon(ft.Icons.CATEGORY_OUTLINED, size=16, color=ft.Colors.INDIGO_600),
                    ft.Text(f"Família: {offer_data['FAMILIA']}", size=12, color=ft.Colors.GREY_700),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.ACCESS_TIME, size=16, color=ft.Colors.AMBER_700),
                    ft.Text(f"Torn: {offer_data['TURNO']}", size=12, color=ft.Colors.GREY_700),
                    ft.Container(width=10),
                    ft.Icon(ft.Icons.GROUP, size=16, color=ft.Colors.GREEN_700),
                    ft.Text(f"Unitats: {offer_data['UNIDADES']}", size=12, color=ft.Colors.GREY_700, weight=ft.FontWeight.BOLD),
                    ft.Container(width=10),
                    
                    ft.TextButton(
                        "Veure ubicació (GMaps)",
                        icon=ft.Icons.MAP_OUTLINED,
                        on_click=open_map_external,
                        style=ft.ButtonStyle(color=ft.Colors.BLUE_500, padding=0)
                    )
                ], spacing=5),
                
                # Informació de coordenades (oculta normalment, útil per debugging)
                ft.Container(
                    content=ft.Text(coords_info, size=9, color=ft.Colors.GREY_500, italic=True),
                    visible=False  # Canvia a True per veure coordenades
                )
            ], spacing=8)
        )
        
        return ft.Card(
            elevation=2,
            content=card_content
        )
    
    def center_map_on_selected(self, offer_data: pd.Series):
        """Centra el mapa en el centre seleccionat."""
        if self.map_container_ref.current:
            # Crear contingut detallat per al mapa
            map_content = ft.Column([
                ft.Row([
                    ft.Text(f"📍 {offer_data['CENTRO']}", size=16, weight="bold", expand=True),
                    self.show_all_button
                ]),
                ft.Text(f"{offer_data['LOCALIDAD']} ({offer_data['PROVINCIA']})", size=14, color=ft.Colors.BLUE_700, weight=ft.FontWeight.W_600),
                ft.Text(f"{offer_data['CICLO']} - {offer_data['FAMILIA']}", size=12, color=ft.Colors.GREY_600),
                ft.Text(f"Grau: {offer_data['GRADO']} | Torn: {offer_data['TURNO']} | Unitats: {offer_data['UNIDADES']}", size=11, color=ft.Colors.GREY_500),
                ft.Container(
                    ft.WebView(
                        url=get_osm_url_single_center(
                            offer_data['latitud'], 
                            offer_data['longitud'],
                            offer_data['CENTRO'],
                            offer_data['LOCALIDAD'],
                            offer_data['PROVINCIA']
                        ),
                        expand=True
                    ),
                    height=650,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                ),
                ft.Text(f"Coordenades: {offer_data['latitud']:.6f}, {offer_data['longitud']:.6f}", 
                       size=10, color=ft.Colors.GREY_500, italic=True)
            ], spacing=10)
            
            self.map_container_ref.current.content = ft.Container(
                content=map_content,
                padding=10
            )
            self.page.update()
    
    def show_all_centers(self, e=None):
        """Torna a mostrar tots els centres al mapa."""
        if self.map_container_ref.current and not self.current_filtered_df.empty:
            # Desmarcar la targeta seleccionada
            if self.selected_card_index is not None and self.selected_card_index < len(self.results_list_column.controls):
                old_card = self.results_list_column.controls[self.selected_card_index]
                if hasattr(old_card.content, 'bgcolor'):
                    old_card.content.bgcolor = ft.Colors.WHITE
                    old_card.elevation = 2
                    old_card.content.border = None
            
            self.selected_card_index = None
            
            # Crear contingut per mostrar tots els centres
            map_content = ft.Column([
                ft.Text(f"📍 Mapa de tots els centres ({len(self.current_filtered_df)} centres)", 
                       size=18, weight="bold"),
                ft.Container(
                    ft.WebView(
                        url=get_osm_url_all_centers(self.current_filtered_df),
                        expand=True
                    ),
                    height=700,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                ),
                ft.Text(f"Mostrant fins a 100 marcadors. Total de centres: {len(self.current_filtered_df)}", 
                       size=12, color=ft.Colors.GREY_600)
            ], spacing=10)
            
            self.map_container_ref.current.content = ft.Container(
                content=map_content,
                padding=10
            )
            self.page.update()
    
    def update_cycle_dropdown(self, e=None):
        """Actualitza el dropdown de cicles segons els filtres seleccionats."""
        filtered_df = self.initial_df.copy()
        selected_province = self.province_dropdown.value
        selected_grade = self.grade_dropdown.value
        
        if selected_province and selected_province != "TOTES LES PROVÍNCIES":
            filtered_df = filtered_df[filtered_df['PROVINCIA'] == selected_province]
            
        if selected_grade and selected_grade != "TOTS ELS GRAUS":
            filtered_df = filtered_df[filtered_df['GRADO'] == selected_grade]
        
        filtered_cycles = get_clean_sorted_list(filtered_df['CICLO'])
        
        self.cycle_dropdown.options.clear()
        self.cycle_dropdown.options.append(ft.dropdown.Option("TOTS ELS CICLES/CURSOS"))
        self.cycle_dropdown.options.extend([ft.dropdown.Option(c) for c in filtered_cycles])
        self.cycle_dropdown.value = "TOTS ELS CICLES/CURSOS"
        
        if e:
            self.page.update()
    
    def update_results(self, e=None):
        """Aplica tots els filtres i actualitza la llista de resultats i el mapa."""
        self.update_button.disabled = True
        self.clear_button.disabled = True
        if e:
            self.page.update()
        
        # Aplicar filtres
        filtered_df = self.initial_df.copy()
        
        selected_province = self.province_dropdown.value
        selected_grade = self.grade_dropdown.value
        selected_cycle = self.cycle_dropdown.value
        
        if selected_province and selected_province != "TOTES LES PROVÍNCIES":
            filtered_df = filtered_df[filtered_df['PROVINCIA'] == selected_province]
            
        if selected_grade and selected_grade != "TOTS ELS GRAUS":
            filtered_df = filtered_df[filtered_df['GRADO'] == selected_grade]

        if selected_cycle and selected_cycle != "TOTS ELS CICLES/CURSOS":
            filtered_df = filtered_df[filtered_df['CICLO'] == selected_cycle]
        
        # Guardar el DataFrame filtrat
        self.current_filtered_df = filtered_df.copy()
        
        # Actualitzar el mapa amb tots els centres
        if self.map_container_ref.current:
            map_content = ft.Column([
                ft.Text(f"📍 Mapa de tots els centres ({len(filtered_df)} centres)", 
                       size=18, weight="bold"),
                ft.Container(
                    ft.WebView(
                        url=get_osm_url_all_centers(filtered_df),
                        expand=True
                    ),
                    height=700,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                ),
                ft.Text(f"Mostrant fins a 100 marcadors", size=12, color=ft.Colors.GREY_600)
            ], spacing=10)
            
            self.map_container_ref.current.content = ft.Container(
                content=map_content,
                padding=10
            )
        
        # Actualitzar resultats
        total_units = filtered_df['UNIDADES'].sum()
        self.counter_text.value = f"Ofertes trobades: {len(filtered_df)}"
        self.total_units_text.value = f"Unitats ofertades: {total_units:,}".replace(",", ".") 
        
        self.results_list_column.controls.clear()
        self.selected_card_index = None
        
        if not filtered_df.empty:
            display_df = filtered_df.sort_values(by=['LOCALIDAD', 'CENTRO']).head(1000)
            
            for index, row in display_df.iterrows():
                self.results_list_column.controls.append(
                    self.create_offer_card(row, len(self.results_list_column.controls))
                )

            if len(filtered_df) > 1000:
                 self.results_list_column.controls.append(
                    ft.Container(
                        content=ft.Text(f"⚠️ Mostrant les primeres 1000 ofertes d'un total de {len(filtered_df)}.", 
                                      color=ft.Colors.ORANGE_700, italic=True, size=12), 
                        alignment=ft.alignment.center, 
                        padding=ft.padding.all(10)
                    )
                )
        else:
            self.results_list_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SEARCH_OFF, size=60, color=ft.Colors.ORANGE_300), 
                        ft.Text("No s'han trobat ofertes amb aquests criteris.", 
                              color=ft.Colors.ORANGE_700, text_align=ft.TextAlign.CENTER)], 
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                        spacing=20
                    ), 
                    padding=ft.padding.all(40)
                )
            )
        
        self.update_button.disabled = False
        self.clear_button.disabled = False
        self.page.update()
    
    def clear_filters(self, e=None):
        """Neteja els filtres."""
        self.province_dropdown.value = "TOTES LES PROVÍNCIES"
        self.grade_dropdown.value = "TOTS ELS GRAUS"
        
        self.cycle_dropdown.options.clear()
        self.cycle_dropdown.options.append(ft.dropdown.Option("TOTS ELS CICLES/CURSOS"))
        self.cycle_dropdown.options.extend([ft.dropdown.Option(c) for c in self.CYCLES])
        self.cycle_dropdown.value = "TOTS ELS CICLES/CURSOS"
        
        self.update_results()
    
    def initialize_results(self):
        """Inicialitza els resultats sense disparar l'actualització de la pàgina."""
        self.update_results()

def main(page: ft.Page):
    """Funció principal de l'aplicació Flet amb pestanyes i mapa."""
    
    # Configuració de la pàgina
    page.title = "Oferta de Formació Professional 25/26 - CV"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.window_width = 1400
    page.window_height = 900
    
    if fp_standard_df.empty and fp_esp_df.empty:
        page.add(
            ft.Text("❌ Error: No s'ha pogut carregar o processar l'oferta de FP.", 
                    size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED)
        )
        page.update()
        return
    
    # Contenidor per al mapa (referència per a actualitzacions)
    map_container_ref = ft.Ref[ft.Container]()
    
    # Crear contingut de les pestanyes
    tab_standard = TabContent(page, fp_standard_df, "FP Estàndard (Bàsic, Medi, Superior)", map_container_ref)
    tab_especializacion = TabContent(page, fp_esp_df, "FP Cursos d'Especialització", map_container_ref)
    
    # Contenidor per al contingut de la pestanya activa
    active_tab_content = ft.Ref[ft.Column]()
    
    # Contenidor del mapa (inicialitzat buit)
    map_container_ref.current = ft.Container(
        content=ft.Column([
            ft.Text("📍 Mapa OpenStreetMap", size=18, weight="bold"),
            ft.Text("Fes clic a qualsevol centre de la llista per veure la seva ubicació", 
                   size=14, color=ft.Colors.GREY_600),
            ft.Container(
                ft.WebView(
                    url="https://www.openstreetmap.org/export/embed.html?bbox=-0.5%2C39.2%2C0.5%2C40.0&layer=mapnik",
                    expand=True
                ),
                height=700,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=10,
            )
        ], spacing=10)
    )
    
    def on_tab_change(e):
        """Gestiona el canvi de pestanya."""
        if active_tab_content.current is None:
            active_tab_content.current = ft.Column(expand=True)
        
        # Actualitzar el contingut visible
        active_tab_content.current.controls.clear()
        if e.control.selected_index == 0:
            active_tab_content.current.controls.append(tab_standard.content)
            tab_standard.initialize_results()
        else:
            active_tab_content.current.controls.append(tab_especializacion.content)
            tab_especializacion.initialize_results()
        
        page.update()
    
    # Interfície principal
    header_section = ft.Column([
        ft.Row([
            ft.Text("📚 Oferta de Formació Professional 25/26", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Container(expand=True),
            ft.Text("📍 Coordenades consistents per centre", size=12, color=ft.Colors.GREEN_700)
        ]),
        ft.Text("Filtra i visualitza l'oferta de FP. Cada centre té coordenades úniques i consistents.", 
               size=14, color=ft.Colors.GREY_600),
        ft.Divider(height=10, color=ft.Colors.GREY_300),
    ])
    
    # Inicialitzar la columna activa
    active_tab_content.current = ft.Column([tab_standard.content], expand=True)
    
    # Layout principal
    main_row = ft.Row([
        # Columna de contingut (pestanyes)
        ft.Column([
            ft.Tabs(
                selected_index=0,
                animation_duration=300,
                on_change=on_tab_change,
                tabs=[
                    ft.Tab(text="FP Estàndard", icon=ft.Icons.CLASS_OUTLINED),
                    ft.Tab(text="FP Especialització", icon=ft.Icons.STAR_HALF_OUTLINED),
                ],
                expand=True
            ),
            active_tab_content.current
        ], expand=2),
        
        # Columna del mapa
        ft.Column([
            map_container_ref.current
        ], expand=1)
    ], spacing=20, expand=True)
    
    # Afegir tot a la pàgina
    page.add(header_section, main_row)
    
    # Inicialitzar la primera pestanya
    tab_standard.initialize_results()

# Punt d'entrada de l'aplicació
if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER)
    
    