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

# --- 3. INICIALIZACIÓN DE ESTADOS Y RESURRECCIÓN AUTOMÁTICA ---

if 'sh' not in st.session_state:
    st.session_state.sh = cargar_datos_golf()

# 1. Determinamos si hay una partida incompleta en Google Sheets ANTES de fijar el menú
menu_inicial = "Inicio"
game_detectado = None

if "partida_id" in st.query_params:
    menu_inicial = "Nueva Partida"
    game_detectado = {
        'id': st.query_params["partida_id"],
        'h_sel': int(st.query_params.get("hoyo", 1)),
        'fecha': datetime.now().strftime("%d/%m/%Y"), 
        'temporada': str(datetime.now().year)
    }
else:
    # Comprobamos en la BD si hay un partido abierto (menos de 18 hoyos jugados)
    try:
        hoja_temp = st.session_state.sh
        datos_temp = hoja_temp.get_all_values()
        if len(datos_temp) > 1:
            df_check = pd.DataFrame(datos_temp[1:], columns=datos_temp[0])
            if not df_check.empty and 'partido_id' in df_check.columns:
                ultimo_p_id = str(df_check['partido_id'].iloc[-1]).split('.')[0].strip()
                df_ultimo = df_check[df_check['partido_id'].astype(str).str.split('.').str[0] == ultimo_p_id]
                hoyos_jugados = df_ultimo['hoyo'].nunique() if 'hoyo' in df_ultimo.columns else 0
                
                if hoyos_jugados < 18:
                    menu_inicial = "Nueva Partida"
                    siguiente_hoyo = hoyos_jugados + 1
                    fecha_p = df_ultimo['fecha'].iloc[0] if 'fecha' in df_ultimo.columns else datetime.now().strftime("%d/%m/%Y")
                    temp_p = str(df_ultimo['temporada'].iloc[0]) if 'temporada' in df_ultimo.columns else str(datetime.now().year)
                    
                    game_detectado = {
                        'id': ultimo_p_id,
                        'h_sel': siguiente_hoyo,
                        'fecha': fecha_p,
                        'temporada': temp_p
                    }
                    st.query_params["partida_id"] = ultimo_p_id
                    st.query_params["hoyo"] = siguiente_hoyo
    except:
        pass

# 2. Inicializamos los estados
default_states = {
    'refresco_id': 0,
    'hoyo_modificado': False,
    'menu_seleccionado': menu_inicial,
    'game': game_detectado if game_detectado else {"h_sel": 1}
}

for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value
    
def borrar_partido_completo(partido_id):
    try:
        hoja = st.session_state.sh
        id_p_buscar = str(partido_id).split('.')[0].strip()
        
        filas = hoja.get_all_values()
        if not filas:
            return False
            
        header = filas[0]
        datos_originales = filas[1:]
        
        nuevos_datos = []
        for fila in datos_originales:
            if len(fila) > 1:
                id_fila = str(fila[1]).split('.')[0].strip()
                if id_fila == id_p_buscar:
                    continue
            
            fila_tipada = []
            for idx, valor in enumerate(fila):
                val_str = str(valor).strip()
                if val_str == "" or val_str.lower() == "nan":
                    fila_tipada.append("")
                    continue
                
                try:
                    if idx in [1, 2, 4, 5, 6, 11, 12, 13, 14, 15]:
                        fila_tipada.append(int(float(val_str)))
                    elif idx in [7, 8, 9, 10]:
                        fila_tipada.append(float(val_str.replace(',', '.')))
                    else:
                        fila_tipada.append(val_str)
                except ValueError:
                    fila_tipada.append(val_str)
                    
            nuevos_datos.append(fila_tipada)
            
        hoja.clear()
        hoja.update('A1', [header] + nuevos_datos, value_input_option='USER_ENTERED')
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error interno al borrar: {e}")
        return False
        
# --- CONFIGURACIÓN DE NAVEGACIÓN ---

def cb_editar_partido(p_id, fecha, temporada):
    st.session_state.game = {
        "id": str(p_id),
        "fecha": fecha,
        "temporada": str(temporada),
        "h_sel": 1
    }
    st.session_state.menu_seleccionado = "Nueva Partida"

if 'menu_seleccionado' not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

# --- EL SIDEBAR (MENÚ LATERAL ÚNICO Y LIMPIO) ---
with st.sidebar:
    st.markdown("# ⛳ Cañita Brava")
    st.write("---")
    
    opciones_menu = ["Inicio", "Nueva Partida", "Admin", "Estadísticas"]
    
    try:
        idx_actual = opciones_menu.index(st.session_state.menu_seleccionado)
    except ValueError:
        idx_actual = 0

    nuevo_menu = st.radio(
        "Navegación",
        opciones_menu,
        index=idx_actual
    )
    
    if nuevo_menu != st.session_state.menu_seleccionado:
        st.session_state.menu_seleccionado = nuevo_menu
        st.rerun()

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
            cols_mvp = ['p1_pts', 'p2_pts', 'p3_pts', 'p4_pts']
            for col in cols_mvp:
                if col in df_raw.columns:
                    df_raw[col] = pd.to_numeric(
                        df_raw[col].astype(str).str.replace(',', '.').str.strip(), 
                        errors='coerce'
                    ).fillna(0.0)

            cols_int = [
                'resultado_a', 'resultado_b', 
                's0', 's1', 's2', 's3',
                'p0', 'p1', 'p2', 'p3',
                'hoyo', 'temporada', 'partido_id'
            ]
            for col in cols_int:
                if col in df_raw.columns:
                    df_raw[col] = pd.to_numeric(
                        df_raw[col].astype(str).str.replace(',', '.').str.strip(), 
                        errors='coerce'
                    ).fillna(0).astype(int)
            
            if 'fecha' in df_raw.columns:
                df_raw['fecha'] = df_raw['fecha'].astype(str).str.strip()

        return df_raw

    except Exception as e:
        st.error(f"Error al leer la base de datos: {e}")
        return pd.DataFrame()

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
    e1 = [s0, s2]
    e2 = [s1, s3]
    pts_e1, pts_e2 = 0, 0
    
    if min(e1) < min(e2): pts_e1 += 1
    elif min(e2) < min(e1): pts_e2 += 1
    
    if max(e1) < max(e2): pts_e1 += 1
    elif max(e2) < max(e1): pts_e2 += 1
    
    def get_bonus(golpes, p):
        dif = golpes - p
        if dif <= -3: return 3
        if dif == -2: return 2
        if dif == -1: return 1
        return 0

    pts_e1 += sum([get_bonus(g, par) for g in e1])
    pts_e2 += sum([get_bonus(g, par) for g in e2])
    
    return pts_e1, pts_e2

