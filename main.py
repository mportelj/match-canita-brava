import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,5])}
TODOS = ["MANUEL", "JOSE", "ROGE", "LALO"]
COLOR_A, COLOR_B = "#2e7d32", "#c62828"
INICIO_2026_A, INICIO_2026_B = 3.5, 3.5

# --- 2. GESTIÓN DE NAVEGACIÓN ---
if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu():
    st.session_state.menu_seleccionado = st.session_state.radio_menu
    for key in list(st.session_state.keys()):
        if "confirm_del_" in key:
            del st.session_state[key]

menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Admin"], key="radio_menu", on_change=cambiar_menu)

# --- 3. FUNCIONES DE DATOS ---
def leer_datos():
    st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0)
        if df is None or df.empty: return pd.DataFrame()
        df = df.dropna(subset=['id'])
        for c in ['resultado_a', 'resultado_b', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts', 's0', 's1', 's2', 's3']:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

def guardar_hoyo(df_fila):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_hist = leer_datos()
        id_hoyo = str(df_fila["id"].iloc[0])
        df_final = pd.concat([df_hist[df_hist["id"].astype(str) != id_hoyo], df_fila], ignore_index=True) if not df_hist.empty else df_fila
        conn.update(worksheet="historial", data=df_final)
        st.cache_data.clear()
        return True
    except:
        return False

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

# --- 4. LÓGICA DE PANTALLAS ---

if st.session_state.menu_seleccionado == "Inicio":
    c1, c2 = st.columns([0.8, 0.2])
    c1.title("⛳ CAÑITA BRAVA")
    if c2.button("🔄"): st.rerun()

    df = leer_datos()
    pts_a, pts_b = INICIO_2026_A, INICIO_2026_B
    
    if not df.empty:
        df_26 = df[df['temporada'].astype(str).str.contains("2026")]
        if not df_26.empty:
            res = df_26.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
            for _, r in res.iterrows():
                if r['resultado_a'] > r['resultado_b']: pts_a += 1
                elif r['resultado_b'] > r['resultado_a']: pts_b += 1
                else: pts_a += 0.5; pts_b += 0.5

    st.markdown(f"""<div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;margin-bottom:20px;">
        <h3 style="margin:0;">TEMPORADA 2026</h3><div style="display:flex;justify-content:space-around;align-items:center;">
        <div><h2 style="color:{COLOR_A};margin:0;">M&J</h2><h1 style="margin:0;">{pts_a:g}</h1></div>
        <h2 style="color:#999;margin:0;">VS</h2>
        <div><h2 style="color:{COLOR_B};margin:0;">R&L</h2><h1 style="margin:0;">{pts_b:g}</h1></div></div></div>""", unsafe_allow_html=True)

    with st.popover("⭐ Ver Ranking MVP Temporada", use_container_width=True):
        if not df.empty:
            rk = {TODOS[i]: df[f"p{i+1}_pts"].sum() for i in range(4)}
            df_rk = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in rk.items()]).sort_values("Pts", ascending=False)
            st.table(df_rk)

