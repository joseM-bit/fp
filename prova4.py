from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

# =========================
# CONFIGURACIÓN
# =========================
URL = "https://somfp.gva.es/fpcv/#/access-roads"
WAIT_TIME = 20

# =========================
# INICIAR NAVEGADOR
# =========================
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

driver.get(URL)

# =========================
# ESPERAR A QUE CARGUE LA TABLA
# =========================
wait = WebDriverWait(driver, WAIT_TIME)

wait.until(
    EC.presence_of_element_located((By.TAG_NAME, "table"))
)

time.sleep(2)  # estabilidad extra

# =========================
# EXTRAER TABLA
# =========================
table = driver.find_element(By.TAG_NAME, "table")
rows = table.find_elements(By.TAG_NAME, "tr")

data = []

for row in rows:
    cells = row.find_elements(By.TAG_NAME, "td")
    if cells:
        data.append([cell.text.strip() for cell in cells])

# =========================
# CREAR DATAFRAME
# =========================
columns = [
    "Vía de acceso",
    "Descripción",
    "Requisitos",
    "Observaciones"
]

df = pd.DataFrame(data, columns=columns[:len(data[0])])

# =========================
# GUARDAR CSV
# =========================
df.to_csv("access_roads_somfp.csv", index=False, encoding="utf-8")

print("✅ CSV generado: access_roads_somfp.csv")

driver.quit()