if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

def calcular_bonus_hoyo(golpes_jugador, par):
    if golpes_jugador <= 0:
        return 0
            
    diferencia = par - golpes_jugador
    if diferencia == 1:
        return 1
    elif diferencia == 2:
        return 2
    elif diferencia >= 3:
        return 3
    return 0

def borrar_hoyo_especifico(partido_id, hoyo_id):
    try:
        hoja = st.session_state.sh
        filas = hoja.get_all_values()
        header = filas[0]
        datos = filas[1:]
        
        nuevos_datos = []
        for f in datos:
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
# SECCIÓN: INICIO
# ==========================================
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    if not df.empty:
        st.write(f"Último partido registrado: {df['fecha'].iloc[-1]}")
    
    anio_actual = datetime.now().year

    if not df.empty:
        temps = sorted(df['temporada'].unique().tolist(), reverse=True)
    else:
        temps = [str(anio_actual)]
    
    if str(anio_actual) not in [str(t) for t in temps]:
        temps.insert(0, str(anio_actual))
    
    st.selectbox("Temporada:", temps, key="sel_temp")
    
    pa_t, pb_t = (3.5, 3.5) if str(st.session_state.sel_temp) == "2026" else (0.0, 0.0)
        
    if not df.empty:
        df_t = df[df['temporada'].astype(str) == str(st.session_state.sel_temp)]
        
        if not df_t.empty:
            partidos = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
            
            for _, r in partidos.iterrows():
                if r['resultado_a'] > r['resultado_b']: 
                    pa_t += 1
                elif r['resultado_b'] > r['resultado_a']: 
                    pb_t += 1
                else:
                    pa_t += 0.5; pb_t += 0.5
            
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
    st.session_state['marcador_acumulado_a'] = pa_t
    st.session_state['marcador_acumulado_b'] = pb_t

