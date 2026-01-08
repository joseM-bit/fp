import flet as ft
import pandas as pd
import webbrowser
import os
from flet import Container, Text, Column, Row, padding 

# ----------------------------------------------------------------------
# 1. Carga y Preprocesamiento de Datos de FP (Corregido y Separado)
# ----------------------------------------------------------------------

# Nombres de archivos
FP_FILE = "oferta_fp_25_26.csv"
ESP_FILE = "oferta_fp_especialitzacio.csv" 

# Columnas finales esperadas (9 elementos)
FP_COLS = ['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'GRADO', 'FAMILIA', 'CICLO', 'TURNO', 'UNIDADES']
# Grados canónicos solicitados para FP Estándar
CANONICAL_GRADES = ['BÁSICO', 'BÁSICO 2A OPORTUNIDAD', 'MEDIO', 'SUPERIOR']

# --- MAPA DE ESTANDARIZACIÓN DE PROVINCIAS ---
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
    
def standardize_grade(g_upper):
    """Mapea el texto de la columna GRADO a las categorías canónicas de FP Estándar."""
    if pd.isna(g_upper): return None
    g_upper = g_upper.upper().strip()
    if 'BÁSICO 2A OPORT' in g_upper or 'BÁSICO 2ª OPORT' in g_upper: return 'BÁSICO 2A OPORTUNIDAD'
    if 'BÁSICO' in g_upper: return 'BÁSICO'
    if 'MEDIO' in g_upper: return 'MEDIO'
    if 'SUPERIOR' in g_upper: return 'SUPERIOR'
    return None 

def standardize_esp_grade(g_upper):
    """Mapea el texto de la columna GRADO a las categorías canónicas de Especialización (Medio/Superior)."""
    if pd.isna(g_upper): return 'ESPECIALIZACIÓN' # Marcador a eliminar
    g_upper = g_upper.upper().strip()
    if 'SUPERIOR' in g_upper: return 'SUPERIOR'
    if 'MEDIO' in g_upper: return 'MEDIO'
    return 'ESPECIALIZACIÓN' # Todo lo que no sea Superior o Medio lo marcamos para eliminar


def load_and_clean_data():
    """Carga y limpia los dos archivos CSV, retornando un dict de DataFrames."""
    data_frames = {}

    # --- Procesar oferta_fp_25_26.csv (FP Standard) ---
    try:
        df_fp = pd.read_csv(FP_FILE, header=None, skiprows=lambda x: x < 4, encoding='utf-8')
        
        # Lógica para manejar 9 (separado) o 8 (combinado) columnas
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
            raise ValueError(f"El archivo {FP_FILE} tiene menos de 8 columnas.")
        
        # Limpieza y estandarización de PROVINCIA
        df_fp['PROVINCIA'] = df_fp['PROVINCIA'].astype(str).str.strip().str.upper()
        df_fp['PROVINCIA'] = df_fp['PROVINCIA'].apply(lambda x: PROVINCE_MAP.get(x, x))
        
        # Limpieza de Grado, Régimen y Unidades
        df_fp['GRADO'] = df_fp['GRADO'].astype(str).apply(standardize_grade)
        df_fp['RÉGIMEN'] = df_fp['RÉGIMEN'].astype(str).str.split(',').str[0].str.strip().str.upper()
        df_fp = df_fp[df_fp['GRADO'].isin(CANONICAL_GRADES)].copy()
        df_fp['UNIDADES'] = pd.to_numeric(df_fp['UNIDADES'], errors='coerce').fillna(0).astype(int)
        
        # Limpieza final para el resto de columnas
        for col in ['LOCALIDAD', 'CENTRO', 'FAMILIA', 'CICLO', 'TURNO']:
             df_fp[col] = df_fp[col].astype(str).str.strip().str.upper().replace('NAN', '', regex=False)

        data_frames['FP_STANDARD'] = df_fp
        print(f"✅ Cargado {FP_FILE} con {len(df_fp)} registros.")
    except Exception as e:
        print(f"❌ Error al cargar {FP_FILE}: {e}")
        data_frames['FP_STANDARD'] = pd.DataFrame(columns=FP_COLS)


    # --- Procesar oferta_fp_especialitzacio.csv (Especialización) ---
    try:
        df_esp = pd.read_csv(ESP_FILE, header=None, skiprows=lambda x: x < 3, encoding='utf-8', on_bad_lines='skip')
        
        if df_esp.shape[1] >= 9:
            df_esp = df_esp.iloc[:, :9].copy()
            df_esp.columns = ['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'GRADO', 'FAMILIA', 'CICLO', 'TURNO', 'UNIDADES']
        else:
             raise ValueError(f"El archivo {ESP_FILE} tiene menos de 9 columnas.")

        # 1. ESTANDARIZACIÓN DE GRADO (Manteniendo solo MEDIO o SUPERIOR)
        df_esp['GRADO'] = df_esp['GRADO'].astype(str).apply(standardize_esp_grade)
        
        # 2. Limpieza y estandarización de PROVINCIA (mismo mapa)
        df_esp['PROVINCIA'] = df_esp['PROVINCIA'].astype(str).str.strip().str.upper()
        df_esp['PROVINCIA'] = df_esp['PROVINCIA'].apply(lambda x: PROVINCE_MAP.get(x, x))
        
        # 3. Limpieza de Régimen y Unidades
        df_esp['RÉGIMEN'] = df_esp['RÉGIMEN'].astype(str).str.split(',').str[0].str.strip().str.upper()
        df_esp['UNIDADES'] = pd.to_numeric(df_esp['UNIDADES'], errors='coerce').fillna(0).astype(int)
        
        # 4. Limpieza de Turno y otras columnas
        for col in ['LOCALIDAD', 'CENTRO', 'FAMILIA', 'CICLO', 'TURNO']:
             df_esp[col] = df_esp[col].astype(str).str.strip().str.upper().replace('NAN', '', regex=False)
        
        # --- APLICACIÓN DE FILTROS PERMANENTES REQUERIDOS ---
        
        # A. Eliminar el grado 'ESPECIALIZACIÓN' (que incluía los no clasificados)
        df_esp = df_esp[df_esp['GRADO'] != 'ESPECIALIZACIÓN'].copy()
        
        # B. y C. Filtros de UNIDADES y TURNO ELIMINADOS para mostrar la data completa.
        
        # ----------------------------------------------------
        
        data_frames['FP_ESPECIALIZACION'] = df_esp
        print(f"✅ Cargado {ESP_FILE} con {len(df_esp)} registros.")
    except Exception as e:
        print(f"❌ Error al cargar {ESP_FILE}: {e}")
        data_frames['FP_ESPECIALIZACION'] = pd.DataFrame(columns=FP_COLS)

    return data_frames

def get_clean_sorted_list(series):
    """Filtra NaNs, convierte a string y ordena la lista de valores únicos."""
    return sorted(series.dropna().astype(str).str.strip().unique().tolist())

# Cargar y separar los datos
data_dict = load_and_clean_data()
fp_standard_df = data_dict['FP_STANDARD']
fp_esp_df = data_dict['FP_ESPECIALIZACION']


# ----------------------------------------------------------------------
# 2. Lógica y UI de Flet (Adaptada para Pestañas)
# ----------------------------------------------------------------------

# Funciones de UI (sin cambios en la lógica de Flet)

def get_regime_style(regime: str):
    """Devuelve colores y textos estilizados basados en el régimen."""
    regime_upper = regime.upper()
    if 'PÚBLICO' in regime_upper:
        return ft.Colors.BLUE_700, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_700), ft.Icons.SCHOOL
    elif 'PRIVADO' in regime_upper:
        return ft.Colors.RED_700, ft.Colors.with_opacity(0.1, ft.Colors.RED_700), ft.Icons.BUSINESS
    else:
        return ft.Colors.GREY_700, ft.Colors.with_opacity(0.1, ft.Colors.GREY_700), ft.Icons.APARTMENT

def create_offer_card(offer_data: pd.Series) -> ft.Card:
    """Crea una tarjeta de Flet para una oferta de FP."""
    
    regime_color, bg_color, icon = get_regime_style(offer_data['RÉGIMEN'])
    
    search_query = f"{offer_data['CENTRO']}, {offer_data['LOCALIDAD']}, {offer_data['PROVINCIA']}"
    map_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}" 

    def open_map_external(e):
         webbrowser.open(map_url)

    grado_text = offer_data['GRADO'].upper() if offer_data['GRADO'] else 'N/A' 
    
    # Marcador visual si es Especialización (detectado si tiene la palabra CURSO en el ciclo)
    is_esp_course = 'CURSO' in offer_data['CICLO'].upper()
    
    grado_style_text = grado_text
    if is_esp_course:
        # Se asume que en la pestaña de Especialización, el Grado es el tipo de Curso (Medio/Superior)
        grado_style_text = f"C. ESP. ({grado_text})"

    return ft.Card(
        elevation=2, 
        content=ft.Container(
            padding=15, 
            bgcolor=ft.Colors.WHITE, 
            border_radius=8,
            content=ft.Column([
                # Fila Principal: Título del Ciclo y Grado
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
                
                # Fila de Centro y Localidad
                ft.Row([
                    ft.Icon(icon, size=16, color=regime_color),
                    ft.Text(offer_data['CENTRO'], size=13, color=ft.Colors.GREY_800, weight=ft.FontWeight.W_600, expand=True),
                    ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=14, color=ft.Colors.GREY_600),
                    ft.Text(f"{offer_data['LOCALIDAD']} ({offer_data['PROVINCIA']})", size=12, color=ft.Colors.GREY_700)
                ], spacing=8),

                # Fila de Familia, Turno y Unidades
                ft.Row([
                    ft.Icon(ft.Icons.CATEGORY_OUTLINED, size=16, color=ft.Colors.INDIGO_600),
                    ft.Text(f"Familia: {offer_data['FAMILIA']}", size=12, color=ft.Colors.GREY_700),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.ACCESS_TIME, size=16, color=ft.Colors.AMBER_700),
                    ft.Text(f"Turno: {offer_data['TURNO']}", size=12, color=ft.Colors.GREY_700),
                    ft.Container(width=10),
                    ft.Icon(ft.Icons.GROUP, size=16, color=ft.Colors.GREEN_700),
                    ft.Text(f"Unidades: {offer_data['UNIDADES']}", size=12, color=ft.Colors.GREY_700, weight=ft.FontWeight.BOLD),
                    ft.Container(width=10),
                    
                    ft.TextButton(
                        "Ver ubicación",
                        icon=ft.Icons.MAP_OUTLINED,
                        on_click=open_map_external,
                        style=ft.ButtonStyle(color=ft.Colors.BLUE_500, padding=0)
                    )
                ], spacing=5)
            ], spacing=8)
        )
    )

