import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,5])}
TODOS = ["MANUEL", "JOSE", "ROGE", "LALO"]
COLOR_A, COLOR_B = "#2e7d32", "#c62828"
PUNTOS_INICIO = {"2026": (3.5, 3.5)} 

# --- 2. GESTIÓN DE NAVEGACIÓN ---
if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu():
    st.session_state.menu_seleccionado = st.session_state.radio_menu

menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Estadísticas", "Admin"], 
                        index=["Inicio", "Jugar/Editar", "Estadísticas", "Admin"].index(st.session_state.menu_seleccionado),
                        key="radio_menu", on_change=cambiar_menu)

# --- 3. FUNCIONES DE DATOS ---
def leer_datos():
    st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        df = df.dropna(subset=['id'])
        df['temporada'] = pd.to_numeric(df['temporada'], errors='coerce').fillna(0).astype(int).astype(str)
        for col in ['s0', 's1', 's2', 's3', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def guardar_hoyo_db(df_fila):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_hist = leer_datos()
        id_hoyo = str(df_fila["id"].iloc[0])
        if not df_hist.empty:
            df_hist['id'] = df_hist['id'].astype(str)
            df_final = pd.concat([df_hist[df_hist["id"] != id_hoyo], df_fila], ignore_index=True)
        else: df_final = df_fila
        conn.update(worksheet="historial", data=df_final)
        st.cache_data.clear()
        return True
    except: return False

def calcular_puntos_hoyo(scores, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    v = [s if s > 0 else 99 for s in scores]
    ba, wa, bb, wb = min(v[0], v[1]), max(v[0], v[1]), min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    for i, s in enumerate(scores):
        p_bonus = 2.0 if 0 < s <= par - 2 else (1.0 if 0 < s == par - 1 else 0)
        if i < 2: pa += p_bonus 
        else: pb += p_bonus
    mvp = {f"p{i+1}": 0.0 for i in range(4)}
    for i in range(4):
        if scores[i] <= 0: continue
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]: mvp[f"p{i+1}"] += 0.5
        if scores[i] <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif scores[i] == par - 1: mvp[f"p{i+1}"] += 1.5
        elif scores[i] == par: mvp[f"p{i+1}"] += 0.5
    return pa, pb, mvp

def ejecutar_guardado_automatico():
    if 'game' not in st.session_state: return
    g = st.session_state.game
    h = g['h_sel']
    s1, s2 = st.session_state.get(f"s1_h{h}", PAR_RIA_VIGO[h]), st.session_state.get(f"s2_h{h}", PAR_RIA_VIGO[h])
    s3, s4 = st.session_state.get(f"s3_h{h}", PAR_RIA_VIGO[h]), st.session_state.get(f"s4_h{h}", PAR_RIA_VIGO[h])
    golpes = [s1, s2, s3, s4]
    pa, pb, mi = calcular_puntos_hoyo(golpes, h)
    g['logs'][str(h)] = {'s': golpes, 'pts': (pa, pb), 'mvp': mi}
    anio_partida = str(datetime.strptime(g['fecha'], "%d/%m/%Y").year)
    fila = pd.DataFrame([{"id": f"{g['id']}_H{h}", "partido_id": g['id'], "hoyo": h, "fecha": g['fecha'], "temporada": anio_partida, "resultado_a": pa, "resultado_b": pb, "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4'], "s0": s1, "s1": s2, "s2": s3, "s3": s4}])
    guardar_hoyo_db(fila)

def generar_texto_whatsapp_desde_df(df_partido):
    fecha = df_partido['fecha'].iloc[0]
    txt = f"⛳ *CAÑITA BRAVA - {fecha}*\n\n"
    
    pts_a = df_partido['resultado_a'].sum()
    pts_b = df_partido['resultado_b'].sum()
    m_a, m_b = max(0, pts_a - pts_b), max(0, pts_b - pts_a)
    
    txt += f"🏆 *MATCH:* {TODOS[0]}/{TODOS[1]} *{m_a:g}* vs *{m_b:g}* {TODOS[2]}/{TODOS[3]}\n\n"
    
    p_mvp = {
        TODOS[0]: df_partido['p1_pts'].sum(),
        TODOS[1]: df_partido['p2_pts'].sum(),
        TODOS[2]: df_partido['p3_pts'].sum(),
        TODOS[3]: df_partido['p4_pts'].sum()
    }
    ranking = sorted(p_mvp.items(), key=lambda x: x[1], reverse=True)
    txt += "🎖️ *MVP PARTIDO:*\n"
    for j, (nom, p) in enumerate(ranking):
        med = "🥇" if j==0 else "🥈" if j==1 else "🥉" if j==2 else "🎖️"
        txt += f"{med} {nom}: {p:g} pts\n"
    
    txt += "\n⛳ *DETALLE POR HOYO:*\n"
    for _, fila in df_partido.sort_values('hoyo').iterrows():
        # Calcular quién fue el MVP del hoyo específico
        mvps_hoyo = {TODOS[0]: fila['p1_pts'], TODOS[1]: fila['p2_pts'], TODOS[2]: fila['p3_pts'], TODOS[3]: fila['p4_pts']}
        mvp_nom = max(mvps_hoyo, key=mvps_hoyo.get)
        txt += f"H{int(fila['hoyo'])}: {fila['resultado_a']:g}-{fila['resultado_b']:g} | {mvp_nom}\n"
    
    return txt

# --- 4. PANTALLAS ---

if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    anios_db = df['temporada'].unique().tolist() if not df.empty else []
    anio_hoy = str(datetime.now().year)
    if anio_hoy not in anios_db: anios_db.append(anio_hoy)
    anios_finales = sorted(list(set(anios_db)), reverse=True)
    temp_sel = st.selectbox("📅 Temporada:", anios_finales, index=anios_finales.index(anio_hoy))
    p_ini_a, p_ini_b = PUNTOS_INICIO.get(temp_sel, (0.0, 0.0))
    df_temp = df[df['temporada'] == temp_sel] if not df.empty else pd.DataFrame()
    if not df_temp.empty:
        res = df_temp.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
        for _, r in res.iterrows():
            if r['resultado_a'] > r['resultado_b']: p_ini_a += 1
            elif r['resultado_b'] > r['resultado_a']: p_ini_b += 1
            else: p_ini_a += 0.5; p_ini_b += 0.5
    st.markdown(f"""<div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;">
        <h3>TEMPORADA {temp_sel}</h3><div style="display:flex;justify-content:space-around;">
        <div><h2 style="color:{COLOR_A};">{TODOS[0]}/{TODOS[1]}</h2><h1>{p_ini_a:g}</h1></div>
        <div><h2 style="color:{COLOR_B};">{TODOS[2]}/{TODOS[3]}</h2><h1>{p_ini_b:g}</h1></div></div></div>""", unsafe_allow_html=True)

elif st.session_state.menu_seleccionado == "Jugar/Editar":
    if 'game' not in st.session_state:
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': datetime.now().strftime("%Y%m%d%H%M%S")}
            st.rerun()
    else:
        g = st.session_state.game
        h = g['h_sel']
        ya_guardado = str(h) in g['logs']
        st.markdown(f"<h2 style='text-align:center; background:#2c3e50; color:white; border-radius:10px; padding:10px;'>HOYO {h} (PAR {PAR_RIA_VIGO[h]})</h2>", unsafe_allow_html=True)
        c_nav1, c_nav2 = st.columns(2)
        if c_nav1.button("⬅️ Anterior", use_container_width=True): ejecutar_guardado_automatico(); g['h_sel'] = max(1, h-1); st.rerun()
        if c_nav2.button("Siguiente ➡️", use_container_width=True): ejecutar_guardado_automatico(); g['h_sel'] = min(18, h+1); st.rerun()
        
        v = g['logs'][str(h)]['s'] if ya_guardado else [PAR_RIA_VIGO[h]]*4
        c_izq, c_der = st.columns(2)
        with c_izq:
            s1 = st.number_input(TODOS[0], 0, 10, v[0], key=f"s1_h{h}")
            s2 = st.number_input(TODOS[1], 0, 10, v[1], key=f"s2_h{h}")
        with c_der:
            s3 = st.number_input(TODOS[2], 0, 10, v[2], key=f"s3_h{h}")
            s4 = st.number_input(TODOS[3], 0, 10, v[3], key=f"s4_h{h}")
        
        if ya_guardado: st.button("✅ Hoyo Registrado", disabled=True, use_container_width=True)
        else:
            if st.button("💾 Guardar Hoyo", type="primary", use_container_width=True): ejecutar_guardado_automatico(); st.rerun()

        pts_a = sum(v['pts'][0] for v in g['logs'].values())
        pts_b = sum(v['pts'][1] for v in g['logs'].values())
        m_a, m_b = max(0, pts_a - pts_b), max(0, pts_b - pts_a)
        st.markdown(f"""<div style="display:flex; gap:10px; justify-content:center; margin-top:20px;">
            <div style="flex:1; border:3px solid {COLOR_A}; border-radius:15px; padding:10px; text-align:center; background:#f1f8f1;">
            <span style="font-weight:900; color:{COLOR_A}; font-size:0.8em;">{TODOS[0]}/{TODOS[1]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_A};">{m_a:g}</div></div>
            <div style="flex:1; border:3px solid {COLOR_B}; border-radius:15px; padding:10px; text-align:center; background:#fef2f2;">
            <span style="font-weight:900; color:{COLOR_B}; font-size:0.8em;">{TODOS[2]}/{TODOS[3]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_B};">{m_b:g}</div></div></div>""", unsafe_allow_html=True)

        st.divider()
        if st.button("🏁 Finalizar Partida", type="secondary", use_container_width=True): del st.session_state.game; st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas")
    df = leer_datos()
    if df.empty: st.info("Sin datos.")
    else:
        mvp_partidos = df.groupby('partido_id').agg({'p1_pts':'sum','p2_pts':'sum','p3_pts':'sum','p4_pts':'sum'})
        conteo_mvp = {jugador: 0 for jugador in TODOS}
        for _, fila in mvp_partidos.iterrows():
            m = fila.max()
            if m > 0:
                for j in fila[fila == m].index: conteo_mvp[TODOS[int(j[1])-1]] += 1
        stats = []
        for i, jug in enumerate(TODOS):
            c = f's{i}'
            temp = df[df[c] > 0].copy()
            temp['diff'] = temp[c] - temp['hoyo'].map(PAR_RIA_VIGO)
            stats.append({"Jugador": jug, "MVP": conteo_mvp[jug], "Birdie": len(temp[temp['diff'] == -1]), "Par": len(temp[temp['diff'] == 0])})
        st.table(pd.DataFrame(stats).set_index("Jugador"))

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Admin")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id]
            with st.expander(f"📅 {dp['fecha'].iloc[0]}"):
                c1, c2, c3 = st.columns(3)
                # Botón WhatsApp
                msg_wa = generar_texto_whatsapp_desde_df(dp)
                c1.download_button("📱 WhatsApp", msg_wa, file_name=f"partida_{p_id}.txt", key=f"wa_{p_id}")
                
                # Botón Editar
                if c2.button("✏️ Editar", key=f"ed_{p_id}"):
                    rec = {str(int(f['hoyo'])): {'s':[int(f['s0']),int(f['s1']),int(f['s2']),int(f['s3'])], 'pts':(f['resultado_a'],f['resultado_b']), 'mvp':{'p1':f['p1_pts'],'p2':f['p2_pts'],'p3':f['p3_pts'],'p4':f['p4_pts']}} for _, f in dp.iterrows()}
                    st.session_state.game = {'fecha': dp['fecha'].iloc[0], 'h_sel': 1, 'logs': rec, 'id': str(p_id)}
                    st.session_state.menu_seleccionado = "Jugar/Editar"
                    st.rerun()
                
                # Botón Borrar
                if c3.button("🗑️ Borrar", key=f"del_{p_id}", type="primary"):
                    st.connection("gsheets", type=GSheetsConnection).update(worksheet="historial", data=df[df['partido_id'] != p_id])
                    st.cache_data.clear(); st.rerun()
