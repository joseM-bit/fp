import flet as ft
import pyproj
import webbrowser


def utm_to_latlon(easting, northing):
    """
    Convierte coordenadas UTM EPSG:25830 (ETRS89 / UTM 30N)
    a WGS84 (latitud / longitud).
    """
    transformer = pyproj.Transformer.from_crs(
        "EPSG:25830",  # ETRS89 / UTM zona 30N
        "EPSG:4326",   # WGS84 lat/lon
        always_xy=True
    )
    lon, lat = transformer.transform(easting, northing)
    return lat, lon


def main(page: ft.Page):
    # ---------------- CONFIGURACIÓN DE LA PÁGINA ----------------
    page.title = "Visualizador de Coordenadas UTM - Alicante"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.window_width = 900
    page.window_height = 800
    page.window_resizable = True

    # ---------------- COORDENADAS UTM ----------------
    utm_easting = 736527.717980862
    utm_northing = 4328279.18681103

    try:
        # Conversión
        lat, lon = utm_to_latlon(utm_easting, utm_northing)

        # ---------------- TÍTULO ----------------
        title = ft.Text(
            "🗺️ Visualizador de Coordenadas UTM",
            size=28,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_800
        )

        # ---------------- TARJETA DE COORDENADAS ----------------
        coordinates_card = ft.Card(
            elevation=6,
            content=ft.Container(
                padding=20,
                border_radius=10,
                bgcolor=ft.Colors.BLUE_GREY_50,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("📌 Coordenadas UTM (EPSG:25830)",
                                size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Este (Easting): {utm_easting:.3f} m"),
                        ft.Text(f"Norte (Northing): {utm_northing:.3f} m"),
                        ft.Text("Zona: 30N"),

                        ft.Divider(),

                        ft.Text("🌍 Coordenadas geográficas (WGS84)",
                                size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Latitud: {lat:.6f}°"),
                        ft.Text(f"Longitud: {lon:.6f}°"),
                    ]
                )
            )
        )

        # ---------------- MAPA EMBEBIDO ----------------
        delta = 0.005  # nivel de zoom
        map_url = (
            "https://www.openstreetmap.org/export/embed.html"
            f"?bbox={lon-delta}%2C{lat-delta}%2C{lon+delta}%2C{lat+delta}"
            f"&layer=mapnik&marker={lat}%2C{lon}"
        )

        map_container = ft.Container(
            height=400,
            border=ft.border.all(1, ft.Colors.GREY_400),
            border_radius=10,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.Container(
                        padding=10,
                        bgcolor=ft.Colors.BLUE_GREY_100,
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.MAP, color=ft.Colors.BLUE),
                                ft.Text(
                                    "Mapa interactivo (OpenStreetMap)",
                                    size=16,
                                    weight=ft.FontWeight.BOLD
                                ),
                            ]
                        )
                    ),
                    ft.WebView(
                        url=map_url,
                        expand=True
                    )
                ]
            )
        )

        # ---------------- FUNCIONES ----------------
        def open_google_maps(e):
            webbrowser.open(f"https://www.google.com/maps?q={lat},{lon}")

        def open_openstreetmap(e):
            webbrowser.open(f"https://www.openstreetmap.org/#map=16/{lat}/{lon}")

        def copy_coordinates(e):
            page.set_clipboard(f"{lat:.6f}, {lon:.6f}")
            page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("✅ Coordenadas copiadas al portapapeles"),
                    duration=2000
                )
            )

        # ---------------- BOTONES ----------------
        action_buttons = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            controls=[
                ft.ElevatedButton(
                    "Google Maps",
                    icon=ft.Icons.MAP,
                    on_click=open_google_maps,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE
                ),
                ft.ElevatedButton(
                    "OpenStreetMap",
                    icon=ft.Icons.PUBLIC,
                    on_click=open_openstreetmap,
                    bgcolor=ft.Colors.GREEN,
                    color=ft.Colors.WHITE
                ),
                ft.ElevatedButton(
                    "Copiar coordenadas",
                    icon=ft.Icons.COPY,
                    on_click=copy_coordinates,
                    bgcolor=ft.Colors.ORANGE,
                    color=ft.Colors.WHITE
                ),
            ]
        )

        # ---------------- INFO ----------------
        info_box = ft.Container(
            padding=15,
            bgcolor=ft.Colors.AMBER_50,
            border_radius=10,
            content=ft.Text(
                "Estas coordenadas pertenecen a la provincia de Alicante (España). "
                "El sistema EPSG:25830 es el estándar oficial utilizado por "
                "catastro, IGN y cartografía oficial.",
                size=14
            )
        )

        # ---------------- AÑADIR A LA PÁGINA ----------------
        page.add(
            title,
            ft.Divider(),
            coordinates_card,
            ft.Divider(),
            map_container,
            ft.Divider(),
            action_buttons,
            ft.Divider(),
            info_box
        )

    except Exception as e:
        page.add(
            ft.Text("❌ Error al procesar las coordenadas",
                    size=20, color=ft.Colors.RED),
            ft.Text(str(e))
        )


# ---------------- PUNTO DE ENTRADA ----------------
if __name__ == "__main__":
    ft.app(target=main,view=ft.WEB_BROWSER)
