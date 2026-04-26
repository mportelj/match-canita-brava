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
            return pd.DataFrame()
        df = df.dropna(subset=['id'])
        df['temporada'] = df['temporada'].astype(str).str.replace('.0', '', regex=False).str.strip()
        for c in ['resultado_a', 'resultado_b', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts']:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

def guardar_hoyo(df_fila):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_hist = leer_datos()
        id_hoyo = str(df_fila["id"].iloc[0])
        if not df_hist.empty:
            df_hist['id'] = df_hist['id'].astype(str)
            df_final = df_hist[df_hist["id"] != id_hoyo].copy()
            df_final = pd.concat([df_final, df_fila], ignore_index=True)
        else:
            df_final = df_fila
        conn.update(worksheet="historial", data=df_final)
        st.cache_data.clear()
        return True
    except:
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
    mvp = {f"p1": 0.0, f"p2": 0.0, f"p3": 0.0, f"p4": 0.0}
    for i in range(4):
        if scores[i] <= 0: continue
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]: mvp[f"p{i+1}"] += 0.5
        if scores[i] <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif scores[i] == par - 1: mvp[f"p{i+1}"] += 1.5
        elif scores[i] == par: mvp[f"p{i+1}"] += 0.5
    return pa, pb, mvp

# --- CONTROL DE NAVEGACIÓN INSTANTÁNEA ---
if "menu_previo" not in st.session_state:
    st.session_state.menu_previo = "Inicio"

menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Admin"], key="menu_actual")

# Si el usuario cambia de menú, forzamos limpieza de estados temporales
if st.session_state.menu_actual != st.session_state.menu_previo:
    st.session_state.menu_previo = st.session_state.menu_actual
    # Limpiamos confirmaciones de borrado pendientes si las hubiera
    for key in list(st.session_state.keys()):
        if "confirm_del_" in key:
            del st.session_state[key]
    st.rerun()

# --- INICIO ---
if menu == "Inicio":
    c1, c2 = st.columns([0.8, 0.2])
    c1.markdown("<h1 style='margin:0;'>⛳ CAÑITA BRAVA</h1>", unsafe_allow_html=True)
    if c2.button("🔄"):
        st.cache_data.clear()
        st.rerun()

    df = leer_datos()
    pts_a, pts_b = INICIO_2026_A, INICIO_2026_B
    
    if not df.empty:
        df_2026 = df[df['temporada'] == "2026"]
        if not df_2026.empty:
            resumen = df_2026.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'}).reset_index()
            for _, r in resumen.iterrows():
                if (r['resultado_a'] + r['resultado_b']) > 0:
                    if r['resultado_a'] > r['resultado_b']: pts_a += 1
                    elif r['resultado_b'] > r['resultado_a']: pts_b += 1
                    else: pts_a += 0.5; pts_b += 0.5

    st.markdown(f"""
        <div style="border: 2px solid #ccc; border-radius: 15px; padding: 20px; background-color: #f9f9f9; text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #333;">TEMPORADA 2026</h2>
            <div style="display: flex; justify-content: space-around; align-items: center;">
                <div><h4 style="margin:0; color:{COLOR_A};">M & J</h4><h1 style="color:{COLOR_A}; margin:0;">{pts_a:g}</h1></div>
                <h2 style="margin:0; color:#999;">VS</h2>
                <div><h4 style="margin:0; color:{COLOR_B};">R & L</h4><h1 style="color:{COLOR_B}; margin:0;">{pts_b:g}</h1></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.popover("⭐ Ver MVP Acumulado Temporada", use_container_width=True):
        if not df.empty and not df[df['temporada'] == "2026"].empty:
            df_m = df[df['temporada'] == "2026"]
            ranking = {TODOS[i]: df_m[f"p{i+1}_pts"].sum() for i in range(4)}
            df_r = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in ranking.items()]).sort_values("Pts", ascending=False)
            st.table(df_r.style.apply(estilo_tabla, axis=1).format({"Pts": "{:.1f}"}))

# --- JUGAR / EDITAR ---
elif menu == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>Nueva Partida</h2>", unsafe_allow_html=True)
        f = st.date_input("Fecha:", datetime.now())
        if st.button("🚀 Iniciar", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': "2026", 'h_sel': 1, 'logs': {}, 'partido_id': f.strftime("%Y%m%d")}
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']
        
        st.markdown(f"<div style='background:#f0f2f6; padding:10px; border-radius:10px; text-align:center; border:1px solid #ddd; margin-bottom:10px;'><h3>Hoyo {h_idx} (Par {PAR_RIA_VIGO[h_idx]})</h3></div>", unsafe_allow_html=True)
        
        c_nav1, c_nav2 = st.columns(2)
        if c_nav1.button("⬅️ Anterior", use_container_width=True): 
            g['h_sel'] = max(1, h_idx-1)
            st.rerun()
        if c_nav2.button("Siguiente ➡️", use_container_width=True): 
            g['h_sel'] = min(18, h_idx+1)
            st.rerun()
        
        v_def = g['logs'][str(h_idx)]['s'] if str(h_idx) in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        
        st.markdown(f"<b style='color:{COLOR_A}'>{TODOS[0]}</b>", unsafe_allow_html=True)
        s1 = st.number_input("g1", 0, 10, v_def[0], key=f"s0_{h_idx}", label_visibility="collapsed")
        st.markdown(f"<b style='color:{COLOR_A}'>{TODOS[1]}</b>", unsafe_allow_html=True)
        s2 = st.number_input("g2", 0, 10, v_def[1], key=f"s1_{h_idx}", label_visibility="collapsed")
        st.markdown(f"<b style='color:{COLOR_B}'>{TODOS[2]}</b>", unsafe_allow_html=True)
        s3 = st.number_input("g3", 0, 10, v_def[2], key=f"s2_{h_idx}", label_visibility="collapsed")
        st.markdown(f"<b style='color:{COLOR_B}'>{TODOS[3]}</b>", unsafe_allow_html=True)
        s4 = st.number_input("g4", 0, 10, v_def[3], key=f"s3_{h_idx}", label_visibility="collapsed")
        
        golpes = [s1, s2, s3, s4]
        ya_g = str(h_idx) in g['logs'] and g['logs'][str(h_idx)]['s'] == golpes

        if st.button("✅ Sincronizado" if ya_g else "💾 Guardar Hoyo", type="primary", use_container_width=True, disabled=ya_g):
            pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, h_idx)
            g['logs'][str(h_idx)] = {'s': golpes, 'pts': (pa, pb), 'mvp': mi}
            fila = pd.DataFrame([{"id": f"{g['partido_id']}_H{h_idx}", "partido_id": g['partido_id'], "hoyo": h_idx, "fecha": g['fecha'], "temporada": "2026", "resultado_a": pa, "resultado_b": pb, "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4'], "s0": s1, "s1": s2, "s2": s3, "s3": s4}])
            if guardar_hoyo(fila): st.toast("Hoyo Guardado"); st.rerun()

        if g['logs']:
            st.write("---")
            match_a = sum(v['pts'][0] for v in g['logs'].values())
            match_b = sum(v['pts'][1] for v in g['logs'].values())
            
            st.markdown(f"""
                <div style="border: 2px solid #ccc; border-radius: 12px; padding: 15px; background-color: #ffffff; text-align: center; margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-around; align-items: center;">
                        <div><p style="margin: 0; font-weight: bold; color: {COLOR_A};">M & J</p><h1 style="margin: 0; color: {COLOR_A}; font-size: 2.2em;">{match_a:g}</h1></div>
                        <h2 style="margin: 0; color: #999;">vs</h2>
                        <div><p style="margin: 0; font-weight: bold; color: {COLOR_B};">R & L</p><h1 style="margin: 0; color: {COLOR_B}; font-size: 2.2em;">{match_b:g}</h1></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                with st.popover("🎯 MVP Hoyo", use_container_width=True):
                    if str(h_idx) in g['logs']:
                        h_data = g['logs'][str(h_idx)]['mvp']
                        df_h = pd.DataFrame([{"Jugador": TODOS[i], "Pts": h_data[f"p{i+1}"]} for i in range(4)])
                        st.table(df_h.style.apply(estilo_tabla, axis=1).format({"Pts": "{:.1f}"}))
            with c_m2:
                with st.popover("🏆 MVP Match", use_container_width=True):
                    rk_d = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
                    df_rd = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in rk_d.items()]).sort_values("Pts", ascending=False)
                    st.table(df_rd.style.apply(estilo_tabla, axis=1).format({"Pts": "{:.1f}"}))

        st.write("---")
        if st.button("🏁 Finalizar y Salir", use_container_width=True):
            del st.session_state.game; st.rerun()

