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


# --- CONFIGURACIÓN DE NAVEGACIÓN ---

import streamlit as st
import pandas as pd
# ... otros imports ...


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
# --- CONFIGURACIÓN DEL MENÚ EN EL SIDEBAR ---
opciones_menu = ["Inicio", "Nueva Partida", "Estadísticas", "Admin"]

# Inicializamos la variable si no existe
if 'menu_seleccionado' not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

# Calculamos el índice basándonos en el texto guardado
try:
    idx_actual = opciones_menu.index(st.session_state.menu_seleccionado)
except ValueError:
    idx_actual = 0

with st.sidebar:
    st.title("⛳ Menú Principal")
    # USAMOS index=idx_actual y QUITAMOS el key del radio para evitar conflictos
    seleccion = st.radio(
        "Ir a:", 
        opciones_menu, 
        index=idx_actual
    )
    # Actualizamos la variable con la selección manual del usuario
    st.session_state.menu_seleccionado = seleccion


# --- LÓGICA DE DATOS ---
@st.cache_data(ttl=60)
def leer_datos():
    try:
        sh = st.session_state.sh
        data = sh.get_all_records()
        df = pd.DataFrame(data)
        if df.empty: return pd.DataFrame()
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

df_raw = leer_datos()


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
@st.cache_data(ttl=0)  # ttl=0 asegura que si hay cambios, los intente leer frescos

@st.cache_data(ttl=60) # Mantiene los datos en memoria 1 minuto
def leer_datos():
    """
    Lee la base de datos completa desde Google Sheets.
    Mapea todas las columnas: id, partido_id, hoyo, fecha, temporada, etc.
    """
    try:
        # 1. Configuración de conexión (usando lo que ya funciona)
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
        
        # 2. Abrir la hoja y leer
        sh = client.open_by_url(s["url"])
        worksheet = sh.worksheet("historial")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty:
            return pd.DataFrame(columns=['id', 'partido_id', 'hoyo', 'fecha', 'temporada', 's0', 's1', 's2', 's3'])

        # 3. Limpieza de nombres de columnas (quitar espacios y minúsculas)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # 4. MAPEO COMPLETO SEGÚN TU LISTA
        # Esto asegura que aunque el Excel tenga nombres algo distintos, Python use estos:
        columnas_ordenadas = [
            'id', 'partido_id', 'hoyo', 'fecha', 'temporada', 
            'resultado_a', 'resultado_b', 'p1_pts', 'p2_pts', 
            'p3_pts', 'p4_pts', 's0', 's1', 's2', 's3'
        ]
        
        # Mapeamos dinámicamente por posición para evitar errores si cambias un nombre en el Excel
        mapeo = {df.columns[i]: columnas_ordenadas[i] for i in range(len(columnas_ordenadas)) if i < len(df.columns)}
        df = df.rename(columns=mapeo)

        # 5. Conversiones de tipo necesarias
        df['hoyo'] = pd.to_numeric(df['hoyo'], errors='coerce')
        df['temporada'] = df['temporada'].astype(str) # Para que el filtro de temporada no falle
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        
        return df

    except Exception as e:
        st.error(f"Error al leer la base de datos: {e}")
        # Devolvemos estructura mínima en caso de error para que no rompa la línea 239
        return pd.DataFrame(columns=['fecha', 'hoyo', 'temporada', 's0', 's1', 's2', 's3'])


