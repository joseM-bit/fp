import flet as ft
import flet_webview as ftwv

def main(page: ft.Page):
    page.title = "Mapa en subfinestra"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 30
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # 1. Coordenades
    lat, lon = 41.3851, 2.1734
    delta = 0.005
    map_url = f"https://www.openstreetmap.org/export/embed.html?bbox={lon-delta}%2C{lat-delta}%2C{lon+delta}%2C{lat+delta}&layer=mapnik&marker={lat}%2C{lon}"

    # 2. Creem el WebView
    wv = ftwv.WebView(
        url=map_url,
        expand=True, # Dins del contenidor, que s'estire tot el que puga
    )

    # 3. La "Subfinestra" (Contenidor amb mides fixes)
    mapa_reduit = ft.Container(
        content=wv,
        width=500,        # Amplada de la subfinestra
        height=400,       # Alçada de la subfinestra
        border_radius=15, # Cantons arredonits
        border=ft.border.all(2, ft.Colors.BLUE_GREY_200),
        shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.BLACK12),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS, # Perquè el mapa no se n'isca dels cantons arredonits
    )

    # 4. Disseny de la pantalla principal
    page.add(
        ft.Text("La meua aplicació amb mapa", size=30, weight="bold"),
        ft.Text("Això és un text fora del mapa per demostrar l'espai.", color="grey"),
        ft.Divider(height=20),
        
        # Afegim el contenidor del mapa
        mapa_reduit,
        
        ft.Divider(height=20),
        ft.ElevatedButton("Botó de prova", icon="settings")
    )

if __name__ == "__main__":
    # Seguim usant el mode WEB per evitar errors a Linux
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)