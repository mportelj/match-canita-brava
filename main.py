import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}
TODOS = ["MANUEL", "JOSE", "ROGE", "LALO"]
COLOR_A = "#2e7d32"
COLOR_B = "#c62828"
INICIO_2026_A = 3.5  
INICIO_2026_B = 3.5  

st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# --- FUNCIONES ---
def estilo_tabla(row):
    color = COLOR_A if row['Jugador'] in ["MANUEL", "JOSE"] else COLOR_B
    return [f'color: {color}; font-weight: bold'] * len(row)

def leer_datos():
    st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "s0", "s1", "s2", "s3"])
        return df.dropna(subset=['id'])
    except:
        return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "s0", "s1", "s2", "s3"])

def guardar_hoyo(df_fila):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = leer_datos()
        id_hoyo = str(df_fila["id"].iloc[0])
        if not df_existente.empty:
            df_existente['id'] = df_existente['id'].astype(str)
            df_final = df_existente[df_existente["id"] != id_hoyo].copy()
            df_final = pd.concat([df_final, df_fila], ignore_index=True)
        else:
            df_final = df_fila
        conn.update(worksheet="historial", data=df_final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    scores = [s1, s2, s3, s4]
    v = [s if s > 0 else 99 for s in scores]
    ba, wa = min(v[0], v[1]), max(v[0], v[1])
    bb, wb = min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    for s in [s1, s2]:
        if 0 < s <= par - 2: pa += 2.0
        elif 0 < s == par - 1: pa += 1.0
    for s in [s3, s4]:
        if 0 < s <= par - 2: pb += 2.0
        elif 0 < s == par - 1: pb += 1.0
    mvp = {f"p{i+1}": 0.0 for i in range(4)}
    for i in range(4):
        if scores[i] <= 0: continue
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]: mvp[f"p{i+1}"] += 0.5
        if scores[i] <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif scores[i] == par - 1: mvp[f"p{i+1}"] += 1.5
        elif scores[i] == par: mvp[f"p{i+1}"] += 0.5
    return pa, pb, mvp

# --- NAVEGACIÓN ---
if 'menu' not in st.session_state:
    st.session_state.menu = "Inicio"

def ir_a(pagina):
    st.session_state.menu = pagina
    st.rerun()

# Sidebar manual (actualiza el estado al hacer clic)
with st.sidebar:
    st.title("⛳ Menú")
    if st.button("Inicio", use_container_width=True): ir_a("Inicio")
    if st.button("Jugar/Editar", use_container_width=True): ir_a("Jugar/Editar")
    if st.button("Admin", use_container_width=True): ir_a("Admin")

# --- PANTALLAS ---
if st.session_state.menu == "Inicio":
    st.markdown("<h1 style='text-align: center;'>⛳ CAÑITA BRAVA 2026</h1>", unsafe_allow_html=True)
    df = leer_datos()
    df_2026 = df[df['temporada'] == "2026"]
    
    pts_a, pts_b = INICIO_2026_A, INICIO_2026_B
    if not df_2026.empty:
        resumen = df_2026.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'}).reset_index()
        for _, r in resumen.iterrows():
            if r['resultado_a'] > r['resultado_b']: pts_a += 1
            elif r['resultado_b'] > r['resultado_a']: pts_b += 1
            else: pts_a += 0.5; pts_b += 0.5
    
    st.markdown(f"""
        <div style="border:2px solid #ccc;border-radius:15px;padding:20px;background:#f9f9f9;text-align:center;margin-bottom:25px;">
            <h2 style="color:#333;">TEMPORADA 2026</h2>
            <div style="display:flex;justify-content:space-around;">
                <div><h4 style="color:{COLOR_A};">M & J</h4><h1 style="color:{COLOR_A};">{pts_a:g}</h1></div>
                <h2>VS</h2>
                <div><h4 style="color:{COLOR_B};">R & L</h4><h1 style="color:{COLOR_B};">{pts_b:g}</h1></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if not df_2026.empty:
        st.markdown("<h3 style='text-align:center;'>⭐ MVP 2026</h3>", unsafe_allow_html=True)
        mvps = {TODOS[i]: df_2026[f"p{i+1}_pts"].sum() for i in range(4)}
        df_mvp = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in mvps.items()]).sort_values("Pts", ascending=False)
        st.table(df_mvp.style.apply(estilo_tabla, axis=1).format({"Pts": "{:.1f}"}))

elif st.session_state.menu == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.markdown("<h2 style='text-align:center;'>Nueva Partida</h2>", unsafe_allow_html=True)
        f = st.date_input("Fecha:", datetime.now())
        if st.button("🚀 Iniciar", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'h_sel': 1, 'logs': {}, 'partido_id': f.strftime("%Y%m%d")}
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']
        st.markdown(f"<div style='background:#f0f2f6;padding:5px;border-radius:10px;text-align:center;border:1px solid #ddd;'><h3>Hoyo {h_idx} (Par {PAR_RIA_VIGO[h_idx]})</h3></div>", unsafe_allow_html=True)

        v_def = g['logs'][str(h_idx)]['s'] if str(h_idx) in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        
        # Un jugador por línea con color
        st.markdown(f"<b style='color:{COLOR_A}'>{TODOS[0]}</b>", unsafe_allow_html=True)
        s1 = st.number_input("", 0, 10, v_def[0], key=f"s0_{h_idx}", label_visibility="collapsed")
        st.markdown(f"<b style='color:{COLOR_A}'>{TODOS[1]}</b>", unsafe_allow_html=True)
        s2 = st.number_input("", 0, 10, v_def[1], key=f"s1_{h_idx}", label_visibility="collapsed")
        st.markdown(f"<b style='color:{COLOR_B}'>{TODOS[2]}</b>", unsafe_allow_html=True)
        s3 = st.number_input("", 0, 10, v_def[2], key=f"s2_{h_idx}", label_visibility="collapsed")
        st.markdown(f"<b style='color:{COLOR_B}'>{TODOS[3]}</b>", unsafe_allow_html=True)
        s4 = st.number_input("", 0, 10, v_def[3], key=f"s3_{h_idx}", label_visibility="collapsed")
        
        if st.button("💾 Guardar Hoyo", type="primary", use_container_width=True):
            pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, h_idx)
            g['logs'][str(h_idx)] = {'s': [s1, s2, s3, s4], 'pts': (pa, pb), 'mvp': mi}
            nueva_fila = pd.DataFrame([{"id": f"{g['partido_id']}_H{h_idx}", "partido_id": g['partido_id'], "hoyo": h_idx, "fecha": g['fecha'], "temporada": g['temp'], "resultado_a": pa, "resultado_b": pb, "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4'], "s0": s1, "s1": s2, "s2": s3, "s3": s4}])
            if guardar_hoyo(nueva_fila): st.toast("✅ Guardado"); st.rerun()

        c_nav = st.columns(2)
        if c_nav[0].button("⬅️ Anterior", use_container_width=True): g['h_sel'] = max(1, h_idx-1); st.rerun()
        if c_nav[1].button("Siguiente ➡️", use_container_width=True): g['h_sel'] = min(18, h_idx+1); st.rerun()

        if st.button("🏁 Salir", use_container_width=True):
            del st.session_state.game; ir_a("Inicio")

elif st.session_state.menu == "Admin":
    st.markdown("<h2 style='text-align: center;'>Admin</h2>", unsafe_allow_html=True)
    df = leer_datos()
    if
