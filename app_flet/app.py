import flet as ft
import pandas as pd
import numpy as np
import os
import flet_webview as ftwv

# 1. Càrrega inicial de dades
try:
    directori_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.join(directori_actual, "data/12_Centros(Valencia).csv")
    
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"No s'ha trobat el fitxer a: {ruta_csv}")

    centros_df = pd.read_csv(ruta_csv)
    
    # Neteja i normalització de columnes crítiques
    centros_df.dropna(subset=['provincia', 'comarca', 'latitud', 'longitud'], inplace=True)
    
    # Creem la columna 'provincia_neta' dins del DataFrame
    centros_df['provincia_neta'] = centros_df['provincia'].str.split('/').str[-1].str.strip().str.upper()
    centros_df['latitud'] = pd.to_numeric(centros_df['latitud'], errors='coerce')
    centros_df['longitud'] = pd.to_numeric(centros_df['longitud'], errors='coerce')
    centros_df.dropna(subset=['latitud', 'longitud'], inplace=True)
    
    PROVINCES = sorted(centros_df['provincia_neta'].unique().tolist())
    REGIMES = sorted(centros_df['regimen'].unique().tolist())
    
except Exception as e:
    print(f"Error en la càrrega: {e}")
    centros_df = pd.DataFrame()
    PROVINCES, REGIMES = [], []

def get_osm_url(data_subset: pd.DataFrame) -> str:
    if data_subset.empty:
        lat, lon, delta = 39.4697, -0.3773, 0.1
    else:
        lat = data_subset['latitud'].mean()
        lon = data_subset['longitud'].mean()
        lat_range = data_subset['latitud'].max() - data_subset['latitud'].min()
        lon_range = data_subset['longitud'].max() - data_subset['longitud'].min()
        delta = max(lat_range, lon_range, 0.01) + 0.01

    return (f"https://www.openstreetmap.org/export/embed.html?"
            f"bbox={lon-delta}%2C{lat-delta}%2C{lon+delta}%2C{lat+delta}&"
            f"layer=mapnik&marker={lat}%2C{lon}")

def main(page: ft.Page):
    page.title = "Visualitzador de Centres Educatius"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1400
    page.window_height = 900

    # --- CONTROLS ---
    province_dropdown = ft.Dropdown(
        label="Província", width=200,
        options=[ft.dropdown.Option(p) for p in PROVINCES],
        value=PROVINCES[0] if PROVINCES else None,
    )
    
    comarca_dropdown = ft.Dropdown(
        label="Comarca", width=250,
        options=[ft.dropdown.Option("TOTES LES COMARQUES")],
        value="TOTES LES COMARQUES",
        disabled=True
    )
    
    regime_dropdown = ft.Dropdown(
        label="Règim", width=200,
        options=[ft.dropdown.Option("TOTS ELS RÈGIMS")] + [ft.dropdown.Option(r) for r in REGIMES],
        value="TOTS ELS RÈGIMS"
    )

    wv_mapa = ftwv.WebView(url=get_osm_url(pd.DataFrame()), expand=True)
    centers_list_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    counter_text = ft.Text("Centres trobats: 0", size=16, weight="bold")

    # --- LÒGICA D'ACTUALITZACIÓ ---
    def update_comarcas(e):
        if not province_dropdown.value:
            return
        
        # Filtrem el dataframe per la província seleccionada
        sel_prov = province_dropdown.value # Ja està en majúscules
        comarcas_filtrades = sorted(centros_df[centros_df['provincia_neta'] == sel_prov]['comarca'].unique().tolist())
        
        # Actualitzem les opcions del dropdown
        comarca_dropdown.options = [ft.dropdown.Option("TOTES LES COMARQUES")] + \
                                   [ft.dropdown.Option(c) for c in comarcas_filtrades]
        comarca_dropdown.value = "TOTES LES COMARQUES"
        comarca_dropdown.disabled = False
        page.update()

    def apply_filters(e):
        # Filtre base per província
        df = centros_df[centros_df['provincia_neta'] == province_dropdown.value]
        
        # Filtre opcional per comarca
        if comarca_dropdown.value != "TOTES LES COMARQUES":
            df = df[df['comarca'] == comarca_dropdown.value]
        
        # Filtre opcional per règim
        if regime_dropdown.value != "TOTS ELS RÈGIMS":
            df = df[df['regimen'] == regime_dropdown.value]

        # Actualització de mapa i llista
        wv_mapa.url = get_osm_url(df)
        counter_text.value = f"Centres trobats: {len(df)}"
        
        centers_list_column.controls.clear()
        for _, row in df.head(100).iterrows():
            centers_list_column.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.SCHOOL, color="blue"),
                    title=ft.Text(row['dlibre'], size=12, weight="bold"),
                    subtitle=ft.Text(f"{row['direccion']} ({row['localidad_oficial']})", size=11),
                )
            )
        page.update()

    # Assignació d'esdeveniments
    province_dropdown.on_change = update_comarcas
    btn_update = ft.ElevatedButton("Actualitzar Mapa", icon="refresh", on_click=apply_filters)

    page.add(
        ft.Text("🗺️ Cercador de Centres Educatius - CV", size=28, weight="bold", color="blue800"),
        ft.Row([province_dropdown, comarca_dropdown, regime_dropdown, btn_update, counter_text], spacing=15),
        ft.Divider(),
        ft.Row([
            # Columna Esquerra: Llista (amb un poc de separació de la vora esquerra)
            ft.Column([
                ft.Text("🏛️ Llista de Centres", size=18, weight="bold"), 
                ft.Container(centers_list_column, height=650, border=ft.border.all(1, "grey300"), border_radius=10, padding=10)
            ], expand=1),
            
            # Columna Dreta: Mapa (sense expand=True al Container per a que el Column mane)
            ft.Column([
                ft.Text("📍 Mapa Geogràfic", size=18, weight="bold"), 
                ft.Container(
                    wv_mapa, 
                    height=650, 
                    # Eliminem border_radius dret per a un efecte visual de "pantalla completa" en eixe costat
                    border=ft.border.only(left=ft.border.BorderSide(1, "grey300"), top=ft.border.BorderSide(1, "grey300"), bottom=ft.border.BorderSide(1, "grey300")),
                    border_radius=ft.border_radius.only(top_left=10, bottom_left=10),
                    margin=ft.margin.only(right=0) # Assegurem marge zero
                )
            ], expand=2, spacing=10),
        ], 
        expand=True, 
        spacing=20, # Espai entre llista i mapa
        alignment=ft.MainAxisAlignment.START # Alineació al principi
        )
    )
    
    # Carreguem comarques inicials segons la província per defecte
    if PROVINCES:
        update_comarcas(None)

ft.app(target=main, view=ft.AppView.WEB_BROWSER)