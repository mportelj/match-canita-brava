import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# --- CONFIGURACIÓN DEL CAMPO (RIA DE VIGO) ---
PAR_RIA_VIGO = {
    1: 5, 2: 4, 3: 4, 4: 4, 5: 3, 6: 5, 7: 4, 8: 3, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 4, 14: 3, 15: 5, 16: 4, 17: 4, 18: 4  # <-- Actualizado a Par 4
}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
EQUIPO_A_NOMBRES = f"{TODOS[0]}/{TODOS[1]}"
EQUIPO_B_NOMBRES = f"{TODOS[2]}/{TODOS[3]}"
COLOR_A, COLOR_B = "#2e7d32", "#c62828"
COL_NECESARIAS = ['id', 'partido_id', 'hoyo', 'fecha', 'temporada', 'resultado_a', 'resultado_b', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts', 's0', 's1', 's2', 's3']

# Conexión global para evitar NameError
conn = st.connection("gsheets", type=GSheetsConnection)

if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu():
    st.session_state.menu_seleccionado = st.session_state.radio_menu

# --- 2. FUNCIONES DE DATOS ---
def leer_datos():
    try:
        # Forzamos ttl=0 para leer siempre lo último de la nube
        df = conn.read(worksheet="historial", ttl=0) 
        if df is None or df.empty: 
            return pd.DataFrame(columns=COL_NECESARIAS)
        
        # Normalización de columnas a minúsculas para evitar KeyError
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Asegurar tipos de datos para filtros de Pandas
        df['partido_id'] = df['partido_id'].astype(str)
        df['hoyo'] = pd.to_numeric(df['hoyo'], errors='coerce').fillna(0).astype(int)
        df['temporada'] = pd.to_numeric(df['temporada'], errors='coerce').fillna(0).astype(int)
        df['fecha'] = df['fecha'].astype(str)
        
        return df.drop_duplicates(subset=['partido_id', 'hoyo'], keep='last')
    except:
        return pd.DataFrame(columns=COL_NECESARIAS)

def calcular_puntos_hoyo(scores, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    v = [int(s) for s in scores]
    # Lógica Match Play Parejas
    ba, wa, bb, wb = min(v[0], v[1]), max(v[0], v[1]), min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    
    # Bonus Birdie/Eagle para el equipo
    for i, s in enumerate(v):
        p_bonus = 2.0 if s <= par - 2 else (1.0 if s == par - 1 else 0)
        if i < 2: pa += p_bonus 
        else: pb += p_bonus
        
    # Puntos MVP Individuales
    mvp = {f"p1": 0.0, f"p2": 0.0, f"p3": 0.0, f"p4": 0.0}
    for i in range(4):
        for j in range(4):
            if i != j and v[i] < v[j]: mvp[f"p{i+1}"] += 0.5
        if v[i] <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif v[i] == par - 1: mvp[f"p{i+1}"] += 1.5
        elif v[i] == par: mvp[f"p{i+1}"] += 0.5
    return pa, pb, mvp

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
    if not df.empty:
        df_t = df[df['temporada'] == int(sel_temp)]
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
    if 'refresco_id' not in st.session_state: 
        st.session_state.refresco_id = 0

    if 'game' not in st.session_state:
        st.markdown("### ⛳ Nueva Partida")
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            st.session_state.game = {
                'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 
                'id': datetime.now().strftime("%Y%m%d%H%M%S")
            }
            st.rerun()
    else:
        g = st.session_state.game
        df_p = leer_datos()
        df_partido_actual = df_p[df_p['partido_id'] == str(g['id'])]
        
        # --- 1. MARCADOR MATCH PLAY ---
        pts_a_total = df_partido_actual['resultado_a'].sum()
        pts_b_total = df_partido_actual['resultado_b'].sum()
        dif = pts_a_total - pts_b_total
        m_a, m_b = (dif, 0) if dif > 0 else (0, abs(dif))

        st.markdown(f"""
            <div style="border: 2px solid #2e7d32; border-radius: 15px; padding: 15px; background-color: #f0f4f0; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-around; align-items: center; text-align: center;">
                    <div style="flex: 1;">
                        <h4 style="color: #2e7d32; margin: 0; font-size: 0.9em; font-weight: bold;">{EQUIPO_A_NOMBRES}</h4>
                        <h1 style="margin: 0; font-size: 4.5em; color: {COLOR_A if m_a > 0 else '#333'};">{m_a:g}</h1>
                    </div>
                    <div style="background: #ccc; border-radius: 50%; width: 45px; height: 45px; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #666; font-size: 0.8em;">VS</div>
                    <div style="flex: 1;">
                        <h4 style="color: #c62828; margin: 0; font-size: 0.9em; font-weight: bold;">{EQUIPO_B_NOMBRES}</h4>
                        <h1 style="margin: 0; font-size: 4.5em; color: {COLOR_B if m_b > 0 else '#333'};">{m_b:g}</h1>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- 2. NAVEGACIÓN Y SELECTOR DESTACADO ---
        c_nav1, c_nav2 = st.columns(2)
        if c_nav1.button("← Anterior", use_container_width=True):
            g['h_sel'] = max(1, g['h_sel'] - 1)
            st.session_state.refresco_id += 1
            st.rerun()
        if c_nav2.button("Siguiente →", use_container_width=True):
            g['h_sel'] = min(18, g['h_sel'] + 1)
            st.session_state.refresco_id += 1
            st.rerun()

        # CSS para agrandar el texto del selector y ponerlo en negrita
        st.markdown("""
            <style>
                div[data-baseweb="select"] > div {
                    font-size: 26px !important;
                    font-weight: 800 !important;
                    height: 65px !important;
                    border-radius: 10px !important;
                }
            </style>
        """, unsafe_allow_html=True)

        lista_hoyos = [f"Hoyo {i} (Par {PAR_RIA_VIGO[i]})" for i in range(1, 19)]
        seleccion = st.selectbox(
            "h_sel", lista_hoyos, index=g['h_sel']-1, 
            label_visibility="collapsed", 
            key=f"h_selector_{st.session_state.refresco_id}"
        )
        
        nuevo_h_id = int(seleccion.split(" ")[1])
        if nuevo_h_id != g['h_sel']:
            g['h_sel'] = nuevo_h_id
            st.session_state.refresco_id += 1
            st.rerun()

        h = g['h_sel']
        par_h = PAR_RIA_VIGO[h]
        fila_hoyo = df_partido_actual[df_partido_actual['hoyo'] == h]
        ya_existe = not fila_hoyo.empty

        # --- 3. RESULTADO HOYO ---
        if ya_existe:
            ha, hb = fila_hoyo.iloc[0]['resultado_a'], fila_hoyo.iloc[0]['resultado_b']
            color_res = COLOR_A if ha > hb else (COLOR_B if hb > ha else "#666")
            st.markdown(f"""
                <div style="border: 1px solid #eee; border-radius: 10px; padding: 10px; text-align: center; background: white; margin-bottom: 15px;">
                    <h2 style="margin: 0; letter-spacing: 4px; color: {color_res};">{ha:g} — {hb:g}</h2>
                </div>
            """, unsafe_allow_html=True)

        # --- 4. ENTRADA DE GOLPES (SIN ETIQUETAS DE TEXTO EXTRA) ---
        v_ref = [int(fila_hoyo.iloc[0][f's{i}']) if ya_existe else par_h for i in range(4)]
        col_j1, col_j2 = st.columns(2)
        s1 = col_j1.number_input(TODOS[0], 1, 15, v_ref[0], key=f"s1_{h}_{st.session_state.refresco_id}")
        s2 = col_j1.number_input(TODOS[1], 1, 15, v_ref[1], key=f"s2_{h}_{st.session_state.refresco_id}")
        s3 = col_j2.number_input(TODOS[2], 1, 15, v_ref[2], key=f"s3_{h}_{st.session_state.refresco_id}")
        s4 = col_j2.number_input(TODOS[3], 1, 15, v_ref[3], key=f"s4_{h}_{st.session_state.refresco_id}")

        if st.button("💾 Actualizar Hoyo", type="primary", use_container_width=True, disabled=([s1,s2,s3,s4] == v_ref)):
            ejecutar_guardado_automatico()
            st.rerun()

        st.write("---")
        with st.popover("🏁 Finalizar Partida", use_container_width=True):
            if st.button("Confirmar Cierre", type="primary", use_container_width=True):
                if 'game' in st.session_state: del st.session_state.game
                st.cache_data.clear()
                st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas del Partido")
    df_raw = leer_datos()
    
    if not df_raw.empty:
        # --- FILTRO DE PARTIDO ACTUAL ---
        if 'game' in st.session_state:
            id_actual = str(st.session_state.game['id'])
            # Filtramos solo las filas que pertenecen a esta partida
            df_partido = df_raw[df_raw['partido_id'] == id_actual].copy()
            st.info(f"Análisis del partido: {st.session_state.game['fecha']}")
        else:
            df_partido = df_raw.copy()
            st.info("Mostrando acumulado histórico (No hay partida activa)")

        stats = []

        # Iteramos por los 4 jugadores (s0, s1, s2, s3)
        for i, jug in enumerate(TODOS):
            col_s = f's{i}'
            
            # Inicializamos contadores para este jugador
            counts = {"Eagle": 0, "Birdie": 0, "Par": 0, "Bogey": 0, "D.Bogey": 0, "3+ Bogey": 0}
            
            # Filtramos filas donde el jugador tenga golpes anotados (> 0)
            puntos_jugador = df_partido[pd.to_numeric(df_partido[col_s], errors='coerce') > 0]
            
            for _, fila in puntos_jugador.iterrows():
                hoyo_num = int(fila['hoyo'])
                golpes = int(fila[col_s])
                par_hoyo = PAR_RIA_VIGO.get(hoyo_num, 4) # Por defecto 4 si no lo encuentra
                
                dif = golpes - par_hoyo
                
                # Clasificación estricta
                if dif <= -2: counts["Eagle"] += 1
                elif dif == -1: counts["Birdie"] += 1
                elif dif == 0:  counts["Par"] += 1
                elif dif == 1:  counts["Bogey"] += 1
                elif dif == 2:  counts["D.Bogey"] += 1
                elif dif >= 3:  counts["3+ Bogey"] += 1
            
            # Puntos MVP (columna p1_pts...p4_pts)
            col_p_pts = f'p{i+1}_pts'
            pts_mvp = pd.to_numeric(df_partido[col_p_pts], errors='coerce').sum() if col_p_pts in df_partido.columns else 0
            
            stats.append({
                "Jugador": jug,
                "Eagle": counts["Eagle"],
                "Birdie": counts["Birdie"],
                "Par": counts["Par"],
                "Bogey": counts["Bogey"],
                "D.Bogey": counts["D.Bogey"],
                "3+ Bogey": counts["3+ Bogey"],
                "Puntos MVP": round(float(pts_mvp), 2)
            })
        
        # Crear DataFrame final
        df_final = pd.DataFrame(stats)
        
        # Mostramos la tabla principal (sin gráficos)
        st.dataframe(df_final.set_index("Jugador"), use_container_width=True)
        
        # Resumen de Puntos por Equipo
        st.write("---")
        c1, c2 = st.columns(2)
        total_a = df_partido['resultado_a'].sum() if 'resultado_a' in df_partido.columns else 0
        total_b = df_partido['resultado_b'].sum() if 'resultado_b' in df_partido.columns else 0
        c1.metric(f"Total {EQUIPO_A_NOMBRES}", f"{total_a:g}")
        c2.metric(f"Total {EQUIPO_B_NOMBRES}", f"{total_b:g}")
        
    else:
        st.warning("No hay datos en la base de datos.")
elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Administración")
    df = leer_datos()
    
    if not df.empty:
        # Filtrar IDs válidos
        ids_unicos = [pid for pid in df['partido_id'].unique() if pid and str(pid).strip() != ""]
        
        for p_id in ids_unicos[::-1]:
            dp = df[df['partido_id'] == p_id].sort_values('hoyo')
            
            if dp.empty:
                continue
                
            fecha_p = str(dp['fecha'].iloc[0])
            num_hoyos = len(dp)
            
            # Título limpio
            titulo_expander = f"📅 {fecha_p} — ({num_hoyos} hoyos jugados)"
            
            with st.expander(titulo_expander):
                c1, c2, c3 = st.columns([1, 1, 2])
                
                # --- BOTÓN EDITAR ---
                if c1.button("✏️ Editar", key=f"edit_{p_id}", use_container_width=True):
                    st.session_state.game = {
                        'fecha': fecha_p, 
                        'h_sel': 1, 
                        'logs': {}, 
                        'id': str(p_id)
                    }
                    st.session_state.menu_seleccionado = "Jugar/Editar"
                    st.rerun()
                
                # --- BOTÓN BORRAR CON CONFIRMACIÓN ---
                with c2:
                    # El popover actúa como el primer paso de seguridad
                    with st.popover("🗑️ Borrar", use_container_width=True):
                        st.warning("¿Estás seguro?")
                        if st.button("Sí, eliminar", key=f"conf_del_{p_id}", type="primary", use_container_width=True):
                            # Lógica de borrado
                            df_new = df[df['partido_id'] != p_id]
                            conn.update(worksheet="historial", data=df_new)
                            st.cache_data.clear()
                            st.success("Partido eliminado.")
                            st.rerun()
                
                with c3:
                    st.write("") 

    else:
        st.info("No hay datos en el historial.")
