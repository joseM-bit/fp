import flet as ft
from flet_webview import WebView
import pandas as pd
import webbrowser
import hashlib
from flet import Container, Text, Column, Row 
import os
import sys
import boto3
import re

# ----------------------------------------------------------------------
# 1. CÀRREGA I PREPROCESSAMENT DE DADES DE FP 
# ----------------------------------------------------------------------

# Noms d'arxius
FP_FILE = "oferta_fp_25_26.csv"
ESP_FILE = "oferta_fp_especialitzacio.csv" 
CENTER_COORDS_FILE = "a.csv" # <--- Arxiu amb coordenades reals


# Columnes finals esperades (9 elements)
FP_COLS = ['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'GRADO', 'FAMILIA', 'CICLO', 'TURNO', 'UNIDADES']
CANONICAL_GRADES = ['BÁSICO', 'BÁSICO 2A OPORTUNIDAD', 'MEDIO', 'SUPERIOR']

# --- MAPA DE COLUMNES DE L'ARXIU DE COORDENADES (a.csv) ---
COORDS_COLUMNS = {
    'dlibre': 'CENTRO_NAME',
    'noms_mun': 'LOCALIDAD_NAME',
    'provincia': 'PROVINCIA_NAME',
    'latitud': 'LATITUD',
    'longitud': 'LONGITUD',
}

# --- MAPA DE ESTANDARITZACIÓ DE PROVÍNCIES ---
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
    'ALACANT/ALICANTE': 'ALACANT', 
    'VALÈNCIA/VALENCIA': 'VALÈNCIA',
    # Añadimos variantes para Castelló
    'CASTELLÓ/CASTELLÓN': 'CASTELLÓ',
    'CASTELLO/CASTELLON': 'CASTELLÓ',
    'CASTELLON': 'CASTELLÓ',
    'CASTELLO DE LA PLANA': 'CASTELLÓ',
    'CASTELLÓN DE LA PLANA': 'CASTELLÓ',
    'CASTELLO DE LA PLANA': 'CASTELLÓ',
    'CASTELLÓN DE LA PLANA': 'CASTELLÓ',
    'CASTELLÓ - CASTELLÓN': 'CASTELLÓ',
    'CASTELLO - CASTELLON': 'CASTELLÓ',
    'CASTELLÓ/CASTELLÓN DE LA PLANA': 'CASTELLÓ',
    'CASTELLO/CASTELLON DE LA PLANA': 'CASTELLÓ',
}

# --- DADES DE GEOLOCALITZACIÓ SIMULADES (Com a últim recurs) ---
PROVINCE_CENTER_COORDS = {
    'ALACANT': {'lat': 38.3452, 'lon': -0.4810, 'delta_lat': 0.15, 'delta_lon': 0.2},
    'VALÈNCIA': {'lat': 39.4699, 'lon': -0.3763, 'delta_lat': 0.15, 'delta_lon': 0.15},
    'CASTELLÓ': {'lat': 39.9871, 'lon': -0.0381, 'delta_lat': 0.15, 'delta_lon': 0.2},
}

# Diccionari per guardar coordenades consistents per a cada centre
coords_cache = {}
comarca_map = {}

# --- MAPA DE COMARQUES MÉS COMPLET ---
# Si hi ha un fitxer comarcas.csv, es carregarà d'allà
# Si no, utilitzem aquest mapa ampliat
COMARCA_DATA = {}