def ejecutar_guardado_automatico(hoyo_id, g0, g1, g2, g3):
    try:
        hoja = st.session_state.sh
        g = st.session_state.game
        par_hoyo = PAR_RIA_VIGO[int(hoyo_id)]
        
        # 1. LÓGICA DE PUNTOS INDIVIDUALES (MVP)
        golpes = [int(g0), int(g1), int(g2), int(g3)] # Manu, Jose, Roge, Lalo
        mejor_resultado = min(golpes)
        
        # ¿Quiénes hicieron la mejor bola?
        ganadores_hoyo = [i for i, score in enumerate(golpes) if score == mejor_resultado]
        num_ganadores = len(ganadores_hoyo)
        
        # Inicializamos puntos MVP en 0
        p_mvp = [0.0, 0.0, 0.0, 0.0]
        
        # Reparto del punto de "Mejor Bola" (1 pto a repartir)
        # Si uno gana solo -> 1 pto. Si empatan dos -> 0.5 cada uno. Si empatan tres -> 0.33...
        valor_punto = 1.0 / num_ganadores
        for i in ganadores_hoyo:
            p_mvp[i] = valor_punto

        # 2. BONUS DE CALIDAD PERSONAL (Independiente del resultado del hoyo)
        def calc_bonus(score, p):
            dif = score - p
            if dif <= -3: return 3.0 # Albatros
            if dif == -2: return 2.0 # Eagle
            if dif == -1: return 1.0 # Birdie
            return 0.0

        # Sumamos el bonus individual a cada jugador
        for i in range(4):
            p_mvp[i] += calc_bonus(golpes[i], par_hoyo)

        # 3. MARCADOR DEL MATCH (Parejas - Columnas F y G)
        # Esto sigue funcionando por equipo: mejor de (Manu/Jose) vs mejor de (Roge/Lalo)
        res_equipo_a = min(golpes[0], golpes[1])
        res_equipo_b = min(golpes[2], golpes[3])
        
        match_a = 1.0 if res_equipo_a < res_equipo_b else (0.5 if res_equipo_a == res_equipo_b else 0.0)
        match_b = 1.0 if res_equipo_b < res_equipo_a else (0.5 if res_equipo_a == res_equipo_b else 0.0)

        # 4. NORMALIZAR ID Y CONSTRUIR FILA
        id_partido_busqueda = f"{float(g['id']):.1f}"
        nueva_fila = [
            f"{id_partido_busqueda}_H{hoyo_id}", 
            id_partido_busqueda,                 
            int(hoyo_id),                        
            str(g['fecha']),                     
            str(g['temporada']),                 
            float(match_a), float(match_b),      # F, G (Match Parejas)
            p_mvp[0], p_mvp[1],                  # H, I (Manu, Jose)
            p_mvp[2], p_mvp[3],                  # J, K (Roge, Lalo)
            int(g0), int(g1),                    
            int(g2), int(g3)                     
        ]

        # 5. GUARDADO EN GOOGLE SHEETS (Sin errores de indentación)
        filas = hoja.get_all_values()
        header = filas[0]
        datos_restantes = [f for f in filas[1:] if not (f[1] == id_partido_busqueda and int(f[2]) == int(hoyo_id))]
        
        datos_restantes.append(nueva_fila)
        datos_restantes.sort(key=lambda x: (str(x[1]), int(x[2])))

        hoja.clear()
        hoja.update('A1', [header] + datos_restantes)
        
        st.toast(f"✅ Hoyo {hoyo_id} guardado correctamente")
        st.cache_data.clear()

    except Exception as e:
        st.error(f"Error al guardar: {e}")
