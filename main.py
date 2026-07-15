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

# --- 3. INICIALIZACIÓN DE ESTADOS ---

# 1. Variables base del sistema (que requieren lógica o carga previa)
if 'sh' not in st.session_state:
    st.session_state.sh = cargar_datos_golf()

# 2. Inicializamos todos los estados por defecto de una sola vez
default_states = {
    'refresco_id': 0,
    'hoyo_modificado': False,
    'menu_seleccionado': 'Inicio',
    'nav_radio': 'Inicio'
}

for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# 3. 🚀 MOTOR DE RESURRECCIÓN TRAS BLOQUEO
# Esta parte es correcta y necesaria, ya que sobrescribe los valores si venimos de una URL
if "partida_id" in st.query_params:
    st.session_state.menu_seleccionado = "Nueva Partida"
    st.session_state.nav_radio = "Nueva Partida"
    
    if 'game' not in st.session_state or st.session_state.game is None:
        st.session_state.game = {
            'id': st.query_params["partida_id"],
            'h_sel': int(st.query_params.get("hoyo", 1)),
            'fecha': datetime.now().strftime("%d/%m/%Y"), 
            'temporada': str(datetime.now().year)
        }
elif 'game' not in st.session_state:
    st.session_state.game = {"h_sel": 1}
    
def borrar_partido_completo(partido_id):
    try:
        hoja = st.session_state.sh
        id_p_buscar = str(partido_id).split('.')[0].strip()
        
        # 1. Leemos todas las filas actuales
        filas = hoja.get_all_values()
        if not filas:
            return False
            
        header = filas[0]
        datos_originales = filas[1:]
        
        # 2. Filtramos dejando fuera las filas del partido que queremos borrar
        nuevos_datos = []
        for fila in datos_originales:
            if len(fila) > 1:
                id_fila = str(fila[1]).split('.')[0].strip()
                if id_fila == id_p_buscar:
                    continue # Nos saltamos las filas de este partido (borrado)
            
            # --- 🔥 FORMATEO DE TIPOS ELEMENTO POR ELEMENTO ---
            # Para evitar que Google Sheets lo guarde todo como texto plano,
            # convertimos cada columna a su tipo correcto basándonos en tu estructura de la hoja:
            fila_tipada = []
            for idx, valor in enumerate(fila):
                val_str = str(valor).strip()
                if val_str == "" or val_str.lower() == "nan":
                    fila_tipada.append("")
                    continue
                
                try:
                    # Columnas de ID, hoyo, temporada, resultados, golpes (s0-s3) y hoyo_real deben ser enteros (INT)
                    # Índices: 1 (id_partido), 2 (hoyo), 4 (temporada), 5 (res_a), 6 (res_b), 11, 12, 13, 14 (golpes), 15 (hoyo_real)
                    if idx in [1, 2, 4, 5, 6, 11, 12, 13, 14, 15]:
                        fila_tipada.append(int(float(val_str))) # Pasamos por float primero por si viene con un .0
                    
                    # Columnas de puntos MVP (p1_pts a p4_pts) deben ser números decimales (FLOAT)
                    # Índices: 7, 8, 9, 10
                    elif idx in [7, 8, 9, 10]:
                        fila_tipada.append(float(val_str.replace(',', '.')))
                    
                    # El resto de columnas (0: ID_Hoyo compuesto, 3: Fecha texto) se quedan como texto plano
                    else:
                        fila_tipada.append(val_str)
                except ValueError:
                    # Si falla cualquier conversión por un caso extraño, dejamos el string original
                    fila_tipada.append(val_str)
                    
            nuevos_datos.append(fila_tipada)
            
        # 3. Limpiamos y reescribimos la hoja con la opción USER_ENTERED para que respete los tipos numéricos
        hoja.clear()
        hoja.update('A1', [header] + nuevos_datos, value_input_option='USER_ENTERED')
        
        # Limpiamos caché de Streamlit para que los cambios se vean en el acto
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error interno al borrar: {e}")
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

# 🎯 CORRECCIÓN 1: Inicializamos la variable principal ANTES de dibujar el menú
if 'menu_seleccionado' not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