# --- ADMIN ---
elif menu == "Admin":
    st.markdown("<h2 style='text-align: center;'>Administración</h2>", unsafe_allow_html=True)
    df = leer_datos()
    if not df.empty:
        partidos = df['partido_id'].unique()[::-1]
        for p_id in partidos:
            dp = df[df['partido_id'] == p_id]
            fecha_str = dp['fecha'].iloc[0]
            with st.expander(f"📅 Partido: {fecha_str}"):
                f_a, f_b = dp['resultado_a'].sum(), dp['resultado_b'].sum()
                st.write(f"**Final:** {f_a:g} (M&J) vs {f_b:g} (R&L)")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    with st.popover("🏆 MVP", use_container_width=True):
                        st.markdown(f"**MVP del {fecha_str}**")
                        rk_h = {TODOS[i]: dp[f"p{i+1}_pts"].sum() for i in range(4)}
                        df_rh = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in rk_h.items()]).sort_values("Pts", ascending=False)
                        st.table(df_rh.style.apply(estilo_tabla, axis=1).format({"Pts": "{:.1f}"}))

                if col2.button("✏️ Edit", key=f"ed_{p_id}", use_container_width=True):
                    rec = {str(int(f['hoyo'])): {'s':[int(f['s0']),int(f['s1']),int(f['s2']),int(f['s3'])], 'pts':(f['resultado_a'],f['resultado_b']), 'mvp':{'p1':f['p1_pts'],'p2':f['p2_pts'],'p3':f['p3_pts'],'p4':f['p4_pts']}} for _, f in dp.iterrows()}
                    st.session_state.game = {'fecha': fecha_str, 'temp': "2026", 'h_sel': 1, 'logs': rec, 'partido_id': p_id}
                    st.success("Cargado. Ve a Jugar/Editar")
                
                borrar_key = f"confirm_del_{p_id}"
                if borrar_key not in st.session_state: st.session_state[borrar_key] = False

                if col3.button("🗑️ Del", key=f"btn_del_{p_id}", use_container_width=True):
                    st.session_state[borrar_key] = True

                if st.session_state[borrar_key]:
                    st.error("⚠️ ¿Eliminar?")
                    c_c1, c_c2 = st.columns(2)
                    if c_c1.button("✅ SÍ", key=f"real_del_{p_id}", use_container_width=True, type="primary"):
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(worksheet="historial", data=df[df['partido_id'] != p_id])
                        st.session_state[borrar_key] = False
                        st.cache_data.clear(); st.rerun()
                    if c_c2.button("❌ NO", key=f"cancel_del_{p_id}", use_container_width=True):
                        st.session_state[borrar_key] = False
                        st.rerun()