# --- 4. PANTALLAS ---
# ==========================================
# SECCIÓN: INICIO (Marcador de Temporada)
# ==========================================
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()

    
    # Definimos la temporada actual
    anio_actual = 2026
    temps = sorted(df['temporada'].unique().tolist(), reverse=True) if not df.empty else [anio_actual]
    if anio_actual not in temps: temps.insert(0, anio_actual)
    
    sel_temp = st.selectbox("Temporada:", temps)
    
    # Lógica de puntos acumulados de la temporada
    pa_t, pb_t = 3.5, 3.5  # Ventaja histórica inicial
    # CAMBIO AQUÍ: Convertimos sel_temp a string para que coincida con el DF
    if not df.empty:
        df_t = df[df['temporada'].astype(str) == str(sel_temp)] # Forzamos string en ambos lados
        partidos = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
       
        for _, r in partidos.iterrows():
            if r['resultado_a'] > r['resultado_b']: pa_t += 1
            elif r['resultado_b'] > r['resultado_a']: pb_t += 1
            else: pa_t += 0.5; pb_t += 0.5
            
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
        # --- BLOQUE B: LECTURA ÚNICA (CORREGIDO) ---
        g = st.session_state.game
        
        try:
            df_p = leer_datos() 
            if df_p is not None and not df_p.empty:
                # AJUSTE 1: Limpieza profunda de nombres de columnas
                df_p.columns = [str(c).strip().lower() for c in df_p.columns]
                
                # AJUSTE 2: Normalización robusta del ID
                # Convertimos ambos a string puro para evitar problemas de .0
                id_target = str(g['id']).split('.')[0] # Quita el .0 si existe
                df_p['partido_id'] = df_p['partido_id'].astype(str).str.split('.').str[0]
                
                df_partido_actual = df_p[df_p['partido_id'] == id_target]
        except Exception as e:
            st.error(f"Error al leer datos: {e}")

        # --- BLOQUE C: MARCADOR MATCH PLAY ---
        # (Tu código de CSS y HTML está perfecto, se mantiene igual)
        pts_a_total = df_partido_actual['resultado_a'].sum() if not df_partido_actual.empty else 0
        pts_b_total = df_partido_actual['resultado_b'].sum() if not df_partido_actual.empty else 0
        
        dif = pts_a_total - pts_b_total
        m_a, m_b = (dif, 0) if dif > 0 else (0, abs(dif))

        # AJUSTE 3: Mostrar título de edición ARRIBA para confirmar que estamos dentro
        st.subheader(f"📍 Editando: Partido {g['fecha']}")

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

        # --- RESTO DE TU CÓDIGO (Navegación, Golpes, Guardado) ---
        # Asegúrate de que los inputs usen v_ref para mostrar los golpes ya guardados

        
        # --- BLOQUE D: NAVEGACIÓN ---
        c_nav1, c_nav2 = st.columns(2)
        if c_nav1.button("← Anterior", use_container_width=True):
            g['h_sel'] = max(1, g['h_sel'] - 1)
            st.session_state.refresco_id += 1
            st.rerun()
        if c_nav2.button("Siguiente →", use_container_width=True):
            g['h_sel'] = min(18, g['h_sel'] + 1)
            st.session_state.refresco_id += 1
            st.rerun()

        # --- BLOQUE E: SELECTOR DE HOYO ---
        lista_hoyos = [f"Hoyo {i} (Par {PAR_RIA_VIGO[i]})" for i in range(1, 19)]
        seleccion = st.selectbox("h_sel", lista_hoyos, index=g['h_sel']-1, label_visibility="collapsed", key=f"h_selector_{st.session_state.refresco_id}")
        
        nuevo_h_id = int(seleccion.split(" ")[1])
        if nuevo_h_id != g['h_sel']:
            g['h_sel'] = nuevo_h_id
            st.session_state.refresco_id += 1
            st.rerun()

        # --- BLOQUE F: GOLPES (Carga s0 a s3) ---
        h = g['h_sel']
        
        if not df_partido_actual.empty:
            fila_hoyo = df_partido_actual[df_partido_actual['hoyo'].astype(int) == int(h)]
        else:
            fila_hoyo = pd.DataFrame()

        ya_existe = not fila_hoyo.empty
        v_ref = []
        
        if ya_existe:
            v_ref = [
                int(fila_hoyo.iloc[0]['s0']),
                int(fila_hoyo.iloc[0]['s1']),
                int(fila_hoyo.iloc[0]['s2']),
                int(fila_hoyo.iloc[0]['s3'])
            ]
        else:
            v_ref = [PAR_RIA_VIGO[h]] * 4

        col_j1, col_j2 = st.columns(2)
        s0_val = col_j1.number_input(TODOS[0], 1, 15, v_ref[0], key=f"in_s0_{h}_{st.session_state.refresco_id}")
        s1_val = col_j1.number_input(TODOS[1], 1, 15, v_ref[1], key=f"in_s1_{h}_{st.session_state.refresco_id}")
        s2_val = col_j2.number_input(TODOS[2], 1, 15, v_ref[2], key=f"in_s2_{h}_{st.session_state.refresco_id}")
        s3_val = col_j2.number_input(TODOS[3], 1, 15, v_ref[3], key=f"in_s3_{h}_{st.session_state.refresco_id}")

        # --- BLOQUE G: ACCIÓN DE GUARDADO ---
        if st.button("💾 Guardar Hoyo", type="primary", use_container_width=True):
            st.toast("⏳ Iniciando guardado...", icon="⏳")
            ejecutar_guardado_automatico(h, s0_val, s1_val, s2_val, s3_val)
            st.rerun()

        # --- BLOQUE H: FINALIZAR ---
        st.write("---") 
        
        with st.popover("🏁 Finalizar Partida", use_container_width=True):
            st.warning("¿Estás seguro de que quieres cerrar la partida actual?")
            if st.button("Confirmar Cierre y Borrar Sesión", type="primary", use_container_width=True):
                if 'game' in st.session_state:
                    del st.session_state.game
                st.cache_data.clear()
                st.rerun()
        st.subheader(f"📍 Editando: Partido {st.session_state.game['fecha']}")
