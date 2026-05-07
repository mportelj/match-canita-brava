import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# CSS para el selector de hoyo (Grande y Negrita)
st.markdown("""
    <style>
    div[data-baseweb="select"] > div {
        font-size: 1.3rem !important;
        font-weight: bold !important;
    }
    label p { font-weight: bold !important; font-size: 1.1rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- 1. DEFINIR LA CONEXIÓN (Arregla el error 'conn' is not defined) ---
# Asegúrate de que esta línea esté al principio para que 'conn' sea global
conn = st.connection("gsheets", type=GSheetsConnection)



def calcular_puntos_jornada(par, lista_golpes):
    pts_finales = [0.0, 0.0, 0.0, 0.0]
    for i in range(len(lista_golpes)):
        for j in range(len(lista_golpes)):
            if i != j:
                if lista_golpes[i] < lista_golpes[j]: pts_finales[i] += 1.0
                elif lista_golpes[i] == lista_golpes[j]: pts_finales[i] += 0.5
    # Bonus calidad
    for i, g in enumerate(lista_golpes):
        diff = g - par
        if diff <= -2: pts_finales[i] += 1.0
        elif diff == -1: pts_finales[i] += 0.5
    return pts_finales

def actualizar_hoja_google(df):
    # Usamos la conexión que definiste (conn)
    try:
        conn.update(data=df)
        return True
    except Exception as e:
        st.error(f"Error al subir: {e}")
        return False
        
def guardar_hoyo_en_nube(hoyo, golpes_jugadores, puntos_reales):
    try:
        st.cache_data.clear()
        df_nube = leer_datos() # Lee lo que hay ahora en la nube
        
        # Normalizar nombres de columnas a MAYÚSCULAS
        df_nube.columns = [str(c).strip().upper() for c in df_nube.columns]
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        # Preparamos los datos del hoyo
        nueva_fila = {
            'FECHA': fecha_hoy,
            'HOYO': int(hoyo),
            'PAR': int(PAR_RIA_VIGO[hoyo])
        }
        
        for i in range(len(TODOS)):
            nueva_fila[f'S{i}'] = int(golpes_jugadores[i])
            # AQUÍ ESTÁ LA CLAVE: Aseguramos que se graben en P1_PTS, P2_PTS...
            nueva_fila[f'P{i+1}_PTS'] = float(puntos_reales[i])
            
        # Lógica para no duplicar filas del mismo hoyo
        mascara = (df_nube['FECHA'] == fecha_hoy) & (df_nube['HOYO'] == hoyo)
        
        if mascara.any():
            idx = df_nube.index[mascara][0]
            for col, val in nueva_fila.items():
                df_nube.at[idx, col] = val
        else:
            df_nube = pd.concat([df_nube, pd.DataFrame([nueva_fila])], ignore_index=True)
        
        # SUBIDA FINAL
        return actualizar_hoja_google(df_nube)
    except Exception as e:
        st.error(f"Error al procesar datos: {e}")
        return False

# Datos de campo y jugadores
PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,4])}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
EQUIPO_A_NOMBRES = f"{TODOS[0]} & {TODOS[1]}"
EQUIPO_B_NOMBRES = f"{TODOS[2]} & {TODOS[3]}"
COLOR_A, COLOR_B = "#2e7d32", "#c62828"

if "menu_seleccionado" not in st.session_state: st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu(): st.session_state.menu_seleccionado = st.session_state.radio_menu

menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Estadísticas", "Admin"], 
                        index=["Inicio", "Jugar/Editar", "Estadísticas", "Admin"].index(st.session_state.menu_seleccionado),
                        key="radio_menu", on_change=cambiar_menu)

# --- 2. FUNCIONES DE DATOS ---
def leer_datos():
    # Leemos la hoja
    df = conn.read()
    # ESTO ES CRÍTICO: Limpia espacios y pasa todo a MAYÚSCULAS
    df.columns = [str(c).strip().upper() for c in df.columns]
    # Si hay filas vacías al principio, las quitamos
    df = df.dropna(how='all', axis=0)
    return df
    
def calcular_puntos_jornada(par, lista_golpes):
    """
    Calcula los puntos que se grabarán en las columnas P1_PTS... P4_PTS
    Basado en enfrentamientos entre jugadores y bonus por calidad.
    """
    pts_finales = [0.0, 0.0, 0.0, 0.0]
    
    # 1. Puntos por enfrentamiento (Oponentes)
    # Cada jugador se compara con los otros 3
    for i in range(len(lista_golpes)):
        for j in range(len(lista_golpes)):
            if i != j:
                if lista_golpes[i] < lista_golpes[j]:
                    pts_finales[i] += 1.0  # Gana el hoyo al oponente
                elif lista_golpes[i] == lista_golpes[j]:
                    pts_finales[i] += 0.5  # Empata el hoyo

    # 2. Bonus de Calidad (Opcional, según vuestras reglas)
    # Ejemplo: Birdie +0.5, Eagle +1.0
    for i, g in enumerate(lista_golpes):
        diff = g - par
        if diff <= -2: 
            pts_finales[i] += 1.0  # Bonus por Eagle o mejor
        elif diff == -1: 
            pts_finales[i] += 0.5  # Bonus por Birdie

    return pts_finales

def calcular_puntos_hoyo(scores, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    v = [int(s) for s in scores]
    ba, wa, bb, wb = min(v[0], v[1]), max(v[0], v[1]), min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    for i, s in enumerate(v):
        p_bonus = 2.0 if s <= par - 2 else (1.0 if s == par - 1 else 0)
        if i < 2: pa += p_bonus 
        else: pb += p_bonus
    mvp = {f"p{i+1}": sum(0.5 for j in range(4) if i!=j and v[i]<v[j]) + (3.0 if v[i]<=par-2 else 1.5 if v[i]==par-1 else 0.5 if v[i]==par else 0) for i in range(4)}
    return pa, pb, mvp

def calcular_puntos_jornada(par, lista_golpes):
    pts_finales = [0.0, 0.0, 0.0, 0.0]
    for i in range(len(lista_golpes)):
        for j in range(len(lista_golpes)):
            if i != j:
                if lista_golpes[i] < lista_golpes[j]: pts_finales[i] += 1.0
                elif lista_golpes[i] == lista_golpes[j]: pts_finales[i] += 0.5
    # Bonus calidad
    for i, g in enumerate(lista_golpes):
        diff = g - par
        if diff <= -2: pts_finales[i] += 1.0
        elif diff == -1: pts_finales[i] += 0.5
    return pts_finales

def actualizar_hoja_google(df):
    # Usamos la conexión que definiste (conn)
    try:
        conn.update(data=df)
        return True
    except Exception as e:
        st.error(f"Error al subir: {e}")
        return False
        
def ejecutar_guardado_automatico():
    g = st.session_state.game
    h = int(g['h_sel'])
    s = [int(st.session_state[f"s1_h{h}_{g['id']}"]), int(st.session_state[f"s2_h{h}_{g['id']}"]),
         int(st.session_state[f"s3_h{h}_{g['id']}"]), int(st.session_state[f"s4_h{h}_{g['id']}"])]
    pa, pb, mi = calcular_puntos_hoyo(s, h)
    
    anio_int = int(datetime.strptime(g['fecha'], "%d/%m/%Y").year)
    p_id = str(g['id'])
    nueva_fila = {"id": f"{p_id}_H{h}", "partido_id": p_id, "hoyo": h, "fecha": g['fecha'], "temporada": anio_int, 
                  "resultado_a": pa, "resultado_b": pb, **{f"p{i+1}_pts": mi[f"p{i+1}"] for i in range(4)},
                  "s0": s[0], "s1": s[1], "s2": s[2], "s3": s[3]}
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = leer_datos()
    df = pd.concat([df[~((df['partido_id']==p_id) & (df['hoyo']==h))], pd.DataFrame([nueva_fila])], ignore_index=True)
    conn.update(worksheet="historial", data=df)
    st.cache_data.clear()
    
    st.session_state.game['logs'][str(h)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
    if h < 18: st.session_state.game['h_sel'] = h + 1

# --- 3. PANTALLAS ---
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    temps = sorted(df['temporada'].unique().tolist(), reverse=True) if not df.empty else [2026]
    sel_temp = st.selectbox("Temporada:", temps, format_func=lambda x: str(int(x)))
    
    pa_t, pb_t = 3.5, 3.5 # Puntuación inicial histórica
    if not df.empty:
        df_t = df[df['temporada'] == int(sel_temp)]
        for _, r in df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'}).iterrows():
            if r['resultado_a'] > r['resultado_b']: pa_t += 1
            elif r['resultado_b'] > r['resultado_a']: pb_t += 1
            else: pa_t += 0.5; pb_t += 0.5
            
    st.markdown(f"""<div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;">
        <h3>MATCH {int(sel_temp)}</h3><div style="display:flex;justify-content:space-around;">
        <div><h2 style="color:{COLOR_A};">{EQUIPO_A_NOMBRES}</h2><h1>{pa_t:g}</h1></div>
        <div style="font-size:2em; align-self:center;">VS</div>
        <div><h2 style="color:{COLOR_B};">{EQUIPO_B_NOMBRES}</h2><h1>{pb_t:g}</h1></div></div></div>""", unsafe_allow_html=True)


            
elif st.session_state.menu_seleccionado == "Jugar/Editar":
    st.title("🏌️ JUGAR / EDITAR PARTIDO")

    # --- 1. GESTIÓN DE SINCRONIZACIÓN ---
    if "ultima_sincro" not in st.session_state:
        st.session_state.ultima_sincro = "No sincronizado"
    
    col_info, col_btn = st.columns([3, 1])
    col_info.info(f"☁️ **Sincronización:** {st.session_state.ultima_sincro}")
    
    if col_btn.button("🔄 REFRESCAR NUBE", use_container_width=True):
        st.cache_data.clear()
        st.session_state.ultima_sincro = datetime.now().strftime("%H:%M:%S")
        st.rerun()

    st.write("---")

    # --- 2. SELECCIÓN DE HOYO Y LECTURA DE DATOS ---
    hoyo_sel = st.number_input("Selecciona el hoyo:", min_value=1, max_value=18, step=1)
    par_hoyo = int(PAR_RIA_VIGO[hoyo_sel])
    
    # Leemos datos y limpiamos columnas inmediatamente para evitar KeyError
    df_actual = leer_datos() 
    df_actual.columns = [str(c).strip().upper() for c in df_actual.columns]
    
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    # Buscamos si ya existen datos para este hoyo hoy
    datos_existentes = pd.DataFrame()
    if 'FECHA' in df_actual.columns and 'HOYO' in df_actual.columns:
        df_actual['HOYO'] = pd.to_numeric(df_actual['HOYO'], errors='coerce')
        datos_existentes = df_actual[(df_actual['FECHA'] == fecha_hoy) & (df_actual['HOYO'] == hoyo_sel)]

    # --- 3. INTERFAZ DE ENTRADA DE GOLPES ---
    st.subheader(f"⛳ Hoyo {hoyo_sel} (Par {par_hoyo})")
    cols = st.columns(4)
    golpes_finales = []

    # Mapeo de columnas de golpes según tu Excel: S0, S1, S2, S3
    columnas_golpes = ['S0', 'S1', 'S2', 'S3']

    for i, jug in enumerate(TODOS):
        # Valor por defecto: lo que haya en la nube, si no, el Par
        val_default = par_hoyo
        if not datos_existentes.empty:
            col_nombre = columnas_golpes[i]
            if col_nombre in datos_existentes.columns:
                val_nube = datos_existentes.iloc[0][col_nombre]
                if pd.notna(val_nube):
                    val_default = int(val_nube)
            
        g = cols[i].number_input(f"{jug}", min_value=1, max_value=15, value=val_default, key=f"edit_h{hoyo_sel}_j{i}")
        golpes_finales.append(g)

    st.write("---")

    # --- 4. BOTÓN DE GUARDADO SEGURO ---
    if st.button("💾 GUARDAR CAMBIOS Y SUBIR", type="primary", use_container_width=True):
        with st.spinner("Subiendo datos a Google Sheets..."):
            try:
                # A. Calculamos puntos con tu función
                puntos_reales = calcular_puntos_jornada(par_hoyo, golpes_finales)
                
                # B. Preparamos el diccionario con los nombres EXACTOS de tu Excel
                datos_hoyo = {
                    'FECHA': fecha_hoy,
                    'HOYO': int(hoyo_sel),
                    'PAR': int(par_hoyo),
                    'TEMPORADA': "2024",
                    'PARTIDO_ID': fecha_hoy.replace("-", ""),
                    # Golpes (S0-S3)
                    'S0': int(golpes_finales[0]),
                    'S1': int(golpes_finales[1]),
                    'S2': int(golpes_finales[2]),
                    'S3': int(golpes_finales[3]),
                    # Puntos (P1_PTS-P4_PTS)
                    'P1_PTS': float(puntos_reales[0]),
                    'P2_PTS': float(puntos_reales[1]),
                    'P3_PTS': float(puntos_reales[2]),
                    'P4_PTS': float(puntos_reales[3])
                }
                
                # C. Actualizamos el DataFrame local
                mascara = (df_actual['FECHA'] == fecha_hoy) & (df_actual['HOYO'] == int(hoyo_sel))
                
                if mascara.any():
                    idx = df_actual.index[mascara][0]
                    for col, val in datos_hoyo.items():
                        if col in df_actual.columns:
                            df_actual.at[idx, col] = val
                else:
                    df_actual = pd.concat([df_actual, pd.DataFrame([datos_hoyo])], ignore_index=True)
                
                # D. Subida a la nube
                conn.update(data=df_actual)
                
                st.success(f"✅ Hoyo {hoyo_sel} sincronizado con éxito.")
                st.session_state.ultima_sincro = datetime.now().strftime("%H:%M:%S")
                st.cache_data.clear()
                st.balloons()
                
            except Exception as e:
                st.error(f"Error al guardar: {e}")

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 ESTADÍSTICAS")
    
    df_historico = leer_datos()
    
    if df_historico is not None and not df_historico.empty:
        # Normalizamos nombres de columnas a mayúsculas para evitar errores
        df_historico.columns = [str(c).strip().upper() for c in df_historico.columns]
        col_fecha = 'FECHA' if 'FECHA' in df_historico.columns else df_historico.columns[0]
        
        if "vista_stats" not in st.session_state:
            st.session_state.vista_stats = "Resumen"
        if "modo_historia" not in st.session_state:
            st.session_state.modo_historia = "Jornada"

        # 1. NAVEGACIÓN
        col_nav1, col_nav2, col_nav3 = st.columns(3)
        if col_nav1.button("📋 RESUMEN", disabled=(st.session_state.vista_stats == "Resumen"), use_container_width=True):
            st.session_state.vista_stats = "Resumen"
            st.rerun()
        if col_nav2.button("🌟 MVP Jornada", disabled=(st.session_state.vista_stats == "MVP" and st.session_state.modo_historia == "Jornada"), use_container_width=True):
            st.session_state.vista_stats = "MVP"
            st.session_state.modo_historia = "Jornada"
            st.rerun()
        if col_nav3.button("👑 MVP Acumulado", disabled=(st.session_state.vista_stats == "MVP" and st.session_state.modo_historia == "Acumulado"), use_container_width=True):
            st.session_state.vista_stats = "MVP"
            st.session_state.modo_historia = "Acumulado"
            st.rerun()

        st.write("---")

        # 2. SELECCIÓN DE DATOS
        fechas_disp = sorted(df_historico[col_fecha].unique().tolist(), reverse=True)
        if st.session_state.modo_historia == "Jornada":
            f_sel = st.selectbox("Seleccionar Partido:", fechas_disp)
            df_final = df_historico[df_historico[col_fecha] == f_sel]
            subtitulo = f"Jornada: {f_sel}"
        else:
            df_final = df_historico
            subtitulo = "Histórico Acumulado"

        # 3. PROCESAMIENTO (Puntos reales de P1_PTS, P2_PTS...)
        stats = {jug: {"Puntos": 0, "H": 0, "EAG": 0, "BIR": 0, "PAR": 0, "BOG": 0, "DB": 0, "TB": 0} for jug in TODOS}
        
        for _, fila in df_final.iterrows():
            try:
                h_num = int(fila.get('HOYO'))
                p_hoyo = int(PAR_RIA_VIGO[h_num])
                
                for i, jug in enumerate(TODOS):
                    # 1. Sumar Puntos Reales (P1_PTS, P2_PTS, P3_PTS, P4_PTS)
                    # i+1 porque tus columnas empiezan en 1
                    col_pts = f"P{i+1}_PTS" 
                    val_p = fila.get(col_pts)
                    if pd.notna(val_p):
                        stats[jug]["Puntos"] += float(val_p)
                    
                    # 2. Contar Calidad de Golpes (S0, S1, S2, S3)
                    val_g = fila.get(f'S{i}')
                    if pd.notna(val_g) and str(val_g).strip() != "":
                        g_hoyo = int(float(val_g))
                        diff = g_hoyo - p_hoyo
                        stats[jug]["H"] += 1
                        if diff <= -2: stats[jug]["EAG"] += 1
                        elif diff == -1: stats[jug]["BIR"] += 1
                        elif diff == 0: stats[jug]["PAR"] += 1
                        elif diff == 1: stats[jug]["BOG"] += 1
                        elif diff == 2: stats[jug]["DB"] += 1
                        else: stats[jug]["TB"] += 1
            except: continue

        # 4. TABLA Y ORDENACIÓN (Por Puntos DESC)
        tabla_raw = []
        for jug in TODOS:
            d = stats[jug]
            if d["H"] == 0: continue
            tabla_raw.append({
                "Jugador": jug, "Puntos": d["Puntos"], "H": d["H"],
                "EAG": d["EAG"], "BIR": d["BIR"], "PAR": d["PAR"], 
                "BOG": d["BOG"], "DB": d["DB"], "TB": d["TB"]
            })

        df_ranking = pd.DataFrame(tabla_raw).sort_values(by="Puntos", ascending=False)

        # 5. MENSAJE WHATSAPP
        import urllib.parse
        total_h = int(df_ranking['H'].max()) if not df_ranking.empty else 0
        txt_wa = f"🍺 *CAÑITA BRAVA* ⛳\n📍 _{subtitulo}_\n⛳ *Hoyos: {total_h}*\n"
        txt_wa += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"

        for _, r in df_ranking.iterrows():
            pct = lambda v: f"{(v/r['H'])*100:.1f}%"
            txt_wa += f"👤 *{r['Jugador'].upper()}*\n"
            txt_wa += f"🏆 *PUNTOS: {r['Puntos']:.1f}*\n"
            txt_wa += f"🦅 Egl: {r['EAG']} ({pct(r['EAG'])}) | 🐥 Bir: {r['BIR']} ({pct(r['BIR'])})\n"
            txt_wa += f"🛡️ Par: {r['PAR']} ({pct(r['PAR'])}) | ⚠️ Bog: {r['BOG']} ({pct(r['BOG'])})\n"
            txt_wa += f"💀 D.Bog: {r['DB']} ({pct(r['DB'])}) | 💣 +T.Bog: {r['TB']} ({pct(r['TB'])})\n"
            txt_wa += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"

        # 6. RENDER WEB
        st.markdown("<style>th, td { text-align: center !important; vertical-align: middle !important; }</style>", unsafe_allow_html=True)
        
        if st.session_state.vista_stats == "Resumen":
            st.subheader(f"📋 RESUMEN - {subtitulo}")
            df_web = df_ranking.copy()
            for cat in ["EAG", "BIR", "PAR", "BOG", "DB", "TB"]:
                df_web[cat] = df_web.apply(lambda x: f"{x[cat]}<br><small style='color:gray;'>{(x[cat]/x['H'])*100:.1f}%</small>", axis=1)
            
            df_web.rename(columns={"DB": "D.Bogey", "TB": "+T.Bogey"}, inplace=True)
            cols = ["Jugador", "Puntos", "EAG", "BIR", "PAR", "BOG", "D.Bogey", "+T.Bogey"]
            st.write(df_web[cols].to_html(escape=False, index=False), unsafe_allow_html=True)

        elif st.session_state.vista_stats == "MVP":
            st.subheader(f"🌟 MVP - {subtitulo}")
            if not df_ranking.empty:
                ganador = df_ranking.iloc[0]
                st.balloons()
                c1, c2 = st.columns(2)
                c1.metric("🏆 LÍDER", ganador["Jugador"])
                c2.metric("PUNTOS TOTALES", f"{ganador['Puntos']:.1f} pts")
                st.write("### Clasificación")
                st.write(df_ranking[["Jugador", "Puntos", "H"]].to_html(escape=False, index=False), unsafe_allow_html=True)

        # 7. BOTÓN WHATSAPP
        st.markdown(f"""
            <a href="https://wa.me/?text={urllib.parse.quote(txt_wa)}" target="_blank" style="text-decoration:none;">
                <button style="background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; width:100%; cursor:pointer; font-weight:bold; margin-top:25px; font-size:16px;">
                    Compartir Reporte CAÑITA BRAVA 📱
                </button>
            </a>
        """, unsafe_allow_html=True)
        
elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Gestión")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id]
            with st.expander(f"Partida {dp['fecha'].iloc[0]} ({len(dp)} hoyos)"):
                c1, c2 = st.columns(2)
                if c1.button("✏️ Editar", key=f"ed_{p_id}"):
                    logs = {str(r['hoyo']): {'s':[r['s0'],r['s1'],r['s2'],r['s3']], 'pts':(r['resultado_a'],r['resultado_b']), 
                            'mvp':{f'p{i+1}':r[f'p{i+1}_pts'] for i in range(4)}} for _,r in dp.iterrows()}
                    st.session_state.game = {'fecha':dp['fecha'].iloc[0], 'h_sel':1, 'logs':logs, 'id':p_id}
                    st.session_state.menu_seleccionado = "Jugar/Editar"
                    st.rerun()
                if c2.checkbox("Borrar", key=f"del_cb_{p_id}"):
                    if st.button("🗑️ Confirmar", key=f"del_btn_{p_id}", type="primary"):
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(worksheet="historial", data=df[df['partido_id'] != p_id])
                        st.cache_data.clear()
                        st.rerun()