def create_tab_content(initial_df: pd.DataFrame, title: str):
    """
    Crea y retorna un Column control de Flet que contiene la interfaz de filtros
    y resultados para un DataFrame específico.
    """
    
    # 1. Preparación de datos específicos de la pestaña
    PROVINCES = get_clean_sorted_list(initial_df['PROVINCIA'])
    GRADES = get_clean_sorted_list(initial_df['GRADO'])
    CYCLES = get_clean_sorted_list(initial_df['CICLO'])
    
    # Controles de UI (Definición dentro de la función para encapsular el estado)
    results_list_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)
    counter_text = ft.Text("Ofertas encontradas: 0", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)
    total_units_text = ft.Text("Unidades ofertadas: 0", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800)
    
    # Dropdowns
    province_options = [ft.dropdown.Option("TODAS LAS PROVINCIAS")] + [ft.dropdown.Option(p) for p in PROVINCES]
    province_dropdown = ft.Dropdown(options=province_options, label="Provincia", width=180, value="TODAS LAS PROVINCIAS")
    
    grade_options = [ft.dropdown.Option("TODOS LOS GRADOS")] + [ft.dropdown.Option(g) for g in GRADES]
    grade_dropdown = ft.Dropdown(options=grade_options, label="Grado (FP)", width=280, value="TODOS LOS GRADOS")

    cycle_options = [ft.dropdown.Option("TODOS LOS CICLOS/CURSOS")] + [ft.dropdown.Option(c) for c in CYCLES]
    cycle_dropdown = ft.Dropdown(options=cycle_options, label="Ciclo / Curso", width=400, value="TODOS LOS CICLOS/CURSOS")
    
    # Botones
    update_button = ft.ElevatedButton(text="🔍 Aplicar Filtros", icon=ft.Icons.SEARCH, on_click=None, style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, padding=ft.padding.symmetric(horizontal=20, vertical=12), elevation=5), height=45)
    clear_button = ft.TextButton(text="Limpiar Filtros", icon=ft.Icons.CLEAR_ALL, on_click=None, style=ft.ButtonStyle(color=ft.Colors.GREY_700), height=45)


    # 2. Lógica de Filtrado (encapsulada)
    
    def update_cycle_dropdown(e=None):
        """Actualiza la lista de ciclos y cursos basado en Provincia y Grado."""
        
        filtered_df = initial_df.copy()
        selected_province = province_dropdown.value
        selected_grade = grade_dropdown.value
        
        if selected_province and selected_province != "TODAS LAS PROVINCIAS":
            filtered_df = filtered_df[filtered_df['PROVINCIA'] == selected_province]
            
        if selected_grade and selected_grade != "TODOS LOS GRADOS":
            filtered_df = filtered_df[filtered_df['GRADO'] == selected_grade]
        
        filtered_cycles = get_clean_sorted_list(filtered_df['CICLO'])
        
        cycle_dropdown.options.clear()
        cycle_dropdown.options.append(ft.dropdown.Option("TODOS LOS CICLOS/CURSOS"))
        cycle_dropdown.options.extend([ft.dropdown.Option(c) for c in filtered_cycles])
        cycle_dropdown.value = "TODOS LOS CICLOS/CURSOS"
        
        if e and e.page: e.page.update()

    def update_results(e=None):
        """Aplica todos los filtros y actualiza la lista de resultados de esta pestaña."""
        
        # Deshabilitar botones
        update_button.disabled = True
        clear_button.disabled = True
        if e and e.page: e.page.update()
        
        # Aplicar filtros
        filtered_df = initial_df.copy()
        
        selected_province = province_dropdown.value
        selected_grade = grade_dropdown.value
        selected_cycle = cycle_dropdown.value
        
        if selected_province and selected_province != "TODAS LAS PROVINCIAS":
            filtered_df = filtered_df[filtered_df['PROVINCIA'] == selected_province]
            
        if selected_grade and selected_grade != "TODOS LOS GRADOS":
            filtered_df = filtered_df[filtered_df['GRADO'] == selected_grade]

        if selected_cycle and selected_cycle != "TODOS LOS CICLOS/CURSOS":
            filtered_df = filtered_df[filtered_df['CICLO'] == selected_cycle]
        
        # Actualizar contadores
        total_units = filtered_df['UNIDADES'].sum()
        counter_text.value = f"Ofertas encontradas: {len(filtered_df)}"
        total_units_text.value = f"Unidades ofertadas: {total_units:,}".replace(",", ".") 
        
        # Actualizar lista de tarjetas
        results_list_column.controls.clear()
        
        if not filtered_df.empty:
            display_df = filtered_df.sort_values(by=['LOCALIDAD', 'CENTRO']).head(1000)
            
            for _, row in display_df.iterrows():
                results_list_column.controls.append(create_offer_card(row))

            if len(filtered_df) > 1000:
                 results_list_column.controls.append(
                    ft.Container(
                        content=ft.Text(f"⚠️ Mostrando las primeras 1000 ofertas de un total de {len(filtered_df)}.", color=ft.Colors.ORANGE_700, italic=True, size=12), 
                        alignment=ft.alignment.center, 
                        padding=ft.padding.all(10)
                    )
                )
        else:
            results_list_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SEARCH_OFF, size=60, color=ft.Colors.ORANGE_300), 
                        ft.Text("No se encontraron ofertas con estos criterios.", color=ft.Colors.ORANGE_700, text_align=ft.TextAlign.CENTER)], 
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                        spacing=20
                    ), 
                    padding=ft.padding.all(40)
                )
            )
        
        # Re-habilitar botones y actualizar UI
        update_button.disabled = False
        clear_button.disabled = False
        if e and e.page: e.page.update()
        
    def clear_filters(e=None):
        """Limpia los filtros de esta pestaña."""
        province_dropdown.value = "TODAS LAS PROVINCIAS"
        grade_dropdown.value = "TODOS LOS GRADOS"
        
        # Reestablecer el ciclo completo
        cycle_dropdown.options.clear()
        cycle_dropdown.options.append(ft.dropdown.Option("TODOS LOS CICLOS/CURSOS"))
        cycle_dropdown.options.extend([ft.dropdown.Option(c) for c in CYCLES])
        cycle_dropdown.value = "TODOS LOS CICLOS/CURSOS"
        
        update_results()
        if e and e.page: e.page.update()

    # 3. Asignación de Handlers
    update_button.on_click = update_results
    clear_button.on_click = clear_filters
    province_dropdown.on_change = update_cycle_dropdown
    grade_dropdown.on_change = update_cycle_dropdown
    
    # 4. Construcción de la interfaz de la pestaña
    
    filter_section = ft.Container(
        padding=ft.padding.all(15),
        border_radius=10,
        bgcolor=ft.Colors.BLUE_GREY_50,
        content=ft.Column([
            ft.Text(f"Filtros para {title}", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_800),
            ft.Row([
                province_dropdown,
                grade_dropdown,
                cycle_dropdown,
                ft.Container(width=20),
                update_button,
                clear_button
            ], vertical_alignment=ft.CrossAxisAlignment.END)
        ], spacing=10)
    )
    
    results_section = ft.Column([
        ft.Row([
            counter_text,
            ft.Container(width=20),
            total_units_text,
            ft.Container(expand=True),
            ft.Text("Cada tarjeta representa una unidad ofertada (ej. un grupo)", size=12, color=ft.Colors.GREY_500)
        ]),
        ft.Container(
            content=results_list_column,
            height=500,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            padding=10,
            bgcolor=ft.Colors.WHITE
        )
    ], spacing=10, expand=True)

    tab_content = ft.Column(
        controls=[filter_section, results_section],
        expand=True
    )
    
    setattr(tab_content, 'initialize_results', update_results)

    return tab_content