# En la función load_comarcas_data, corregir la variable
def load_comarcas_data(file_path):
    """Carrega les dades de comarques des d'un fitxer CSV si existeix."""
    global COMARCA_DATA
    
    if os.path.exists(file_path):
        try:
            print(f"✅ Carregant comarques des de '{file_path}'")
            
            # Leer con cabecera
            try:
                df_a = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='warn')
            except UnicodeDecodeError:
                df_a = pd.read_csv(file_path, encoding='latin1', on_bad_lines='warn')
            
            print(f"   Files trobades: {len(df_a)}")
            
            # Reiniciar el diccionario de comarcas
            COMARCA_DATA = {}
            
            # Contadores para estadísticas
            localitats_carregades = 0
            provincies_trobades = set()
            comarcas_trobades = set()
            
            # Intentar identificar las columnas correctas
            # Posibles nombres de columnas para localidad, comarca y provincia
            posibles_localidad = ['localidad_oficial', 'noms_mun', 'localidad']
            posibles_comarca = ['comarca']
            posibles_provincia = ['provincia']
            
            # Encontrar las columnas reales
            col_localidad = None
            for col in posibles_localidad:
                if col in df_a.columns:
                    col_localidad = col
                    break
            
            col_comarca = None
            for col in posibles_comarca:
                if col in df_a.columns:
                    col_comarca = col
                    break
            
            col_provincia = None
            for col in posibles_provincia:
                if col in df_a.columns:
                    col_provincia = col
                    break
            
            if not all([col_localidad, col_comarca, col_provincia]):
                print(f"❌ No es poden trobar totes les columnes necessàries")
                print(f"   Localidad: {col_localidad}, Comarca: {col_comarca}, Provincia: {col_provincia}")
                return False
            
            print(f"   Columnes utilitzades: Localidad={col_localidad}, Comarca={col_comarca}, Provincia={col_provincia}")
            
            # Procesar cada fila
            for idx, row in df_a.iterrows():
                try:
                    # Obtener valores
                    provincia_raw = str(row[col_provincia]).strip() if not pd.isna(row[col_provincia]) else ""
                    localidad_raw = str(row[col_localidad]).strip() if not pd.isna(row[col_localidad]) else ""
                    comarca_raw = str(row[col_comarca]).strip() if not pd.isna(row[col_comarca]) else ""
                    
                    # Normalizar provincia
                    provincia_upper = provincia_raw.upper()
                    
                    # Aplicar mapeo de provincias
                    provincia = PROVINCE_MAP.get(provincia_upper, provincia_upper)
                    
                    # Si no coincide con las provincias esperadas, intentar detectar
                    if provincia not in ['ALACANT', 'VALÈNCIA', 'CASTELLÓ']:
                        if 'ALACANT' in provincia_upper or 'ALICANT' in provincia_upper:
                            provincia = 'ALACANT'
                        elif 'VALÈNCIA' in provincia_upper or 'VALENCIA' in provincia_upper:
                            provincia = 'VALÈNCIA'
                        elif 'CASTELL' in provincia_upper:
                            provincia = 'CASTELLÓ'
                        else:
                            continue  # Saltar si no es de las provincias objetivo
                    
                    # Normalizar localidad (convertir a mayúsculas y limpiar)
                    localidad = localidad_raw.upper().strip()
                    
                    # Normalizar comarca
                    comarca = comarca_raw.strip()
                    if comarca:
                        # Eliminar artículos iniciales y convertir a mayúsculas
                        comarca = re.sub(r'^(el |la |l\'|els |les )', '', comarca, flags=re.IGNORECASE)
                        comarca = comarca.upper()
                    
                    # Saltar si falta algún campo
                    if not provincia or not localidad or not comarca:
                        continue
                    
                    # Inicializar provincia si no existe
                    if provincia not in COMARCA_DATA:
                        COMARCA_DATA[provincia] = {}
                    
                    # Asignar comarca a localidad (si no existe ya)
                    if localidad not in COMARCA_DATA[provincia]:
                        COMARCA_DATA[provincia][localidad] = comarca
                        localitats_carregades += 1
                        provincies_trobades.add(provincia)
                        comarcas_trobades.add(comarca)
                        
                        # También registrar variaciones sin paréntesis
                        if '(' in localidad:
                            localidad_sin_parentesis = localidad.split('(')[0].strip()
                            if localidad_sin_parentesis and localidad_sin_parentesis != localidad:
                                COMARCA_DATA[provincia][localidad_sin_parentesis] = comarca
                                localitats_carregades += 1
                
                except Exception as e:
                    # Si hay error en una fila, continuar con la siguiente
                    continue
            
            print(f"✅ Carregades {localitats_carregades} localitats amb comarca")
            print(f"✅ Províncies trobades: {', '.join(sorted(provincies_trobades))}")
            
            # Mostrar estadísticas por provincia
            for provincia in sorted(COMARCA_DATA.keys()):
                print(f"   - {provincia}: {len(COMARCA_DATA[provincia])} localitats")
                
                # Mostrar algunas localidades de Castelló para debug
                if provincia == 'CASTELLÓ':
                    print(f"     Exemple de localitats de Castelló: {', '.join(list(COMARCA_DATA[provincia].keys())[:10])}")
            
            # Mostrar comarcas únicas
            print(f"✅ Comarques úniques trobades: {len(comarcas_trobades)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error carregant comarques des de '{file_path}': {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Si no hay archivo, usar el mapa interno
    print("⚠️ No s'ha trobat fitxer a.csv. Utilitzant mapa intern de comarcas.")
    
    # [Mantener el mapa interno existente...]
    
    return False

def load_center_coordinates(file_path):
    """
    Carrega el catàleg de centres (a.csv) i crea un diccionari de recerca de coordenades.
    """
    global coords_cache
    if not os.path.exists(file_path):
        print(f"⚠️ NO es pot carregar '{file_path}'. Utilitzant simulació de coordenades.")
        return

    try:
        # Intentar UTF-8 y luego ISO-8859-1 (latin1)
        try:
            df_coords = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='warn')
        except UnicodeDecodeError:
            df_coords = pd.read_csv(file_path, encoding='latin1', on_bad_lines='warn')

        print(f"✅ Carregant coordenades des de '{file_path}'")
        print(f"   Columnes trobades: {list(df_coords.columns)}")
        
        # Según la estructura del archivo, las columnas relevantes son:
        # dlibre: nombre del centro (columna 3)
        # noms_mun: localidad (columna 18)
        # provincia: provincia (columna 21)
        # latitud: latitud (columna 22)
        # longitud: longitud (columna 23)
        
        # Renombrar según COORDS_COLUMNS (ajustar según los nombres reales)
        if 'dlibre' in df_coords.columns and 'noms_mun' in df_coords.columns and 'provincia' in df_coords.columns and 'latitud' in df_coords.columns and 'longitud' in df_coords.columns:
            
            # Renombrar para mantener consistencia
            df_coords = df_coords.rename(columns={
                'dlibre': 'CENTRO_NAME',
                'noms_mun': 'LOCALIDAD_NAME',
                'provincia': 'PROVINCIA_NAME',
                'latitud': 'LATITUD',
                'longitud': 'LONGITUD'
            })
            
            # Resto del código permanece igual...
            # Neteja i estandardització
            for col in ['CENTRO_NAME', 'LOCALIDAD_NAME', 'PROVINCIA_NAME']:
                if col in df_coords.columns:
                    df_coords[col] = df_coords[col].astype(str).str.strip().str.upper()
                else:
                    print(f"⚠️ Columna {col} no encontrada en el archivo")
                    return
            
            df_coords['PROVINCIA_NAME'] = df_coords['PROVINCIA_NAME'].apply(lambda x: PROVINCE_MAP.get(x, x))
            
            # Convertir coordenades a numèric
            df_coords['LATITUD'] = pd.to_numeric(df_coords['LATITUD'], errors='coerce')
            df_coords['LONGITUD'] = pd.to_numeric(df_coords['LONGITUD'], errors='coerce')
            
            # Filtrar files sense coordenades vàlides
            df_coords = df_coords.dropna(subset=['LATITUD', 'LONGITUD'])
            
            # Crear la clau de recerca: CENTRE + LOCALITAT + PROVINCIA
            df_coords['KEY'] = df_coords['PROVINCIA_NAME'] + "_" + df_coords['LOCALIDAD_NAME'] + "_" + df_coords['CENTRO_NAME']
            
            # Omplir la caché de coordenades
            for index, row in df_coords.iterrows():
                if row['KEY'] not in coords_cache:
                    coords_cache[row['KEY']] = {'latitud': row['LATITUD'], 'longitud': row['LONGITUD']}
            
            print(f"✅ Coordenades de {len(coords_cache)} centres carregades de '{file_path}'.")
        else:
            print(f"❌ El archivo '{file_path}' no tiene las columnas esperadas")
            print(f"   Columnas necesarias: dlibre, noms_mun, provincia, latitud, longitud")
            print(f"   Columnas encontradas: {list(df_coords.columns)}")

    except Exception as e:
        print(f"❌ Error crític en processar les coordenades de '{file_path}': {e}")
        import traceback
        traceback.print_exc()
        coords_cache = {}


