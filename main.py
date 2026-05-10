import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# --- FUNCIONES DE CONEXIÓN ---
def cargar_datos_golf():
    s = st.secrets["gsheets"]
    credentials_dict = {
        "type": s["type"],
        "project_id": s["project_id"],
        "private_key_id": s["private_key_id"],
        "private_key": s["private_key"].replace("\\n", "\n"),
        "client_email": s["client_email"],
        "client_id": s["client_id"],
        "auth_uri": s["auth_uri"],
        "token_uri": s["token_uri"],
        "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
        "client_x509_cert_url": s["client_x509_cert_url"]
    }
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_url(s["url"]).sheet1

if 'sh' not in st.session_state:
    st.session_state.sh = cargar_datos_golf()

def borrar_partido_completo(id_partido_a_borrar):
    try:
        hoja = st.session_state.sh
        filas = hoja.get_all_values()
        header = filas[0]
        
        # Normalizamos el ID que queremos borrar para que sea string sin .0
        id_target = str(id_partido_a_borrar).split('.')[0]
        
        # Filtramos la lista: nos quedamos solo con lo que NO sea ese partido
        nuevas_filas = [header]
        conteo_borrados = 0
        
        for fila in filas[1:]:
            if len(fila) > 1:
                # Normalizamos el ID de la fila actual del Excel
                id_fila = str(fila[1]).split('.')[0]
                if id_fila == id_target:
                    conteo_borrados += 1
                    continue # No la incluimos (borrado)
            nuevas_filas.append(fila)
        
        if conteo_borrados > 0:
            hoja.clear()
            hoja.update('A1', nuevas_filas)
            st.success(f"🔥 Partido eliminado ({conteo_borrados} hoyos borrados).")
            st.cache_data.clear()
            return True
        else:
            st.error("No se encontró el partido para borrar.")
            return False
            
    except Exception as e:
        st.error(f"Error en el borrado: {e}")
        return False
# --- CONFIGURACIÓN DE NAVEGACIÓN ---

def cb_editar_partido(p_id, fecha, temporada):
    # Esto prepara los datos de la partida
    st.session_state.game = {
        "id": str(p_id),
        "fecha": fecha,
        "temporada": str(temporada),
        "h_sel": 1
    }
    # Esto cambia el menú lateral automáticamente
    st.session_state.nav_radio = "Nueva Partida"
    st.session_state.menu_seleccionado = "Nueva Partida"

# --- 2. EL SIDEBAR (MENÚ LATERAL) ---
# --- 4. SIDEBAR (MENÚ COMO LISTA DE BOTONES) ---
with st.sidebar:
    st.markdown("# ⛳ Cañita Brava")
    st.write("---")
    
    # Inicialización segura del menú
    opciones_menu = ["Inicio", "Nueva Partida", "Admin", "Estadísticas"]
    if 'menu_seleccionado' not in st.session_state:
        st.session_state.menu_seleccionado = "Inicio"

    # Renderizar lista de botones
    for opcion in opciones_menu:
        # Resaltar el botón de la pestaña activa
        estilo = "primary" if st.session_state.menu_seleccionado == opcion else "secondary"
        if st.button(opcion, use_container_width=True, type=estilo):
            st.session_state.menu_seleccionado = opcion
            st.rerun()
# Inicializamos la variable si no existe
if 'menu_seleccionado' not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

# Calculamos el índice basándonos en el texto guardado
try:
    idx_actual = opciones_menu.index(st.session_state.menu_seleccionado)
except ValueError:
    idx_actual = 0

# --- FUNCIÓN PARA CAMBIO DE PÁGINA ---
def cambiar_pagina():
    if "selector_menu" in st.session_state:
        st.session_state.menu_seleccionado = st.session_state.selector_menu



# --- LÓGICA DE DATOS ---
@st.cache_data(ttl=60)
def leer_datos():
    try:
        # 1. Verificamos que la conexión existe
        if 'sh' not in st.session_state:
            return pd.DataFrame()
            
        hoja = st.session_state.sh
        filas = hoja.get_all_values() # Aquí obtenemos los datos
        
        # 2. Verificamos que 'filas' tenga contenido antes de usar len()
        if filas and len(filas) > 1:
            df_raw = pd.DataFrame(filas[1:], columns=filas[0])
            
            # --- LIMPIEZA Y CONVERSIÓN A NÚMERO ---
            # Columnas que deben ser números sí o sí
            cols_numericas = ['resultado_a', 'resultado_b', 'hoyo', 's0', 's1', 's2', 's3']
            
            for col in cols_numericas:
                if col in df_raw.columns:
                    # Convertimos a string, quitamos comas por puntos y forzamos a número
                    df_raw[col] = df_raw[col].astype(str).str.replace(',', '.')
                    df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)
            
            # --- LIMPIEZA DE FECHAS (dd/mm/aaaa) ---
            df_raw['fecha'] = pd.to_datetime(df_raw['fecha'], errors='coerce', dayfirst=True)
            df_raw['fecha'] = df_raw['fecha'].dt.strftime('%d/%m/%Y')
            
            # --- LIMPIEZA DE ID (Quitar el .0) ---
            df_raw['partido_id'] = df_raw['partido_id'].astype(str).str.split('.').str[0]
            
            return df_raw
        
        return pd.DataFrame()
        
    except Exception as e:
        # Si algo falla, mostramos el error pero devolvemos un DF vacío para no romper la app
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()
        