# --- 2. EL SIDEBAR (MENÚ LATERAL) ---
# --- 4. SIDEBAR DEFINITIVO ---
# --- 2. EL SIDEBAR (MENÚ LATERAL) ---
with st.sidebar:
    st.markdown("# ⛳ Cañita Brava")
    st.write("---")
    
    opciones_menu = ["Inicio", "Nueva Partida", "Admin", "Estadísticas"]
    
    # 🎯 LA SOLUCIÓN SEGURO: Calculamos el índice real antes de dibujar el radio
    try:
        idx_actual = opciones_menu.index(st.session_state.menu_seleccionado)
    except ValueError:
        idx_actual = 0

    # Función limpia para actualizar el estado al hacer clic manual
    def cambiar_menu():
        st.session_state.menu_seleccionado = st.session_state.get('nav_radio', 'Inicio')

    # El radio utiliza su index dinámico y se sincroniza a la perfección
    st.radio(
        "Navegación",
        opciones_menu,
        index=idx_actual,
        key="nav_radio",
        on_change=cambiar_menu
    )
# Calculamos el índice basándonos en el texto guardado (mantenido por si lo usas en el resto del código)
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
                'p0', 'p1', 'p2', 'p3',
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

# 🔥 BONUS: +1 por Birdie, +2 por Eagle, +3 por Albatros
def calcular_bonus_hoyo(golpes_jugador, par):
    if golpes_jugador <= 0:  # Por si hay algún valor vacío o cero
        return 0
            
    diferencia = par - golpes_jugador
    if diferencia == 1:    # Birdie
        return 1
    elif diferencia == 2:  # Eagle
        return 2
    elif diferencia >= 3:  # Albatros o mejor
        return 3
    return 0

        

def ejecutar_guardado_automatico(hoyo_id, g0, g1, g2, g3, p0, p1, p2, p3):
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
        # Aplicamos el bonus acumulado a cada bando
        res_a += calcular_bonus_hoyo(golpes[0], par_hoyo)
        res_a += calcular_bonus_hoyo(golpes[1], par_hoyo)
        res_b += calcular_bonus_hoyo(golpes[2], par_hoyo)
        res_b += calcular_bonus_hoyo(golpes[3], par_hoyo)
        
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
            int(p0), int(p1), int(p2), int(p3),
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

def borrar_hoyo_especifico(partido_id, hoyo_id):
    try:
        hoja = st.session_state.sh
        filas = hoja.get_all_values()
        header = filas[0]
        datos = filas[1:]
        
        # Filtramos: guardamos todas las filas MENOS la del partido y hoyo específico
        nuevos_datos = []
        for f in datos:
            # Comparamos partido_id y hoyo (asegurando tipos)
            if str(f[1]).split('.')[0].strip() == str(partido_id).split('.')[0].strip() and str(f[2]).strip() == str(hoyo_id).strip():
                continue
            nuevos_datos.append(f)
            
        hoja.clear()
        hoja.update('A1', [header] + nuevos_datos, value_input_option='USER_ENTERED')
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al borrar hoyo: {e}")
        return False


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
   # Pon esto en tu pantalla de inicio justo donde se calculan los totales correctos:
    st.session_state['marcador_acumulado_a'] = pa_t  # O la variable que uses para Manu/Jose
    st.session_state['marcador_acumulado_b'] = pb_t  # O la variable que uses para Roge/Lalo
