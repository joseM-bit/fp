import flet as ft
import pandas as pd
import numpy as np
import webbrowser
import os
import math
import io
import base64
import warnings
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Suprimir advertencias de contextily
warnings.filterwarnings('ignore')

# Intentar importar contextily
CONTEXTILY_AVAILABLE = False
try:
    import contextily as ctx
    CONTEXTILY_AVAILABLE = True
except ImportError:
    pass

# 1. Carga inicial de datos
try:
    csv_file_name = "12_Centros(Valencia).csv"
    if not os.path.exists(csv_file_name):
        raise FileNotFoundError(f"El archivo {csv_file_name} no se encontró en el directorio actual.")
    
    centros_df = pd.read_csv(csv_file_name)
    
    # Limpieza básica de datos
    centros_df.dropna(subset=['provincia', 'comarca', 'latitud', 'longitud', 'dlibre', 'direccion', 'regimen'], inplace=True)
    
    # Estandarizar la provincia para el filtro
    centros_df['provincia_simple'] = centros_df['provincia'].str.split('/').str[1].str.lower().str.strip()
    
    # Asegurarse de que las coordenadas son numéricas
    centros_df['latitud'] = pd.to_numeric(centros_df['latitud'], errors='coerce')
    centros_df['longitud'] = pd.to_numeric(centros_df['longitud'], errors='coerce')
    centros_df = centros_df.dropna(subset=['latitud', 'longitud'])
    
    PROVINCES = sorted(centros_df['provincia_simple'].unique().tolist())
    REGIMES = sorted(centros_df['regimen'].unique().tolist())
    
except Exception as e:
    centros_df = pd.DataFrame()
    PROVINCES = []
    REGIMES = []

