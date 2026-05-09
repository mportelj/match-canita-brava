
import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime

# 1. PRIMERO DEFINES LA FUNCIÓN
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
    
    url_hoja = "https://docs.google.com/spreadsheets/d/17mwvtZY-f6BWXOlDGkDdYur8l0ATvGYpbkshjv1sJAk/edit?gid=0#gid=0"
    return client.open_by_url(url_hoja).sheet1

# 2. DESPUÉS LA LLAMAS
if 'sh' not in st.session_state:
    st.session_state.sh = cargar_datos_golf()

sh = st.session_state.sh

# --- INICIALIZACIÓN GLOBAL (Al principio de tu main.py) ---
if 'menu_seleccionado' not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

if 'radio_menu' not in st.session_state:
    st.session_state.radio_menu = "Inicio" # <--- ESTO EVITA EL ERROR

# Lógica de la app
#st.title("⛳ CAÑITA BRAVA")


# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

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

def calcular_puntos_hoyo(s0, s1, s2, s3, par):
    # Equipos: E1 (Manu s0, Jose s2) vs E2 (Roge s1, Lalo s3)
    e1 = [s0, s2]
    e2 = [s1, s3]
    
    pts_e1, pts_e2 = 0, 0
    
    # A) Punto a la Mejor Bola
    if min(e1) < min(e2): pts_e1 += 1
    elif min(e2) < min(e1): pts_e2 += 1
    
    # B) Punto a la Peor Bola
    if max(e1) < max(e2): pts_e1 += 1
    elif max(e2) < max(e1): pts_e2 += 1
    
    # C) Bonus por Birdie o mejor
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
        g = st.session_state.game  # Aquí ya vienen la fecha y temporada elegidas
        
        # --- LÓGICA DE PUNTOS ---
        res_a, res_b = min(g0, g1), min(g2, g3)
        p_a = 1 if res_a < res_b else (0.5 if res_a == res_b else 0)
        p_b = 1 if res_b < res_a else (0.5 if res_a == res_b else 0)
        
        # --- CONSTRUCCIÓN DE LA FILA (15 CAMPOS) ---
        # Respetando el orden: id, partido_id, hoyo, fecha, temporada, etc.
        nueva_fila = [
            f"{g['id']}_{hoyo_id}", # A: id (único)
            str(g['id']),           # B: partido_id
            int(hoyo_id),           # C: hoyo
            g['fecha'],             # D: fecha (la seleccionada en el combo)
            g['temporada'],         # E: temporada (año de la fecha seleccionada)
            p_a,                    # F: resultado_a
            p_b,                    # G: resultado_b
            0, 0, 0, 0,             # H-K: p1_pts a p4_pts (rellenar según tu lógica)
            int(g0), int(g1),       # L, M: s0, s1
            int(g2), int(g3)        # N, O: s2, s3
        ]

        # --- ACTUALIZACIÓN ---
        filas = hoja.get_all_values()
        header = filas[0]
        
        # Filtro para evitar duplicar el mismo hoyo en la misma partida
        datos_actualizados = [
            f for f in filas[1:] 
            if not (len(f) > 2 and str(f[1]) == str(g['id']) and str(f[2]) == str(hoyo_id))
        ]
        
        datos_actualizados.append(nueva_fila)
        datos_actualizados.sort(key=lambda x: int(x[2])) # Ordenar por hoyo para el Excel

        hoja.clear()
        hoja.update('A1', [header] + datos_actualizados)
        st.toast(f"✅ Hoyo {hoyo_id} guardado en Temporada {g['temporada']}")

    except Exception as e:
        st.error(f"Error al guardar: {e}")

# --- 3. NAVEGACIÓN ---
menu = st.sidebar.radio("Ir a:", ["Inicio", "Nueva Partida", "Estadísticas", "Admin"], 
                       index=["Inicio", "Nueva Partida", "Estadísticas", "Admin"].index(st.session_state.menu_seleccionado),
                       key="radio_menu", on_change=cambiar_menu)


df_raw = leer_datos()