# ==========================================
elif st.session_state.menu_seleccionado == "Nueva Partida":
        # --- BLOQUE 0: INICIALIZACIÓN DE ESTADO ---
        if 'refresco_id' not in st.session_state: 
            st.session_state.refresco_id = 0
        
        # 🎯 NUEVA VARIABLE DE CONTROL PARA EL BOTÓN GUARDAR
        if 'hoyo_modificado' not in st.session_state:
            st.session_state.hoyo_modificado = False
        
        # Inicializamos DataFrames vacíos para evitar errores de referencia
        df_p = pd.DataFrame()
        df_partido_actual = pd.DataFrame()

        # --- BLOQUE A: CONFIGURACIÓN DE INICIO (PANTALLA DE BIENVENIDA) ---
        game_activo = st.session_state.get('game')
        if not game_activo or not isinstance(game_activo, dict) or 'id' not in game_activo:
            st.title("⛳ Nueva Partida")
            fecha_nueva = st.date_input("Fecha del partido", key="fecha_nueva_p")
            if st.button("🚀 INICIAR PARTIDO", type="primary", use_container_width=True):
                # 1. Generamos el ID único
                nuevo_id = datetime.now().strftime("%Y%m%d%H%M%S")
                
                # 2. Inicializamos el estado del juego solo con el nuevo ID
                st.session_state.game = {
                    "id": nuevo_id,
                    "fecha": fecha_nueva.strftime("%d/%m/%Y"),
                    "temporada": str(fecha_nueva.year),
                    "h_sel": 1
                }
                
                # 3. Preparamos el entorno para la nueva partida
                st.session_state.refresco_id += 1
                st.cache_data.clear()
                
                # 4. Actualizamos la URL para el "Motor de Resurrección"
                st.query_params["partida_id"] = nuevo_id
                st.query_params["hoyo"] = 1
                
                # 5. Recargamos la app
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

            
            # 5. SELECTOR DE HOYO Y NAVEGACIÓN
            h_actual = st.selectbox(
                "📍 HOYO SELECCIONADO", 
                options=list(range(1, 19)), 
                index=int(st.session_state.game['h_sel']) - 1,
                key=f"sb_hoyo_{st.session_state.refresco_id}"
            )
            st.session_state.game['h_sel'] = h_actual
            st.query_params["hoyo"] = h_actual
            
            
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
            # 🎯 INDICADOR VISUAL: Si existe en la base de datos está JUGADO, si no, PENDIENTE
            
            if hay_datos_hoyo:
                badge_estado = "<span style='font-size:13px; font-weight:bold; vertical-align:middle;'>🟢 JUGADO</span>"
            else:
                badge_estado = "<span style='font-size:13px; font-weight:bold; vertical-align:middle;'>🟡 PENDIENTE</span>"
            
           # --- TÍTULO ---
            st.markdown(
                f"### ⛳ Hoyo {h_actual} "
                f"<span style='font-size:20px; color:gray; font-weight:normal;'>*(Par {val_par_hoyo})*</span> "
                f"<span style='color:#ccc; font-size:14px;'>&nbsp;|&nbsp;</span> "
                f"{badge_estado}", 
                unsafe_allow_html=True
            )
            
            def activar_boton_guardar():
                st.session_state.hoyo_modificado = True

           # --- 1. CONFIGURACIÓN DE COLORES Y CSS ---
            config_jugadores = {
                "MANU": {"color": "#2E8B57", "clase": "borde-manu"},
                "JOSE": {"color": "#1E90FF", "clase": "borde-jose"},
                "ROGE": {"color": "#DC143C", "clase": "borde-roge"},
                "LALO": {"color": "#000000", "clase": "borde-lalo"}
            }
            
           # --- CSS AGRESIVO PARA COMPACTAR AL MÁXIMO ---
            st.markdown("""
                <style>
                    .nombre-jugador { font-size: 18px !important; font-weight: bold !important; margin: 0; }
                    .stNumberInput { margin-top: -10px !important; margin-bottom: 0px !important; }
                    /* Ajuste de columnas para que estén pegadas */
                    div[data-testid="column"] { padding: 0 2px !important; }
                </style>
            """, unsafe_allow_html=True)
                        
            # --- 2. INPUTS (MANTENIENDO TU LÓGICA DE VALORES) ---
            jugadores = ["MANU", "JOSE", "ROGE", "LALO"]
            inputs_s = []
            inputs_p = []
            
            # Si NO hay datos, usamos el PAR del hoyo. Si hay datos, usamos los de la BD.
            if hay_datos_hoyo:
                g_defaults = [int(df_hoyo_actual[f's{i}'].iloc[0]) for i in range(4)]
                p_defaults = [int(df_hoyo_actual[f'p{i}'].iloc[0]) for i in range(4)]
            else:
                # AQUÍ ESTÁ EL CAMBIO: Usamos val_par_hoyo como valor inicial
                g_defaults = [val_par_hoyo] * 4 
                p_defaults = [2] * 4 # O el valor por defecto que prefieras
            
           
            for i in range(4):
                nombre = jugadores[i]
                cfg = config_jugadores[nombre]
                
                # Columna 1: Nombre (más ancho), Columna 2: Golpes, Columna 3: Putts
                c1, c2, c3 = st.columns([0.6, 1, 1], vertical_alignment="center")
                
                with c1:
                    st.markdown(f"<p class='nombre-jugador' style='color:{cfg['color']};'>{nombre}</p>", unsafe_allow_html=True)
                
                with c2:
                    st.markdown(f'<div class="{cfg["clase"]}">', unsafe_allow_html=True)
                    val_s = st.number_input(f"G{i}", min_value=1, value=g_defaults[i], 
                                            on_change=activar_boton_guardar, key=f"s{i}_h{h_actual}", label_visibility="collapsed")
                    st.markdown('</div>', unsafe_allow_html=True)
                    inputs_s.append(val_s)
                    
                with c3:
                    st.markdown(f'<div class="{cfg["clase"]}">', unsafe_allow_html=True)
                    val_p = st.number_input(f"P{i}", min_value=0, value=p_defaults[i], 
                                            on_change=activar_boton_guardar, key=f"p{i}_h{h_actual}", label_visibility="collapsed")
                    st.markdown('</div>', unsafe_allow_html=True)
                    inputs_p.append(val_p)
                    
                               
            # Desempaquetado
            s0, s1, s2, s3 = inputs_s
            p0, p1, p2, p3 = inputs_p
            
            
                        
           # --- 3. BOTÓN DE GUARDADO ---
            no_hay_cambios = not st.session_state.hoyo_modificado
            if st.button("💾 GUARDAR RESULTADO HOYO", use_container_width=True, key=f"btn_guardar_h{h_actual}", disabled=no_hay_cambios):
                ejecutar_guardado_automatico(h_actual, s0, s1, s2, s3, p0, p1, p2, p3)
                st.session_state.hoyo_modificado = False
                if h_actual < 18:
                    st.session_state.game['h_sel'] = h_actual + 1
                    st.query_params["hoyo"] = st.session_state.game['h_sel']
                    st.session_state.refresco_id += 1
                st.rerun()
            st.write("---")
            col_nav_1, col_nav_2 = st.columns(2)
            if col_nav_1.button("⬅️ ANTERIOR", use_container_width=True):
                st.session_state.game['h_sel'] = max(1, int(st.session_state.game['h_sel']) - 1)
                st.query_params["hoyo"] = st.session_state.game['h_sel']
                st.session_state.refresco_id += 1
                st.rerun()
            if col_nav_2.button("SIGUIENTE ➡️", use_container_width=True):
                st.session_state.game['h_sel'] = min(18, int(st.session_state.game['h_sel']) + 1)
                st.query_params["hoyo"] = st.session_state.game['h_sel']
                st.session_state.refresco_id += 1
                st.rerun()      

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
                    st.query_params.clear()
                    st.cache_data.clear()
                    st.rerun()

