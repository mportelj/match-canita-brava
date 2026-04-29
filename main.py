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

def cambiar_menu(nuevo_destino=None):
    if nuevo_destino:
        st.session_state.menu_seleccionado = nuevo_destino
    else:
        st.session_state.menu_seleccionado = st.session_state.radio_menu

def boton_volver_inicio():
    if st.button("🏠 Volver al Menú Principal", use_container_width=True):
        st.session_state.menu_seleccionado = "Inicio"
        st.rerun()

menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Admin"], 
                        index=["Inicio", "Jugar/Editar", "Admin"].index(st.session_state.menu_seleccionado),
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
        for c in ['resultado_a', 'resultado_b', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts', 's0', 's1', 's2', 's3']:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

def guardar_hoyo_db(df_fila):
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

# --- 4. LÓGICA DE PANTALLAS ---

if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    
    anios_db = df['temporada'].unique().tolist() if not df.empty else []
    anio_hoy = str(datetime.now().year)
    if anio_hoy not in anios_db: anios_db.append(anio_hoy)
    anios_finales = sorted(list(set(anios_db)), reverse=True)
    
    temp_sel = st.selectbox("📅 Seleccionar Temporada:", anios_finales, index=anios_finales.index(anio_hoy))

    p_ini_a, p_ini_b = PUNTOS_INICIO.get(temp_sel, (0.0, 0.0))
    df_temp = df[df['temporada'] == temp_sel] if not df.empty else pd.DataFrame()
    
    if not df_temp.empty:
        res = df_temp.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
        for _, r in res.iterrows():
            if r['resultado_a'] > r['resultado_b']: p_ini_a += 1
            elif r['resultado_b'] > r['resultado_a']: p_ini_b += 1
            else: p_ini_a += 0.5; p_ini_b += 0.5

    st.markdown(f"""<div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;margin-bottom:15px;">
        <h3 style="margin:0;">TEMPORADA {temp_sel}</h3><div style="display:flex;justify-content:space-around;align-items:center;">
        <div><h2 style="color:{COLOR_A};margin:0;font-size:1.1em;">{TODOS[0]} & {TODOS[1]}</h2><h1 style="margin:0;">{p_ini_a:g}</h1></div>
        <h2 style="color:#999;margin:0;">VS</h2>
        <div><h2 style="color:{COLOR_B};margin:0;font-size:1.1em;">{TODOS[2]} & {TODOS[3]}</h2><h1 style="margin:0;">{p_ini_b:g}</h1></div></div></div>""", unsafe_allow_html=True)

    with st.expander(f"🏆 Clasificación MVP {temp_sel}"):
        if not df_temp.empty:
            ranking = {TODOS[0]: df_temp['p1_pts'].sum(), TODOS[1]: df_temp['p2_pts'].sum(), TODOS[2]: df_temp['p3_pts'].sum(), TODOS[3]: df_temp['p4_pts'].sum()}
            df_rank = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in ranking.items()]).sort_values("Pts", ascending=False)
            st.table(df_rank.style.format({"Pts": "{:.1f}"}))
        else: st.info(f"Sin datos en {temp_sel}.")