# ==========================================
elif st.session_state.menu_seleccionado == "Nueva Partida":
    if 'refresco_id' not in st.session_state: 
        st.session_state.refresco_id = 0
    
    if 'hoyo_modificado' not in st.session_state:
        st.session_state.hoyo_modificado = False

    if 'confirmando_hoyo' not in st.session_state:
        st.session_state.confirmando_hoyo = False
    
    df_p = pd.DataFrame()
    df_partido_actual = pd.DataFrame()

    def ejecutar_guardado_automatico(hoyo_num):
        try:
            hoja = st.session_state.sh
            g_actual = st.session_state.game
            id_p = str(g_actual['id']).split('.')[0].strip()
            f_p = pd.to_datetime(g_actual['fecha'], dayfirst=True).strftime('%d/%m/%Y')
            t_p = int(g_actual.get('temporada', 2026))
            
            s0_v = int(st.session_state.get(f"s0_h{hoyo_num}", 4))
            s1_v = int(st.session_state.get(f"s1_h{hoyo_num}", 4))
            s2_v = int(st.session_state.get(f"s2_h{hoyo_num}", 4))
            s3_v = int(st.session_state.get(f"s3_h{hoyo_num}", 4))
            
            p0_v = int(st.session_state.get(f"p0_h{hoyo_num}", 2))
            p1_v = int(st.session_state.get(f"p1_h{hoyo_num}", 2))
            p2_v = int(st.session_state.get(f"p2_h{hoyo_num}", 2))
            p3_v = int(st.session_state.get(f"p3_h{hoyo_num}", 2))
            
            hoyo_cronologico = int(hoyo_num)
            if g_actual.get('modo_9_hoyos', False):
                vuelta_base = 1 if g_actual.get('vuelta_repetida') == "1ª Vuelta (Hoyos 1-9)" else 10
                hoyo_real_campo = ((hoyo_cronologico - 1) % 9) + vuelta_base
            else:
                hoyo_real_campo = hoyo_cronologico

            par_hoyo = int(PAR_RIA_VIGO[hoyo_real_campo])
            golpes = [s0_v, s1_v, s2_v, s3_v]
            
            mejor_a = min(golpes[0], golpes[1])
            mejor_b = min(golpes[2], golpes[3])
            peor_a = max(golpes[0], golpes[1])
            peor_b = max(golpes[2], golpes[3])
            
            res_a, res_b = 0, 0
            if mejor_a < mejor_b:   res_a += 1
            elif mejor_b < mejor_a: res_b += 1
            if peor_a < peor_b:     res_a += 1
            elif peor_b < peor_a:   res_b += 1
            
            res_a += calcular_bonus_hoyo(golpes[0], par_hoyo)
            res_a += calcular_bonus_hoyo(golpes[1], par_hoyo)
            res_b += calcular_bonus_hoyo(golpes[2], par_hoyo)
            res_b += calcular_bonus_hoyo(golpes[3], par_hoyo)
            
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

            nueva_fila = [
                f"{id_p}_H{hoyo_cronologico}", int(id_p), int(hoyo_cronologico), f_p, 
                t_p, int(res_a), int(res_b), 
                p_mvp[0], p_mvp[1], p_mvp[2], p_mvp[3], 
                golpes[0], golpes[1], golpes[2], golpes[3],
                int(p0_v), int(p1_v), int(p2_v), int(p3_v),
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
            st.toast(f"✅ Hoyo {hoyo_cronologico} guardado correctamente", icon="💾")
            return True
        except Exception as err:
            st.error(f"Error al guardar los datos: {err}")
            return False

    game_activo = st.session_state.get('game')
    if not game_activo or not isinstance(game_activo, dict) or 'id' not in game_activo:
        st.title("⛳ Nueva Partida")
        fecha_nueva = st.date_input("Fecha del partido", key="fecha_nueva_p")
        if st.button("🚀 INICIAR PARTIDO", type="primary", use_container_width=True):
            nuevo_id = datetime.now().strftime("%Y%m%d%H%M%S")
            
            st.session_state.game = {
                "id": nuevo_id,
                "fecha": fecha_nueva.strftime("%d/%m/%Y"),
                "temporada": str(fecha_nueva.year),
                "h_sel": 1
            }
            
            st.session_state.refresco_id += 1
            st.cache_data.clear()
            
            st.query_params["partida_id"] = nuevo_id
            st.query_params["hoyo"] = 1
            
            st.rerun()
    
    else:
        g = st.session_state.game
        st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)

        try:
            df_p = leer_datos() 
            if df_p is not None and not df_p.empty:
                id_sesion = str(int(float(g['id'])))
                
                def normalizar_id(val):
                    try: return str(int(float(val)))
                    except: return ""
                
                df_p['partido_id_str'] = df_p['partido_id'].apply(normalizar_id)
                df_partido_actual = df_p[df_p['partido_id_str'] == id_sesion].copy()
                
                if not df_partido_actual.empty:
                    df_partido_actual['hoyo_int'] = df_partido_actual['hoyo'].apply(lambda x: int(float(x)) if pd.notnull(x) else 0)
                    df_partido_actual = df_partido_actual.drop_duplicates(subset=['hoyo_int'], keep='last')
        except Exception as e:
            st.error(f"Error al conectar con la base de datos: {e}")

        if 'h_sel' not in g:
            g['h_sel'] = 1

        puntos_equipo_a = 0
        puntos_equipo_b = 0
        if not df_partido_actual.empty:
            puntos_equipo_a = df_partido_actual['resultado_a'].sum()
            puntos_equipo_b = df_partido_actual['resultado_b'].sum()
        
        diferencia_global = puntos_equipo_a - puntos_equipo_b
        marcador_a, marcador_b = (diferencia_global, 0) if diferencia_global > 0 else (0, abs(diferencia_global))

        # 4. MARCADOR VISUAL GLOBAL (CORREGIDO Y VISIBLE)
        st.markdown(f"""
            <div style="border: 2px solid #2e7d32; border-radius: 12px; padding: 10px; background-color: #f0f4f0; margin-bottom: 10px; text-align: center;">
                <div style="display: flex; justify-content: space-around; align-items: center; width: 100%;">
                    <div style="flex: 1; padding: 0;">
                        <p style="margin:0; font-size:0.75em; font-weight:bold; white-space: nowrap;">MANU & JOSE</p>
                        <h1 style="margin:0; font-size:2.8rem; line-height:1.1; color:{COLOR_A if marcador_a > 0 else '#333'};">{marcador_a:g}</h1>
                    </div>
                    <div style="background:#ccc; border-radius:50%; width:26px; height:26px; min-width:26px; display:flex; align-items:center; justify-content:center; font-weight:bold; color:#666; font-size:0.7em; margin: 0 4px;">VS</div>
                    <div style="flex: 1; padding: 0;">
                        <p style="margin:0; font-size:0.75em; font-weight:bold; white-space: nowrap;">ROGE & LALO</p>
                        <h1 style="margin:0; font-size:2.8rem; line-height:1.1; color:{COLOR_B if marcador_b > 0 else '#333'};">{marcador_b:g}</h1>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        h_actual = int(g['h_sel'])
        hoyo_anterior = max(1, h_actual - 1)
        hoyo_siguiente = min(18, h_actual + 1)

        def obtener_icono_estado(h_num):
            if df_partido_actual.empty or 'hoyo_int' not in df_partido_actual.columns:
                return "⏳"
            df_h = df_partido_actual[df_partido_actual['hoyo_int'] == h_num]
            if df_h.empty or df_h.iloc[0][['s0', 's1', 's2', 's3']].sum() == 0:
                return "⏳"
            
            ra = int(df_h.iloc[0]['resultado_a'])
            rb = int(df_h.iloc[0]['resultado_b'])
            if ra > rb:
                return "🟢"
            elif rb > ra:
                return "🔴"
            else:
                return "⚪"

        icono_anterior = obtener_icono_estado(hoyo_anterior)
        icono_siguiente = obtener_icono_estado(hoyo_siguiente)

        st.markdown("""
            <style>
                div.stButton > button {
                    height: 45px !important;
                    font-size: 1rem !important;
                    font-weight: bold !important;
                }
            </style>
        """, unsafe_allow_html=True)

        col_nav_1, col_nav_2 = st.columns(2)
        
        espacios = "\u00A0\u00A0\u00A0"
        texto_btn_anterior = f"⬅️ Hoyo: {hoyo_anterior}{espacios}{icono_anterior}" if h_actual > 1 else "⬅️ ANT."
        texto_btn_siguiente = f"Hoyo: {hoyo_siguiente}{espacios}{icono_siguiente} ➡️" if h_actual < 18 else "SIG. ➡️"

        if col_nav_1.button(texto_btn_anterior, use_container_width=True, disabled=(h_actual == 1)):
            st.session_state.game['h_sel'] = hoyo_anterior
            st.query_params["hoyo"] = hoyo_anterior
            st.session_state.refresco_id += 1
            st.rerun()
            
        if col_nav_2.button(texto_btn_siguiente, use_container_width=True, disabled=(h_actual == 18)):
            st.session_state.game['h_sel'] = hoyo_siguiente
            st.query_params["hoyo"] = hoyo_siguiente
            st.session_state.refresco_id += 1
            st.rerun()

        st.markdown("""
            <style>
                div[data-baseweb="select"] > div:first-child {
                    font-size: 1.2rem !important;
                }
            </style>
        """, unsafe_allow_html=True)

        def format_hoyo(x):
            par_h = int(PAR_RIA_VIGO.get(int(x), 4))
            
            def to_bold(num):
                bold_digits = {"0": "𝟬", "1": "𝟭", "2": "𝟮", "3": "𝟯", "4": "𝟰", "5": "𝟱", "6": "𝟲", "7": "𝟳", "8": "𝟴", "9": "𝟵"}
                return "".join(bold_digits.get(c, c) for c in str(num))

            h_bold = to_bold(x)
            par_bold = to_bold(par_h)

            estado_str = "⏳ 𝗣𝗲𝗻𝗱𝗶𝗲𝗻𝘁𝗲"
            if not df_partido_actual.empty and 'hoyo_int' in df_partido_actual.columns:
                df_h = df_partido_actual[df_partido_actual['hoyo_int'] == x]
                if not df_h.empty and df_h.iloc[0][['s0', 's1', 's2', 's3']].sum() > 0:
                    ra = int(df_h.iloc[0]['resultado_a'])
                    rb = int(df_h.iloc[0]['resultado_b'])
                    if ra > rb:
                        diff_bold = to_bold(ra - rb)
                        estado_str = f"🟢 𝗠&𝗝 +{diff_bold}"
                    elif rb > ra:
                        diff_bold = to_bold(rb - ra)
                        estado_str = f"🔴 𝗥&𝗟 +{diff_bold}"
                    else:
                        estado_str = "⚪ 𝗘𝗺𝗽𝗮𝘁𝗲 𝗔𝗦"
            
            return f"𝗛𝗼𝘆𝗼 {h_bold} (𝗣𝗮𝗿 {par_bold}) — {estado_str}"

        h_actual = st.selectbox(
            "📍 Seleccionar Hoyo:", 
            options=list(range(1, 19)), 
            index=int(st.session_state.game['h_sel']) - 1,
            format_func=format_hoyo,
            key=f"sb_hoyo_{st.session_state.refresco_id}"
        )
        st.session_state.game['h_sel'] = h_actual
        st.query_params["hoyo"] = h_actual

        try:
            val_par_hoyo = int(PAR_RIA_VIGO[int(h_actual)])
        except:
            val_par_hoyo = 4

        df_hoyo_actual = pd.DataFrame()
        hay_datos_hoyo = False
        if not df_partido_actual.empty and 'hoyo_int' in df_partido_actual.columns:
            df_hoyo_actual = df_partido_actual[df_partido_actual['hoyo_int'] == int(h_actual)]
            if not df_hoyo_actual.empty:
                if df_hoyo_actual.iloc[0][['s0', 's1', 's2', 's3']].sum() > 0:
                    hay_datos_hoyo = True

        if 'h_cargado_actual' not in st.session_state or st.session_state.h_cargado_actual != h_actual:
            st.session_state.h_cargado_actual = h_actual
            if hay_datos_hoyo:
                try:
                    for i in range(4):
                        st.session_state[f"s{i}_h{h_actual}"] = int(df_hoyo_actual[f's{i}'].iloc[0])
                        st.session_state[f"p{i}_h{h_actual}"] = int(df_hoyo_actual[f'p{i}'].iloc[0])
                except:
                    pass
            else:
                for i in range(4):
                    st.session_state[f"s{i}_h{h_actual}"] = val_par_hoyo
                    st.session_state[f"p{i}_h{h_actual}"] = 2
            st.session_state.hoyo_modificado = False

        def activar_boton_guardar():
            st.session_state.hoyo_modificado = True

        config_jugadores = {
            "MANU": {"color": "#2E8B57", "clase": "borde-manu"},
            "JOSE": {"color": "#1E90FF", "clase": "borde-jose"},
            "ROGE": {"color": "#DC143C", "clase": "borde-roge"},
            "LALO": {"color": "#000000", "clase": "borde-lalo"}
        }
        
        st.markdown("""
            <style>
                div[data-testid="stNumberInput"] label { font-size: 1.3rem !important; font-weight: bold !important; color: #2e7d32; }
                div[data-testid="stNumberInput"] input { font-size: 2.2rem !important; height: 75px !important; }
                .stButton button { height: 70px !important; font-size: 1.4rem !important; font-weight: bold !important; }
                .nombre-jugador { font-size: 18px !important; font-weight: bold !important; margin: 0; }
                .stNumberInput { margin-top: -10px !important; margin-bottom: 0px !important; }
                div[data-testid="column"] { padding: 0 2px !important; }
                .borde-manu input { border: 2px solid #2E8B57 !important; }
                .borde-jose input { border: 2px solid #1E90FF !important; }
                .borde-roge input { border: 2px solid #DC143C !important; }
                .borde-lalo input { border: 2px solid #000000 !important; }
            </style>
        """, unsafe_allow_html=True)
        
        jugadores = ["MANU", "JOSE", "ROGE", "LALO"]
        
        for i in range(4):
            nombre = jugadores[i]
            cfg = config_jugadores[nombre]
            
            c1, c2, c3 = st.columns([0.6, 1, 1], vertical_alignment="center")
            
            with c1:
                st.markdown(f"<p class='nombre-jugador' style='color:{cfg['color']};'>{nombre}</p>", unsafe_allow_html=True)
            
            with c2:
                st.markdown(f'<div class="{cfg["clase"]}">', unsafe_allow_html=True)
                st.number_input(f"G{i}", min_value=1, on_change=activar_boton_guardar, key=f"s{i}_h{h_actual}", label_visibility="collapsed")
                st.markdown('</div>', unsafe_allow_html=True)
                
            with c3:
                st.markdown(f'<div class="{cfg["clase"]}">', unsafe_allow_html=True)
                st.number_input(f"P{i}", min_value=0, on_change=activar_boton_guardar, key=f"p{i}_h{h_actual}", label_visibility="collapsed")
                st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.confirmando_hoyo:
            st.markdown(f"""
                <div style="border: 2px solid #2e7d32; border-radius: 12px; padding: 15px; background-color: #f0f4f0; margin-bottom: 15px;">
                    <h3 style="margin-top:0; color:#2e7d32; text-align:center;">📋 Confirmar Hoyo {h_actual}</h3>
                    <p style="text-align:center; font-size:0.95em; color:#555; margin-bottom:10px;">Ordenado de menor a mayor número de golpes:</p>
            """, unsafe_allow_html=True)
            
            s0_v = int(st.session_state.get(f"s0_h{h_actual}", 4))
            s1_v = int(st.session_state.get(f"s1_h{h_actual}", 4))
            s2_v = int(st.session_state.get(f"s2_h{h_actual}", 4))
            s3_v = int(st.session_state.get(f"s3_h{h_actual}", 4))
            
            p0_v = int(st.session_state.get(f"p0_h{h_actual}", 2))
            p1_v = int(st.session_state.get(f"p1_h{h_actual}", 2))
            p2_v = int(st.session_state.get(f"p2_h{h_actual}", 2))
            p3_v = int(st.session_state.get(f"p3_h{h_actual}", 2))

            datos_confirmar = [
                ("MANU", s0_v, p0_v, config_jugadores["MANU"]["color"]),
                ("JOSE", s1_v, p1_v, config_jugadores["JOSE"]["color"]),
                ("ROGE", s2_v, p2_v, config_jugadores["ROGE"]["color"]),
                ("LALO", s3_v, p3_v, config_jugadores["LALO"]["color"])
            ]
            datos_ordenados = sorted(datos_confirmar, key=lambda x: x[1])
            
            for idx, (nom, golpes, putts, color_j) in enumerate(datos_ordenados, 1):
                st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #ffffff; border: 1px solid #d1d5db; border-radius: 8px; padding: 8px 12px; margin-bottom: 6px;">
                        <span style="font-weight: bold; font-size: 1rem; color: {color_j};">{idx}. {nom}</span>
                        <span style="font-size: 0.95rem; color: #374151;"><b>{golpes}</b> golpes — <span style="color: {color_j}; font-weight: bold;">{putts} putts</span></span>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            col_conf_1, col_conf_2 = st.columns(2)
            if col_conf_1.button("✅ SÍ, GUARDAR", type="primary", use_container_width=True, key="btn_conf_si"):
                if ejecutar_guardado_automatico(h_actual):
                    st.session_state.confirmando_hoyo = False
                    st.session_state.hoyo_modificado = False
                    if h_actual < 18:
                        st.session_state.game['h_sel'] = h_actual + 1
                        st.query_params["hoyo"] = st.session_state.game['h_sel']
                        st.session_state.refresco_id += 1
                    st.rerun()
                
            if col_conf_2.button("❌ CANCELAR", use_container_width=True, key="btn_conf_no"):
                st.session_state.confirmando_hoyo = False
                st.rerun()

        else:
            if st.button("💾 GUARDAR RESULTADO HOYO", use_container_width=True, key=f"btn_guardar_h{h_actual}"):
                st.session_state.confirmando_hoyo = True
                st.rerun()

        st.write("---")
        if st.checkbox("📊 Ver Clasificación MVP"):
            if not df_partido_actual.empty:
                df_mvp = df_partido_actual.sort_values('hoyo_int').drop_duplicates('hoyo_int', keep='last')
                
                nombres = ["MANU", "JOSE", "ROGE", "LALO"]
                
                st.write(f"**🌟 Puntos Hoyo {h_actual}**")
                c1, c2, c3, c4 = st.columns(4)
                for i, col_obj in enumerate([c1, c2, c3, c4]):
                    h_reg = df_mvp[df_mvp['hoyo_int'] == h_actual]
                    val = float(h_reg[f'p{i+1}_pts'].iloc[0]) if not h_reg.empty else 0.0
                    col_obj.metric(nombres[i], f"{val:.1f}")

                st.write("**🏆 Acumulado Jornada**")
                totales = []
                for i in range(1, 5):
                    totales.append(df_mvp[f'p{i}_pts'].sum())
                
                ranking = sorted(zip(nombres, totales), key=lambda x: x[1], reverse=True)
                cols_r = st.columns(4)
                for idx, (nom, pts) in enumerate(ranking):
                    cols_r[idx].write(f"**{nom}**")
                    cols_r[idx].write(f"{pts:.1f}")

        st.write("---")
        st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.9em;'>📅 Fecha del partido: <b>{g.get('fecha', 'S/F')}</b></p>", unsafe_allow_html=True)
        
        with st.popover("🏁 FINALIZAR PARTIDA", use_container_width=True):
            st.warning("⚠️ Esta acción cerrará la sesión actual.")
            if st.button("Confirmar y Salir", type="primary", use_container_width=True):
                st.session_state.game = None
                st.query_params.clear()
                st.cache_data.clear()
                st.rerun()

# ==========================================
# SECCIÓN: ESTADÍSTICAS
# ==========================================
elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas y Clasificación")
    
    df_raw = leer_datos()
    if df_raw.empty:
        st.warning("No hay datos para procesar.")
    else:
        def limpiar_valor(v):
            return str(v).split('.')[0].strip()

        df_raw['t_limpia'] = df_raw['temporada'].apply(limpiar_valor)
        df_raw['res_a'] = pd.to_numeric(df_raw['resultado_a'], errors='coerce').fillna(0)
        df_raw['res_b'] = pd.to_numeric(df_raw['resultado_b'], errors='coerce').fillna(0)
        
        for i in range(1, 5):
            c_pts = f'p{i}_pts'
            df_raw[c_pts] = pd.to_numeric(df_raw.get(c_pts, 0), errors='coerce').fillna(0)

        df_raw['fecha_dt'] = pd.to_datetime(df_raw['fecha'], dayfirst=True, errors='coerce')
        df_raw['fecha'] = df_raw['fecha_dt'].dt.strftime('%d/%m/%Y')
        
        df_raw_ordenado = df_raw.dropna(subset=['fecha_dt']).sort_values('fecha_dt', ascending=False)
        fechas_unicas = []
        for f in df_raw_ordenado['fecha']:
            if f not in fechas_unicas:
                fechas_unicas.append(f)
                
        temporadas_unicas = sorted(df_raw['t_limpia'].unique().tolist(), reverse=True)

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
                seleccion_filtro = st.selectbox("Seleccionar Jornada:", fechas_unicas, format_func=lambda x: opciones_fecha[x], key="st_v_final_j")
        
        if ver_acumulado and str(seleccion_filtro) == '2026':
            st.caption("ℹ️ Putts, GIR y U&D calculados a partir del 08/07/2026")

        if ver_acumulado:
            temp_actual = str(seleccion_filtro)
            df_stats = df_raw[df_raw['t_limpia'] == temp_actual].copy()
        else:
            df_stats = df_raw[df_raw['fecha'] == seleccion_filtro].copy()
            temp_actual = df_stats['t_limpia'].iloc[0] if not df_stats.empty else "2026"

        if not df_stats.empty:
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

            lista_resultados = []
            
            if 'fecha' in df_stats.columns:
                df_stats['fecha_dt_parsed'] = pd.to_datetime(df_stats['fecha'], dayfirst=True, errors='coerce')
            
            fecha_corte_putts = pd.to_datetime('2026-07-08')
            es_vista_movil = st.sidebar.checkbox("📱 Vista reducida (Ocultar Scratch)", False)

            for i, jug in enumerate(TODOS):
                col_s = f's{i}'
                col_p = f'p{i}'
                col_mvp = f'p{i+1}_pts'
                
                df_stats[col_s] = pd.to_numeric(df_stats[col_s], errors='coerce').fillna(0)
                
                d_p = df_stats[df_stats[col_s] > 0].copy()

                if d_p.empty:
                    continue

                d_p[col_p] = pd.to_numeric(d_p[col_p], errors='coerce')
                
                if temp_actual == '2026' or '2026' in str(seleccion_filtro):
                    d_p_putts = d_p[(d_p['fecha_dt_parsed'] >= fecha_corte_putts) & (d_p[col_p].notna())].copy()
                else:
                    d_p_putts = d_p[d_p[col_p].notna()].copy()
                
                avg_putts = d_p_putts[col_p].mean() if not d_p_putts.empty else 0
                hoyos_putts = len(d_p_putts)
                
                if not d_p_putts.empty:
                    d_p_putts['par_h'] = d_p_putts['hoyo'].map(PAR_RIA_VIGO)
                    d_p_putts['shots_a_green'] = d_p_putts[col_s] - pd.to_numeric(d_p_putts[col_p], errors='coerce')
                    d_p_putts['is_gir'] = d_p_putts['shots_a_green'] <= (d_p_putts['par_h'] - 2)
                    d_p_putts['is_updown'] = (~d_p_putts['is_gir']) & (pd.to_numeric(d_p_putts[col_p], errors='coerce') == 1) & ((d_p_putts[col_s] - d_p_putts['par_h']) <= 0)
                    gir_cnt = int(d_p_putts['is_gir'].sum())
                    ud_cnt = int(d_p_putts['is_updown'].sum())
                else:
                    gir_cnt = 0
                    ud_cnt = 0
                
                d_p['par_h'] = d_p['hoyo'].map(PAR_RIA_VIGO)
                d_p['dif'] = d_p[col_s] - d_p['par_h']
                
                def cs(d):
                    if d <= -2: return 4
                    if d == -1: return 3
                    if d == 0:  return 2
                    if d == 1:  return 1
                    return 0
                
                scr = int(d_p['dif'].apply(cs).sum())
                pts_mvp_total = float(df_stats[col_mvp].sum())
                partidos_jugados = int(d_p['fecha'].nunique()) if 'fecha' in d_p.columns else 1

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
                    "hoyos_putts": hoyos_putts,
                    "partidos": partidos_jugados,
                    "gir_cnt": gir_cnt,      
                    "ud_cnt": ud_cnt
                })
            
            lista_resultados = sorted(lista_resultados, key=lambda x: x['scr'], reverse=True)

            if lista_resultados:
                stats_rows = []
                for res in lista_resultados:
                    def f_pct(v, th):
                        p = (v/th*100) if th > 0 else 0
                        return f"<b>{v}</b><br><span style='color:gray; font-size:0.8em;'>{p:.0f}%</span>"
                    
                    h = res['hoyos']
                    hp = res['hoyos_putts']
                    partidos = res['partidos']
                    
                    if ver_acumulado:
                        val_pm = res['pm'] / partidos
                        val_scr = res['scr'] / h if h > 0 else 0
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
                        "GIR": f_pct(res['gir_cnt'], hp),
                        "U&D": f_pct(res['ud_cnt'], hp),
                        "Eagle": f_pct(res['e'], h), "Birdie": f_pct(res['b'], h), 
                        "Par": f_pct(res['p'], h), "Bogey": f_pct(res['bog'], h), 
                        "D.Bogey": f_pct(res['db'], h), "3+ Bogey": f_pct(res['tb'], h)
                    })
                
                df_html_data = pd.DataFrame(stats_rows)
                
                if ver_acumulado:
                    df_html_data = df_html_data.rename(columns={"+/-": "+/- Med (partido)", "Scratch": "Scratch Med (hoyo)"})
                
                if es_vista_movil:
                    col_a_ocultar = "Scratch Med (hoyo)" if ver_acumulado else "Scratch"
                    if col_a_ocultar in df_html_data.columns:
                        df_html_data = df_html_data.drop(columns=[col_a_ocultar])

                df_html = df_html_data.to_html(escape=False, index=False)
                df_html = df_html.replace('<td>', '<td style="text-align: center; vertical-align: middle; padding: 10px;">')
                df_html = df_html.replace('<th>', '<th style="text-align: center; background-color: #f8f9fa;">')
                st.write(df_html, unsafe_allow_html=True)
                
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

                import urllib.parse
                
                w_icon = "📂" if ver_acumulado else "📅"
                tit_w = temp_actual if ver_acumulado else seleccion_filtro
                
                if ver_acumulado:
                    df_temp = df_raw[df_raw['t_limpia'] == temp_actual].copy()
                    total_a = st.session_state.get('marcador_acumulado_a', 3.5)
                    total_b = st.session_state.get('marcador_acumulado_b', 3.5)
                                            
                    año_txt = str(temp_actual).strip()
                    if total_a == 0.0 and total_b == 0.0:
                        if año_txt=="2026":
                            total_a = 3.5
                            total_b = 3.5
                
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
                    hp = res['hoyos_putts']
                    partidos = res['partidos']
                    
                    if ver_acumulado:
                        scr_promedio = res['scr'] / partidos
                        pm_promedio = res['pm'] / partidos
                        texto_scratch = f"{scr_promedio:.1f} med. scratch"
                        texto_pm = f"+{pm_promedio:.1f}" if pm_promedio > 0 else (f"{pm_promedio:.1f}" if pm_promedio < 0 else "E")
                    else:
                        texto_scratch = f"{res['scr']} pts scratch"
                        texto_pm = f"+{res['pm']}" if res['pm'] > 0 else (str(res['pm']) if res['pm'] < 0 else "E")
                    
                    def wf_base(v, base): 
                        return f"{v} ({v/base*100:.0f}%)" if base > 0 else f"{v} (0%)"
                    
                    txt_wa += f"👤 *{res['Jugador'].upper()}*\n"
                    txt_wa += f"🏆 *{texto_pm}* ({texto_scratch})\n"
                    txt_wa += f"🎯 *GIR:* {wf_base(res['gir_cnt'], hp)}\n"
                    txt_wa += f"⬆️ *U&D:* {wf_base(res['ud_cnt'], hp)}\n"
                    
                    s_l = ""
                    if not ver_acumulado:
                        birdie_o_mejor = int(res.get('e', 0)) + int(res.get('b', 0))
                        triple_o_peor = int(res.get('tb', 0))
                        
                        s_l += f"🐤 *Birdie o mejor:* {wf_base(birdie_o_mejor, h)}\n"
                        s_l += f"🅿️ *Par:* {wf_base(res['p'], h)}\n"
                        s_l += f"⚠️ *Bog:* {wf_base(res['bog'], h)}\n"
                        s_l += f"💀 *D.B:* {wf_base(res['db'], h)}\n"
                        s_l += f"💣 *💥 Triple o peor:* {wf_base(triple_o_peor, h)}\n"
                    else:
                        if res['e'] > 0:  s_l += f"🦅 Egl: {wf_base(res['e'], h)}\n"
                        if res['b'] > 0:  s_l += f"🐤 Bir: {wf_base(res['b'], h)}\n"
                        s_l += f"🅿️ *Par:* {wf_base(res['p'], h)}\n"
                        s_l += f"⚠️ *Bog:* {wf_base(res['bog'], h)}\n"
                        s_l += f"💀 *D.B:* {wf_base(res['db'], h)}\n"
                        if res['tb'] > 0: s_l += f"💣 +3B: {wf_base(res['tb'], h)}\n"
                        
                    txt_wa += s_l + "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                
                st.write("")
                st.link_button(
                    "📲 Enviar por WhatsApp", 
                    f"https://wa.me/?text={urllib.parse.quote(txt_wa)}", 
                    use_container_width=True
                )

                import plotly.express as px
                
                st.markdown("---")
                st.markdown("### 📈 Análisis Gráfico de Rendimiento")
                
                if lista_mvp:
                    df_graficos = pd.DataFrame(lista_mvp)
                    
                    df_dist = df_graficos[['Jugador', 'e', 'b', 'p', 'bog', 'db', 'tb']].copy()
                    df_dist.columns = ['Jugador', 'Eagle', 'Birdie', 'Par', 'Bogey', 'D.Bogey', '+3 Bogey']
                    df_long = df_dist.melt(id_vars='Jugador', var_name='Resultado', value_name='Cantidad')
                    
                    colores_golf = {
                        'Eagle': '#FFD700',
                        'Birdie': '#00BFFF',
                        'Par': '#28B463',
                        'Bogey': '#F39C12',
                        'D.Bogey': '#E74C3C',
                        '|+3 Bogey': '#7B241C'
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
                    fig1.update_layout(yaxis_title=None, xaxis_title=None) 
                    st.plotly_chart(fig1, use_container_width=True)
                
                import altair as alt
                st.markdown("---")
                st.markdown("### 📊 Análisis de Putts")
                
                if ver_acumulado:
                    temp_val = str(seleccion_filtro)
                    df_putts_source = df_raw[df_raw['t_limpia'] == temp_val].copy()
                else:
                    df_putts_source = df_raw[df_raw['fecha'] == seleccion_filtro].copy()
                
                fecha_corte = pd.Timestamp('2026-07-08')
                if 'fecha_dt' not in df_putts_source.columns:
                    df_putts_source['fecha_dt'] = pd.to_datetime(df_putts_source['fecha'], dayfirst=True)
                
                if '2026' in df_putts_source['t_limpia'].values:
                    df_putts_source = df_putts_source[
                        (df_putts_source['t_limpia'] != '2026') | (df_putts_source['fecha_dt'] >= fecha_corte)
                    ]
                
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
                
                    chart = alt.Chart(df_consistencia).mark_bar().encode(
                        x=alt.X('Jugador:N', sort=orden_jugadores, axis=alt.Axis(labelAngle=0, title=None)), 
                        y=alt.Y('Media Putts', scale=alt.Scale(domain=[0, 3])), 
                        color=alt.Color('Jugador:N', sort=orden_jugadores, legend=None) 
                    ).properties(height=300)
                    
                    text = chart.mark_text(align='center', baseline='bottom', dy=-5, color='black').encode(
                        text=alt.Text('Media Putts', format='.2f')
                    )
                    
                    st.altair_chart(chart + text, use_container_width=True)
                    
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

# ==========================================
# SECCIÓN: ADMIN
# ==========================================
elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Panel de Administración")
    
    df_admin = leer_datos()
    
    if df_admin.empty:
        st.info("No hay partidos registrados en la base de datos.")
    else:
        df_admin['id_clean'] = df_admin['partido_id'].astype(str).str.split('.').str[0]
        
        temps_admin = sorted(df_admin['temporada'].unique().tolist(), reverse=True)
        sel_temp_admin = st.selectbox("Filtrar por temporada:", temps_admin, key="sb_admin_temp")
        
        df_filtrado = df_admin[df_admin['temporada'].astype(str) == str(sel_temp_admin)]

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
            pts_a = float(row['resultado_a'])
            pts_b = float(row['resultado_b'])
            num_hoyos = int(row['hoyo'])
            
            if pts_a > pts_b:
                marcador = f"🏆 MANU/JOSE +{int(pts_a - pts_b)}"
            elif pts_b > pts_a:
                marcador = f"🏆 ROGE/LALO +{int(pts_b - pts_a)}"
            else:
                marcador = "🤝 Empate (AS)"

            titulo_expander = f"📅 {row['fecha']}  |  {marcador}  |  ({num_hoyos} hoyos)"
            
            with st.expander(titulo_expander):
                df_partido = df_admin[df_admin['id_clean'] == p_id].sort_values('hoyo')
                
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

                col_ed, col_bor, col_bor_h = st.columns(3)
                
                if col_ed.button("📝 Seguir/Editar", key=f"ed_{p_id}", use_container_width=True):
                    st.session_state.game = {
                        "id": p_id,
                        "fecha": row['fecha'],
                        "temporada": row['temporada'],
                        "h_sel": int(df_partido['hoyo'].max())
                    }
                    st.session_state.menu_seleccionado = "Nueva Partida"
                    st.rerun()

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

                with col_bor_h:
                    with st.popover("🗑️ Borrar Hoyo", use_container_width=True):
                        hoyos_disponibles = sorted(df_partido['hoyo'].astype(int).tolist())
                        hoyo_sel = st.selectbox("¿Qué hoyo borrar?", hoyos_disponibles, key=f"sel_h_{p_id}")
                        
                        if st.button(f"Confirmar Hoyo {hoyo_sel}", key=f"btn_del_h_{p_id}_{hoyo_sel}", type="primary", use_container_width=True):
                            if borrar_hoyo_especifico(p_id, hoyo_sel):
                                st.success(f"Hoyo {hoyo_sel} eliminado.")
                                st.cache_data.clear()
                                st.rerun()
