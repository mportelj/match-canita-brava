import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,5])}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
COLOR_A, COLOR_B = "#2e7d32", "#c62828"
COL_NECESARIAS = ['id', 'partido_id', 'hoyo', 'fecha', 'temporada', 'resultado_a', 'resultado_b', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts', 's0', 's1', 's2', 's3']

if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu():
    st.session_state.menu_seleccionado = st.session_state.radio_menu

menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Estadísticas", "Admin"], 
                        index=["Inicio", "Jugar/Editar", "Estadísticas", "Admin"].index(st.session_state.menu_seleccionado),
                        key="radio_menu", on_change=cambiar_menu)

# --- 2. FUNCIONES DE DATOS ---
def leer_datos():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0) 
        if df is None or df.empty: return pd.DataFrame(columns=COL_NECESARIAS)
        df.columns = [c.lower().strip() for c in df.columns]
        df['partido_id'] = df['partido_id'].astype(str)
        df['hoyo'] = df['hoyo'].astype(int)
        df['temporada'] = pd.to_numeric(df['temporada'], errors='coerce').fillna(0).astype(int)
        return df.drop_duplicates(subset=['partido_id', 'hoyo'], keep='last')
    except:
        return pd.DataFrame(columns=COL_NECESARIAS)

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
    mvp = {f"p{i+1}": 0.0 for i in range(4)}
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
    s = [int(st.session_state[f"s1_h{h}"]), int(st.session_state[f"s2_h{h}"]), 
         int(st.session_state[f"s3_h{h}"]), int(st.session_state[f"s4_h{h}"])]
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
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_actual = leer_datos()
    df_actual = df_actual[~((df_actual['partido_id'] == p_id) & (df_actual['hoyo'] == h))]
    df_final = pd.concat([df_actual, pd.DataFrame([nueva_fila])], ignore_index=True)
    conn.update(worksheet="historial", data=df_final)
    st.cache_data.clear()

# --- 3. PANTALLAS ---
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    anio_actual = 2026
    temps = sorted(df['temporada'].unique().tolist(), reverse=True) if not df.empty else [anio_actual]
    if anio_actual not in temps: temps.insert(0, anio_actual)
    sel_temp = st.selectbox("Temporada:", temps, index=temps.index(anio_actual) if anio_actual in temps else 0)
    
    pa_t, pb_t = 3.5, 3.5 
    if not df.empty:
        df_t = df[df['temporada'] == int(sel_temp)]
        partidos = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
        for _, r in partidos.iterrows():
            if r['resultado_a'] > r['resultado_b']: pa_t += 1
            elif r['resultado_b'] > r['resultado_a']: pb_t += 1
            else: pa_t += 0.5; pb_t += 0.5
            
    st.markdown(f"""<div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;margin-top:10px;">
        <h3 style="margin:0;">MARCADOR ACTUAL {sel_temp}</h3>
        <div style="display:flex;justify-content:space-around; align-items:center; margin-top:15px;">
        <div><h2 style="color:{COLOR_A}; margin:0; font-size:1.2em;">{TODOS[0]}/{TODOS[1]}</h2><h1 style="font-size:3.5em; margin:0;">{pa_t:g}</h1></div>
        <div style="font-size:1.5em; font-weight:bold; color:#777;">VS</div>
        <div><h2 style="color:{COLOR_B}; margin:0; font-size:1.2em;">{TODOS[2]}/{TODOS[3]}</h2><h1 style="font-size:3.5em; margin:0;">{pb_t:g}</h1></div></div></div>""", unsafe_allow_html=True)