def get_consistent_coords(row):
    """
    Retorna coordenades consistents. 
    1. Busca a la caché de coordenades reals (carregada d'a.csv).
    2. Si no troba, genera coordenades simulades.
    """
    # Crear la clau de recerca amb les dades de l'oferta de FP
    key = f"{row['PROVINCIA']}_{row['LOCALIDAD']}_{row['CENTRO']}"
    
    # 1. Intentar trobar a la caché REAL 
    if key in coords_cache:
        return pd.Series(coords_cache[key])
    
    # 2. Si no troba, generar coordenades SIMULADES (fallback)
    if row['PROVINCIA'] in PROVINCE_CENTER_COORDS:
        
        # Generació de hash consistent per simular
        hash_str = hashlib.md5(key.encode()).hexdigest()
        hash_int_lat = int(hash_str[:8], 16)
        hash_int_lon = int(hash_str[8:16], 16)
        
        norm_lat = hash_int_lat / 0xFFFFFFFF
        norm_lon = hash_int_lon / 0xFFFFFFFF
        
        base = PROVINCE_CENTER_COORDS[row['PROVINCIA']]
        
        lat = base['lat'] + (norm_lat - 0.5) * base['delta_lat'] * 1.5
        lon = base['lon'] + (norm_lon - 0.5) * base['delta_lon'] * 1.5
        
        localidad_hash = hashlib.md5(f"{row['PROVINCIA']}_{row['LOCALIDAD']}".encode()).hexdigest()
        localidad_int = int(localidad_hash[:8], 16)
        norm_localidad = localidad_int / 0xFFFFFFFF
        
        localidad_lat_offset = (norm_localidad - 0.5) * base['delta_lat'] * 0.2
        localidad_lon_offset = (norm_localidad - 0.5) * base['delta_lon'] * 0.2
        
        lat += localidad_lat_offset
        lon += localidad_lon_offset
        
        result = {'latitud': lat, 'longitud': lon}
        coords_cache[key] = result
        return pd.Series(result)
    
    # Retornar coordenades de fallback (0.0, 0.0) si la província no està mapejada
    return pd.Series({'latitud': 0.0, 'longitud': 0.0})