def create_static_map_image(data_subset: pd.DataFrame, map_status_callback) -> bytes:
    """Crea una imagen estática del mapa con relieve y los centros marcados."""
    
    center_lat = 0
    center_lon = 0
    status_message = "Cargando..."
    
    if data_subset.empty:
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.set_facecolor('#f7f7e8')
        ax.text(0.5, 0.5, 'No hay centros para mostrar\nSeleccione otros filtros', 
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=14, color='gray')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        status_message = f"Centros encontrados: 0"
    else:
        fig, ax = plt.subplots(figsize=(12, 10))
        
        center_lat = data_subset['latitud'].mean()
        center_lon = data_subset['longitud'].mean()
        
        lat_min = data_subset['latitud'].min() - 0.08
        lat_max = data_subset['latitud'].max() + 0.08
        lon_min = data_subset['longitud'].min() - 0.08
        lon_max = data_subset['longitud'].max() + 0.08
        
        ax.set_xlim(lon_min, lon_max)
        ax.set_ylim(lat_min, lat_max)
        ax.set_aspect(1.0 / np.cos(np.radians(center_lat)))
        
        # ===============================================
        # LÓGICA DE CARGA DEL MAPA BASE (Contextily)
        # Se han eliminado los servicios de Stamen.
        # ===============================================
        
        basemap_loaded = False
        try:
            if CONTEXTILY_AVAILABLE:
                # Proveedores estables y con relieve topográfico
                providers = [
                    ctx.providers.Esri.WorldTopoMap,      # Topográfico de ESRI (Recomendado y estable)
                    ctx.providers.OpenTopoMap,            # Topográfico
                    ctx.providers.CartoDB.Positron        # Mapa base claro (si fallan los topográficos)
                ]
                
                for provider in providers:
                    try:
                        ctx.add_basemap(ax, crs='EPSG:4326', 
                                       source=provider,
                                       zoom=11)
                        basemap_loaded = True
                        if provider == ctx.providers.CartoDB.Positron:
                             status_message = f"⚠️ Mapa sin relieve (Usando CartoDB). {len(data_subset)} centros."
                        else:
                             status_message = f"✅ Mapa Topográfico con {len(data_subset)} centros."
                        break
                    except Exception as basemap_error:
                        # Falló este proveedor, probar el siguiente
                        continue
            
            if not basemap_loaded:
                # FALLBACK si contextily no está disponible o todos los proveedores fallan
                ax.set_facecolor('#f7f7e8') # Color beige/tierra claro
                ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
                
                if not CONTEXTILY_AVAILABLE:
                     status_message = "❌ Error: Contextily no está instalado. Instálalo para ver el relieve real."
                else:
                    status_message = "⚠️ Advertencia: No se pudo cargar el mapa base (Error de red/servidor de mapas)."
                
                ax.text(center_lon, center_lat, 
                        status_message.replace("❌ Error: ", "").replace("⚠️ Advertencia: ", ""),
                        horizontalalignment='center', verticalalignment='center',
                        fontsize=11, color='red', zorder=1,
                        bbox=dict(facecolor='white', alpha=0.8, boxstyle="round,pad=0.5"))

        except Exception as e:
            # Fallback general
            ax.set_facecolor('#f7f7e8') 
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            status_message = f"❌ Error Crítico al dibujar mapa: {type(e).__name__}."
            
        # ===============================================
        # DIBUJO DE PUNTOS DE CENTROS
        # ===============================================
        
        color_map = {
            'PÚBLICO': '#1E88E5',
            'PRIVADO': '#E53935',
            'CONCERTADO': '#43A047'
        }
        marker_map = {
            'PÚBLICO': '^',
            'PRIVADO': 's',
            'CONCERTADO': 'D'
        }
        size_map = {
            'PÚBLICO': 120,
            'PRIVADO': 100,
            'CONCERTADO': 110
        }
        
        legend_handles = []
        for regimen in ['PÚBLICO', 'PRIVADO', 'CONCERTADO']:
            mask = data_subset['regimen'].str.upper().str.contains(regimen)
            subset = data_subset[mask]
            
            if not subset.empty:
                color = color_map.get(regimen, '#757575')
                marker = marker_map.get(regimen, 'o')
                size = size_map.get(regimen, 80)
                
                ax.scatter(subset['longitud'], subset['latitud'],
                          c=color, marker=marker, s=size,
                          alpha=0.9, edgecolors='white', linewidth=2,
                          label=regimen, zorder=5)
                
                from matplotlib.lines import Line2D
                legend_handles.append(Line2D([0], [0], marker=marker, color='w',
                                           markerfacecolor=color, markersize=10,
                                           label=regimen.capitalize()))
        
        # Agregar título y leyenda
        provincia_text = data_subset['provincia_simple'].iloc[0].capitalize()
        ax.set_title(f'Centros Educativos - {provincia_text}\n({len(data_subset)} centros encontrados)', 
                    fontsize=16, fontweight='bold', pad=20, color='#2c3e50')
        
        if legend_handles:
            legend = ax.legend(handles=legend_handles, loc='upper left', 
                             framealpha=0.95, fancybox=True,
                             fontsize=10, title="Régimen", title_fontsize=11)
            legend.get_frame().set_facecolor('#ffffff')
            legend.get_frame().set_edgecolor('#cccccc')
        
        # Ejes, escala y norte
        ax.set_xlabel('Longitud', fontsize=12, color='#2c3e50')
        ax.set_ylabel('Latitud', fontsize=12, color='#2c3e50')
        ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.7, color='#666666')
        
        scale_lon = lon_min + (lon_max - lon_min) * 0.05
        scale_lat = lat_min + (lat_max - lat_min) * 0.05
        scale_length_deg = 10 / (111.32 * np.cos(np.radians(center_lat))) 
        ax.plot([scale_lon, scale_lon + scale_length_deg], [scale_lat, scale_lat], color='black', linewidth=3, solid_capstyle='butt')
        ax.text(scale_lon + scale_length_deg/2, scale_lat - 0.005, '10 km', ha='center', va='top', fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
        ax.text(lon_max - 0.01, lat_max - 0.01, 'N', fontsize=12, weight='bold', ha='center', va='center', bbox=dict(boxstyle="circle,pad=0.2", facecolor="white", alpha=0.8))
        
        for spine in ax.spines.values():
            spine.set_edgecolor('#2c3e50')
            spine.set_linewidth(1.5)
    
    plt.tight_layout()
    
    map_status_callback(status_message)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close(fig)
    
    buf.seek(0)
    return buf.read()

def main(page: ft.Page):
    """Función principal de la aplicación Flet."""
    
    # ------------------
    # CONFIGURACIÓN DE LA PÁGINA
    # ------------------
    page.title = "Visualizador de Centros Educativos - CV"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.window_width = 1400
    page.window_height = 900
    
    if centros_df.empty:
        page.add(
            ft.Text("❌ Error: No se pudo cargar el archivo CSV o no contiene datos válidos.", 
                    size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED)
        )
        page.update()
        return

    # ------------------
    # VARIABLES DE ESTADO Y CONTROLES
    # ------------------
    province_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(p.capitalize()) for p in PROVINCES],
        label="Seleccionar Provincia",
        width=200,
        value=PROVINCES[0].capitalize() if PROVINCES else None,
    )
    
    comarca_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option("TODAS LAS COMARCAS")],
        label="Seleccionar Comarca",
        width=250,
        disabled=True
    )
    
    regime_options = [ft.dropdown.Option("TODOS LOS REGÍMENES")]
    regime_options.extend([ft.dropdown.Option(r.capitalize()) for r in REGIMES])
    regime_dropdown = ft.Dropdown(
        options=regime_options,
        label="Seleccionar Régimen",
        width=200,
        value="TODOS LOS REGÍMENES"
    )

    update_button = ft.ElevatedButton(
        text="🗺️ Actualizar Mapa", icon=ft.Icons.MAP, on_click=None, 
        style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, padding=ft.padding.symmetric(horizontal=20, vertical=12), elevation=5), height=45
    )
    clear_button = ft.ElevatedButton(
        text="🗑️ Limpiar Filtros", icon=ft.Icons.CLEAR_ALL, on_click=None, 
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_700, color=ft.Colors.WHITE, padding=ft.padding.symmetric(horizontal=20, vertical=12), elevation=5), height=45
    )
    export_button = ft.ElevatedButton(
        text="📊 Exportar Datos", icon=ft.Icons.DOWNLOAD, on_click=None, 
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, padding=ft.padding.symmetric(horizontal=20, vertical=12), elevation=5), height=45
    )
    
    map_image = ft.Image(
        src_base64=None, width=800, height=550, fit=ft.ImageFit.CONTAIN, border_radius=ft.border_radius.all(10),
        error_content=ft.Column([
            ft.Icon(ft.Icons.MAP_OUTLINED, size=48, color=ft.Colors.BLUE_300),
            ft.Text("Presione 'Actualizar Mapa'\npara generar el mapa con relieve", color=ft.Colors.GREY_600, size=16, text_align=ft.TextAlign.CENTER)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)
    )
    
    map_container = ft.Container(
        height=550, width=800, border=ft.border.all(2, ft.Colors.GREY_400), border_radius=10, clip_behavior=ft.ClipBehavior.HARD_EDGE,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.Colors.BLACK12),
        content=ft.Column([
            ft.Container(height=35, bgcolor=ft.Colors.BLUE_50, border_radius=ft.border_radius.only(top_left=10, top_right=10), border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_300)),
                content=ft.Row([
                    ft.Icon(ft.Icons.TERRAIN, color=ft.Colors.BLUE_800, size=22),
                    ft.Text("Mapa con Relieve de Centros Educativos", color=ft.Colors.BLUE_800, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=ft.Colors.BLUE_600)
                ], spacing=10),
                padding=ft.padding.only(left=15, right=15, top=8, bottom=8),
            ),
            ft.Container(
                expand=True,
                content=ft.Column([
                    map_image,
                    ft.Container(height=25, content=ft.Row([ft.Icon(ft.Icons.PALETTE, size=16, color=ft.Colors.BLUE_600), ft.Text("", size=12, color=ft.Colors.BLUE_600)], spacing=5), alignment=ft.alignment.center)
                ], alignment=ft.MainAxisAlignment.CENTER),
                padding=ft.padding.all(5),
            )
        ])
    )
    
    centers_list_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)
    
    title_text = ft.Text("🏔️ Visualizador de Centros Educativos con Relieve - CV", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900)
    subtitle_text = ft.Text("Filtra por provincia, comarca y régimen educativo", size=14, color=ft.Colors.GREY_600)
    counter_text = ft.Text("Centros encontrados: 0", size=16, color=ft.Colors.BLUE_800)
    loading_indicator = ft.ProgressRing(width=20, height=20, visible=False)
    map_status_text = ft.Text("Seleccione filtros y presione 'Actualizar Mapa'", 
                             size=13, color=ft.Colors.BLUE_700, weight=ft.FontWeight.BOLD)
    
    current_filtered_data = None
    
    # ------------------
    # FUNCIONES DE LÓGICA
    # ------------------
    
    def update_map_status(message: str):
        """Callback para actualizar el estado del mapa desde el hilo de Matplotlib."""
        map_status_text.value = message
        page.update()

    def update_comarca_dropdown(e=None):
        if not province_dropdown.value: return
        selected_province = province_dropdown.value.lower()
        filtered_by_province = centros_df[centros_df['provincia_simple'] == selected_province]
        comarcas = sorted(filtered_by_province['comarca'].unique().tolist())
        comarca_dropdown.options.clear()
        comarca_dropdown.options.append(ft.dropdown.Option("TODAS LAS COMARCAS"))
        comarca_dropdown.options.extend([ft.dropdown.Option(c) for c in comarcas])
        comarca_dropdown.value = "TODAS LAS COMARCAS"
        comarca_dropdown.disabled = False
        update_map_status("Filtros actualizados. Presione 'Actualizar Mapa' para ver el relieve")
        page.update()

    def create_center_card(center_data: pd.Series) -> ft.Card:
        lat = center_data['latitud']
        lon = center_data['longitud']
        def open_google_maps(e): webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={lat},{lon}")
        
        if 'PÚBLICO' in center_data['regimen'].upper():
            regime_color, icon_color, icon = ft.Colors.BLUE_700, ft.Colors.BLUE_400, ft.Icons.SCHOOL
        elif 'PRIVADO' in center_data['regimen'].upper():
            regime_color, icon_color, icon = ft.Colors.RED_700, ft.Colors.RED_400, ft.Icons.BUSINESS
        elif 'CONCERTADO' in center_data['regimen'].upper():
            regime_color, icon_color, icon = ft.Colors.GREEN_700, ft.Colors.GREEN_400, ft.Icons.HANDSHAKE
        else:
            regime_color, icon_color, icon = ft.Colors.GREY_700, ft.Colors.GREY_400, ft.Icons.SCHOOL
        
        lat_dir, lon_dir = ("N" if lat >= 0 else "S"), ("E" if lon >= 0 else "W")
        lat_abs, lon_abs = abs(lat), abs(lon)
        
        return ft.Card(elevation=4, surface_tint_color=ft.Colors.WHITE, content=ft.Container(padding=15, bgcolor=ft.Colors.WHITE, border_radius=8,
            content=ft.Column([
                ft.Row([ft.Icon(icon, color=icon_color, size=20), ft.Text(center_data['dlibre'], weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.BLUE_GREY_900, expand=True)], spacing=10),
                ft.Divider(height=5, color=ft.Colors.GREY_200),
                ft.Row([ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=16, color=ft.Colors.GREY_600), ft.Text(f"{center_data['direccion']}, {center_data['localidad_oficial']}", size=12, color=ft.Colors.GREY_700, expand=True)], spacing=8),
                ft.Row([
                    ft.Icon(ft.Icons.TERRAIN, size=16, color=ft.Colors.GREY_600),
                    ft.Text(f"Comarca: {center_data['comarca']}", size=12, color=ft.Colors.GREY_700, expand=True),
                    ft.Container(
                        content=ft.Text(center_data['regimen'].upper(), size=11, color=regime_color, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.with_opacity(0.1, regime_color), border_radius=8, padding=ft.padding.symmetric(horizontal=10, vertical=4)
                    )
                ], spacing=8),
                ft.Row([
                    ft.Text(f"📍 {lat_abs:.4f}°{lat_dir}, {lon_abs:.4f}°{lon_abs:.4f}°{lon_dir}", size=10, color=ft.Colors.GREY_500, italic=True),
                    ft.Container(expand=True),
                    ft.FloatingActionButton("Ver en Maps", on_click=open_google_maps, icon=ft.Icons.EXPLORE, mini=True, bgcolor=ft.Colors.BLUE_50, shape=ft.RoundedRectangleBorder(radius=8))
                ], spacing=5)
            ], spacing=8)
        ))
    
    def update_map_image(data_subset: pd.DataFrame):
        """Genera y actualiza la imagen del mapa con relieve."""
        nonlocal current_filtered_data
        current_filtered_data = data_subset
        
        try:
            image_bytes = create_static_map_image(data_subset, update_map_status)
            base64_str = base64.b64encode(image_bytes).decode('utf-8')
            map_image.src_base64 = base64_str
            
        except Exception as e:
            update_map_status(f"❌ Error crítico en Matplotlib/Contextily. Revisar consola: {type(e).__name__}.")
            map_image.src_base64 = None
            
        finally:
            pass

    def update_data_and_map(e=None):
        """Filtra el DataFrame y actualiza el mapa y la lista cuando se presiona el botón."""
        
        if not province_dropdown.value:
            update_map_status("❌ Seleccione una provincia primero")
            return
        
        loading_indicator.visible = True
        update_map_status("🗻 Filtrando datos y generando relieve...")
        
        try:
            selected_province = province_dropdown.value.lower()
            selected_comarca = comarca_dropdown.value
            selected_regime = regime_dropdown.value
            
            filtered_df = centros_df[centros_df['provincia_simple'] == selected_province]
            
            if selected_comarca and selected_comarca != "TODAS LAS COMARCAS":
                filtered_df = filtered_df[filtered_df['comarca'] == selected_comarca]
            
            if selected_regime and selected_regime != "TODOS LOS REGÍMENES":
                filtered_df = filtered_df[filtered_df['regimen'].str.lower() == selected_regime.lower()]
            
            counter_text.value = f"Centros encontrados: {len(filtered_df)}"
            
            centers_list_column.controls.clear()
            display_df = filtered_df
            
            if not display_df.empty:
                for _, row in display_df.head(50).iterrows():
                    centers_list_column.controls.append(create_center_card(row))
                
                if len(display_df) > 50:
                    centers_list_column.controls.append(
                        ft.Container(content=ft.Text(f"🔍 ... y {len(display_df) - 50} centros más", color=ft.Colors.BLUE_600, italic=True, size=12), alignment=ft.alignment.center, padding=ft.padding.all(10))
                    )
            else:
                centers_list_column.controls.append(
                    ft.Container(content=ft.Column([ft.Icon(ft.Icons.SEARCH_OFF, size=48, color=ft.Colors.ORANGE_300), ft.Text("No se encontraron centros para los criterios seleccionados.", color=ft.Colors.ORANGE_700, text_align=ft.TextAlign.CENTER)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20), padding=ft.padding.all(20))
                )
            
            update_map_image(display_df)
            
        except Exception as ex:
            update_map_status(f"❌ Error en filtrado: {str(ex)[:50]}...")
            
        finally:
            loading_indicator.visible = False
            page.update()
    
    def clear_filters(e=None):
        if PROVINCES: province_dropdown.value = PROVINCES[0].capitalize()
        update_comarca_dropdown()
        regime_dropdown.value = "TODOS LOS REGÍMENES"
        update_map_status("🗺️ Filtros limpiados. Presione 'Actualizar Mapa' para ver el relieve")
        page.update()
    
    def export_data(e=None):
        if current_filtered_data is None or len(current_filtered_data) == 0:
            page.dialog = ft.AlertDialog(title=ft.Text("❌ Sin datos"), content=ft.Text("No hay datos para exportar. Filtre primero algunos centros."), actions=[ft.TextButton("OK", on_click=close_dialog)])
            page.dialog.open = True
            page.update()
            return
        
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"centros_educativos_{timestamp}.csv"
            current_filtered_data.to_csv(filename, index=False, encoding='utf-8-sig')
            page.dialog = ft.AlertDialog(title=ft.Text("✅ Datos exportados"), content=ft.Text(f"Se exportaron {len(current_filtered_data)} centros a:\n{filename}"), actions=[ft.TextButton("OK", on_click=close_dialog)])
            page.dialog.open = True
            page.update()
            
        except Exception as ex:
            page.dialog = ft.AlertDialog(title=ft.Text("❌ Error"), content=ft.Text(f"Error al exportar: {str(ex)[:100]}"), actions=[ft.TextButton("OK", on_click=close_dialog)])
            page.dialog.open = True
            page.update()
    
    def close_dialog(e):
        page.dialog.open = False
        page.update()
    
    # Asignar funciones a los botones
    update_button.on_click = update_data_and_map
    clear_button.on_click = clear_filters
    export_button.on_click = export_data
    province_dropdown.on_change = lambda e: update_comarca_dropdown()
    
    # ------------------
    # INTERFAZ DE USUARIO
    # ------------------
    
    selectors_row = ft.Column([
        ft.Row([
            ft.Column([ft.Text("Provincia:", size=12, color=ft.Colors.GREY_700), province_dropdown], spacing=5),
            ft.Column([ft.Text("Comarca:", size=12, color=ft.Colors.GREY_700), comarca_dropdown], spacing=5),
            ft.Column([ft.Text("Régimen:", size=12, color=ft.Colors.GREY_700), regime_dropdown], spacing=5),
            ft.VerticalDivider(width=1), 
            ft.Column([ft.Text("Acciones:", size=12, color=ft.Colors.GREY_700), ft.Row([update_button, clear_button, export_button], spacing=10)], spacing=5),
        ], spacing=15, vertical_alignment=ft.CrossAxisAlignment.END),
        
        ft.Row([
            counter_text, ft.Container(expand=True),
            ft.Row([loading_indicator, map_status_text], spacing=10)
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
    ], spacing=15)
    
    content_area = ft.Row([
        ft.Column([
            ft.Text("🗻 Mapa con Relieve Topográfico", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Text("Los centros se muestran sobre relieve del terreno", size=12, color=ft.Colors.GREY_600),
            map_container,
        ], expand=2, spacing=10),
        
        ft.Column([
            ft.Row([
                ft.Text("🏫 Lista de Centros", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Container(expand=True),
                ft.Text(f"(Mostrando primeros 50)", size=11, color=ft.Colors.GREY_600)
            ]),
            ft.Container(
                border=ft.border.all(1, ft.Colors.GREY_300), border_radius=10, padding=10, height=550,
                content=centers_list_column, expand=True, bgcolor=ft.Colors.GREY_50
            )
        ], expand=1, spacing=10),
    ], expand=True, spacing=20)
    
    page.add(
        ft.Column([
            title_text, subtitle_text,
            ft.Divider(height=20, color=ft.Colors.GREY_300),
            selectors_row,
            ft.Divider(height=20, color=ft.Colors.GREY_300),
            content_area
        ], spacing=0)
    )
    
    # Inicializar comarcas para la provincia por defecto
    if PROVINCES:
        update_comarca_dropdown()

# Punto de entrada de la aplicación
if __name__ == "__main__":
    ft.app(target=main,view=ft.WEB_BROWSER)