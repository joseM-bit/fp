import pandas as pd
import os

def neteja_sql(text):
    """Escapa cometes simples per evitar errors de sintaxi SQL."""
    if pd.isna(text) or text == "":
        return "NULL"
    text_net = str(text).replace("'", "''").strip()
    return f"'{text_net}'"

directori_actual = os.path.dirname(os.path.abspath(__file__))
ruta_csv1 = os.path.join(directori_actual, "data/12_Centros(Valencia).csv")
ruta_csv2 = os.path.join(directori_actual, "data/oferta_fp.csv")
ruta_csv3 = os.path.join(directori_actual, "data/oferta_fp_especialitzacio.csv")

# 1. Carregar dades
print("📖 Carregant CSVs...")
centres_df = pd.read_csv(ruta_csv1)

# Definim les columnes exactes per als CSV d'oferta (CSV2 i CSV3)
cols_oferta = ['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'GRADO', 'FAMILIA', 'CICLO', 'TURNO', 'CURSOS']

# Carreguem ambdós CSV d'oferta
df_o_normal = pd.read_csv(ruta_csv2, names=cols_oferta, header=0, usecols=range(9))
df_o_especialitzacio = pd.read_csv(ruta_csv3, names=cols_oferta, header=0, usecols=range(9))

# ESTRATÈGIA: Ajuntem TOTA l'oferta en un sol DataFrame
# Així les titulacions del CSV3 també es crearan a la base de dades
oferta_total_df = pd.concat([df_o_normal, df_o_especialitzacio], ignore_index=True)

# 2. Neteja per a Matching
centres_df['nom_clean'] = centres_df['dlibre'].str.strip().str.upper()
oferta_total_df['CENTRO_clean'] = oferta_total_df['CENTRO'].str.strip().str.upper()

# 3. Processar Titulacions (Ara inclou les del CSV3)
print("🏗️ Preparant titulacions (FP + Especialització)...")
df_titulacions = oferta_total_df[['CICLO', 'FAMILIA', 'GRADO']].drop_duplicates().reset_index(drop=True)
df_titulacions['id_tit'] = df_titulacions.index + 1

# 4. Matching d'oferta total
print("🔗 Realitzant matching d'oferta...")
df_merge = pd.merge(oferta_total_df, centres_df[['codcen', 'nom_clean']], left_on='CENTRO_clean', right_on='nom_clean', how='left')
df_merge = pd.merge(df_merge, df_titulacions, on=['CICLO', 'FAMILIA', 'GRADO'], how='left')

# Eliminem duplicats basats en la clau primària (codcen, id_tit, torn)
df_oferta_final = df_merge.drop_duplicates(subset=['codcen', 'id_tit', 'TURNO']).copy()

# 5. GENERACIÓ DEL FITXER SQL ÚNIC
print("💾 Generant fitxer SQL amb dades de centres, FP i Especialització...")
centres_no_trobats = []

with open('inserts_fpdb0.sql', 'w', encoding='utf-8') as f:
    f.write("USE fpdb;\n")
    f.write("SET FOREIGN_KEY_CHECKS = 0; -- Seguretat total per a les claus estrangeres\n\n")

    # --- BLOC 1: CENTRES ---
    f.write("-- 1. INSERTS CENTRES\n")
    for _, r in centres_df.iterrows():
        f.write(f"INSERT INTO centres (codi, nom, descripcio, titular, provincia, comarca, localitat, direccio, telefon, correu, web, latitud, longitud) "
                f"VALUES ({r['codcen']}, {neteja_sql(r['dlibre'])}, {neteja_sql(r['dgenerica_val'])}, {neteja_sql(r['titular'])}, "
                f"{neteja_sql(r['provincia'])}, {neteja_sql(r['comarca'])}, {neteja_sql(r['localidad_oficial'])}, {neteja_sql(r['direccion'])}, "
                f"{neteja_sql(r['telef'])}, {neteja_sql(r['mail'])}, {neteja_sql(r['web'])}, {r['latitud']}, {r['longitud']});\n")

    # --- BLOC 2: TITULACIONS (Incloent el CSV3) ---
    f.write("\n-- 2. INSERTS TITULACIONS (FP i Cursos d'Especialització)\n")
    for _, r in df_titulacions.iterrows():
        f.write(f"INSERT INTO titulacions (id, nom_cicle, familia, grau) "
                f"VALUES ({r['id_tit']}, {neteja_sql(r['CICLO'])}, {neteja_sql(r['FAMILIA'])}, {neteja_sql(r['GRADO'])});\n")

    # --- BLOC 3: OFERTA TOTAL ---
    f.write("\n-- 3. INSERTS OFERTA (Dades combinades)\n")
    for _, r in df_oferta_final.iterrows():
        if pd.isna(r['codcen']):
            centres_no_trobats.append(r['CENTRO'])
        else:
            f.write(f"INSERT INTO oferta (codcen, id_titulacio, regim_formatiu, torn) "
                    f"VALUES ({int(r['codcen'])}, {int(r['id_tit'])}, {neteja_sql(r['RÉGIMEN'])}, {neteja_sql(r['TURNO'])});\n")

    f.write("\nSET FOREIGN_KEY_CHECKS = 1;")

# 6. Guardar errors de matching
centres_no_trobats_unics = sorted(list(set(centres_no_trobats)))
with open('errors_centres.txt', 'w', encoding='utf-8') as f_err:
    f_err.write(f"CENTRES ORFES DETECTATS (CSV2 + CSV3):\n" + "="*40 + "\n")
    for c in centres_no_trobats_unics: f_err.write(f"{c}\n")

print(f"✅ Procés finalitzat.")
print(f"📊 Titulacions totals processades: {len(df_titulacions)}")
print(f"📊 Inserts d'oferta generats: {len(df_oferta_final) - len(centres_no_trobats_unics)}")