elif st.session_state.menu_seleccionado == "Jugar/Editar":
    if 'game' not in st.session_state:
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': datetime.now().strftime("%Y%m%d%H%M%S")}
            st.rerun()
    else:
        g = st.session_state.game; h = int(g['h_sel']); ya = str(h) in g['logs']
        st.markdown(f"<h2 style='text-align:center; background:#2c3e50; color:white; border-radius:10px; padding:10px;'>HOYO {h} (PAR {PAR_RIA_VIGO[h]})</h2>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        if c1.button("⬅️ Anterior", use_container_width=True): g['h_sel'] = max(1, h-1); st.rerun()
        if c2.button("Siguiente ➡️", use_container_width=True): g['h_sel'] = min(18, h+1); st.rerun()
        
        v_old = [int(x) for x in g['logs'][str(h)]['s']] if ya else [int(PAR_RIA_VIGO[h])]*4
        ci, cd = st.columns(2)
        s1 = ci.number_input(TODOS[0], 0, 15, v_old[0], key=f"s1_h{h}")
        s2 = ci.number_input(TODOS[1], 0, 15, v_old[1], key=f"s2_h{h}")
        s3 = cd.number_input(TODOS[2], 0, 15, v_old[2], key=f"s3_h{h}")
        s4 = cd.number_input(TODOS[3], 0, 15, v_old[3], key=f"s4_h{h}")
        
        if st.button("💾 Guardar Hoyo", type="primary", use_container_width=True):
            ejecutar_guardado_automatico()
            st.rerun()

        if ya:
            pha, phb = g['logs'][str(h)]['pts']
            st.markdown(f"<div style='text-align:center; font-weight:bold; background:#eef2f3; padding:10px; border-radius:10px; margin:10px 0;'>Puntos Hoyo {h}: <span style='color:{COLOR_A}'>{pha:g}</span> - <span style='color:{COLOR_B}'>{phb:g}</span></div>", unsafe_allow_html=True)

        pts_a = sum(v['pts'][0] for v in g['logs'].values()); pts_b = sum(v['pts'][1] for v in g['logs'].values())
        ma, mb = max(0, pts_a-pts_b), max(0, pts_b-pts_a)
        st.markdown(f"""<div style="display:flex; gap:10px; justify-content:center; margin-top:20px;">
            <div style="flex:1; border:3px solid {COLOR_A}; border-radius:15px; padding:10px; text-align:center; background:#f1f8f1;">
            <span style="font-weight:900; color:{COLOR_A}; font-size:0.8em;">{TODOS[0]}/{TODOS[1]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_A};">{ma:g}</div></div>
            <div style="flex:1; border:3px solid {COLOR_B}; border-radius:15px; padding:10px; text-align:center; background:#fef2f2;">
            <span style="font-weight:900; color:{COLOR_B}; font-size:0.8em;">{TODOS[2]}/{TODOS[3]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_B};">{mb:g}</div></div></div>""", unsafe_allow_html=True)
        
        st.write("---")
        if st.button("🏁 Finalizar Partida", use_container_width=True): del st.session_state.game; st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas")
    df = leer_datos()
    if not df.empty:
        partidos = df.groupby('partido_id').agg({'p1_pts':'sum','p2_pts':'sum','p3_pts':'sum','p4_pts':'sum'})
        mvps_count = {j: 0 for j in TODOS}
        for _, fila_p in partidos.iterrows():
            ganador_puntos = fila_p.max()
            if ganador_puntos > 0:
                for idx_jugador in fila_p[fila_p == ganador_puntos].index:
                    mvps_count[TODOS[int(idx_jugador[1])-1]] += 1
        res = []
        for i, jug in enumerate(TODOS):
            col = f's{i}'; t = df[df[col] > 0].copy(); t['dif'] = t[col] - t['hoyo'].map(PAR_RIA_VIGO)
            res.append({"Jugador": jug, "MVP": int(mvps_count[jug]), "Eagle": len(t[t['dif'] <= -2]), "Birdie": len(t[t['dif'] == -1]), "Par": len(t[t['dif'] == 0])})
        st.table(pd.DataFrame(res).set_index("Jugador"))

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Administración")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id].sort_values('hoyo')
            fecha_p = dp['fecha'].iloc[0]; temp_p = int(dp['temporada'].iloc[0])
            with st.expander(f"📅 {fecha_p}"):
                p_a, p_b = dp['resultado_a'].sum(), dp['resultado_b'].sum()
                c1, c2, c3 = st.columns(3)
                if c1.button("✏️", key=f"e_{p_id}", use_container_width=True):
                    rec = {str(int(f['hoyo'])): {'s':[f['s0'],f['s1'],f['s2'],f['s3']], 'pts':(f['resultado_a'],f['resultado_b']), 'mvp':{'p1':f['p1_pts'],'p2':f['p2_pts'],'p3':f['p3_pts'],'p4':f['p4_pts']}} for _, f in dp.iterrows()}
                    st.session_state.game = {'fecha': fecha_p, 'h_sel': 1, 'logs': rec, 'id': str(p_id)}
                    st.session_state.menu_seleccionado = "Jugar/Editar"; st.rerun()
                with c2:
                    with st.popover("🗑️", use_container_width=True):
                        if st.button("Borrar", key=f"del_{p_id}"):
                            st.connection("gsheets", type=GSheetsConnection).update(worksheet="historial", data=df[df['partido_id'] != p_id])
                            st.cache_data.clear(); st.rerun()
                with c3:
                    # CÁLCULO ACUMULADO TEMPORADA
                    df_temp = df[df['temporada'] == temp_p]
                    # Agrupar por partido_id y sumar para obtener ganadores de cada día
                    partidos_temp = df_temp.groupby('partido_id').agg({'resultado_a':'sum', 'resultado_b':'sum'})
                    ac_a, ac_b = 3.5, 3.5
                    for _, r in partidos_temp.iterrows():
                        if r['resultado_a'] > r['resultado_b']: ac_a += 1
                        elif r['resultado_b'] > r['resultado_a']: ac_b += 1
                        else: ac_a += 0.5; ac_b += 0.5

                    # RANKING MVP PARTIDA
                    mvp_pts = {TODOS[0]: dp['p1_pts'].sum(), TODOS[1]: dp['p2_pts'].sum(), TODOS[2]: dp['p3_pts'].sum(), TODOS[3]: dp['p4_pts'].sum()}
                    mvp_sorted = sorted(mvp_pts.items(), key=lambda x: x[1], reverse=True)
                    
                    # CATEGORÍAS PARTIDA
                    resumen_j = []
                    for i, jug in enumerate(TODOS):
                        col = f's{i}'; t = dp[dp[col] > 0].copy(); t['dif'] = t[col] - t['hoyo'].map(PAR_RIA_VIGO)
                        resumen_j.append(f"{jug}: {len(t[t['dif']<=-2])} Eagle, {len(t[t['dif']==-1])} Birdie, {len(t[t['dif']==0])} Par")

                    # MENSAJE WHATSAPP (Emojis simplificados para evitar errores de codificación)
                    msg = (f"⛳ *CAÑITA BRAVA*\n📅 {fecha_p}\n\n"
                           f"🏆 *RESULTADO MATCH*\n🟢 {TODOS[0]}/{TODOS[1]}: *{p_a:g}*\n🔴 {TODOS[2]}/{TODOS[3]}: *{p_b:g}*\n\n"
                           f"📈 *TEMPORADA {temp_p}*\nEquipo A: *{ac_a:g}* |  Equipo B: *{ac_b:g}*\n\n"
                           f"⭐ *MVP RANKING*\n" + "\n".join([f"{i+1}. {n}: {p:g} pts" for i, (n, p) in enumerate(mvp_sorted)]) +
                           f"\n\n🏅 *RESUMEN*\n" + "\n".join(resumen_j))
                    
                    st.link_button("📲", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)
