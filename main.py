
import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime

# --- INICIALIZACIÓN GLOBAL (Al principio de tu main.py) ---
if 'menu_seleccionado' not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

if 'radio_menu' not in st.session_state:
    st.session_state.radio_menu = "Inicio" # <--- ESTO EVITA EL ERROR

# Función para conectar sin usar st.connection
def cargar_datos_golf():
    # 1. Cargamos los secretos
    s = st.secrets["gsheets"]
    
    # 2. Construimos el diccionario de credenciales
    # El .replace garantiza que los saltos de línea sean correctos
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
    
    # 3. Autorizamos
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(credentials_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # 4. Abrimos y leemos
    sh = client.open_by_url(s["url"])
    worksheet = sh.worksheet("historial")
    return pd.DataFrame(worksheet.get_all_records())

# Lógica de la app
#st.title("⛳ CAÑITA BRAVA")

#try:
#    df = cargar_datos_golf()
#   st.success("¡Datos cargados!")
#    st.dataframe(df)
#except Exception as e:
#    st.error(f"Error de conexión: {e}")

#=================================



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


def ejecutar_guardado_automatico():
    g = st.session_state.game
    h = int(g['h_sel'])
    # Recuperamos los valores de los inputs usando las keys dinámicas
    s = [
        int(st.session_state[f"s1_h{h}_r{st.session_state.get('refresco_id',0)}"]),
        int(st.session_state[f"s2_h{h}_r{st.session_state.get('refresco_id',0)}"]), 
        int(st.session_state[f"s3_h{h}_r{st.session_state.get('refresco_id',0)}"]),
        int(st.session_state[f"s4_h{h}_r{st.session_state.get('refresco_id',0)}"])
    ]
    pa, pb, mi = calcular_puntos_hoyo(s, h)
    g['logs'][str(h)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
    
    anio_int = int(datetime.strptime(g['fecha'], "%d/%m/%Y").year)
    p_id = str(g['id'])
    
    nueva_fila = {
        "id": f"{p_id}_H{h}", "partido_id": p_id, "hoyo": h, "fecha": g['fecha'], 
        "temporada": anio_int, "resultado_a": pa, "resultado_b": pb, 
        "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4'], 
        "s0": s[0], "s1": s[1], "s2": s[2], "s3": s[3]
    }
    
    df_actual = leer_datos()
    # Eliminar si ya existe para sobreescribir
    df_actual = df_actual[~((df_actual['partido_id'] == p_id) & (df_actual['hoyo'] == h))]
    df_final = pd.concat([df_actual, pd.DataFrame([nueva_fila])], ignore_index=True)
    
    conn.update(worksheet="historial", data=df_final)
    st.cache_data.clear()

# --- 3. NAVEGACIÓN ---
menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Estadísticas", "Admin"], 
                       index=["Inicio", "Jugar/Editar", "Estadísticas", "Admin"].index(st.session_state.menu_seleccionado),
                       key="radio_menu", on_change=cambiar_menu)

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
# SECCIÓN: JUGAR / EDITAR (Modo Match Play)
# ==========================================
elif st.session_state.menu_seleccionado == "Jugar/Editar":
    st.title("⛳ Jugar / Editar Hoyo")
    
    # --- 1. INICIALIZACIÓN DE ESTADO ---
    if 'hoyo_actual' not in st.session_state:
        st.session_state.hoyo_actual = 1
    if 'hoyo_guardado' not in st.session_state:
        st.session_state.hoyo_guardado = False
    if 'fecha_partida' not in st.session_state:
        st.session_state.fecha_partida = datetime.now()

    # --- 2. SELECTOR DE FECHA Y NAVEGACIÓN ---
    fecha_input = st.date_input(
        "Fecha de la partida:", 
        value=st.session_state.fecha_partida,
        format="DD/MM/YYYY"
    )
    # Guardamos en el estado para que no se resetee al hoyo siguiente
    st.session_state.fecha_partida = fecha_input
    fecha_str = fecha_input.strftime("%d/%m/%Y")
    
    h_idx = st.session_state.hoyo_actual
    par_hoyo = PAR_RIA_VIGO.get(h_idx, 4)

    # --- 3. CARGA DE DATOS Y LÓGICA DE MARCADOR ---
    df_actual = leer_datos()
    
    # Inicialización de seguridad (Evita errores de "variable not defined")
    m_e1, m_e2 = 0, 0 
    golpes_a_mostrar = {0: par_hoyo, 1: par_hoyo, 2: par_hoyo, 3: par_hoyo}
    
    if not df_actual.empty:
        # Formatos de búsqueda (Europa e ISO)
        f_iso = fecha_input.strftime("%Y-%m-%d")
        f_eur = fecha_input.strftime("%d/%m/%Y")

        # Filtramos todas las filas de ese día
        df_f = df_actual[
            (df_actual['fecha'].astype(str) == f_eur) | 
            (df_actual['fecha'].astype(str) == f_iso)
        ]
        
        if not df_f.empty:
            # Calcular marcador acumulado del Match
            for _, row in df_f.iterrows():
                try:
                    p_h = int(PAR_RIA_VIGO.get(int(row['hoyo']), 4))
                    p1, p2 = calcular_puntos_hoyo(
                        int(row['s0']), int(row['s1']), 
                        int(row['s2']), int(row['s3']), p_h
                    )
                    m_e1 += p1
                    m_e2 += p2
                except:
                    continue

            # Buscar si el hoyo actual ya tiene golpes grabados
            busqueda = df_f[df_f['hoyo'].astype(str).str.strip() == str(h_idx)]
            if not busqueda.empty:
                for i in range(4):
                    try:
                        v = int(float(busqueda.iloc[0][f's{i}']))
                        if v > 0: golpes_a_mostrar[i] = v
                    except:
                        continue

    # --- 4. DISEÑO DEL MARCADOR SUPERIOR ---
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 2px solid #2e7d32; text-align: center;">
        <div style="display: flex; justify-content: space-around; align-items: center;">
            <div style="flex: 1;">
                <p style="margin: 0; font-weight: bold; color: #333;">MANU & JOSE</p>
                <h1 style="margin: 0; font-size: 3em; color: #2e7d32;">{m_e1}</h1>
            </div>
            <div style="background-color: #555; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold;">VS</div>
            <div style="flex: 1;">
                <p style="margin: 0; font-weight: bold; color: #333;">ROGE & LALO</p>
                <h1 style="margin: 0; font-size: 3em; color: #1976d2;">{m_e2}</h1>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- 5. BOTONES DE NAVEGACIÓN ENTRE HOYOS ---
    st.write("") # Espacio
    col_nav1, col_h, col_nav2 = st.columns([1, 2, 1])
    with col_nav1:
        if st.button("⬅️ ANT.") and h_idx > 1:
            st.session_state.hoyo_actual -= 1
            st.session_state.hoyo_guardado = False
            st.rerun()
    with col_h:
        st.markdown(f"<h3 style='text-align: center; margin: 0;'>Hoyo {h_idx} (Par {par_hoyo})</h3>", unsafe_allow_html=True)
    with col_nav2:
        if st.button("SIG. ➡️") and h_idx < 18:
            st.session_state.hoyo_actual += 1
            st.session_state.hoyo_guardado = False
            st.rerun()

    st.divider()

    # --- 6. INPUTS DE GOLPES ---
    cols = st.columns(2)
    # s0:Manu, s1:Roge, s2:Jose, s3:Lalo
    config = [
        {"n": "MANU", "id": 0}, {"n": "ROGE", "id": 1},
        {"n": "JOSE", "id": 2}, {"n": "LALO", "id": 3}
    ]
    
    in_golpes = {}
    for i, j in enumerate(config):
        with cols[i % 2]:
            val_defecto = golpes_a_mostrar[j["id"]]
            v = st.number_input(j["n"], 1, 15, value=val_defecto, key=f"g_{j['n']}_{h_idx}")
            in_golpes[j["id"]] = v

    # Cálculo en tiempo real del hoyo actual
    ph_e1, ph_e2 = calcular_puntos_hoyo(in_golpes[0], in_golpes[1], in_golpes[2], in_golpes[3], par_hoyo)
    
    st.markdown(f"""
    <div style="text-align: center; background: #fff; border: 1px solid #ddd; padding: 10px; border-radius: 10px; margin-top: 10px;">
        <small>Puntos hoyo {h_idx}:</small><br>
        <b style="color: #2e7d32;">M&J: {ph_e1}</b> | <b style="color: #1976d2;">R&L: {ph_e2}</b>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- 7. BOTÓN DE GUARDADO ---
    if st.session_state.hoyo_guardado:
        st.button("✅ HOYO GUARDADO", use_container_width=True, disabled=True)
    else:
        if st.button("💾 GUARDAR HOYO", use_container_width=True, type="primary"):
            # IMPORTANTE: Usamos fecha_str (la del selector)
            fila = [fecha_str, h_idx, in_golpes[0], in_golpes[1], in_golpes[2], in_golpes[3]]
            try:
                actualizar_o_insertar_hoyo(fila) 
                st.session_state.hoyo_guardado = True
                st.success(f"Hoyo {h_idx} guardado correctamente")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ==========================================
# SECCIÓN: ESTADISTICAS
# ==========================================
elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas y Clasificación")
    df_raw = leer_datos()
    
    if not df_raw.empty:
        # --- SELECTORES ---
        col1, col2 = st.columns(2)
        with col1:
            fechas = sorted(df_raw['fecha'].unique().tolist(), reverse=True)
            jornada_sel = st.selectbox("Seleccionar Jornada:", fechas)
        with col2:
            ver_acumulado = st.toggle("📂 Ver Acumulado de la Temporada", value=False)

        # --- FILTRADO DE DATOS ---
        if ver_acumulado:
            df_stats = df_raw.copy()
            titulo_seccion = "Acumulado Total Temporada"
        else:
            df_stats = df_raw[df_raw['fecha'] == jornada_sel].copy()
            titulo_seccion = f"Jornada: {jornada_sel}"

        df_stats['hoyo'] = pd.to_numeric(df_stats['hoyo'], errors='coerce')
        
        lista_resultados = []
        for i, jug in enumerate(TODOS):
            col_s = f's{i}'
            df_stats[col_s] = pd.to_numeric(df_stats[col_s], errors='coerce')
            
            # Solo hoyos con golpes > 0
            d_p = df_stats[df_stats[col_s] > 0][['hoyo', col_s]].copy()
            if d_p.empty: continue

            d_p['par_h'] = d_p['hoyo'].map(PAR_RIA_VIGO)
            d_p['dif'] = d_p[col_s] - d_p['par_h']
            
            # Puntos Scratch (Stableford Bruto)
            def calcular_puntos_scratch(dif):
                if dif <= -2: return 4
                if dif == -1: return 3
                if dif == 0:  return 2
                if dif == 1:  return 1
                return 0
            
            scratch_total = int(d_p['dif'].apply(calcular_puntos_scratch).sum())
            
            # Tu fórmula: (Hoyos Jugados * 2) - Puntos Scratch
            n_hoyos_total = len(d_p)
            plus_minus = (n_hoyos_total * 2) - scratch_total

            # Conteos
            e = int((d_p['dif'] <= -2).sum())
            b = int((d_p['dif'] == -1).sum())
            p = int((d_p['dif'] == 0).sum())
            bog = int((d_p['dif'] == 1).sum())
            db = int((d_p['dif'] == 2).sum())
            tb = int((d_p['dif'] >= 3).sum())

            lista_resultados.append({
                "Jugador": jug, "plus_minus": plus_minus, "scratch": scratch_total,
                "e": e, "b": b, "p": p, "bog": bog, "db": db, "tb": tb,
                "hoyos": n_hoyos_total
            })

        # Ordenar por Scratch descendente
        lista_resultados = sorted(lista_resultados, key=lambda x: x['scratch'], reverse=True)

        # --- MENSAJE WHATSAPP ---
        whatsapp_text = f"🍺 *CAÑITA BRAVA* 🍺\n📊 *{titulo_seccion.upper()}*\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"

        stats_rows = []
        for res in lista_resultados:
            pm_txt = f"+{res['plus_minus']}" if res['plus_minus'] > 0 else (str(res['plus_minus']) if res['plus_minus'] < 0 else "E")
            whatsapp_text += f"👤 *{res['Jugador'].upper()}*\n"
            whatsapp_text += f"⛳ Hoyos: {res['hoyos']} | 🏆 Res: *{pm_txt}* ({res['scratch']} pts)\n"
            whatsapp_text += f"🦅 Egl: {res['e']} | 🐤 Bir: {res['b']} | 🅿️ Par: {res['p']}\n"
            whatsapp_text += f"⚠️ Bog: {res['bog']} | 💀 D.Bog: {res['db']} | 💣 +T.Bog: {res['tb']}\n"
            whatsapp_text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"

            def fmt(v, total_h):
                pct = (v / total_h * 100) if total_h > 0 else 0
                return f"<b>{v}</b><br><span style='color:gray; font-size:0.8em;'>{pct:.1f}%</span>"

            stats_rows.append({
                "Jugador": res['Jugador'],
                "Hoyos": res['hoyos'],
                "+/-": f"<b style='color:red;'>+{res['plus_minus']}</b>" if res['plus_minus'] > 0 else (f"<b>{res['plus_minus']}</b>" if res['plus_minus'] < 0 else "<b>E</b>"),
                "Scratch": f"<b>{res['scratch']}</b>",
                "Eagle": fmt(res['e'], res['hoyos']), 
                "Birdie": fmt(res['b'], res['hoyos']), 
                "Par": fmt(res['p'], res['hoyos']),
                "Bogey": fmt(res['bog'], res['hoyos']), 
                "D.Bogey": fmt(res['db'], res['hoyos']), 
                "3+ Bogey": fmt(res['tb'], res['hoyos'])
            })

        # --- RENDERIZADO ---
        st.subheader(f"📈 {titulo_seccion}")
        st.markdown("<style>table {width:100%; text-align:center;} th {background:#f8f9fa;} td {padding:8px; border-bottom:1px solid #eee;}</style>", unsafe_allow_html=True)
        st.write(pd.DataFrame(stats_rows).to_html(escape=False, index=False), unsafe_allow_html=True)

        import urllib.parse
        st.write("")
        btn_label = "📲 Enviar ACUMULADO por WhatsApp" if ver_acumulado else "📲 Enviar JORNADA por WhatsApp"
        st.link_button(btn_label, f"https://wa.me/?text={urllib.parse.quote(whatsapp_text)}", use_container_width=True)

    else:
        st.info("No hay datos cargados.")

# ==========================================
# SECCIÓN: ADMIN
# ==========================================

elif st.session_state.menu_seleccionado == "Administración":
    st.title("⚙️ Administración de Partidas")
    st.info("Desde aquí puedes ver un resumen de las jornadas y eliminar datos si es necesario.")

    df = leer_datos()

    if df.empty:
        st.warning("No hay datos registrados en la base de datos.")
    else:
        # 1. PREPARACIÓN DE DATOS
        # Aseguramos que la columna fecha sea tratada correctamente
        df['fecha_dt'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
        
        # Agrupamos por fecha (usando la fecha original como string para no perder el formato)
        # pero ordenamos por la fecha real (dt)
        partidos = df.sort_values(by='fecha_dt', ascending=False).groupby('fecha', sort=False)

        st.subheader(f"Total jornadas encontradas: {len(partidos)}")

        # 2. RENDERIZADO DE PARTIDOS
        for fecha_str, datos_jornada in partidos:
            # Limpiamos la fecha para que siempre salga dd/mm/aaaa
            # Si viene como "2026-05-05 00:00:00", nos quedamos con los primeros 10 caracteres
            fecha_limpia = str(fecha_str).split(" ")[0]
            try:
                # Intentamos darle formato dd/mm/aaaa
                fecha_formateada = pd.to_datetime(fecha_limpia).strftime("%d/%m/%Y")
            except:
                fecha_formateada = fecha_limpia

            # Contamos cuántos hoyos únicos se han jugado ese día
            num_hoyos = len(datos_jornada['hoyo'].unique())
            
            # Calculamos puntos totales de la jornada para el título
            puntos_e1 = 0
            puntos_e2 = 0
            for _, row in datos_jornada.iterrows():
                try:
                    p_h = int(PAR_RIA_VIGO.get(int(row['hoyo']), 4))
                    p1, p2 = calcular_puntos_hoyo(int(row['s0']), int(row['s1']), int(row['s2']), int(row['s3']), p_h)
                    puntos_e1 += p1
                    puntos_e2 += p2
                except:
                    continue

            # Creamos el desplegable (Expander)
            with st.expander(f"📅 {fecha_formateada} — ({num_hoyos} hoyos jugados) — Resultado: {puntos_e1} vs {puntos_e2}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write("**Detalle de hoyos grabados:**")
                    # Mostramos una tabla resumida de la jornada
                    resumen_view = datos_jornada[['hoyo', 's0', 's1', 's2', 's3']].sort_values(by='hoyo')
                    resumen_view.columns = ['Hoyo', 'Manu', 'Roge', 'Jose', 'Lalo']
                    st.dataframe(resumen_view, hide_index=True, use_container_width=True)

                with col2:
                    st.write("**Acciones:**")
                    # Botón para borrar la jornada completa
                    if st.button(f"🗑️ Borrar Jornada", key=f"del_{fecha_str}"):
                        # Aquí llamarías a una función para borrar filas por fecha
                        # eliminar_partido_por_fecha(fecha_str)
                        st.error("Función de borrado no conectada por seguridad")
                        
                # Si quieres ver quién ganó cada hoyo en el administrador
                st.caption("Puntos calculados según sistema Match Play + Bonus Birdie.")

    # Botón para refrescar datos
    if st.button("🔄 Actualizar Datos"):
        st.rerun()