#df_raw = leer_datos()


# --- 1. CONFIGURACIÓN CORREGIDA DEL CAMPO ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 4
}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
EQUIPO_A_NOMBRES = f"{TODOS[0]}/{TODOS[1]}"
EQUIPO_B_NOMBRES = f"{TODOS[2]}/{TODOS[3]}"
COLOR_A, COLOR_B = "#2e7d32", "#c62828"
COL_NECESARIAS = ['id', 'partido_id', 'hoyo', 'fecha', 'temporada', 'resultado_a', 'resultado_b', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts', 's0', 's1', 's2', 's3']

def calcular_puntos_hoyo(s0, s2, s1, s3, par):
    # s0/s2: Equipo A | s1/s3: Equipo B
    e1 = [s0, s2]
    e2 = [s1, s3]
    pts_e1, pts_e2 = 0, 0
    
    # --- A) PUNTOS POR HOYO (MATCH PLAY) ---
    if min(e1) < min(e2): pts_e1 += 1
    elif min(e2) < min(e1): pts_e2 += 1
    
    # Punto por Peor Bola (opcional, si vuestras reglas lo usan)
    if max(e1) < max(e2): pts_e1 += 1
    elif max(e2) < max(e1): pts_e2 += 1
    
    # --- B) BONUS DE CALIDAD (ALBATROS, EAGLE, BIRDIE) ---
    def get_bonus(golpes, p):
        dif = golpes - p
        if dif <= -3: return 3 # Albatros
        if dif == -2: return 2 # Eagle
        if dif == -1: return 1 # Birdie
        return 0

    pts_e1 += sum([get_bonus(g, par) for g in e1])
    pts_e2 += sum([get_bonus(g, par) for g in e2])
    
    return pts_e1, pts_e2

if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu():
    # Usamos .get() para que si no existe, devuelva "Inicio" en lugar de dar error
    nuevo_menu = st.session_state.get('radio_menu', 'Inicio')
    st.session_state.menu_seleccionado = nuevo_menu

def actualizar_o_insertar_hoyo(datos):
    """
    datos: [fecha, hoyo, s0, s1, s2, s3]
    """
    # 1. Leemos los datos actuales
    df = leer_datos()
    
    fecha_nueva = str(datos[0])
    hoyo_nuevo = int(datos[1])
    
    # Creamos un nuevo DataFrame con la fila que queremos guardar
    nueva_fila = pd.DataFrame([datos], columns=['fecha', 'hoyo', 's0', 's1', 's2', 's3'])

    if not df.empty:
        # 2. Buscamos si ya existe el hoyo para esa fecha
        # Aseguramos tipos para comparar bien
        df['hoyo'] = pd.to_numeric(df['hoyo'], errors='coerce')
        mask = (df['fecha'].astype(str) == fecha_nueva) & (df['hoyo'] == hoyo_nuevo)
        
        if mask.any():
            # EDITAR: Si existe, actualizamos esa fila
            df.loc[mask, ['s0', 's1', 's2', 's3']] = datos[2:]
        else:
            # AÑADIR: Si no existe, concatenamos la nueva fila
            df = pd.concat([df, nueva_fila], ignore_index=True)
    else:
        # Si el Excel está vacío, el nuevo DF es simplemente la nueva fila
        df = nueva_fila

    # 3. Subimos todo el DataFrame actualizado a Google Sheets
    # Usamos clear=True para que no duplique datos si el rango cambia
    conn.update(spreadsheet=st.secrets["gsheets"]["url"], data=df)
    
    # Limpiamos caché para que la app lea los datos nuevos inmediatamente
    st.cache_data.clear()

# --- 2. FUNCIONES DE DATOS ---



def ejecutar_guardado_automatico(hoyo_id, g0, g1, g2, g3):
    try:
        hoja = st.session_state.sh
        g = st.session_state.game
        par_hoyo = PAR_RIA_VIGO[int(hoyo_id)]
        
        # 1. CÁLCULO DE PUNTOS (Manteniendo tus fórmulas)
        golpes = [int(g0), int(g1), int(g2), int(g3)]
        
        def calc_bonus_mvp(score, p):
            dif = score - p
            if dif <= -3: return 4.0
            if dif == -2: return 3.0
            if dif == -1: return 1.5
            if dif == 0:  return 0.5
            return 0.0

        def calc_bonus_match(score, p):
            dif = score - p
            if dif <= -3: return 3.0
            if dif == -2: return 2.0
            if dif == -1: return 1.0
            return 0.0

        p_mvp = [0.0] * 4
        for i in range(4):
            pts_oponentes = sum(0.5 for j in range(4) if i != j and golpes[i] < golpes[j])
            p_mvp[i] = float(pts_oponentes + calc_bonus_mvp(golpes[i], par_hoyo))

        res_a, res_b = min(golpes[0], golpes[1]), min(golpes[2], golpes[3])
        peor_a, peor_b = max(golpes[0], golpes[1]), max(golpes[2], golpes[3])
        
        total_a = (1.0 if res_a < res_b else 0.0) + (1.0 if peor_a < peor_b else 0.0) + \
                  calc_bonus_match(golpes[0], par_hoyo) + calc_bonus_match(golpes[1], par_hoyo)
        total_b = (1.0 if res_b < res_a else 0.0) + (1.0 if peor_b < peor_a else 0.0) + \
                  calc_bonus_match(golpes[2], par_hoyo) + calc_bonus_match(golpes[3], par_hoyo)

        match_a = float(max(0.0, total_a - total_b)) if total_a != total_b else 0.0
        match_b = float(max(0.0, total_b - total_a)) if total_a != total_b else 0.0

        # 2. PROCESAMIENTO DE IDENTIFICADORES Y FECHA
        # ID limpio: Si es "20240510.0", lo dejamos como "20240510" (texto para el ID compuesto)
        id_partido_puro = str(g['id']).split('.')[0]
        
        # Fecha blindada a dd/mm/yyyy
        try:
            fecha_str = pd.to_datetime(g['fecha'], dayfirst=True).strftime('%d/%m/%Y')
        except:
            fecha_str = str(g['fecha'])

        # 3. CONSTRUCCIÓN DE FILA CON TIPOS NATIVOS (Sin f-strings para números)
        nueva_fila = [
            f"{id_partido_puro}_H{hoyo_id}", # Clave única (Texto)
            int(id_partido_puro),           # ID Partido (Número ENTERO)
            int(hoyo_id),                   # Hoyo (Número ENTERO)
            fecha_str,                      # Fecha (Texto dd/mm/aaaa)
            int(g.get('temporada', 2026)),  # Temporada (Número ENTERO)
            match_a, match_b,               # Match (Número con decimales)
            p_mvp[0], p_mvp[1],             # MVP (Número con decimales)
            p_mvp[2], p_mvp[3],             # MVP (Número con decimales)
            int(g0), int(g1),               # Golpes (Número ENTERO)
            int(g2), int(g3)                # Golpes (Número ENTERO)
        ]

        # 4. ACTUALIZACIÓN EN GOOGLE SHEETS
        filas = hoja.get_all_values()
        header = filas[0] if filas else []
        
        # Reemplazar si ya existe el hoyo
        datos_nuevos = []
        for f in filas[1:]:
            if len(f) > 2:
                # Comparamos como strings limpios para evitar fallos de .0
                f_id = str(f[1]).split('.')[0]
                f_hoyo = str(f[2])
                if f_id == id_partido_puro and f_hoyo == str(hoyo_id):
                    continue
            datos_nuevos.append(f)

        datos_nuevos.append(nueva_fila)
        # Ordenamos por ID y luego por Hoyo
        datos_nuevos.sort(key=lambda x: (str(x[1]), int(x[2])))

        # ESCRITURA FINAL
        hoja.clear()
        # IMPORTANTE: USER_ENTERED permite que Google Sheets interprete los tipos
        hoja.update('A1', [header] + datos_nuevos, value_input_option='USER_ENTERED')
        
        st.toast(f"✅ Hoyo {hoyo_id} guardado correctamente")
        st.cache_data.clear()

    except Exception as e:
        st.error(f"Error crítico: {str(e)}")
# --- CÁLCULO DEL MARCADOR ACUMULADO DE LA TEMPORADA ---

def calcular_marcador_acumulado(df):
    if df.empty:
        return 0.0, 0.0
    
    # 1. Sumamos los puntos ganados en el campo (de todos los partidos)
    # Aseguramos que sean numéricos por si hay textos en el Excel
    pts_a_campo = pd.to_numeric(df['resultado_a'], errors='coerce').sum()
    pts_b_campo = pd.to_numeric(df['resultado_b'], errors='coerce').sum()
    
    # 2. REGLA ESPECIAL TEMPORADA 2026
    # Verificamos si en los datos existe la temporada 2026
    # Si el DataFrame tiene registros de 2026, aplicamos el bono
    tiene_2026 = (df['temporada'].astype(str) == "2026").any()
    
    bono = 3.5 if tiene_2026 else 0.0
    
    total_a = pts_a_campo + bono
    total_b = pts_b_campo + bono
    
    return total_a, total_b




# --- 4. PANTALLAS ---
# ==========================================
# SECCIÓN: INICIO (Marcador de Temporada)
# ==========================================
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    if not df.empty:
        # Aquí también saldrá en formato dd/mm/aaaa
        st.write(f"Último partido registrado: {df['fecha'].iloc[-1]}")
    
    # Definimos la temporada actual
    # Obtenemos el año actual automáticamente
anio_actual = datetime.now().year

# Obtenemos las temporadas del DF o usamos el año actual si está vacío
temps = sorted(df['temporada'].unique().tolist(), reverse=True) if not df.empty else [anio_actual]

# Si el año actual no está en la lista de temporadas del Excel, lo añadimos al principio
if anio_actual not in [int(t) for t in temps]:
    temps.insert(0, anio_actual)

# Selector de temporada con llave para session_state
st.selectbox("Temporada:", temps, key="sel_temp")

# Recuperamos la selección (usamos el session_state para evitar NameError en Admin)
sel_temp_activa = st.session_state.sel_temp

# Lógica de puntos acumulados
if str(sel_temp_activa) == "2026":
    pa_t, pb_t = 3.5, 3.5  # Ventaja inicial solo para 2026
else:
    pa_t, pb_t = 0.0, 0.0  # Otras temporadas empiezan de 0

if not df.empty:
    df_t = df[df['temporada'].astype(str) == str(sel_temp)]
    # Agrupamos por partido para saber quién ganó cada jornada
    partidos = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
    
    for _, r in partidos.iterrows():
        # Si un equipo ganó más hoyos en la jornada, suma 1 punto al Match de la temporada
        if r['resultado_a'] > r['resultado_b']: 
            pa_t += 1
        elif r['resultado_b'] > r['resultado_a']: 
            pb_t += 1
        else: 
            # Si empataron la jornada, medio punto para cada uno
            pa_t += 0.5; pb_t += 0.5
            
    # Diseño de tarjeta de marcador de temporada
    st.markdown(f"""
        <div style="border: 2px solid #ccc; border-radius: 15px; padding: 20px; text-align: center; background: #f9f9f9; margin-top: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
            <h3 style="margin: 0; color: #555; text-transform: uppercase; letter-spacing: 2px;">MATCH {sel_temp}</h3>
            <div style="display: flex; justify-content: space-around; align-items: center; margin-top: 15px;">
                <div style="flex: 1;">
                    <h2 style="color: {COLOR_A}; margin: 0; font-size: 1.2em;">{EQUIPO_A_NOMBRES}</h2>
                    <h1 style="font-size: 4em; margin: 0; color: #333;">{pa_t:g}</h1>
                </div>
                <div style="font-size: 1.5em; font-weight: bold; color: #999;">VS</div>
                <div style="flex: 1;">
                    <h2 style="color: {COLOR_B}; margin: 0; font-size: 1.2em;">{EQUIPO_B_NOMBRES}</h2>
                    <h1 style="font-size: 4em; margin: 0; color: #333;">{pb_t:g}</h1>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
   
# ==========================================
# SECCIÓN: NUEVA PARTIDA 
# ==========================================
elif st.session_state.menu_seleccionado == "Nueva Partida":

    # --- BLOQUE 0: INICIALIZACIÓN ---
    if 'refresco_id' not in st.session_state: 
        st.session_state.refresco_id = 0
    
    df_p = pd.DataFrame()
    df_partido_actual = pd.DataFrame()

    # --- BLOQUE A: CONFIGURACIÓN DE INICIO ---
    if 'game' not in st.session_state:
        st.info("💡 Selecciona una fecha para empezar o ve a Admin para editar una partida existente.")
        st.markdown("### ⛳ Nueva Partida")
        fecha_seleccionada = st.date_input("Selecciona la fecha del partido")
        fecha_formateada = fecha_seleccionada.strftime("%d/%m/%Y")
        st.write("Fecha seleccionada:", fecha_formateada)

        
        if st.button("Iniciar Partido", type="primary", use_container_width=True):
            año_temporada = str(fecha_seleccionada.year)
            fecha_formateada = fecha_seleccionada.strftime("%d/%m/%Y")
        
            st.session_state.game = {
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "fecha": fecha_formateada,
                "temporada": año_temporada,
                "h_sel": 1
            }
            st.cache_data.clear()
            st.rerun()
            
    else:
        # --- BLOQUE B: LECTURA DE DATOS ---
        g = st.session_state.game
        try:
            df_p = leer_datos() 
            if df_p is not None and not df_p.empty:
                # Normalización de ID para búsqueda
                id_target = str(g['id']).split('.')[0]
                df_p['partido_id_str'] = df_p['partido_id'].astype(str).str.split('.').str[0]
                df_partido_actual = df_p[df_p['partido_id_str'] == id_target]
        except Exception as e:
            st.error(f"Error al leer datos: {e}")

        # --- BLOQUE C: MARCADOR MATCH PLAY ---
        pts_a_total = df_partido_actual['resultado_a'].sum() if not df_partido_actual.empty else 0
        pts_b_total = df_partido_actual['resultado_b'].sum() if not df_partido_actual.empty else 0
        dif = pts_a_total - pts_b_total
        m_a, m_b = (dif, 0) if dif > 0 else (0, abs(dif))

        st.subheader(f"📍 Editando: {g['fecha']}")

        st.markdown(f"""
            <div style="border: 2px solid #2e7d32; border-radius: 15px; padding: 15px; background-color: #f0f4f0; margin-bottom: 15px; text-align: center;">
                <div style="display: flex; justify-content: space-around; align-items: center;">
                    <div style="flex: 1;">
                        <p style="margin:0; font-size:0.8em; color:#2e7d32; font-weight:bold;">{EQUIPO_A_NOMBRES}</p>
                        <h1 style="margin:0; font-size:4.5em; color:{COLOR_A if m_a > 0 else '#333'};">{m_a:g}</h1>
                    </div>
                    <div style="background:#ccc; border-radius:50%; width:40px; height:40px; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#666;">VS</div>
                    <div style="flex: 1;">
                        <p style="margin:0; font-size:0.8em; color:#c62828; font-weight:bold;">{EQUIPO_B_NOMBRES}</p>
                        <h1 style="margin:0; font-size:4.5em; color:{COLOR_B if m_b > 0 else '#333'};">{m_b:g}</h1>
                    </div>
                </div>
                <p style="margin-top:5px; color:#666; font-size:0.9em;">{"All Square" if dif == 0 else f"{abs(dif)} Up"}</p>
            </div>
        """, unsafe_allow_html=True)

        # --- BLOQUE D/E: NAVEGACIÓN Y SELECTOR ---
        c_nav1, c_nav2 = st.columns([1,1])
        if c_nav1.button("← Anterior", use_container_width=True):
            g['h_sel'] = max(1, g['h_sel'] - 1)
            st.rerun()
        if c_nav2.button("Siguiente →", use_container_width=True):
            g['h_sel'] = min(18, g['h_sel'] + 1)
            st.rerun()

        lista_hoyos = [f"Hoyo {i} (Par {PAR_RIA_VIGO[i]})" for i in range(1, 19)]
        seleccion = st.selectbox("Hoyo", lista_hoyos, index=g['h_sel']-1, key=f"h_sel_input_{g['h_sel']}")
        
        nuevo_h_id = int(seleccion.split(" ")[1])
        if nuevo_h_id != g['h_sel']:
            g['h_sel'] = nuevo_h_id
            st.rerun()

        # --- BLOQUE F: IDENTIFICACIÓN DE GOLPES GUARDADOS ---
        h_actual = g['h_sel']
        # Buscamos el registro del hoyo en el dataframe filtrado del partido
        registro_hoyo = df_partido_actual[df_partido_actual['hoyo'].astype(int) == h_actual]
        
        ya_guardado = not registro_hoyo.empty
        
        if ya_guardado:
            g_prev = [
                int(registro_hoyo.iloc[0]['s0']),
                int(registro_hoyo.iloc[0]['s1']),
                int(registro_hoyo.iloc[0]['s2']),
                int(registro_hoyo.iloc[0]['s3'])
            ]
        else:
            g_prev = [PAR_RIA_VIGO[h_actual]] * 4 # Valor por defecto (Par del hoyo)

        # --- BLOQUE G: INPUTS Y DETECCIÓN DE CAMBIOS ---
        col1, col2, col3, col4 = st.columns(4)
        with col1: v0 = st.number_input("MANU", 1, 15, value=g_prev[0], key=f"n0_{h_actual}")
        with col2: v1 = st.number_input("JOSE", 1, 15, value=g_prev[1], key=f"n1_{h_actual}")
        with col3: v2 = st.number_input("ROGE", 1, 15, value=g_prev[2], key=f"n2_{h_actual}")
        with col4: v3 = st.number_input("LALO", 1, 15, value=g_prev[3], key=f"n3_{h_actual}")

        # Lógica de habilitación
        cambios_detectados = [v0, v1, v2, v3] != g_prev
        boton_disabled = ya_guardado and not cambios_detectados

        if st.button("💾 GUARDAR HOYO", use_container_width=True, type="primary", disabled=boton_disabled):
            ejecutar_guardado_automatico(h_actual, v0, v1, v2, v3)
            st.cache_data.clear() # Forzamos recarga para que el botón se deshabilite tras guardar
            st.rerun()

        if ya_guardado and not cambios_detectados:
            st.success(f"✅ Hoyo {h_actual} verificado. Sin cambios.")
        elif ya_guardado and cambios_detectados:
            st.warning("⚠️ Cambios sin guardar en este hoyo.")

        # --- BLOQUE H: FINALIZAR ---
        st.write("---") 
        with st.popover("🏁 Finalizar Partida", use_container_width=True):
            st.warning("¿Estás seguro de que quieres cerrar la sesión actual?")
            if st.button("Confirmar Cierre", type="primary", use_container_width=True):
                if 'game' in st.session_state:
                    del st.session_state.game
                st.cache_data.clear()
                st.rerun()
# ==========================================
# SECCIÓN: ESTADISTICAS (Versión Restaurada)
# ==========================================
elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas y Clasificación")
    
    df_raw = leer_datos()
    if df_raw.empty:
        st.warning("No hay datos para procesar.")
    else:
        # Evitamos NameError inicializando variables de marcador
        marcador_global_a = df_raw['resultado_a'].sum()
        marcador_global_b = df_raw['resultado_b'].sum()
        
        #st.metric("Total Equipo A", marcador_global_a)
        #st.metric("Total Equipo B", marcador_global_b)
    
    if df_raw is not None and not df_raw.empty:
        # --- PREPARACIÓN DE FECHAS ---
        df_raw['fecha_dt'] = pd.to_datetime(df_raw['fecha'], errors='coerce')
        fechas_unicas = df_raw.sort_values('fecha_dt', ascending=False)['fecha'].unique().tolist()
        opciones_combo = {f: pd.to_datetime(f).strftime('%d/%m/%Y') for f in fechas_unicas}

        col1, col2 = st.columns(2)
        with col1:
            jornada_sel_raw = st.selectbox("Seleccionar Jornada:", options=fechas_unicas, format_func=lambda x: opciones_combo[x])
        with col2:
            ver_acumulado = st.toggle("📂 Ver Acumulado de la Temporada", value=False)

        # --- LÓGICA DE MARCADORES (IGUAL A INICIO) ---
        # 1. Marcador Global (Suma total de victorias por hoyo)
        puntos_a_total = pd.to_numeric(df_raw['resultado_a'], errors='coerce').sum()
        puntos_b_total = pd.to_numeric(df_raw['resultado_b'], errors='coerce').sum()
        
        # Formato idéntico a pantalla inicio (ej: Marcador: 110.5 - 101.5)
        texto_marcador_global = f"Marcador: {puntos_a_total} - {puntos_b_total}"
        
        # Determinamos quién va ganando para el mensaje resaltado
        dif_total = puntos_a_total - puntos_b_total
        if dif_total > 0:
            status_global = f"MANU & JOSE {dif_total} UP"
        elif dif_total < 0:
            status_global = f"ROGE & LALO {abs(dif_total)} UP"
        else:
            status_global = "ALL SQUARE (AS)"

        # --- FILTRADO POR JORNADA ---
        if ver_acumulado:
            df_stats = df_raw.copy()
            f_formateada = "Temporada Completa"
            titulo_seccion = "Acumulado Temporada" # <-- Variable corregida
            res_match_dia = ""
        else:
            df_stats = df_raw[df_raw['fecha'] == jornada_sel_raw].copy()
            f_formateada = opciones_combo[jornada_sel_raw]
            titulo_seccion = f"Jornada: {f_formateada}"
            
            p_a_d = pd.to_numeric(df_stats['resultado_a'], errors='coerce').sum()
            p_b_d = pd.to_numeric(df_stats['resultado_b'], errors='coerce').sum()
            
            # --- NUEVO FORMATO DE MARCADOR DE JORNADA ---
            # res_match_dia = f"<b style='color=green';>+MANU & JOSE: {p_a_d}</b>  vs  <b style='color=red';>+ROGE & LALO: {p_b_d}</b>   - {status_global}"
            res_match_dia = (
                f"<b style='color: green;'>Marcador hoyos: MANU & JOSE: {p_a_d}</b>  vs  "
                f"<b style='color: red;'>ROGE & LALO: {p_b_d}</b>   - <p><b style>{status_global}</b></p>"
            )
            st.markdown(res_match_dia, unsafe_allow_html=True)

            puntos_a_dia = pd.to_numeric(df_stats['resultado_a'], errors='coerce').sum()
            puntos_b_dia = pd.to_numeric(df_stats['resultado_b'], errors='coerce').sum()
            dif_dia = puntos_a_dia - puntos_b_dia
            
            #if dif_dia > 0:
            #    res_match_dia = f"Manu & Jose +{dif_dia}"
            #elif dif_dia < 0:
            #    res_match_dia = f"Roge & Lalo +{abs(dif_dia)}"
            #else:
            #    res_match_dia = "Empate (AS)"
            n_hoyos_info = len(df_stats['hoyo'].unique())

        # --- CÁLCULOS DE JUGADORES ---
        lista_resultados = []
        for i, jug in enumerate(TODOS):
            col_s = f's{i}'
            if col_s not in df_stats.columns: continue
            df_stats[col_s] = pd.to_numeric(df_stats[col_s], errors='coerce').fillna(0)
            d_p = df_stats[df_stats[col_s] > 0][['hoyo', col_s]].copy()
            if d_p.empty: continue

            d_p['par_h'] = d_p['hoyo'].map(PAR_RIA_VIGO)
            d_p['dif'] = d_p[col_s] - d_p['par_h']
            
            def calc_scratch(d):
                if d <= -2: return 4
                if d == -1: return 3
                if d == 0:  return 2
                if d == 1:  return 1
                return 0
            
            scratch_total = int(d_p['dif'].apply(calc_scratch).sum())
            n_h = len(d_p)
            pm = (n_h * 2) - scratch_total
            
            lista_resultados.append({
                "Jugador": jug, "plus_minus": pm, "scratch": scratch_total,
                "e": int((d_p['dif'] <= -2).sum()), "b": int((d_p['dif'] == -1).sum()), 
                "p": int((d_p['dif'] == 0).sum()), "bog": int((d_p['dif'] == 1).sum()), 
                "db": int((d_p['dif'] == 2).sum()), "tb": int((d_p['dif'] >= 3).sum()), "hoyos": n_h
            })

        # ORDENAR POR SCRATCH
        lista_resultados = sorted(lista_resultados, key=lambda x: x['scratch'], reverse=True)

       # Recuperamos los valores de Inicio (o ponemos 0 si no existen)
        g_a = st.session_state.get('global_a', 0.0)
        g_b = st.session_state.get('global_b', 0.0)
    
        texto_temporada = f"{g_a} vs {g_b}"
    
        # Lógica de líder basada en las variables recuperadas
        if g_a > g_b:
            lider_txt = f"MANU & JOSE lideran ({texto_temporada})"
        elif g_b > g_a:
            lider_txt = f"ROGE & LALO lideran ({texto_temporada})"
        else:
            lider_txt = f"EMPATE TEMPORADA ({texto_temporada})"
        n_hoyos_info = len(df_stats['hoyo'].unique())

        # --- CONSTRUCCIÓN MENSAJE WHATSAPP ---
        whatsapp_text = f"🍺 *CAÑITA BRAVA* 🍺\n"
        whatsapp_text += f"📅 *Jornada: {f_formateada}* ({n_hoyos_info} hoyos)\n"
        
        if not ver_acumulado:
            whatsapp_text += f"⛳ Marcador hoy: *{res_match_dia}*\n"
        
            whatsapp_text += f"🏆 *TEMPORADA: {texto_marcador_global}*\n"
        
        if marcador_global_a > marcador_global_b:
            lider_info = f"MANU & JOSE lideran ({texto_marcador_global})"
        elif marcador_global_b > marcador_global_a:
            lider_info = f"ROGE & LALO lideran ({texto_marcador_global})"
        else:
            lider_info = f"EMPATE TEMPORADA ({texto_marcador_global})"

        whatsapp_text += f"✨ *{lider_info.upper()}* ✨\n"
        whatsapp_text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"

        # ESTE ES EL BLOQUE QUE DABA ERROR DE INDENTACIÓN
        for res in lista_resultados:
            pm_txt = f"+{res['plus_minus']}" if res['plus_minus'] > 0 else (str(res['plus_minus']) if res['plus_minus'] < 0 else "E")
            h = res['hoyos']
            def w_fmt(v):
                pct = (v / h * 100) if h > 0 else 0
                return f"{v} ({pct:.0f}%)"

            whatsapp_text += f"👤 *{res['Jugador'].upper()}*\n"
            whatsapp_text += f"🏆 Resultado: *{pm_txt}* ({res['scratch']} pts)\n"
            whatsapp_text += f"🦅 Egl: {w_fmt(res['e'])}\n🐤 Bir: {w_fmt(res['b'])}\n🅿️ Par: {w_fmt(res['p'])}\n"
            whatsapp_text += f"⚠️ Bog: {w_fmt(res['bog'])}\n💀 D.Bog: {w_fmt(res['db'])}\n💣 +T.Bog: {w_fmt(res['tb'])}\n"
            whatsapp_text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"

        # --- RENDERIZADO APP ---
        st.subheader(f"📈 {titulo_seccion} ({n_hoyos_info} hoyos)")
        if not ver_acumulado and res_match_dia:
            st.markdown(f"**{res_match_dia}**")
            st.info(f"**{lider_info}**")
        #st.info(f"Temporada: {texto_marcador_global}")

        if lista_resultados:
            # (Aquí va tu código de la tabla stats_rows que ya tenías)
            stats_rows = []
            for res in lista_resultados:
                def fmt(v, total_h):
                    pct = (v / total_h * 100) if total_h > 0 else 0
                    return f"<b>{v}</b><br><span style='color:gray; font-size:0.8em;'>{pct:.1f}%</span>"
                stats_rows.append({
                    "Jugador": res['Jugador'],
                    "+/-": f"<b style='color:red;'>+{res['plus_minus']}</b>" if res['plus_minus'] > 0 else (f"<b>{res['plus_minus']}</b>" if res['plus_minus'] < 0 else "<b>E</b>"),
                    "Scratch": f"<b>{res['scratch']}</b>",
                    "Eagle": fmt(res['e'], res['hoyos']), "Birdie": fmt(res['b'], res['hoyos']), 
                    "Par": fmt(res['p'], res['hoyos']), "Bogey": fmt(res['bog'], res['hoyos']), 
                    "D.Bogey": fmt(res['db'], res['hoyos']), "3+ Bogey": fmt(res['tb'], res['hoyos'])
                })
            st.markdown("<style>table {width:100%; text-align:center;} th {background:#f8f9fa;} td {padding:8px; border-bottom:1px solid #eee;}</style>", unsafe_allow_html=True)
            st.write(pd.DataFrame(stats_rows).to_html(escape=False, index=False), unsafe_allow_html=True)

            import urllib.parse
            st.write("")
            st.link_button("📲 Enviar por WhatsApp", f"https://wa.me/?text={urllib.parse.quote(whatsapp_text)}", use_container_width=True)
    else:
        st.info("No hay datos cargados.")
        
# ==========================================
# SECCIÓN: ADMIN
# ==========================================

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Panel de Administración")
    
    # 1. Cargamos datos actualizados
    df_admin = leer_datos()
    
    if df_admin.empty:
        st.info("No hay partidos registrados en la base de datos.")
    else:
        # 2. Aseguramos la existencia de la columna id_clean para agrupar
        df_admin['id_clean'] = df_admin['partido_id'].astype(str).str.split('.').str[0]
        
        # Obtenemos las temporadas disponibles para filtrar en Admin también
        temps_admin = sorted(df_admin['temporada'].unique().tolist(), reverse=True)
        sel_temp_admin = st.selectbox("Filtrar por temporada:", temps_admin, key="sb_admin_temp")
        
        # Filtramos el DF por la temporada seleccionada en este menú
        df_filtrado = df_admin[df_admin['temporada'].astype(str) == str(sel_temp_admin)]

        # Ahora agrupamos usando el DF filtrado
        partidos = df_filtrado.groupby('id_clean').agg({
            'fecha': 'first',
            'temporada': 'first',
            'resultado_a': 'sum',
            'resultado_b': 'sum',
            'hoyo': 'count'
        }).sort_values(by='id_clean', ascending=False)
        st.subheader(f"Partidos Registrados ({len(partidos)})")

        for p_id, row in partidos.iterrows():
            # Cálculos de marcador
            pts_a = float(row['resultado_a'])
            pts_b = float(row['resultado_b'])
            num_hoyos = int(row['hoyo']) # Variable para el número de hoyos
            
            if pts_a > pts_b:
                marcador = f"🏆 MANU/JOSE +{int(pts_a - pts_b)}"
            elif pts_b > pts_a:
                marcador = f"🏆 ROGE/LALO +{int(pts_b - pts_a)}"
            else:
                marcador = "🤝 Empate (AS)"

            # 4. INTERFAZ: Título con Fecha, Resultado y Hoyos Jugados
            # Ejemplo: 📅 10/05/2026 | 🏆 MANU/JOSE +2 (18 hoyos)
            titulo_expander = f"📅 {row['fecha']}  |  {marcador}  |  ({num_hoyos} hoyos)"
            
            with st.expander(titulo_expander):
                
                # Datos específicos de este partido para la tabla
                df_partido = df_admin[df_admin['id_clean'] == p_id].sort_values('hoyo')
                
                # Fila de métricas resumen
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Hoyos", f"{num_hoyos}/18")
                m2.metric("MANU & JOSE", int(pts_a))
                m3.metric("ROGE & LALO", int(pts_b))
                m4.metric("Diferencia", int(abs(pts_a - pts_b)))

                # Tabla detallada con nombres de jugadores
                st.dataframe(
                    df_partido[['hoyo', 's0', 's1', 's2', 's3', 'resultado_a', 'resultado_b']],
                    column_config={
                        "hoyo": "H",
                        "s0": "Manu", "s1": "Jose", 
                        "s2": "Roge", "s3": "Lalo",
                        "resultado_a": "Match A", "resultado_b": "Match B"
                    },
                    hide_index=True,
                    use_container_width=True
                )

                # Botones de gestión
                col_ed, col_bor = st.columns(2)
                
                # BOTÓN EDITAR: Carga el partido y salta a Nueva Partida
                if col_ed.button("📝 Seguir/Editar Partido", key=f"ed_{p_id}", use_container_width=True):
                    st.session_state.game = {
                        "id": p_id,
                        "fecha": row['fecha'],
                        "temporada": row['temporada'],
                        "h_sel": int(df_partido['hoyo'].max()) # Te sitúa en el último hoyo jugado
                    }
                    st.session_state.menu_seleccionado = "Nueva Partida"
                    st.rerun()

                # BOTÓN BORRAR con popover de seguridad
                with col_bor:
                    with st.popover("🗑️ Borrar Jornada", use_container_width=True):
                        st.error("¿Seguro? Se eliminarán todos los registros de este día.")
                        if st.button("ELIMINAR DEFINITIVAMENTE", key=f"btn_del_{p_id}", type="primary"):
                            if borrar_partido_completo(p_id):
                                st.rerun()