#ESTADISTICAS ==============

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

        # 🔥 CORRECCIÓN CRÍTICA: Forzamos que lea primero el día (dayfirst=True)
        df_raw['fecha_dt'] = pd.to_datetime(df_raw['fecha'], dayfirst=True, errors='coerce')
        
        # Reescribimos la columna 'fecha' en un formato de texto estandarizado DD/MM/YYYY para que no haya duplicados raros
        df_raw['fecha'] = df_raw['fecha_dt'].dt.strftime('%d/%m/%Y')
        
        # Ahora extraemos las fechas únicas basándonos en el orden cronológico real de 'fecha_dt'
        df_raw_ordenado = df_raw.dropna(subset=['fecha_dt']).sort_values('fecha_dt', ascending=False)
        fechas_unicas = []
        for f in df_raw_ordenado['fecha']:
            if f not in fechas_unicas:
                fechas_unicas.append(f)
                
        temporadas_unicas = sorted(df_raw['t_limpia'].unique().tolist(), reverse=True)

        # Construimos el mapeo visual para el selectbox
        opciones_fecha = {}
        for f in fechas_unicas:
            num_hoyos = len(df_raw[df_raw['fecha'] == f])
            opciones_fecha[f] = f"{f} ({num_hoyos} hoyos)"

        col1, col2 = st.columns(2)
        with col2:
            ver_acumulado = st.toggle("📂 Ver Acumulado de la Temporada", value=False)
        with col1:
            if ver_acumulado:
                seleccion_filtro = st.selectbox("Seleccionar Temporada:", temporadas_unicas, key="st_v_final_t")
            else:
                # Al estar 'fechas_unicas' ya en formato 'dd/mm/aaaa', el combo saldrá perfecto y sin mezclas
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
            
            # Convertimos fecha una sola vez
            if 'fecha' in df_stats.columns:
                df_stats['fecha'] = pd.to_datetime(df_stats['fecha'], dayfirst=True, errors='coerce')

            for i, jug in enumerate(TODOS):
                col_s = f's{i}'
                col_p = f'p{i}'
                
                # --- LÓGICA DE FILTRADO CONDICIONAL ---
                if ver_acumulado:
                    # Filtro específico para Acumulado: Temporada (ya en df_stats) + Fecha desde 07/07/26
                    fecha_limite = pd.to_datetime('2026-07-07')
                    d_p = df_stats[
                        (df_stats[col_s] > 0) & 
                        (df_stats['fecha'].notna()) & 
                        (df_stats['fecha'] >= fecha_limite)
                    ].copy()
                else:
                    # En Jornada, ya tenemos el df_stats filtrado por la fecha exacta en el bloque anterior
                    d_p = df_stats[df_stats[col_s] > 0].copy()

                # --- CÁLCULO DE MEDIA ---
                avg_putts = 0
                if not d_p.empty:
                    # Convertimos a numérico y eliminamos nulos
                    putts_serie = pd.to_numeric(d_p[col_p], errors='coerce')
                    # Solo contamos hoyos donde hubo putts (evita ceros de "no registro")
                    # Si el dato es 0 y lo quieres contar como 0 putts, usa .dropna()
                    # Si los datos viejos son 0 y no quieres que cuenten, asegúrate de que sean NaT/NaN
                    putts_validos = putts_serie.dropna()
                    
                    total_putts = putts_validos.sum()
                    num_hoyos = len(putts_validos)
                    
                    if num_hoyos > 0:
                        avg_putts = total_putts / num_hoyos
                
                #########################################
               # 1. Primero calculamos el PAR y la DIFERENCIA (esto debe ir primero)
                d_p['par_h'] = d_p['hoyo'].map(PAR_RIA_VIGO)
                d_p['dif'] = d_p[col_s] - d_p['par_h'] 
                
                # 2. Ahora calculamos GIR
                d_p['shots_a_green'] = d_p[col_s] - d_p[f'p{i}']
                d_p['is_gir'] = d_p['shots_a_green'] <= (d_p['par_h'] - 2)
                
                # 3. Finalmente, calculamos U&D (ahora 'dif' ya existe y no dará error)
                d_p['is_updown'] = (~d_p['is_gir']) & (d_p[f'p{i}'] == 1) & (d_p['dif'] <= 0)
                
                # 4. Y luego puedes calcular tus métricas de GIR/UD para la lista_resultados
                gir_cnt = int(d_p['is_gir'].sum())
                ud_cnt = int(d_p['is_updown'].sum())
                
                # Calculamos porcentajes
                total_hoyos = len(d_p)
                gir_pct = (d_p['is_gir'].sum() / total_hoyos * 100) if total_hoyos > 0 else 0
                ud_pct = (d_p['is_updown'].sum() / total_hoyos * 100) if total_hoyos > 0 else 0
                # --- DENTRO DEL BUCLE DE JUGADORES ---
                df_jugados = d_p[d_p[col_s] > 0].copy()
                
                                
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
                    
                    # 2. CÁLCULO DEL NÚMERO DE PARTIDOS JUGADOS REALES
                    partidos_jugados = int(d_p['fecha'].nunique()) if 'fecha' in d_p.columns else 1
                    if partidos_jugados == 0: 
                        partidos_jugados = 1

                    lista_resultados.append({
                        "Jugador": jug, 
                        "pm": (len(d_p)*2)-scr, 
                        "scr": scr,
                        "avg_putts": avg_putts,
                        "pts_mvp": pts_mvp_total,
                        "e": int((d_p['dif'] <= -2).sum()), 
                        "b": int((d_p['dif'] == -1).sum()), 
                        "p": int((d_p['dif'] == 0).sum()), 
                        "bog": int((d_p['dif'] == 1).sum()), 
                        "db": int((d_p['dif'] == 2).sum()), 
                        "tb": int((d_p['dif'] >= 3).sum()), 
                        "hoyos": len(d_p),
                        "partidos": partidos_jugados,
                        "gir_cnt": int(d_p['is_gir'].sum()),      
                        "ud_cnt": int(d_p['is_updown'].sum())
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
                        "Media Putts": f"{res['avg_putts']:.1f}",
                        "GIR": f_pct(res['gir_cnt'], res['hoyos']),
                        "U&D": f_pct(res['ud_cnt'], res['hoyos']),
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
                tit_w = temp_actual if ver_acumulado else seleccion_filtro
                
                if ver_acumulado:
                    # 🔥 FILTRAMOS LA TEMPORADA ACTUAL
                    df_temp = df_raw[df_raw['t_limpia'] == temp_actual].copy()
                    total_a = st.session_state.get('marcador_acumulado_a', 3.5)
                    total_b = st.session_state.get('marcador_acumulado_b', 3.5)
                                        
                    año_txt = str(temp_actual).strip()
                    # Fallback de seguridad por si las moscas
                    if total_a == 0.0 and total_b == 0.0:
                        if año_txt=="2026":
                            total_a = 3.5
                            total_b = 3.5
                        else:
                            pass
                    
                    
                    titulo_final_marcador = f"Match: Manu & Jose {total_a:g} Roge & Lalo {total_b:g}"
                    
                    if total_a > total_b:
                        marcador_a_w = total_a - total_b
                        sub_final_marcador = f"MANU/JOSE GANAN {marcador_a_w:g} UP"
                    elif total_b > total_a:
                        marcador_b_w = total_b - total_a
                        sub_final_marcador = f"ROGE/LALO GANAN {marcador_b_w:g} UP"
                    else:
                        sub_final_marcador = "EMPATADOS (ALL SQUARE)"
                else:
                    titulo_final_marcador = titulo_marcador.upper()
                    sub_final_marcador = sub_marcador
                    año_txt = str(temp_actual).strip()
                
                # Construcción del texto para WhatsApp
                txt_wa = f"🍺 *CAÑITA BRAVA* 🍺\n"
                txt_wa += f"{w_icon} *{tit_w}*\n"
                txt_wa += f"🏆 *{titulo_final_marcador}*\n"
                txt_wa += f"⛳ {sub_final_marcador}\n"
                txt_wa += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
                
                txt_wa += "⭐ *CLASIFICACIÓN MVP* ⭐\n"
                for i, res in enumerate(lista_mvp):
                    med = ["🥇", "🥈", "🥉", " "][i] if i < 4 else " "
                    puntos_v = float(res.get('pts_mvp', 0.0))
                    txt_wa += f"{med} {i+1}º {res['Jugador']}: *{puntos_v:g} pts*\n"
                txt_wa += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
                
                txt_wa += "📊 *ESTADÍSTICAS INDIVIDUALES*\n\n"
                for res in lista_mvp:
                    h = res['hoyos']
                    partidos = res['partidos']
                    
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
                    txt_wa += f"🎯 *GIR:* {wf(res['gir_cnt'])}\n"
                    txt_wa += f"⬆️ *U&D:* {wf(res['ud_cnt'])}\n"
                    
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

                # --- 📊 NUEVA SECCIÓN DE GRÁFICOS ---
                import pandas as pd
                import plotly.express as px
                import plotly.graph_objects as go
                
                st.markdown("---")
                st.markdown("### 📈 Análisis Gráfico de Rendimiento")
                
                if lista_mvp:
                    # Convertimos tu lista de resultados a un DataFrame de Pandas para graficar fácilmente
                    df_graficos = pd.DataFrame(lista_mvp)
                    
                    col_graf_1, col_graf_2 = st.columns(2)
                    
                    with col_graf_1:
                        # 1. GRÁFICO DE BARRAS APILADAS: Distribución de Resultados
                        # Preparamos los datos aislando los golpes
                        df_dist = df_graficos[['Jugador', 'e', 'b', 'p', 'bog', 'db', 'tb']].copy()
                        df_dist.columns = ['Jugador', 'Eagle', 'Birdie', 'Par', 'Bogey', 'D.Bogey', '+3 Bogey']
                        
                        # Transformamos la tabla para que Plotly la entienda (formato largo)
                        df_long = df_dist.melt(id_vars='Jugador', var_name='Resultado', value_name='Cantidad')
                        
                        # Colores personalizados e intuitivos para el golf
                        colores_golf = {
                            'Eagle': '#FFD700',     # Oro
                            'Birdie': '#00BFFF',    # Azul claro
                            'Par': '#28B463',       # Verde
                            'Bogey': '#F39C12',     # Naranja
                            'D.Bogey': '#E74C3C',   # Rojo
                            '+3 Bogey': '#7B241C'   # Rojo muy oscuro
                        }
                        
                        fig1 = px.bar(
                            df_long, 
                            x='Jugador', 
                            y='Cantidad', 
                            color='Resultado',
                            title="🎯 Radiografía de Hoyos",
                            color_discrete_map=colores_golf,
                            text_auto=True
                        )
                        # Ocultamos el título del eje Y para que quede más limpio
                        fig1.update_layout(yaxis_title=None, xaxis_title=None) 
                        st.plotly_chart(fig1, use_container_width=True)
                
                    with col_graf_2:
                        # 2. GRÁFICO DE BARRAS AGRUPADAS: Scratch vs Puntos MVP
                        # Comparamos el rendimiento bruto frente a los puntos de MVP que aporta cada uno
                        
                        # Ajustamos los nombres de las columnas que queremos mostrar
                        df_rend = df_graficos[['Jugador', 'scr', 'pts_mvp']].copy()
                        df_rend.rename(columns={'scr': 'Puntos Scratch', 'pts_mvp': 'Puntos MVP'}, inplace=True)
                        df_rend_long = df_rend.melt(id_vars='Jugador', var_name='Métrica', value_name='Valor')
                        
                        fig2 = px.bar(
                            df_rend_long, 
                            x='Jugador', 
                            y='Valor', 
                            color='Métrica', 
                            barmode='group',
                            title="🏆 Rendimiento: Scratch vs MVP",
                            color_discrete_map={'Puntos Scratch': '#34495E', 'Puntos MVP': '#F1C40F'},
                            text_auto='.1f'
                        )
                        fig2.update_layout(yaxis_title=None, xaxis_title=None, legend_title_text='')
                        st.plotly_chart(fig2, use_container_width=True)
                        
                    #PUTT
                    import altair as alt
                    # --- 📊 ANÁLISIS DE PUTTS (Dinámico y Condicionado) ---
                    st.markdown("---")
                    st.markdown("### 📊 Análisis de Putts")
                    
                    # 1. DEFINICIÓN DEL DATASET BASE
                    # Usamos df_raw para filtrar dinámicamente según la selección del usuario
                    if ver_acumulado:
                        # Si estamos en modo acumulado, filtramos por la temporada seleccionada
                        temp_val = str(seleccion_filtro)
                        df_putts_source = df_raw[df_raw['t_limpia'] == temp_val].copy()
                    else:
                        # Si estamos en modo jornada, usamos la jornada seleccionada
                        df_putts_source = df_raw[df_raw['fecha'] == seleccion_filtro].copy()
                    
                    # 2. APLICACIÓN DE LA REGLA ESPECIAL 2026
                    # Si la temporada es '2026', filtramos estrictamente a partir del 8/07/2026
                    fecha_corte = pd.Timestamp('2026-07-08')
                    # Aseguramos que tenemos la columna fecha_dt para comparar
                    if 'fecha_dt' not in df_putts_source.columns:
                        df_putts_source['fecha_dt'] = pd.to_datetime(df_putts_source['fecha'], dayfirst=True)
                    
                    # Filtro: Si la temporada es 2026, solo nos quedamos con fechas >= 08/07/2026
                    if '2026' in df_putts_source['t_limpia'].values:
                        df_putts_source = df_putts_source[
                            (df_putts_source['t_limpia'] != '2026') | (df_putts_source['fecha_dt'] >= fecha_corte)
                        ]
                    
                    # 3. CÁLCULO DE MÉTRICAS (Si hay datos tras el filtrado)
                    if not df_putts_source.empty:
                        stats_list = []
                        cols_putts = {'p0': 'MANU', 'p1': 'JOSE', 'p2': 'ROGE', 'p3': 'LALO'}
                        
                        for col, nombre in cols_putts.items():
                            if col in df_putts_source.columns:
                                datos = pd.to_numeric(df_putts_source[col], errors='coerce').fillna(0)
                                stats_list.append({
                                    'Jugador': nombre,
                                    'Media Putts': datos.mean(),
                                    '% 1-Putt': (datos == 1).mean() * 100,
                                    '% 2-Putts': (datos == 2).mean() * 100,
                                    '💀 % 3-Putts': (datos >= 3).mean() * 100
                                })
                        
                        df_consistencia = pd.DataFrame(stats_list)
                        df_consistencia = df_consistencia.sort_values(by='Media Putts', ascending=True).reset_index(drop=True)
                        orden_jugadores = list(df_consistencia['Jugador'])
                    
                        # 4. GRÁFICO (Altair)
                        chart = alt.Chart(df_consistencia).mark_bar().encode(
                            x=alt.X('Jugador:N', sort=orden_jugadores, axis=alt.Axis(labelAngle=0, title=None)), 
                            y=alt.Y('Media Putts', scale=alt.Scale(domain=[0, 3])), 
                            color=alt.Color('Jugador:N', sort=orden_jugadores, legend=None) 
                        ).properties(height=300)
                        
                        text = chart.mark_text(align='center', baseline='bottom', dy=-5, color='black').encode(
                            text=alt.Text('Media Putts', format='.2f')
                        )
                        
                        st.altair_chart(chart + text, use_container_width=True)
                        
                        # 5. TABLA DE CONSISTENCIA
                        st.markdown(f"### ⛳ Tabla de Consistencia <span style='color:green; font-size: 0.8em;'>({len(df_putts_source)} hoyos registrados)</span>", unsafe_allow_html=True)
                        
                        estilo = df_consistencia.style.format({
                            'Media Putts': '{:.1f}', 
                            '% 1-Putt': '{:.0f}%', 
                            '% 2-Putts': '{:.0f}%', 
                            '💀 % 3-Putts': '{:.0f}%'
                        }).set_table_styles([
                            {'selector': 'th', 'props': [('text-align', 'center')]},
                            {'selector': 'td', 'props': [('text-align', 'center')]}
                        ])
                        st.table(estilo)
                    else:
                        st.warning("No hay datos de putts disponibles para esta selección (o no cumplen el requisito de fecha > 08/07/2026).")
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
            'p0': 'sum', 'p1': 'sum', 'p2': 'sum', 'p3': 'sum',
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
                st.write("---")
                st.write("### ⛳ Putts Totales de la Jornada")
                col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                col_p1.metric("Manu", int(row['p0']))
                col_p2.metric("Jose", int(row['p1']))
                col_p3.metric("Roge", int(row['p2']))
                col_p4.metric("Lalo", int(row['p3']))
                st.write("---")
                
                # Tabla detallada con nombres de jugadores
                st.dataframe(
                    df_partido[['hoyo', 's0', 's1', 's2', 's3', 'p0', 'p1', 'p2', 'p3', 'resultado_a', 'resultado_b']],
                    column_config={
                        "hoyo": "H",
                        "s0": "Manu", "s1": "Jose", 
                        "s2": "Roge", "s3": "Lalo",
                        "p0": "M_Put", "p1": "J_Put", "p2": "R_Put", "p3": "L_Put",
                        "resultado_a": "Match A", "resultado_b": "Match B"
                    },
                    hide_index=True,
                    use_container_width=True
                )

                # --- BOTONES DE GESTIÓN (Ajustados a 3 columnas) ---
                col_ed, col_bor, col_bor_h = st.columns(3)
                
                # 1. BOTÓN EDITAR
                if col_ed.button("📝 Seguir/Editar", key=f"ed_{p_id}", use_container_width=True):
                    st.session_state.game = {
                        "id": p_id,
                        "fecha": row['fecha'],
                        "temporada": row['temporada'],
                        "h_sel": int(df_partido['hoyo'].max())
                    }
                    st.session_state.menu_seleccionado = "Nueva Partida"
                    st.rerun()

                # 2. BOTÓN BORRAR JORNADA
                key_popover = f"popover_del_{p_id}"
                with col_bor:
                    with st.popover("🗑️ Borrar Día", use_container_width=True):
                        st.error("¿Seguro? Se eliminarán todos los registros de este día.")
                        if st.button("ELIMINAR DÍA", key=f"btn_del_{p_id}", type="primary", use_container_width=True):
                            if borrar_partido_completo(p_id):
                                st.toast("Jornada eliminada")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("No se pudo eliminar.")

                # 3. BOTÓN ELIMINAR HOYO (Integrado en la 3ª columna)
                with col_bor_h:
                    with st.popover("🗑️ Borrar Hoyo", use_container_width=True):
                        hoyos_disponibles = sorted(df_partido['hoyo'].astype(int).tolist())
                        hoyo_sel = st.selectbox("¿Qué hoyo borrar?", hoyos_disponibles, key=f"sel_h_{p_id}")
                        
                        if st.button(f"Confirmar Hoyo {hoyo_sel}", key=f"btn_del_h_{p_id}_{hoyo_sel}", type="primary", use_container_width=True):
                            if borrar_hoyo_especifico(p_id, hoyo_sel):
                                st.success(f"Hoyo {hoyo_sel} eliminado.")
                                st.cache_data.clear() # Limpiamos caché para refrescar la tabla
                                st.rerun()


                                


                            


                                


