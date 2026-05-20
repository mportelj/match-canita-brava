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

# --- 3. INICIALIZACIÓN DE ESTADOS (ESTO EVITA EL ERROR DE LINEA 100) ---
if 'sh' not in st.session_state:
    st.session_state.sh = cargar_datos_golf()

if 'menu_seleccionado' not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

if 'game' not in st.session_state:
    st.session_state.game = {"h_sel": 1}

if 'nav_radio' not in st.session_state:
    st.session_state.nav_radio = "Inicio" # O el valor por defecto que tengas

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
# --- 4. SIDEBAR DEFINITIVO ---
with st.sidebar:
    st.markdown("# ⛳ Cañita Brava")
    st.write("---")
    
    opciones_menu = ["Inicio", "Nueva Partida", "Admin", "Estadísticas"]
    
    # Función para cambiar el estado cuando se toca el radio manualmente
    def cambiar_menu():
        st.session_state.menu_seleccionado = st.session_state.nav_radio

    # Un solo radio con índice dinámico
    st.radio(
        "Navegación",
        opciones_menu,
        index=opciones_menu.index(st.session_state.get('menu_seleccionado', 'Inicio')),
        key="nav_radio",
        on_change=cambiar_menu
    )
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
@st.cache_data(ttl=600)
def leer_datos():
    try:
        if 'sh' not in st.session_state:
            st.session_state.sh = cargar_datos_golf()
        
        hoja = st.session_state.sh
        datos = hoja.get_all_values()
        
        if len(datos) <= 1:
            return pd.DataFrame()
            
        df_raw = pd.DataFrame(datos[1:], columns=datos[0])
        
        if not df_raw.empty:
            # --- LIMPIEZA Y CONVERSIÓN DE TIPOS ESTRICTA ---
            
            # 1. Puntos MVP: Deben ser decimales (float)
            # Reemplazamos coma por punto, quitamos espacios y forzamos número
            cols_mvp = ['p1_pts', 'p2_pts', 'p3_pts', 'p4_pts']
            for col in cols_mvp:
                if col in df_raw.columns:
                    df_raw[col] = pd.to_numeric(
                        df_raw[col].astype(str).str.replace(',', '.').str.strip(), 
                        errors='coerce'
                    ).fillna(0.0)

            # 2. Resultados y Golpes: Deben ser enteros (int)
            cols_int = [
                'resultado_a', 'resultado_b', 
                's0', 's1', 's2', 's3', 
                'hoyo', 'temporada', 'partido_id'
            ]
            for col in cols_int:
                if col in df_raw.columns:
                    # Primero a numérico por si hay texto, luego a entero
                    df_raw[col] = pd.to_numeric(
                        df_raw[col].astype(str).str.replace(',', '.').str.strip(), 
                        errors='coerce'
                    ).fillna(0).astype(int)
            
            # 3. Fecha: Aseguramos que sea string limpio
            if 'fecha' in df_raw.columns:
                df_raw['fecha'] = df_raw['fecha'].astype(str).str.strip()

        return df_raw

    except Exception as e:
        st.error(f"Error al leer la base de datos: {e}")
        return pd.DataFrame()
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
    # Usamos .get() que es seguro: si no existe 'nav_radio', devuelve None
    seleccion = st.session_state.get("nav_radio")
    if seleccion:
        st.session_state.menu_seleccionado = seleccion
        
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
        
        hoyo_cronologico = int(hoyo_id)
        if g.get('modo_9_hoyos', False):
            vuelta_base = 1 if g.get('vuelta_repetida') == "1ª Vuelta (Hoyos 1-9)" else 10
            hoyo_real_campo = ((hoyo_cronologico - 1) % 9) + vuelta_base
        else:
            hoyo_real_campo = hoyo_cronologico

        par_hoyo = int(PAR_RIA_VIGO[hoyo_real_campo])
        golpes = [int(g0), int(g1), int(g2), int(g3)]
        
        # --- CÁLCULO MATCH PLAY ---
        mejor_a = min(golpes[0], golpes[1]) # Manu, Jose
        mejor_b = min(golpes[2], golpes[3]) # Roge, Lalo
        peor_a = max(golpes[0], golpes[1])
        peor_b = max(golpes[2], golpes[3])
        
        res_a, res_b = 0, 0
        
        # 1 Punto por Mejor Bola
        if mejor_a < mejor_b:   res_a += 1
        elif mejor_b < mejor_a: res_b += 1
        
        # 1 Punto por Peor Bola
        if peor_a < peor_b:     res_a += 1
        elif peor_b < peor_a:   res_b += 1
        
        # 🔥 BONUS: +1 punto por cada Birdie o mejor (menor o igual a Par - 1)
        if golpes[0] <= par_hoyo - 1: res_a += 1
        if golpes[1] <= par_hoyo - 1: res_a += 1
        if golpes[2] <= par_hoyo - 1: res_b += 1
        if golpes[3] <= par_hoyo - 1: res_b += 1

        # --- CÁLCULO PUNTOS MVP ---
        p_mvp = [0.0, 0.0, 0.0, 0.0]
        for i in range(4):
            puntos_victoria = sum(0.5 for j in range(4) if i != j and golpes[i] < golpes[j])
            puntos_par = 0.0
            dif = golpes[i] - par_hoyo
            if dif == 0:    puntos_par = 0.5
            elif dif == -1: puntos_par = 1.5
            elif dif == -2: puntos_par = 3.0
            elif dif <= -3: puntos_par = 4.0
            p_mvp[i] = float(puntos_victoria + puntos_par)

        id_p = str(g['id']).split('.')[0]
        fecha = pd.to_datetime(g['fecha'], dayfirst=True).strftime('%d/%m/%Y')
        
        nueva_fila = [
            f"{id_p}_H{hoyo_cronologico}", int(id_p), int(hoyo_cronologico), fecha, 
            int(g.get('temporada', 2026)), int(res_a), int(res_b), 
            p_mvp[0], p_mvp[1], p_mvp[2], p_mvp[3], 
            golpes[0], golpes[1], golpes[2], golpes[3],
            int(hoyo_real_campo)
        ]

        filas = hoja.get_all_values()
        header = filas[0]
        
        if 'hoyo_real' not in header:
            header.append('hoyo_real')

        datos = [f for f in filas[1:] if not (str(f[1]).split('.')[0] == id_p and str(f[2]) == str(hoyo_cronologico))]
        
        for f in datos:
            if len(f) < len(header):
                f.append(f[2])

        datos.append(nueva_fila)
        
        hoja.clear()
        hoja.update('A1', [header] + datos, value_input_option='USER_ENTERED')
        st.cache_data.clear()
        st.success(f"Guardado Hoyo {hoyo_cronologico} (Match: {res_a} vs {res_b})")
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        
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