def get_comarca(provincia, localidad):
    """Retorna la comarca per a una localitat i província donades."""
    provincia = str(provincia).strip().upper()
    localidad = str(localidad).strip().upper()
    
    # 1. Buscar exacte
    if provincia in COMARCA_DATA:
        if localidad in COMARCA_DATA[provincia]:
            return COMARCA_DATA[provincia][localidad]
        
        # 2. Buscar variaciones (sin acentos, sin paréntesis, etc.)
        # Normalizar localidad: quitar acentos y caracteres especiales
        localidad_normalizada = localidad
        # Reemplazar caracteres con acentos
        replacements = {
            'À': 'A', 'Á': 'A', 'Â': 'A',
            'È': 'E', 'É': 'E', 'Ê': 'E',
            'Ì': 'I', 'Í': 'I', 'Î': 'I',
            'Ò': 'O', 'Ó': 'O', 'Ô': 'O',
            'Ù': 'U', 'Ú': 'U', 'Û': 'U',
            'Ç': 'C', 'Ñ': 'N'
        }
        for orig, repl in replacements.items():
            localidad_normalizada = localidad_normalizada.replace(orig, repl)
        
        # Buscar en las claves normalizadas
        for loc_key, comarca in COMARCA_DATA[provincia].items():
            loc_key_normalizada = loc_key
            for orig, repl in replacements.items():
                loc_key_normalizada = loc_key_normalizada.replace(orig, repl)
            
            # Comparación flexible
            if (loc_key_normalizada == localidad_normalizada or
                localidad_normalizada in loc_key_normalizada or
                loc_key_normalizada in localidad_normalizada):
                return comarca
        
        # 3. Si la localidad contiene "DE LA PLANA", intentar sin eso
        if 'DE LA PLANA' in localidad:
            localidad_simple = localidad.replace('DE LA PLANA', '').strip()
            if localidad_simple in COMARCA_DATA[provincia]:
                return COMARCA_DATA[provincia][localidad_simple]
    
    # 4. Si no trobem, retornar comarca per defecte
    if provincia == 'VALÈNCIA':
        return 'CIUTAT DE VALÈNCIA'
    elif provincia == 'ALACANT':
        return 'ALACANTÍ'
    elif provincia == 'CASTELLÓ':
        return 'PLANA ALTA'
    
    return f'NO DEFINIDA - {provincia}'


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
    """Càrrega i neteja els dos arxius CSV, retornant un dict de DataFrames amb coordenades (reals + simulades)."""
    data_frames = {}
    
    # Funció auxiliar per llegir i estandarditzar CSV d'oferta
    def safe_read_csv(file, skip_rows_func, cols):
        try:
            try:
                df = pd.read_csv(file, header=None, skiprows=skip_rows_func, encoding='utf-8', on_bad_lines='warn')
            except UnicodeDecodeError:
                df = pd.read_csv(file, header=None, skiprows=skip_rows_func, encoding='latin1', on_bad_lines='warn')

            if df.shape[1] < len(cols) - 1:
                raise ValueError(f"L'arxiu {file} té massa poques columnes.")

            if len(cols) == 9 and df.shape[1] >= 8:
                temp_cols_map = ['PROVINCIA', 'LOCALIDAD', 'CENTRO_REGIMEN', 'GRADO_RAW', 'FAMILIA', 'CICLO', 'TURNO', 'UNIDADES']
                
                # Si hi ha més de 8 columnes, usem les 9 esperades, si no, assumim que CENTRE/RÉGIMEN estan junts
                if df.shape[1] >= 9:
                    df = df.iloc[:, :9].copy()
                    df.columns = cols
                else:
                    df = df.iloc[:, :8].copy()
                    df.columns = temp_cols_map
                    
                    df['RÉGIMEN'] = df['CENTRO_REGIMEN'].astype(str).str.split().str[-1].str.upper()
                    df['CENTRO'] = df['CENTRO_REGIMEN'].astype(str).apply(lambda x: ' '.join(x.split()[:-1]))
                    df.drop(columns=['CENTRO_REGIMEN'], inplace=True)
                    df = df[['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'GRADO_RAW', 'FAMILIA', 'CICLO', 'TURNO', 'UNIDADES']].copy()
                    df.columns = cols
                
                return df
            else:
                raise ValueError(f"L'estructura de columnes de {file} no es correspon amb l'esperada.")
                
        except Exception as e:
            raise Exception(f"Error en llegir {file}: {e}")

    # 0. Carregar el diccionari de coordenades reals
    load_center_coordinates(CENTER_COORDS_FILE)
    
    # 1. Carregar dades de comarques
    load_comarcas_data(CENTER_COORDS_FILE)


    # --- Processar oferta_fp_25_26.csv (FP Standard) ---
    try:
        df_fp = safe_read_csv(FP_FILE, lambda x: x < 4, FP_COLS)
        
        # Neteja i estandardització
        for col in ['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'FAMILIA', 'CICLO', 'TURNO']:
             df_fp[col] = df_fp[col].astype(str).str.strip().str.upper().replace('NAN', '', regex=False)
             
        df_fp['PROVINCIA'] = df_fp['PROVINCIA'].apply(lambda x: PROVINCE_MAP.get(x, x))
        df_fp['GRADO'] = df_fp['GRADO'].astype(str).apply(standardize_grade)
        
        df_fp = df_fp[df_fp['GRADO'].isin(CANONICAL_GRADES)].copy()
        
        df_fp['UNIDADES'] = pd.to_numeric(df_fp['UNIDADES'], errors='coerce').fillna(0).astype(int)

        # Aplicar coordenades (busca real, si no, simula)
        df_fp[['latitud', 'longitud']] = df_fp.apply(get_consistent_coords, axis=1)
        
        # Afegir columna COMARCA
        df_fp['COMARCA'] = df_fp.apply(lambda row: get_comarca(row['PROVINCIA'], row['LOCALIDAD']), axis=1)
        
        data_frames['FP_STANDARD'] = df_fp
        print(f"✅ Carregat {FP_FILE} amb {len(df_fp)} registres.")
    except Exception as e:
        print(f"❌ Error en carregar {FP_FILE}: {e}")
        data_frames['FP_STANDARD'] = pd.DataFrame(columns=FP_COLS + ['latitud', 'longitud', 'COMARCA'])


    # --- Processar oferta_fp_especialitzacio.csv (Especialització) ---
    try:
        df_esp = safe_read_csv(ESP_FILE, lambda x: x < 3, FP_COLS)
        
        # Neteja i estandardització
        for col in ['PROVINCIA', 'LOCALIDAD', 'CENTRO', 'RÉGIMEN', 'FAMILIA', 'CICLO', 'TURNO']:
             df_esp[col] = df_esp[col].astype(str).str.strip().str.upper().replace('NAN', '', regex=False)

        df_esp['PROVINCIA'] = df_esp['PROVINCIA'].apply(lambda x: PROVINCE_MAP.get(x, x))
        df_esp['GRADO'] = df_esp['GRADO'].astype(str).apply(standardize_esp_grade)
        
        df_esp['UNIDADES'] = pd.to_numeric(df_esp['UNIDADES'], errors='coerce').fillna(0).astype(int)
        
        df_esp = df_esp[df_esp['GRADO'] != 'ESPECIALIZACIÓN'].copy()
        
        # Aplicar coordenades (busca real, si no, simula)
        df_esp[['latitud', 'longitud']] = df_esp.apply(get_consistent_coords, axis=1)
        
        # Afegir columna COMARCA
        df_esp['COMARCA'] = df_esp.apply(lambda row: get_comarca(row['PROVINCIA'], row['LOCALIDAD']), axis=1)

        data_frames['FP_ESPECIALIZACION'] = df_esp
        print(f"✅ Carregat {ESP_FILE} amb {len(df_esp)} registres.")
    except Exception as e:
        print(f"❌ Error en carregar {ESP_FILE}: {e}")
        data_frames['FP_ESPECIALIZACION'] = pd.DataFrame(columns=FP_COLS + ['latitud', 'longitud', 'COMARCA'])

    return data_frames

def get_clean_sorted_list(series):
    """Filtra NaNs, converteix a string i ordena la llista de valors únics."""
    return sorted(series.dropna().astype(str).str.strip().unique().tolist())

# Càrrega global de dades
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
        delta = 0.5
    else:
        valid_coords = data_subset[(data_subset['latitud'] != 0.0) & (data_subset['longitud'] != 0.0)]
        
        if len(valid_coords) == 0:
            lat, lon = default_lat, default_lon
            delta = 0.5
        else:
            lat_min, lat_max = valid_coords['latitud'].min(), valid_coords['latitud'].max()
            lon_min, lon_max = valid_coords['longitud'].min(), valid_coords['longitud'].max()
            
            # Ajustar delta per cobrir un rang raonable, fins i tot si només hi ha un punt
            lat_range = max(lat_max - lat_min, 0.05) 
            lon_range = max(lon_max - lon_min, 0.05)
            
            lat = (lat_min + lat_max) / 2
            lon = (lon_min + lon_max) / 2
            
            delta = max(lat_range, lon_range, 0.1) * 1.2 # Marge per zoom

    bbox_str = f"{lon-delta}%2C{lat-delta}%2C{lon+delta}%2C{lat+delta}"
    
    markers = ""
    # Limitem a 100 marcadors per rendiment
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
        if provincia in PROVINCE_CENTER_COORDS:
            base = PROVINCE_CENTER_COORDS[provincia]
            lat, lon = base['lat'], base['lon']
            delta = 0.1
        else:
            lat, lon = 39.4699, -0.3763
            delta = 0.1
    else:
        delta = 0.01
    
    bbox_str = f"{lon-delta}%2C{lat-delta}%2C{lon+delta}%2C{lat+delta}"
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
    elif 'PRIVADO' in regime_upper or 'CONCERTADO' in regime_upper:
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
        self.COMARCAS = get_clean_sorted_list(initial_df['COMARCA'])
        self.LOCALIDADES = get_clean_sorted_list(initial_df['LOCALIDAD'])
        
        # Controles de UI
        self.results_list_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)
        self.counter_text = ft.Text("Ofertes trobades: 0", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)
        self.total_units_text = ft.Text("Unitats ofertades: 0", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800)
        
        # Dropdowns principals
        province_options = [ft.dropdown.Option("TOTES LES PROVÍNCIES")] + [ft.dropdown.Option(p) for p in self.PROVINCES]
        self.province_dropdown = ft.Dropdown(options=province_options, label="Província", width=180, value="TOTES LES PROVÍNCIES")
        
        grade_options = [ft.dropdown.Option("TOTS ELS GRAUS")] + [ft.dropdown.Option(g) for g in self.GRADES]
        self.grade_dropdown = ft.Dropdown(options=grade_options, label="Grau (FP)", width=180, value="TOTS ELS GRAUS")

        # Dropdowns nous per a comarca i ciutat
        comarca_options = [ft.dropdown.Option("TOTES LES COMARQUES")] + [ft.dropdown.Option(c) for c in self.COMARCAS]
        self.comarca_dropdown = ft.Dropdown(options=comarca_options, label="Comarca", width=220, value="TOTES LES COMARQUES")
        
        localidad_options = [ft.dropdown.Option("TOTES LES LOCALITATS")] + [ft.dropdown.Option(l) for l in self.LOCALIDADES]
        self.localidad_dropdown = ft.Dropdown(options=localidad_options, label="Localitat / Ciutat", width=220, value="TOTES LES LOCALITATS")

        cycle_options = [ft.dropdown.Option("TOTS ELS CICLES/CURSOS")] + [ft.dropdown.Option(c) for c in self.CYCLES]
        self.cycle_dropdown = ft.Dropdown(options=cycle_options, label="Cicle / Curs", width=300, value="TOTS ELS CICLES/CURSOS")
        
        # Botons
        self.update_button = ft.IconButton(
            icon=ft.Icons.SEARCH, icon_color="white", bgcolor=ft.Colors.BLUE_700,
            width=45, height=45, on_click=self.update_results, tooltip="Aplicar Filtres"
        )
        
        self.clear_button = ft.IconButton(
            icon=ft.Icons.RESTART_ALT, icon_color=ft.Colors.GREY_700,
            width=45, height=45, on_click=self.clear_filters, tooltip="Netejar Filtres")
        
        self.show_all_button = ft.ElevatedButton(
            text="📌 Mostrar tots els centres",
            icon=ft.Icons.MAP,
            on_click=self.show_all_centers,
            style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE),
            height=40
        )
        
        # Assignació de Handlers
        self.province_dropdown.on_change = self.update_dependent_dropdowns
        self.comarca_dropdown.on_change = self.update_localidad_dropdown
        self.grade_dropdown.on_change = self.update_cycle_dropdown
        
        # Construcció de la interfície amb nova organització
        self.filter_section = ft.Container(
            padding=ft.padding.all(15),
            border_radius=10,
            bgcolor=ft.Colors.BLUE_GREY_50,
            content=ft.Column([
                ft.Text(f"Filtres per a {title}", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_GREY_800),
                
                # Primera fila: Província, Comarca, Localitat
                ft.Row([
                    self.province_dropdown,
                    self.comarca_dropdown,
                    self.localidad_dropdown,
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
                
                # Segona fila: Grau, Cicle, Botons
                ft.Row([
                    self.grade_dropdown,
                    self.cycle_dropdown,
                    ft.Container(width=20),
                    self.update_button,
                    self.clear_button
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
                
                # Informació sobre les comarques
                ft.Container(
                    ft.Text("💡 Selecciona una província per veure les seues comarques i localitats disponibles",
                           size=12, color=ft.Colors.BLUE_700, italic=True),
                    padding=ft.padding.only(top=5)
                )
            ], spacing=15)
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
    
    def update_dependent_dropdowns(self, e=None):
        """Actualitza els dropdowns de comarca i localitat segons la província seleccionada."""
        filtered_df = self.initial_df.copy()
        selected_province = self.province_dropdown.value
        
        if selected_province and selected_province != "TOTES LES PROVÍNCIES":
            filtered_df = filtered_df[filtered_df['PROVINCIA'] == selected_province]
        
        # Actualitzar comarques
        filtered_comarcas = get_clean_sorted_list(filtered_df['COMARCA'])
        self.comarca_dropdown.options = [ft.dropdown.Option("TOTES LES COMARQUES")] + [ft.dropdown.Option(c) for c in filtered_comarcas]
        self.comarca_dropdown.value = "TOTES LES COMARQUES"
        
        # Actualitzar localitats
        self.update_localidad_dropdown()
        
        # Actualitzar cicles
        self.update_cycle_dropdown()
        
        if e:
            self.page.update()
    
    def update_localidad_dropdown(self, e=None):
        """Actualitza el dropdown de localitats segons la província i comarca seleccionades."""
        filtered_df = self.initial_df.copy()
        selected_province = self.province_dropdown.value
        selected_comarca = self.comarca_dropdown.value
        
        if selected_province and selected_province != "TOTES LES PROVÍNCIES":
            filtered_df = filtered_df[filtered_df['PROVINCIA'] == selected_province]
            
        if selected_comarca and selected_comarca != "TOTES LES COMARQUES":
            filtered_df = filtered_df[filtered_df['COMARCA'] == selected_comarca]
        
        filtered_localidades = get_clean_sorted_list(filtered_df['LOCALIDAD'])
        
        # Ordenar alfabèticament
        filtered_localidades.sort()
        
        self.localidad_dropdown.options = [ft.dropdown.Option("TOTES LES LOCALITATS")] + [ft.dropdown.Option(l) for l in filtered_localidades]
        self.localidad_dropdown.value = "TOTES LES LOCALITATS"
        
        if e:
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
        
        self.cycle_dropdown.options = [ft.dropdown.Option("TOTS ELS CICLES/CURSOS")] + [ft.dropdown.Option(c) for c in filtered_cycles]
        self.cycle_dropdown.value = "TOTS ELS CICLES/CURSOS"
        
        if e:
            self.page.update()
    
    def create_offer_card(self, offer_data: pd.Series, index: int) -> ft.Card:
        """Crea una targeta d'oferta amb interacció de clic."""
        regime_color, bg_color, icon = get_regime_style(offer_data['RÉGIMEN'])
        
        # Per obrir el mapa extern (Google Maps)
        search_query = f"{offer_data['CENTRO']}, {offer_data['LOCALIDAD']}, {offer_data['PROVINCIA']}"
        map_url = f"https://www.google.com/maps/search/?api=1&query={search_query.replace(' ', '+')}" 

        def open_map_external(e):
            try:
                webbrowser.open(map_url)
            except Exception as ex:
                print(f"Error obrint el mapa: {ex}")

        def on_card_click(e):
            """Quan es fa clic a la targeta, es selecciona i es centra el mapa."""
            # Desseleccionar la targeta anterior
            if self.selected_card_index is not None and self.selected_card_index < len(self.results_list_column.controls):
                old_card = self.results_list_column.controls[self.selected_card_index]
                if isinstance(old_card.content, ft.Container):
                    old_card.content.bgcolor = ft.Colors.WHITE
                    old_card.elevation = 2
                    old_card.content.border = None
            
            # Seleccionar la targeta actual
            self.selected_card_index = index
            if isinstance(e.control.content, ft.Container):
                 e.control.content.bgcolor = ft.Colors.BLUE_50
                 e.control.elevation = 5
                 e.control.content.border = ft.border.all(2, ft.Colors.BLUE_500)
            
            self.center_map_on_selected(offer_data)
            
            self.page.update()
        
        grado_text = offer_data.get('GRADO', 'N/A').upper() 
        ciclo_text = offer_data.get('CICLO', 'N/A').upper()
        
        is_esp_course = 'CURSO' in ciclo_text
        
        grado_style_text = grado_text
        if is_esp_course:
            grado_style_text = f"C. ESP. ({grado_text})"
        
        # Afegir informació de comarca a la targeta
        comarca_info = offer_data.get('COMARCA', 'N/A')
        
        card_content = ft.Container(
            padding=15,
            bgcolor=ft.Colors.WHITE,
            border_radius=8,
            on_click=on_card_click,
            content=ft.Column([
                ft.Row([
                    ft.Text(ciclo_text, weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.BLUE_GREY_900, expand=True),
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
                    ft.Icon(ft.Icons.MAP_OUTLINED, size=16, color=ft.Colors.PURPLE_600),
                    ft.Text(f"Comarca: {comarca_info}", size=12, color=ft.Colors.GREY_700),
                    ft.Container(width=10),
                    ft.Icon(ft.Icons.CATEGORY_OUTLINED, size=16, color=ft.Colors.INDIGO_600),
                    ft.Text(f"Família: {offer_data['FAMILIA']}", size=12, color=ft.Colors.GREY_700),
                ], spacing=5),

                ft.Row([
                    ft.Icon(ft.Icons.ACCESS_TIME, size=16, color=ft.Colors.AMBER_700),
                    ft.Text(f"Torn: {offer_data['TURNO']}", size=12, color=ft.Colors.GREY_700),
                    ft.Container(expand=True),
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
            ], spacing=8)
        )
        
        return ft.Card(
            elevation=2,
            content=card_content
        )
    
    def center_map_on_selected(self, offer_data: pd.Series):
        """Centra el mapa en el centre seleccionat."""
        if self.map_container_ref.current:
            map_content = ft.Column([
                ft.Row([
                    ft.Text(f"📍 {offer_data['CENTRO']}", size=16, weight="bold", expand=True),
                    self.show_all_button # Botó per tornar a la vista de tots els centres
                ]),
                ft.Text(f"{offer_data['LOCALIDAD']} ({offer_data['PROVINCIA']}) - {offer_data.get('COMARCA', '')}", 
                       size=14, color=ft.Colors.BLUE_700, weight=ft.FontWeight.W_600),
                ft.Text(f"{offer_data['CICLO']} - {offer_data['FAMILIA']}", size=12, color=ft.Colors.GREY_600),
                ft.Text(f"Grau: {offer_data['GRADO']} | Torn: {offer_data['TURNO']} | Unitats: {offer_data['UNIDADES']}", size=11, color=ft.Colors.GREY_500),
                ft.Container(
                    WebView(
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
            ], spacing=10)
            
            self.map_container_ref.current.content = ft.Container(
                content=map_content,
                padding=10
            )
            self.page.update()
    
    def show_all_centers(self, e=None):
        """Torna a mostrar tots els centres al mapa."""
        if self.map_container_ref.current and not self.current_filtered_df.empty:
            
            # Desseleccionar la targeta si n'hi havia una de seleccionada
            if self.selected_card_index is not None and self.selected_card_index < len(self.results_list_column.controls):
                old_card = self.results_list_column.controls[self.selected_card_index]
                if isinstance(old_card.content, ft.Container):
                    old_card.content.bgcolor = ft.Colors.WHITE
                    old_card.elevation = 2
                    old_card.content.border = None
            
            self.selected_card_index = None # IMPORTANT: Reinicia l'índex

            # Crear el contingut del mapa massiu
            total_centers = len(self.current_filtered_df)
            map_content = ft.Column([
                ft.Text(f"📍 Mapa de tots els centres ({total_centers} centres)", 
                       size=18, weight="bold"),
                ft.Container(
                    WebView(
                        url=get_osm_url_all_centers(self.current_filtered_df),
                        expand=True
                    ),
                    height=700,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                ),
                ft.Text(f"Mostrant fins a 100 marcadors. Total de centres: {total_centers}", 
                       size=12, color=ft.Colors.GREY_600)
            ], spacing=10)
            
            self.map_container_ref.current.content = ft.Container(
                content=map_content,
                padding=10
            )
            self.page.update()
    
    def update_results(self, e=None):
        """Aplica tots els filtres i actualitza la llista de resultats i el mapa."""
        self.update_button.disabled = True
        self.clear_button.disabled = True
        if e:
            self.page.update()
        
        filtered_df = self.initial_df.copy()
        
        selected_province = self.province_dropdown.value
        selected_comarca = self.comarca_dropdown.value
        selected_localidad = self.localidad_dropdown.value
        selected_grade = self.grade_dropdown.value
        selected_cycle = self.cycle_dropdown.value
        
        # Aplicar filtres en cascada
        if selected_province and selected_province != "TOTES LES PROVÍNCIES":
            filtered_df = filtered_df[filtered_df['PROVINCIA'] == selected_province]
            
        if selected_comarca and selected_comarca != "TOTES LES COMARQUES":
            filtered_df = filtered_df[filtered_df['COMARCA'] == selected_comarca]
            
        if selected_localidad and selected_localidad != "TOTES LES LOCALITATS":
            filtered_df = filtered_df[filtered_df['LOCALIDAD'] == selected_localidad]
            
        if selected_grade and selected_grade != "TOTS ELS GRAUS":
            filtered_df = filtered_df[filtered_df['GRADO'] == selected_grade]

        if selected_cycle and selected_cycle != "TOTS ELS CICLES/CURSOS":
            filtered_df = filtered_df[filtered_df['CICLO'] == selected_cycle]
        
        self.current_filtered_df = filtered_df.copy()
        
        # MOSTRAR TOTS ELS PUNTS PER DEFECTE (Això és el que garanteix la vista múltiple)
        self.show_all_centers()
        
        total_units = filtered_df['UNIDADES'].sum()
        self.counter_text.value = f"Ofertes trobades: {len(filtered_df)}"
        # Format per separat milers i decimals
        self.total_units_text.value = f"Unitats ofertades: {total_units:,}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".") 
        
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
        self.comarca_dropdown.value = "TOTES LES COMARQUES"
        self.localidad_dropdown.value = "TOTES LES LOCALITATS"
        self.grade_dropdown.value = "TOTS ELS GRAUS"
        
        # Restaurar opcions originals
        self.comarca_dropdown.options = [ft.dropdown.Option("TOTES LES COMARQUES")] + [ft.dropdown.Option(c) for c in self.COMARCAS]
        self.localidad_dropdown.options = [ft.dropdown.Option("TOTES LES LOCALITATS")] + [ft.dropdown.Option(l) for l in self.LOCALIDADES]
        self.cycle_dropdown.options = [ft.dropdown.Option("TOTS ELS CICLES/CURSOS")] + [ft.dropdown.Option(c) for c in self.CYCLES]
        
        self.cycle_dropdown.value = "TOTS ELS CICLES/CURSOS"
        
        self.update_results()
    
    def initialize_results(self):
        """Inicialitza els resultats sense disparar l'actualització de la pàgina."""
        self.update_results()


class ChatTab:
    """Pestanya de Chatbot connectada a AWS Bedrock amb el perfil projecte1."""
    def __init__(self, page: ft.Page):
        self.page = page
        # Configuració de la sessió segons el teu codi
        try:
            self.session = boto3.Session(profile_name="projecte1")
            self.agent_client = self.session.client("bedrock-agent-runtime", region_name="us-east-1")
        except Exception as e:
            print(f"Error de configuració AWS: {e}")
            
        self.agent_id = "BEBBVC6EFW"
        self.agent_alias_id = "TSTALIASID"
        self.session_id = "session_flet_001"

        # UI del Chat
        self.chat_history = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        self.user_input = ft.TextField(
            hint_text="Pregunta a l'agent d'IA sobre la FP...",
            expand=True, on_submit=self.send_message, height=45, text_size=14
        )

    def send_message(self, e):
        if not self.user_input.value: return
        
        user_text = self.user_input.value
        self.chat_history.controls.append(
            ft.Container(
                content=ft.Text(f"Tú: {user_text}", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.BLUE_900, padding=10, border_radius=10, alignment=ft.alignment.center_right
            )
        )
        self.user_input.value = ""
        self.page.update()

        try:
            response = self.agent_client.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=self.session_id,
                inputText=user_text
            )

            full_response = ""
            for event in response.get("completion", []):
                if "chunk" in event:
                    full_response += event["chunk"]["bytes"].decode("utf-8")

            self.chat_history.controls.append(
                ft.Container(
                    content=ft.Text(f"IA: {full_response}", color=ft.Colors.BLACK),
                    bgcolor=ft.Colors.GREY_200, padding=10, border_radius=10
                )
            )
        except Exception as ex:
            self.chat_history.controls.append(ft.Text(f"❌ Error: {ex}", color="red"))
        
        self.page.update()

    @property
    def content(self):
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Assistent Virtual FP", size=24, weight="bold"),
                ft.Container(content=self.chat_history, expand=True, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=10, padding=10),
                ft.Row([self.user_input, ft.IconButton(ft.Icons.SEND, on_click=self.send_message)])
            ])
        )
        
def main(page: ft.Page):
    """Funció principal de l'aplicació Flet amb pestanyes i mapa."""
    
    page.title = "Oferta de Formació Professional 25/26 - CV"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.window_width = 1400
    page.window_height = 900
    
    if fp_standard_df.empty and fp_esp_df.empty:
        page.add(
            ft.Text("❌ Error: No s'ha pogut carregar o processar l'oferta de FP.", 
                    size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
            ft.Text(f"Assegura't que els arxius '{FP_FILE}', '{ESP_FILE}' i el catàleg de coordenades '{CENTER_COORDS_FILE}' estiguin al directori correcte.", 
                    size=14, color=ft.Colors.GREY_700)
        )
        page.update()
        return
    
    map_container_ref = ft.Ref[ft.Container]()
    
    tab_standard = TabContent(page, fp_standard_df, "FP Estàndard (Bàsic, Medi, Superior)", map_container_ref)
    tab_especializacion = TabContent(page, fp_esp_df, "FP Cursos d'Especialització", map_container_ref)
    tab_chat = ChatTab(page)
    
    active_tab_content = ft.Ref[ft.Column]()

    def tabs_changed(e):
        # Amagar o mostrar el mapa segons la pestanya
        map_container.visible = (e.control.selected_index != 2)
        
        if e.control.selected_index == 0:
            active_tab_content.current.controls[0] = tab_standard.content
            tab_standard.show_all_centers()
        elif e.control.selected_index == 1:
            active_tab_content.current.controls[0] = tab_especializacion.content
            tab_especializacion.show_all_centers()
        elif e.control.selected_index == 2:
            active_tab_content.current.controls[0] = tab_chat.content
        
        page.update()

    initial_map_content = ft.Column([
        ft.Text(f"📍 Mapa de tots els centres ({len(fp_standard_df)} centres)", 
               size=18, weight="bold"),
        ft.Container(
            WebView(
                url=get_osm_url_all_centers(fp_standard_df),
                expand=True
            ),
            height=700,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
        ),
        ft.Text(f"Mostrant fins a 100 marcadors", size=12, color=ft.Colors.GREY_600)
    ], spacing=10)
    
    map_container = ft.Container(
        ref=map_container_ref,
        content=initial_map_content,
        expand=2,
        padding=ft.padding.all(10)
    )

    header = ft.Row([
        ft.Icon(ft.Icons.AUTO_STORIES, size=30, color=ft.Colors.BLUE_900),
        ft.Text("Visor d'Oferta de Formació Professional - Generalitat Valenciana", 
                size=28, weight=ft.FontWeight.W_900, color=ft.Colors.BLUE_900)
    ])
    
    tabs_control = ft.Tabs(
        selected_index=0,
        on_change=tabs_changed,
        tabs=[
            ft.Tab(text="FP Estàndard", icon=ft.Icons.CLASS_OUTLINED),
            ft.Tab(text="Especialització", icon=ft.Icons.STAR),
            ft.Tab(text="Agent IA", icon=ft.Icons.SMART_TOY), 
        ],
        expand=True
    )
    
    main_content_row = ft.Row(
        controls=[
            ft.Column(
                ref=active_tab_content,
                controls=[tab_standard.content],
                expand=3,
                scroll=ft.ScrollMode.AUTO
            ),
            ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
            map_container,
        ],
        expand=True,
        spacing=10
    )
    
    page.add(header, tabs_control, main_content_row)

    # Inicialitzar la primera pestanya (Això també crida a show_all_centers)
    tab_standard.initialize_results()

if __name__ == "__main__":
    # S'utilitza AppView.FLET_APP per assegurar la correcta visualització del WebView (mapa)
    ft.app(target=main, view=ft.WEB_BROWSER)