# ==========================================
# SECCIÓN: ESTADISTICAS (Versión Restaurada)
# ==========================================
elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas y Clasificación")
    
    df_raw = leer_datos()
    
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
    
    # Aseguramos que los datos se lean siempre
    df = leer_datos()

    if df is None or df.empty:
        st.warning("No hay datos registrados en la base de datos.")
    else:
        # 1. LIMPIEZA DE DATOS
        columnas_numericas = ['resultado_a', 'resultado_b', 's0', 's1', 's2', 's3', 'hoyo']
        for col in columnas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        if 'partido_id' not in df.columns:
            df['partido_id'] = df['fecha'].astype(str)
        
        df['partido_id'] = df['partido_id'].astype(str)
        partidos = df.groupby('partido_id')
        ids_ordenados = sorted(partidos.groups.keys(), reverse=True)

        # 2. RENDERIZADO DE PARTIDOS
        for p_id in ids_ordenados:
            datos_jornada = partidos.get_group(p_id)
            f_disp = datos_jornada['fecha'].iloc[0]
            num_hoyos = len(datos_jornada['hoyo'].unique())
            
            suma_a = datos_jornada['resultado_a'].sum()
            suma_b = datos_jornada['resultado_b'].sum()
            diferencia = suma_a - suma_b
            
            if diferencia > 0:
                match_txt = f"MANU & JOSE: {int(diferencia)} Up"
            elif diferencia < 0:
                match_txt = f"ROGE & LALO: {int(abs(diferencia))} Up"
            else:
                match_txt = "All Square"

            with st.expander(f"📅 {f_disp} — {num_hoyos} Hoyos — [ {match_txt} ]"):
                tabla_vista = datos_jornada[['hoyo', 's0', 's1', 's2', 's3']].sort_values('hoyo')
                tabla_vista.columns = ['Hoyo', 'MANU', 'JOSE', 'ROGE', 'LALO']
                st.dataframe(tabla_vista, hide_index=True, use_container_width=True)

                c1, c2 = st.columns(2)
                
                with c1:
                    if st.button(f"✏️ Editar Partido", key=f"btn_ed_{p_id}", use_container_width=True):
                        # 1. Cargamos los datos del juego
                        st.session_state.game = {
                            "id": str(p_id),
                            "fecha": f_disp,
                            "temporada": str(datos_jornada['temporada'].iloc[0]) if 'temporada' in datos_jornada.columns else "2026",
                            "h_sel": 1
                        }
        
                        # 2. Cambiamos SOLO la variable de control
                        st.session_state.menu_seleccionado = "Nueva Partida"
        
                        # 3. Forzamos el reinicio. Al recargar, el sidebar leerá "Nueva Partida" 
                        # y el radio se moverá al índice 1 automáticamente.
                        st.rerun()
                
                
                with c2:
                    conf = st.checkbox("Borrar", key=f"ch_{p_id}")
                    if st.button(f"🗑️", key=f"del_{p_id}", disabled=not conf, type="primary", use_container_width=True):
                        st.error("No conectado")

    if st.button("🔄 Refrescar Panel"):
        st.cache_data.clear()
        st.rerun()
