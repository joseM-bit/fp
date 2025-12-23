import pandas as pd
import re


txt_file = "grado.csv.txt"
csv_file = "oferta_fp_25_26.csv"

data = []

# Leer líneas del TXT
with open(txt_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Saltar títulos o líneas vacías
lines = [line.strip() for line in lines if line.strip()]
lines = lines[1:]  # si quieres saltar la primera línea de encabezado grande

# Expresión regular: separar por 2 o más espacios consecutivos
pattern = re.compile(r'\s{2,}')

for line in lines:
    row = pattern.split(line)
    data.append(row)

# Determinar el número máximo de columnas en cualquier fila
max_cols = max(len(row) for row in data)

# Normalizar filas cortas rellenando con ""
for row in data:
    while len(row) < max_cols:
        row.append("")

# Crear nombres de columnas automáticos
columns = [f"col_{i+1}" for i in range(max_cols)]

# Crear DataFrame
df = pd.DataFrame(data, columns=columns)

# Guardar CSV
df.to_csv(csv_file, index=False, encoding="utf-8")

print(f"Archivo CSV generado: {csv_file}")