elif st.session_state.menu_seleccionado == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.subheader("Nueva Partida")
        f = st.date_input("Fecha:", datetime.now())
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': f.strftime("%Y%m%d")}
            st.rerun()
    else:
        g = st.session_state.game
        h = g['h_sel']
        
        st.markdown(f"""<div style="background-color:#2c3e50; padding:15px; border-radius:10px; text-align:center; color:white; margin-bottom:15px;">
            <h2 style="margin:0; color:#ecf0f1;">HOYO {h}</h2>
            <p style="margin:0; font-size:1.2em; color:#bdc3c7;">PAR {PAR_RIA_VIGO[h]}</p>
            </div>""", unsafe_allow_html=True)
        
        c_nav1, c_nav2 = st.columns(2)
        if c_nav1.button("⬅️ Anterior", use_container_width=True): g['h_sel'] = max(1, h-1); st.rerun()
        if c_nav2.button("Siguiente ➡️", use_container_width=True): g['h_sel'] = min(18, h+1); st.rerun()
        
        v_guardados = g['logs'][str(h)]['s'] if str(h) in g['logs'] else [PAR_RIA_VIGO[h]]*4
        s1 = st.number_input(f"🏌️ {TODOS[0]}", 0, 10, v_guardados[0], key=f"s1_h{h}")
        s2 = st.number_input(f"🏌️ {TODOS[1]}", 0, 10, v_guardados[1], key=f"s2_h{h}")
        s3 = st.number_input(f"🏌️ {TODOS[2]}", 0, 10, v_guardados[2], key=f"s3_h{h}")
        s4 = st.number_input(f"🏌️ {TODOS[3]}", 0, 10, v_guardados[3], key=f"s4_h{h}")
        
        golpes_actuales = [s1, s2, s3, s4]
        ya_guardado = str(h) in g['logs'] and g['logs'][str(h)]['s'] == golpes_actuales
        
        btn_label = "✅ Hoyo Sincronizado" if ya_guardado else "💾 Guardar Cambios"
        if st.button(btn_label, type="primary", use_container_width=True, disabled=ya_guardado):
            pa, pb, mi = calcular_puntos_hoyo(golpes_actuales, h)
            g['logs'][str(h)] = {'s': golpes_actuales, 'pts': (pa, pb), 'mvp': mi}
            fila = pd.DataFrame([{"id": f"{g['id']}_H{h}", "partido_id": g['id'], "hoyo": h, "fecha": g['fecha'], "temporada": "2026", "resultado_a": pa, "resultado_b": pb, "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4'], "s0": s1, "s1": s2, "s2": s3, "s3": s4}])
            if guardar_hoyo(fila): st.toast("✅ Guardado"); st.rerun()

        # --- MARCADOR CLÁSICO Y MVP ---
        if g['logs']:
            st.write("---")
            match_a = sum(v['pts'][0] for v in g['logs'].values())
            match_b = sum(v['pts'][1] for v in g['logs'].values())
            
            st.markdown(f"""
            <table style="width:100%; border-collapse: collapse; text-align: center; font-family: sans-serif; border: 1px solid #ddd;">
                <tr style="background-color: #f2f2f2;">
                    <th style="padding: 10px; border: 1px solid #ddd;">PAREJA</th>
                    <th style="padding: 10px; border: 1px solid #ddd;">JUGADORES</th>
                    <th style="padding: 10px; border: 1px solid #ddd;">TOTAL</th>
                </tr>
                <tr>
                    <td style="color:{COLOR_A}; font-weight:bold; border: 1px solid #ddd;">A</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{TODOS[0]} & {TODOS[1]}</td>
                    <td style="font-size: 1.5em; font-weight: bold; color:{COLOR_A}; border: 1px solid #ddd;">{match_a:g}</td>
                </tr>
                <tr>
                    <td style="color:{COLOR_B}; font-weight:bold; border: 1px solid #ddd;">B</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{TODOS[2]} & {TODOS[3]}</td>
                    <td style="font-size: 1.5em; font-weight: bold; color:{COLOR_B}; border: 1px solid #ddd;">{match_b:g}</td>
                </tr>
            </table>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                with st.popover("🎯 MVP Hoyo", use_container_width=True):
                    if str(h) in g['logs']:
                        h_mvp = g['logs'][str(h)]['mvp']
                        df_h = pd.DataFrame([{"Jugador": TODOS[i], "Pts": h_mvp[f"p{i+1}"]} for i in range(4)])
                        st.table(df_h)
            with c2:
                with st.popover("🏆 MVP Partido", use_container_width=True):
                    p_mvp = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
                    df_p = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in p_mvp.items()]).sort_values("Pts", ascending=False)
                    st.table(df_p)

        if st.button("🏁 Finalizar Partida", use_container_width=True):
            del st.session_state.game; st.rerun()

elif st.session_state.menu_seleccionado == "Admin":
    st.title("Administración")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id]
            with st.expander(f"📅 {dp['fecha'].iloc[0]}"):
                st.write(f"Final: {dp['resultado_a'].sum():g} ({TODOS[0]}/{TODOS[1]}) vs {dp['resultado_b'].sum():g} ({TODOS[2]}/{TODOS[3]})")
                c_adm1, c_adm2, c_adm3 = st.columns(3)
                with c_adm1:
                    with st.popover("🏆 MVP", use_container_width=True):
                        rk_h = {TODOS[i]: dp[f"p{i+1}_pts"].sum() for i in range(4)}
                        st.table(pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in rk_h.items()]).sort_values("Pts", ascending=False))
                if c_adm2.button("✏️ Editar", key=f"ed_{p_id}"):
                    rec = {str(int(f['hoyo'])): {'s':[int(f['s0']),int(f['s1']),int(f['s2']),int(f['s3'])], 'pts':(f['resultado_a'],f['resultado_b']), 'mvp':{'p1':f['p1_pts'],'p2':f['p2_pts'],'p3':f['p3_pts'],'p4':f['p4_pts']}} for _, f in dp.iterrows()}
                    st.session_state.game = {'fecha': dp['fecha'].iloc[0], 'h_sel': 1, 'logs': rec, 'id': p_id}
                    st.session_state.menu_seleccionado = "Jugar/Editar"
                    st.session_state.radio_menu = "Jugar/Editar"
                    st.rerun()
                if c_adm3.button("🗑️ Borrar", key=f"del_{p_id}"):
                    st.session_state[f"confirm_del_{p_id}"] = True
                if st.session_state.get(f"confirm_del_{p_id}", False):
                    if st.button("✅ Confirmar", key=f"real_del_{p_id}"):
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(worksheet="historial", data=df[df['partido_id'] != p_id])
                        st.rerun()