elif st.session_state.menu_seleccionado == "Jugar/Editar":
    boton_volver_inicio()
    st.divider()
    
    if 'game' not in st.session_state:
        st.subheader("Nueva Partida")
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': f.strftime("%Y%m%d")}
            st.rerun()
    else:
        g = st.session_state.game
        h = g['h_sel']
        st.markdown(f"""<div style="background-color:#2c3e50; padding:10px; border-radius:10px; text-align:center; color:white; margin-bottom:10px;">
            <h2 style="margin:0; color:#ecf0f1; font-size:1.5em;">HOYO {h} (PAR {PAR_RIA_VIGO[h]})</h2></div>""", unsafe_allow_html=True)
        
        c_nav1, c_nav2 = st.columns(2)
        if c_nav1.button("⬅️ Anterior", key="nav_up_prev", use_container_width=True): ejecutar_guardado_automatico(); g['h_sel'] = max(1, h-1); st.rerun()
        if c_nav2.button("Siguiente ➡️", key="nav_up_next", use_container_width=True): ejecutar_guardado_automatico(); g['h_sel'] = min(18, h+1); st.rerun()
        
        v_guardados = g['logs'][str(h)]['s'] if str(h) in g['logs'] else [PAR_RIA_VIGO[h]]*4
        c_izq, c_der = st.columns(2)
        with c_izq:
            st.markdown(f"<p style='color:{COLOR_A}; font-weight:900; margin-bottom:0;'>{TODOS[0]}</p>", unsafe_allow_html=True)
            s1 = st.number_input(TODOS[0], 0, 10, v_guardados[0], key=f"s1_h{h}", label_visibility="collapsed")
            st.markdown(f"<p style='color:{COLOR_A}; font-weight:900; margin-top:10px; margin-bottom:0;'>{TODOS[1]}</p>", unsafe_allow_html=True)
            s2 = st.number_input(TODOS[1], 0, 10, v_guardados[1], key=f"s2_h{h}", label_visibility="collapsed")
        with c_der:
            st.markdown(f"<p style='color:{COLOR_B}; font-weight:900; margin-bottom:0;'>{TODOS[2]}</p>", unsafe_allow_html=True)
            s3 = st.number_input(TODOS[2], 0, 10, v_guardados[2], key=f"s3_h{h}", label_visibility="collapsed")
            st.markdown(f"<p style='color:{COLOR_B}; font-weight:900; margin-top:10px; margin-bottom:0;'>{TODOS[3]}</p>", unsafe_allow_html=True)
            s4 = st.number_input(TODOS[3], 0, 10, v_guardados[3], key=f"s4_h{h}", label_visibility="collapsed")
        
        actuales = [s1, s2, s3, s4]
        ya_guardado = (str(h) in g['logs'] and g['logs'][str(h)]['s'] == actuales)
        
        btn_label = "✅ Hoyo Guardado" if ya_guardado else "💾 Guardar Hoyo"
        if st.button(btn_label, type="primary", use_container_width=True, disabled=ya_guardado):
            ejecutar_guardado_automatico()
            st.toast("✅ Guardado")
            st.rerun()

        if g['logs']:
            total_a, total_b = sum(v['pts'][0] for v in g['logs'].values()), sum(v['pts'][1] for v in g['logs'].values())
            m_a, m_b = max(0, total_a - total_b), max(0, total_b - total_a)
            st.markdown(f"<h4 style='text-align:center; margin-bottom:5px; color:#666;'>Marcador del Match</h4>", unsafe_allow_html=True)
            st.markdown(f"""<div style="display:flex; gap:8px; align-items:center; justify-content:center; margin-bottom:20px;">
                <div style="flex:1; border:3px solid {COLOR_A}; border-radius:12px; padding:10px; text-align:center; background:#f1f8f1;">
                <span style="font-weight:900; color:{COLOR_A}; font-size:0.8em;">{TODOS[0]}/{TODOS[1]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_A};">{m_a:g}</div></div>
                <div style="font-weight:900; color:#999;">VS</div>
                <div style="flex:1; border:3px solid {COLOR_B}; border-radius:12px; padding:10px; text-align:center; background:#fef2f2;">
                <span style="font-weight:900; color:{COLOR_B}; font-size:0.8em;">{TODOS[2]}/{TODOS[3]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_B};">{m_b:g}</div></div></div>""", unsafe_allow_html=True)
            
            # --- MARCADOR DEL HOYO CON ESTADO "NO JUGADO" ---
            st.markdown(f"""<div style="background:#f0f2f6; border-radius:10px; padding:10px; margin-bottom:15px; border:1px solid #ddd; text-align:center;">
                <div style="font-size:0.85em; color:#555; margin-bottom:5px; font-weight:bold;">PUNTOS HOYO {h}</div>""", unsafe_allow_html=True)
            
            if str(h) in g['logs']:
                h_pts = g['logs'][str(h)]['pts']
                st.markdown(f"""<div style="display:flex; justify-content:space-around; align-items:center;">
                        <b style="color:{COLOR_A}; font-size:1.3em;">{h_pts[0]:g}</b>
                        <span style="color:#999;">—</span>
                        <b style="color:{COLOR_B}; font-size:1.3em;">{h_pts[1]:g}</b>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='color:#999; font-style:italic; font-size:1.1em;'>Hoyo No Jugado</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                with st.popover("🎯 MVP Hoyo", use_container_width=True):
                    if str(h) in g['logs']:
                        df_h = pd.DataFrame([{"Jugador": TODOS[i], "Pts": g['logs'][str(h)]['mvp'][f"p{i+1}"]} for i in range(4)]).sort_values("Pts", ascending=False)
                        st.table(df_h.style.format({"Pts": "{:.1f}"}))
                    else: st.info("Hoyo no jugado.")
            with c2:
                with st.popover("🏆 MVP Partido", use_container_width=True):
                    p_mvp = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
                    df_p = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in p_mvp.items()]).sort_values("Pts", ascending=False)
                    st.table(df_p.style.format({"Pts": "{:.1f}"}))

        st.divider()
        c_nav3, c_nav4 = st.columns(2)
        if c_nav3.button("⬅️ Anterior", key="nav_down_prev", use_container_width=True): ejecutar_guardado_automatico(); g['h_sel'] = max(1, h-1); st.rerun()
        if c_nav4.button("Siguiente ➡️", key="nav_down_next", use_container_width=True): ejecutar_guardado_automatico(); g['h_sel'] = min(18, h+1); st.rerun()

        if st.button("🏁 Finalizar Partida", type="secondary", use_container_width=True): del st.session_state.game; st.rerun()

elif st.session_state.menu_seleccionado == "Admin":
    boton_volver_inicio()
    st.divider()
    st.title("⚙️ Admin")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id]
            with st.expander(f"📅 {dp['fecha'].iloc[0]} (T. {dp['temporada'].iloc[0]})"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.popover("🏆 MVP", use_container_width=True):
                        rk = {TODOS[i]: dp[f"p{i+1}_pts"].sum() for i in range(4)}
                        st.table(pd.DataFrame([{"Jugador":k,"Pts":v} for k,v in rk.items()]).sort_values("Pts",ascending=False).style.format({"Pts":"{:.1f}"}))
                if c2.button("✏️ Editar", key=f"ed_{p_id}"):
                    rec = {str(int(f['hoyo'])): {'s':[int(f['s0']),int(f['s1']),int(f['s2']),int(f['s3'])], 'pts':(f['resultado_a'],f['resultado_b']), 'mvp':{'p1':f['p1_pts'],'p2':f['p2_pts'],'p3':f['p3_pts'],'p4':f['p4_pts']}} for _, f in dp.iterrows()}
                    st.session_state.game = {'fecha': dp['fecha'].iloc[0], 'h_sel': 1, 'logs': rec, 'id': p_id}
                    st.session_state.menu_seleccionado = "Jugar/Editar"
                    st.rerun()
                if c3.button("🗑️ Borrar", key=f"del_{p_id}"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="historial", data=df[df['partido_id'] != p_id])
                    st.rerun()