# 2. Obtenemos las temporadas disponibles
    if not df.empty:
        temps = sorted(df['temporada'].unique().tolist(), reverse=True)
    else:
        temps = [str(anio_actual)]
    
    if str(anio_actual) not in [str(t) for t in temps]:
        temps.insert(0, str(anio_actual))
    
    # 3. Selector de temporada (el valor se guarda en st.session_state.sel_temp)
    st.selectbox("Temporada:", temps, key="sel_temp")
    
    # 4. Lógica de puntos acumulados
    pa_t, pb_t = (3.5, 3.5) if str(st.session_state.sel_temp) == "2026" else (0.0, 0.0)
        
    if not df.empty:
        df_t = df[df['temporada'].astype(str) == str(st.session_state.sel_temp)]
        
        if not df_t.empty:
            # Agrupamos por partido_id (que ya limpiamos en leer_datos)
            partidos = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
            
            for _, r in partidos.iterrows():
                if r['resultado_a'] > r['resultado_b']: 
                    pa_t += 1
                elif r['resultado_b'] > r['resultado_a']: 
                    pb_t += 1
                else:
                    # Empate en la jornada
                    pa_t += 0.5; pb_t += 0.5
            
    # 5. Diseño de la tarjeta (CORREGIDO con st.session_state)
    st.markdown(f"""
        <div style="border: 2px solid #ccc; border-radius: 15px; padding: 20px; text-align: center; background: #f9f9f9; margin-top: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
            <h3 style="margin: 0; color: #555; text-transform: uppercase; letter-spacing: 2px;">
                MATCH {st.session_state.sel_temp}
            </h3>
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
elif st.session_state.menu_seleccionado == "Nueva Partida":
        # --- BLOQUE 0: INICIALIZACIÓN DE ESTADO ---
        if 'refresco_id' not in st.session_state: 
            st.session_state.refresco_id = 0
        
        # Inicializamos DataFrames vacíos para evitar errores de referencia
        df_p = pd.DataFrame()
        df_partido_actual = pd.DataFrame()

        # --- BLOQUE A: CONFIGURACIÓN DE INICIO (PANTALLA DE BIENVENIDA) ---
        game_activo = st.session_state.get('game')
        if not game_activo or not isinstance(game_activo, dict) or 'id' not in game_activo:
            st.title("⛳ Nueva Partida")
            fecha_nueva = st.date_input("Fecha del partido", key="fecha_nueva_p")
            if st.button("🚀 INICIAR PARTIDO", type="primary", use_container_width=True):
                st.session_state.game = {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "fecha": fecha_nueva.strftime("%d/%m/%Y"),
                    "temporada": str(fecha_nueva.year),
                    "h_sel": 1
                }
                st.session_state.refresco_id += 1
                st.cache_data.clear()
                st.rerun()
        
        # --- BLOQUE B: INTERFAZ DE JUEGO (PARTIDO EN CURSO) ---
        else:
            g = st.session_state.game
            # Reducción de márgenes superiores para visualización móvil
            st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)
            st.title(f"⛳ {g.get('fecha', 'S/F')}")

            # 1. CARGA Y FILTRADO ULTRA-SEGURO DE DATOS
            try:
                df_p = leer_datos() 
                if df_p is not None and not df_p.empty:
                    # Normalizamos el ID de la sesión (quitando decimales si los hay)
                    id_sesion = str(int(float(g['id'])))
                    
                    # Normalizamos la columna de la base de datos para que coincida 100%
                    def normalizar_id(val):
                        try:
                            return str(int(float(val)))
                        except:
                            return ""
                    
                    df_p['partido_id_str'] = df_p['partido_id'].apply(normalizar_id)
                    
                    # Creamos el dataset exclusivo de la jornada de hoy
                    df_partido_actual = df_p[df_p['partido_id_str'] == id_sesion].copy()
            except Exception as e:
                st.error(f"Error al conectar con la base de datos: {e}")

            # 2. CÁLCULO DE MARCADOR GLOBAL (MATCH PLAY)
            # Sumamos los hoyos ganados por cada equipo en la jornada
            puntos_equipo_a = 0
            puntos_equipo_b = 0
            if not df_partido_actual.empty:
                puntos_equipo_a = df_partido_actual['resultado_a'].sum()
                puntos_equipo_b = df_partido_actual['resultado_b'].sum()
            
            diferencia_global = puntos_equipo_a - puntos_equipo_b
            marcador_a, marcador_b = (diferencia_global, 0) if diferencia_global > 0 else (0, abs(diferencia_global))

            # 3. ESTILOS CSS PARA BOTONES E INPUTS GIGANTES
            st.markdown("""
                <style>
                    div[data-testid="stNumberInput"] label { font-size: 1.3rem !important; font-weight: bold !important; color: #2e7d32; }
                    div[data-testid="stNumberInput"] input { font-size: 2.2rem !important; height: 75px !important; }
                    .stButton button { height: 70px !important; font-size: 1.4rem !important; font-weight: bold !important; }
                </style>
            """, unsafe_allow_html=True)

            # 4. RENDERIZADO DEL MARCADOR VISUAL (HTML)
            st.markdown(f"""
                <div style="border: 2px solid #2e7d32; border-radius: 15px; padding: 10px; background-color: #f0f4f0; margin-bottom: 15px; text-align: center;">
                    <div style="display: flex; justify-content: space-around; align-items: center;">
                        <div style="flex: 1;"><p style="margin:0; font-size:0.9em; font-weight:bold;">MANU & JOSE</p><h1 style="margin:0; font-size:4.5em; color:{COLOR_A if marcador_a > 0 else '#333'};">{marcador_a:g}</h1></div>
                        <div style="background:#ccc; border-radius:50%; width:35px; height:35px; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#666; font-size:0.8em;">VS</div>
                        <div style="flex: 1;"><p style="margin:0; font-size:0.9em; font-weight:bold;">ROGE & LALO</p><h1 style="margin:0; font-size:4.5em; color:{COLOR_B if marcador_b > 0 else '#333'};">{marcador_b:g}</h1></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # 5. SELECTOR DE HOYO Y NAVEGACIÓN
            h_actual = st.selectbox(
                "📍 HOYO SELECCIONADO", 
                options=list(range(1, 19)), 
                index=int(st.session_state.game['h_sel']) - 1,
                key=f"sb_hoyo_{st.session_state.refresco_id}"
            )
            st.session_state.game['h_sel'] = h_actual

            col_nav_1, col_nav_2 = st.columns(2)
            if col_nav_1.button("⬅️ ANTERIOR", use_container_width=True):
                st.session_state.game['h_sel'] = max(1, int(st.session_state.game['h_sel']) - 1)
                st.session_state.refresco_id += 1
                st.rerun()
            if col_nav_2.button("SIGUIENTE ➡️", use_container_width=True):
                st.session_state.game['h_sel'] = min(18, int(st.session_state.game['h_sel']) + 1)
                st.session_state.refresco_id += 1
                st.rerun()

            # 6. OBTENCIÓN DE DATOS DEL HOYO ESPECÍFICO (CORREGIDO)
           # --- OBTENER GOLPES (COLUMNAS s0, s1, s2, s3) ---
            # --- LÓGICA DE OBTENCIÓN DE DATOS DEL HOYO ---
            # --- OBTENER EL PAR DEL HOYO ACTUAL ---
            try:
                val_par_hoyo = int(PAR_RIA_VIGO[int(h_actual)])
            except:
                val_par_hoyo = 4 # Valor de seguridad

            # --- LÓGICA DE GOLPES POR DEFECTO ---
            # --- 1. DETERMINAR SI EL HOYO TIENE DATOS ---
            # --- 1. DATOS DEL HOYO Y VALORES POR DEFECTO ---
            df_hoyo_actual = df_partido_actual[df_partido_actual['hoyo'].astype(int) == h_actual]
            hay_datos_hoyo = not df_hoyo_actual.empty

            try:
                val_par_hoyo = int(PAR_RIA_VIGO[int(h_actual)])
            except:
                val_par_hoyo = 4

            # Inicializamos siempre con el Par
            golpes_anteriores = [val_par_hoyo] * 4

            # --- 2. CARGAR DATOS SI EXISTEN ---
            if hay_datos_hoyo:
                try:
                    golpes_anteriores = [
                        int(df_hoyo_actual['s0'].iloc[0]),
                        int(df_hoyo_actual['s1'].iloc[0]),
                        int(df_hoyo_actual['s2'].iloc[0]),
                        int(df_hoyo_actual['s3'].iloc[0])
                    ]
                except (KeyError, IndexError):
                    # Si las columnas no existen, mantenemos el Par definido arriba
                    pass

            # --- 3. INTERFAZ DE USUARIO (INPUTS) ---
            st.markdown(f"### ⛳ Hoyo {h_actual} (Par {val_par_hoyo})")
        cols_g = st.columns(4)

        # Mapeo limpio de los inputs
        s0 = cols_g[0].number_input("MANU", min_value=1, value=golpes_anteriores[0], key=f"s0_h{h_actual}")
        s1 = cols_g[1].number_input("JOSE", min_value=1, value=golpes_anteriores[1], key=f"s0_h{h_actual}")
        s2 = cols_g[2].number_input("ROGE", min_value=1, value=golpes_anteriores[2], key=f"s0_h{h_actual}")
        s3 = cols_g[3].number_input("LALO", min_value=1, value=golpes_anteriores[3], key=f"s0_h{h_actual}")
        
        # Comprobamos si los golpes actuales son idénticos a los guardados
        valores_actuales = [s0, s1, s2, s3]
        no_hay_cambios = (valores_actuales == golpes_anteriores)
    
        # El botón permanece deshabilitado hasta que cambie algún número
        if st.button(
            "💾 GUARDAR RESULTADO HOYO", 
            use_container_width=True, 
            key=f"btn_guardar_h{h_actual}", 
            disabled=no_hay_cambios
        ):
            ejecutar_guardado_automatico(h_actual, s0, s1, s2, s3)
            st.rerun()
            
        res_hoyo_a, res_hoyo_b = 0, 0
        if not df_partido_actual.empty:
            reg = df_partido_actual[df_partido_actual['hoyo'].astype(int) == h_actual]
            if not reg.empty:
                if reg.iloc[0][['s0', 's1', 's2', 's3']].sum() > 0:
                    hay_datos_hoyo = True
                    res_hoyo_a = int(reg.iloc[0]['resultado_a'])
                    res_hoyo_b = int(reg.iloc[0]['resultado_b'])
                                
        # Pintamos el resultado real leído del Excel
        if hay_datos_hoyo:
            if res_hoyo_a > res_hoyo_b:
                st.success(f"✅ Manu & Jose +{int(res_hoyo_a - res_hoyo_b)} en este Hoyo ({res_hoyo_a} - {res_hoyo_b})")
            elif res_hoyo_b > res_hoyo_a:
                st.error(f"✅ Roge & Lalo +{int(res_hoyo_b - res_hoyo_a)} en este Hoyo ({res_hoyo_b} - {res_hoyo_a})")
            else:
                st.warning(f"✅ Hoyo Empatado AS ({res_hoyo_a} - {res_hoyo_b})")
        else:
            st.info(f"⏳ Hoyo {h_actual} pendiente de juego")
                
          # 9. SECCIÓN MVP (CON BOTÓN Y CÁLCULO LIMPIO)
            st.write("---")
            
            # Usamos un checkbox con apariencia de botón o un expander
            if st.checkbox("📊 Ver Clasificación MVP"):
                if not df_partido_actual.empty:
                    # Limpiamos duplicados por si acaso
                    df_mvp = df_partido_actual.sort_values('hoyo').drop_duplicates('hoyo', keep='last')
                    
                    nombres = ["MANU", "JOSE", "ROGE", "LALO"]
                    
                    # Mostrar puntos del hoyo actual
                    st.write(f"**🌟 Puntos Hoyo {h_actual}**")
                    c1, c2, c3, c4 = st.columns(4)
                    for i, col_obj in enumerate([c1, c2, c3, c4]):
                        # Buscamos el valor real guardado
                        h_reg = df_mvp[df_mvp['hoyo'].astype(int) == h_actual]
                        val = float(h_reg[f'p{i+1}_pts'].iloc[0]) if not h_reg.empty else 0.0
                        col_obj.metric(nombres[i], f"{val:.1f}")

                    # Mostrar Acumulado
                    st.write("**🏆 Acumulado Jornada**")
                    totales = []
                    for i in range(1, 5):
                        totales.append(df_mvp[f'p{i}_pts'].sum())
                    
                    ranking = sorted(zip(nombres, totales), key=lambda x: x[1], reverse=True)
                    cols_r = st.columns(4)
                    for idx, (nom, pts) in enumerate(ranking):
                        cols_r[idx].write(f"**{nom}**")
                        cols_r[idx].write(f"{pts:.1f}")

            # 10. FINALIZAR PARTIDA
            st.write("---")
            with st.popover("🏁 FINALIZAR PARTIDA", use_container_width=True):
                st.warning("⚠️ Esta acción cerrará la sesión actual.")
                if st.button("Confirmar y Salir", type="primary", use_container_width=True):
                    st.session_state.game = None
                    st.cache_data.clear()
                    st.rerun()

#ESTADUSTICAS ==============

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas y Clasificación")
    
    df_raw = leer_datos()
    if df_raw.empty:
        st.warning("No hay datos para procesar.")
    else:
        # --- 1. LIMPIEZA Y PREPARACIÓN DE DATOS ---
        def limpiar_valor(v):
            return str(v).split('.')[0].strip()

        df_raw['t_limpia'] = df_raw['temporada'].apply(limpiar_valor)
        df_raw['res_a'] = pd.to_numeric(df_raw['resultado_a'], errors='coerce').fillna(0)
        df_raw['res_b'] = pd.to_numeric(df_raw['resultado_b'], errors='coerce').fillna(0)
        
        # Limpiar columnas MVP (p1_pts a p4_pts)
        for i in range(1, 5):
            c_pts = f'p{i}_pts'
            df_raw[c_pts] = pd.to_numeric(df_raw.get(c_pts, 0), errors='coerce').fillna(0)

        df_raw['fecha_dt'] = pd.to_datetime(df_raw['fecha'], errors='coerce')
        fechas_unicas = df_raw.sort_values('fecha_dt', ascending=False)['fecha'].unique().tolist()
        temporadas_unicas = sorted(df_raw['t_limpia'].unique().tolist(), reverse=True)

        opciones_fecha = {}
        for f in fechas_unicas:
            num_hoyos = len(df_raw[df_raw['fecha'] == f])
            fecha_fmt = pd.to_datetime(f).strftime('%d/%m/%Y')
            opciones_fecha[f] = f"{fecha_fmt} ({num_hoyos} hoyos)"

        col1, col2 = st.columns(2)
        with col2:
            ver_acumulado = st.toggle("📂 Ver Acumulado de la Temporada", value=False)
        with col1:
            if ver_acumulado:
                seleccion_filtro = st.selectbox("Seleccionar Temporada:", temporadas_unicas, key="st_v_final_t")
            else:
                seleccion_filtro = st.selectbox("Seleccionar Jornada:", fechas_unicas, format_func=lambda x: opciones_fecha[x], key="st_v_final_j")

        # --- 2. FILTRADO ---
        if ver_acumulado:
            temp_actual = str(seleccion_filtro)
            df_stats = df_raw[df_raw['t_limpia'] == temp_actual].copy()
        else:
            df_stats = df_raw[df_raw['fecha'] == seleccion_filtro].copy()
            temp_actual = df_stats['t_limpia'].iloc[0] if not df_stats.empty else "2026"

        if not df_stats.empty:
            # --- 3. MARCADOR DISCRETO ---
            h_a, h_b = df_stats['res_a'].sum(), df_stats['res_b'].sum()
            if ver_acumulado:
                titulo_marcador = f"Temporada {temp_actual}"
                sub_marcador = f"Acumulado: Manu&Jose {h_a:g} - Roge&Lalo {h_b:g}"
            else:
                dif_h = h_a - h_b
                res_p = f"Manu&Jose {dif_h:g} UP" if dif_h > 0 else (f"Roge&Lalo {abs(dif_h):g} UP" if dif_h < 0 else "AS")
                titulo_marcador = f"Resultado: {res_p}"
                sub_marcador = f"Marcador hoyos: {h_a:g} vs {h_b:g}"

            st.markdown(f"""
                <div style="padding:10px; border-bottom: 2px solid #f0f2f6; margin-bottom:20px;">
                    <h3 style="margin:0; color:#555;">{titulo_marcador}</h3>
                    <p style="margin:0; color:gray;">{sub_marcador}</p>
                </div>
            """, unsafe_allow_html=True)

            # --- 4. ESTADÍSTICAS JUGADORES ---
            lista_resultados = []
            for i, jug in enumerate(TODOS):
                col_s = f's{i}'
                col_mvp = f'p{i+1}_pts'
                
                df_stats[col_s] = pd.to_numeric(df_stats[col_s], errors='coerce').fillna(0)
                d_p = df_stats[df_stats[col_s] > 0].copy()
                
                if not d_p.empty:
                    d_p['par_h'] = d_p['hoyo'].map(PAR_RIA_VIGO)
                    d_p['dif'] = d_p[col_s] - d_p['par_h']
                    
                    def cs(d):
                        if d <= -2: return 4
                        if d == -1: return 3
                        if d == 0:  return 2
                        if d == 1:  return 1
                        return 0
                    
                    # 1. Suma total absoluta de puntos scratch obtenidos en la temporada/jornada
                    scr = int(d_p['dif'].apply(cs).sum())
                    pts_mvp_total = float(df_stats[col_mvp].sum())
                    
                    # 2. CÁLCULO DEL NÚMERO DE PARTIDOS JUGADOS REALES (Fechas únicas con golpes > 0)
                    partidos_jugados = int(d_p['fecha'].nunique()) if 'fecha' in d_p.columns else 1
                    if partidos_jugados == 0: 
                        partidos_jugados = 1

                    lista_resultados.append({
                        "Jugador": jug, 
                        "pm": (len(d_p)*2)-scr, 
                        "scr": scr, 
                        "pts_mvp": pts_mvp_total,
                        "e": int((d_p['dif'] <= -2).sum()), 
                        "b": int((d_p['dif'] == -1).sum()), 
                        "p": int((d_p['dif'] == 0).sum()), 
                        "bog": int((d_p['dif'] == 1).sum()), 
                        "db": int((d_p['dif'] == 2).sum()), 
                        "tb": int((d_p['dif'] >= 3).sum()), 
                        "hoyos": len(d_p),
                        "partidos": partidos_jugados  # Guardamos el número de partidos
                    })
            
            lista_resultados = sorted(lista_resultados, key=lambda x: x['scr'], reverse=True)

            if lista_resultados:
                # TABLA PRINCIPAL (PANTALLA)
                stats_rows = []
                for res in lista_resultados:
                    def f_pct(v, th):
                        p = (v/th*100) if th > 0 else 0
                        return f"<b>{v}</b><br><span style='color:gray; font-size:0.8em;'>{p:.0f}%</span>"
                    
                    h = res['hoyos']
                    partidos = res['partidos']
                    
                    # NUEVA LÓGICA DE CORRECCIÓN: Promedio directo por partido jugado
                    if ver_acumulado:
                        val_pm = res['pm'] / partidos
                        val_scr = res['scr'] / partidos
                        txt_pm = f"<span style='color:red;'>+{val_pm:.1f}</span>" if val_pm > 0 else (f"<span>{val_pm:.1f}</span>" if val_pm < 0 else "E")
                        txt_scr = f"<b>{val_scr:.1f}</b>"
                    else:
                        txt_pm = f"<span style='color:red;'>+{res['pm']}</span>" if res['pm'] > 0 else (f"<span>{res['pm']}</span>" if res['pm'] < 0 else "E")
                        txt_scr = f"<b>{res['scr']}</b>"
                    
                    stats_rows.append({
                        "Jugador": f"<b>{res['Jugador']}</b>",
                        "+/-": txt_pm,
                        "Scratch": txt_scr,
                        "Eagle": f_pct(res['e'], res['hoyos']), "Birdie": f_pct(res['b'], res['hoyos']), 
                        "Par": f_pct(res['p'], res['hoyos']), "Bogey": f_pct(res['bog'], res['hoyos']), 
                        "D.Bogey": f_pct(res['db'], res['hoyos']), "3+ Bogey": f_pct(res['tb'], res['hoyos'])
                    })
                
                df_html_data = pd.DataFrame(stats_rows)
                if ver_acumulado:
                    df_html_data = df_html_data.rename(columns={"+/-": "+/- Med (partido)", "Scratch": "Scratch Med (partido)"})

                df_html = df_html_data.to_html(escape=False, index=False)
                df_html = df_html.replace('<td>', '<td style="text-align: center; vertical-align: middle; padding: 10px;">')
                df_html = df_html.replace('<th>', '<th style="text-align: center; background-color: #f8f9fa;">')
                st.write(df_html, unsafe_allow_html=True)

                # --- 5. CLASIFICACIÓN MVP ---
                st.write("")
                st.subheader("🏆 Clasificación MVP")
                lista_mvp = sorted(lista_resultados, key=lambda x: float(x.get('pts_mvp', 0.0)), reverse=True)
                mvp_rows = []
                for i, res in enumerate(lista_mvp):
                    medalla = ["🥇 ", "🥈 ", "🥉 ", ""][i] if i < 4 else ""
                    mvp_rows.append({
                        "Pos": f"{medalla}{i+1}º",
                        "Jugador": res['Jugador'],
                        "Puntos MVP": f"<b>{res['pts_mvp']:.1f}</b>"
                    })
                
                df_mvp_html = pd.DataFrame(mvp_rows).to_html(escape=False, index=False)
                df_mvp_html = df_mvp_html.replace('<td>', '<td style="text-align: center; padding: 8px;">')
                df_mvp_html = df_mvp_html.replace('<th>', '<th style="text-align: center; background-color: #f8f9fa;">')
                st.write(df_mvp_html, unsafe_allow_html=True)

                # --- 6. WHATSAPP DETALLADO ---
                import urllib.parse
                
                w_icon = "📂" if ver_acumulado else "📅"
                tit_w = temp_actual if ver_acumulado else opciones_fecha[seleccion_filtro]
                
                if ver_acumulado:
                    df_origen = None
                    for var_name in ['df_tabla', 'df', 'df_raw', 'df_stats']:
                        if var_name in locals() or var_name in globals():
                            df_origen = locals().get(var_name, globals().get(var_name))
                            break
                            
                    if df_origen is not None and 'm_a' in df_origen.columns and 'm_b' in df_origen.columns:
                        total_a = float(df_origen['m_a'].sum())
                        total_b = float(df_origen['m_b'].sum())
                    else:
                        total_a = 4.5
                        total_b = 4.5
                    
                    titulo_final_marcador = f"Match: Manu & Jose {total_a:.1f} Roge & Lalo {total_b:.1f}"
                    
                    if total_a > total_b:
                        marcador_a_w = total_a - total_b
                        sub_final_marcador = f"MANU/JOSE GANAN {marcador_a_w:.1f} UP"
                    elif total_b > total_a:
                        marcador_b_w = total_b - total_a
                        sub_final_marcador = f"ROGE/LALO GANAN {marcador_b_w:.1f} UP"
                    else:
                        sub_final_marcador = "EMPATADOS (ALL SQUARE)"
                else:
                    titulo_final_marcador = titulo_marcador.upper()
                    sub_final_marcador = sub_marcador
                
                txt_wa = f"🍺 *CAÑITA BRAVA* 🍺\n{w_icon} *{tit_w}*\n"
                txt_wa += f"🏆 *{titulo_final_marcador}*\n"
                txt_wa += f"⛳ {sub_final_marcador}\n"
                txt_wa += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
                
                txt_wa += "⭐ *CLASIFICACIÓN MVP* ⭐\n"
                for i, res in enumerate(lista_mvp):
                    med = ["🥇", "🥈", "🥉", " "][i] if i < 4 else " "
                    puntos_v = float(res.get('pts_mvp', 0.0))
                    txt_wa += f"{med} {i+1}º {res['Jugador']}: *{puntos_v:.1f} pts*\n"
                txt_wa += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
                
                txt_wa += "📊 *ESTADÍSTICAS INDIVIDUALES*\n\n"
                for res in lista_mvp:
                    h = res['hoyos']
                    partidos = res['partidos']
                    
                    # NUEVA LÓGICA DE SINCRO PARA WHATSAPP: Basada en partidos reales
                    if ver_acumulado:
                        scr_promedio = res['scr'] / partidos
                        pm_promedio = res['pm'] / partidos
                        texto_scratch = f"{scr_promedio:.1f} med. scratch"
                        texto_pm = f"+{pm_promedio:.1f}" if pm_promedio > 0 else (f"{pm_promedio:.1f}" if pm_promedio < 0 else "E")
                    else:
                        texto_scratch = f"{res['scr']} pts scratch"
                        texto_pm = f"+{res['pm']}" if res['pm'] > 0 else (str(res['pm']) if res['pm'] < 0 else "E")
                    
                    def wf(v): 
                        return f"{v} ({v/h*100:.0f}%)"
                    
                    txt_wa += f"👤 *{res['Jugador'].upper()}*\n"
                    txt_wa += f"🏆 *{texto_pm}* ({texto_scratch})\n"
                    
                    s_l = ""
                    if not ver_acumulado:
                        birdie_o_mejor = int(res.get('e', 0)) + int(res.get('b', 0))
                        triple_o_peor = int(res.get('tb', 0))
                        
                        s_l += f"🐤 *Birdie o mejor:* {wf(birdie_o_mejor)}\n"
                        s_l += f"🅿️ *Par:* {wf(res['p'])}\n"
                        s_l += f"⚠️ *Bog:* {wf(res['bog'])}\n"
                        s_l += f"💀 *D.B:* {wf(res['db'])}\n"
                        s_l += f"💣 *💥 Triple o peor:* {wf(triple_o_peor)}\n"
                    else:
                        if res['e'] > 0:  s_l += f"🦅 Egl: {wf(res['e'])}\n"
                        if res['b'] > 0:  s_l += f"🐤 Bir: {wf(res['b'])}\n"
                        s_l += f"🅿️ *Par:* {wf(res['p'])}\n"
                        s_l += f"⚠️ *Bog:* {wf(res['bog'])}\n"
                        s_l += f"💀 *D.B:* {wf(res['db'])}\n"
                        if res['tb'] > 0: s_l += f"💣 +3B: {wf(res['tb'])}\n"
                        
                    txt_wa += s_l + "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                
                st.write("")
                st.link_button(
                    "📲 Enviar por WhatsApp", 
                    f"https://wa.me/?text={urllib.parse.quote(txt_wa)}", 
                    use_container_width=True
                )


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
                                    st.toast("Jornada eliminada")
                                    st.rerun()
                                else:
                                    st.error("No se pudo eliminar el partido.")
                                   
                                    