if df_raw is not None and not df_raw.empty:
    # --- CÁLCULO DEL MARCADOR DE LA TEMPORADA (4.5 vs 3.5) ---
    # Agrupamos por fecha y sumamos los resultados de cada pareja en cada jornada
    jornadas_totales = df_raw.groupby('fecha')[['resultado_a', 'resultado_b']].sum()
    
    # Calculamos los puntos: 1 por ganar jornada, 0.5 por empate
    marcador_global_a = (jornadas_totales['resultado_a'] > jornadas_totales['resultado_b']).sum() + \
                        (jornadas_totales['resultado_a'] == jornadas_totales['resultado_b']).sum() * 0.5
    marcador_global_b = (jornadas_totales['resultado_b'] > jornadas_totales['resultado_a']).sum() + \
                        (jornadas_totales['resultado_a'] == jornadas_totales['resultado_b']).sum() * 0.5
    
    # Guardamos en variables que usaremos en cualquier pestaña
    texto_marcador_global = f"{marcador_global_a} vs {marcador_global_b}"

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

    # --- BLOQUE A: CONFIGURACIÓN DE INICIO ---
    if 'game' not in st.session_state:
        st.markdown("### ⛳ Nueva Partida")
        fecha_seleccionada = st.date_input("Selecciona la fecha del partido")

    if st.button("Iniciar Partido"):
        # Extraemos el año de la fecha seleccionada para la temporada
        año_temporada = str(fecha_seleccionada.year)
        fecha_formateada = fecha_seleccionada.strftime("%d/%m/%Y")
    
        st.session_state.game = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "fecha": fecha_formateada,
        "temporada": año_temporada,
        "puntos_acumulados_a": 0,
        "puntos_acumulados_b": 0
    }
    st.success(f"Partida iniciada para la temporada {año_temporada}")
            # Limpiamos caché para asegurar que al empezar no haya datos viejos
    st.cache_data.clear()
    st.rerun()
            
    else:
        # --- BLOQUE B: LECTURA ÚNICA CENTRALIZADA ---
        g = st.session_state.game
        
        # Leemos los datos UNA SOLA VEZ para todo este renderizado
        df_p = leer_datos() 
        df_partido_actual = pd.DataFrame()

        if df_p is not None and not df_p.empty:
            # Limpieza de nombres de columnas por si hay espacios
            df_p.columns = [str(c).strip() for c in df_p.columns]
            
            # Filtramos el partido actual de forma segura
            if 'partido_id' in df_p.columns:
                df_p['partido_id'] = df_p['partido_id'].astype(str)
                df_partido_actual = df_p[df_p['partido_id'] == str(g['id'])]

        # --- BLOQUE C: MARCADOR MATCH PLAY ---
        pts_a_total = df_partido_actual['resultado_a'].sum() if not df_partido_actual.empty else 0
        pts_b_total = df_partido_actual['resultado_b'].sum() if not df_partido_actual.empty else 0
        
        dif = pts_a_total - pts_b_total
        m_a, m_b = (dif, 0) if dif > 0 else (0, abs(dif))

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
        fila_hoyo = df_partido_actual[df_partido_actual['hoyo'] == h] if not df_partido_actual.empty else pd.DataFrame()
        ya_existe = not fila_hoyo.empty
        v_ref = [int(fila_hoyo.iloc[0][f's{i}']) if ya_existe else PAR_RIA_VIGO[h] for i in range(4)]

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
        # Asegúrate de que st.write esté al mismo nivel que el 'if' del botón de arriba
        st.write("---") 
        
        with st.popover("🏁 Finalizar Partida", use_container_width=True):
            st.warning("¿Estás seguro de que quieres cerrar la partida actual?")
            if st.button("Confirmar Cierre y Borrar Sesión", type="primary", use_container_width=True):
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
    
    df = leer_datos()

    if df is None or df.empty:
        st.warning("No hay datos registrados en la base de datos.")
    else:
        # 1. LIMPIEZA DE DATOS: Aseguramos que los puntos grabados sean números
        columnas_numericas = ['resultado_a', 'resultado_b', 's0', 's1', 's2', 's3', 'hoyo']
        for col in columnas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Normalización de fecha para agrupar
        df['fecha_str'] = df['fecha'].astype(str).apply(lambda x: x.split(' ')[0].strip())
        def formatear_fecha(f):
            try: return pd.to_datetime(f, dayfirst=True).strftime('%d/%m/%Y')
            except: return f
        df['fecha_bonita'] = df['fecha_str'].apply(formatear_fecha)
        
        partidos = df.groupby('fecha_bonita')
        fechas_ordenadas = sorted(partidos.groups.keys(), 
                                key=lambda x: pd.to_datetime(x, format='%d/%m/%Y'), 
                                reverse=True)

        # 2. RENDERIZADO DE CADA JORNADA
        for f_disp in fechas_ordenadas:
            datos_jornada = partidos.get_group(f_disp)
            num_hoyos = len(datos_jornada['hoyo'].unique())
            
            # --- CÁLCULO DIRECTO DESDE LAS COLUMNAS GRABADAS ---
            # Sumamos los valores que ya están escritos en la hoja
            suma_a = datos_jornada['resultado_a'].sum()
            suma_b = datos_jornada['resultado_b'].sum()
            
            # Aplicamos la resta neta para el marcador Match Play
            diferencia = suma_a - suma_b
            
            if diferencia > 18: diferencia = 18 # Capamos a 18 si fuera necesario
            
            if diferencia > 0:
                m_a, m_b = int(diferencia), 0
                match_txt = f"MANU & JOSE: {m_a} vs ROGE & LALO: 0"
            elif diferencia < 0:
                m_a, m_b = 0, int(abs(diferencia))
                match_txt = f"MANU & JOSE: 0 vs ROGE & LALO: {m_b}"
            else:
                m_a, m_b = 0, 0
                match_txt = "EMPATE (All Square)"

            # --- DISEÑO DEL PANEL ---
            with st.expander(f"📅 {f_disp} — {num_hoyos} Hoyos — [ {match_txt} ]"):
                st.markdown(f"**Resultado Acumulado:** `{match_txt}`")
                
                # Tabla con los golpes (s0-s3) mapeados a los nombres
                # s0:MANU, s1:JOSE, s2:ROGE, s3:LALO
                tabla_vista = datos_jornada[['hoyo', 's0', 's1', 's2', 's3']].sort_values('hoyo')
                tabla_vista.columns = ['Hoyo', 'MANU', 'JOSE', 'ROGE', 'LALO']
                
                st.dataframe(tabla_vista, hide_index=True, use_container_width=True)

                # BOTONES DE ACCIÓN
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"✏️ Editar", key=f"ed_{f_disp}"):
                        st.session_state.fecha_partida = pd.to_datetime(f_disp, dayfirst=True)
                        st.session_state.menu_seleccionado = "Jugar/Editar"
                        st.rerun()
                with c2:
                    conf = st.checkbox("Confirmar borrar", key=f"ch_{f_disp}")
                    if st.button(f"🗑️ Borrar", key=f"del_{f_disp}", disabled=not conf, type="primary"):
                        # Aquí iría tu lógica de borrar filas por fecha en el Sheets
                        st.warning("Función de borrado no conectada")

    if st.button("🔄 Refrescar"):
        st.rerun()