def main(page: ft.Page):
    """Función principal de la aplicación Flet con pestañas."""
    
    # ------------------
    # CONFIGURACIÓN DE LA PÁGINA
    # ------------------
    page.title = "Oferta de Formación Profesional 25/26 - CV"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.window_width = 1200
    page.window_height = 800
    
    if fp_standard_df.empty and fp_esp_df.empty:
        page.add(
            ft.Text("❌ Error: No se pudo cargar o procesar la oferta de FP.", 
                    size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED)
        )
        page.update()
        return

    header_section = ft.Column([
        ft.Row([
            ft.Text("📚 Oferta de Formación Profesional 25/26", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Container(expand=True),
        ]),
        ft.Text("Filtra y visualiza la oferta de ciclos formativos y cursos de especialización.", size=14, color=ft.Colors.GREY_600),
        ft.Divider(height=10, color=ft.Colors.GREY_300),
    ])

    # ------------------
    # CREACIÓN DE PESTAÑAS
    # ------------------
    
    fp_standard_content = create_tab_content(
        initial_df=fp_standard_df,
        title="FP Estándar (Básico, Medio, Superior)"
    )
    
    fp_esp_content = create_tab_content(
        initial_df=fp_esp_df,
        title="FP Cursos de Especialización"
    )

    tabs_control = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="FP Estándar",
                icon=ft.Icons.CLASS_OUTLINED, 
                content=fp_standard_content,
            ),
            ft.Tab(
                text="FP Especialización",
                icon=ft.Icons.STAR_HALF_OUTLINED,
                content=fp_esp_content,
            ),
        ],
        expand=True
    )

    def tabs_change(e):
        """Asegura que al cambiar de pestaña, se muestren los resultados iniciales de esa pestaña."""
        if e.control.selected_index == 0:
            fp_standard_content.initialize_results(e)
        elif e.control.selected_index == 1:
            fp_esp_content.initialize_results(e)
        
    tabs_control.on_change = tabs_change
    
    # ------------------
    # MONTAJE DE LA PÁGINA
    # ------------------
    page.add(
        header_section,
        tabs_control
    )
    
    # Inicializar los resultados de la primera pestaña visible después de añadir los controles
    fp_standard_content.initialize_results()

# Punto de entrada de la aplicación
if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER)