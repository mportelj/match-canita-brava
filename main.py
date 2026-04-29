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

def generar_texto_whatsapp(g):
    txt = f"⛳ *CAÑITA BRAVA - {g['fecha']}*\n\n"
    pts_a = sum(v['pts'][0] for v in g['logs'].values())
    pts_b = sum(v['pts'][1] for v in g['logs'].values())
    m_a, m_b = max(0, pts_a - pts_b), max(0, pts_b - pts_a)
    txt += f"🏆 *MATCH:* {TODOS[0]}/{TODOS[1]} *{m_a:g}* vs *{m_b:g}* {TODOS[2]}/{TODOS[3]}\n\n"
    p_mvp = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
    ranking = sorted(p_mvp.items(), key=lambda x: x[1], reverse=True)
    txt += "🎖️ *MVP PARTIDO:*\n"
    for j, (nom, p) in enumerate(ranking):
        med = "🥇" if j==0 else "🥈" if j==1 else "🥉" if j==2 else "🎖️"
        txt += f"{med} {nom}: {p:g} pts\n"
    return txt

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
            st.markdown(f"<p style='color:{COLOR_A}; font-weight:900; margin-bottom:0;'>{TODOS[0]}</p>", unsafe_allow_html=True)
            s1 = st.number_input(TODOS[0], 0, 10, v[0], key=f"s1_h{h}", label_visibility="collapsed")
            st.markdown(f"<p style='color:{COLOR_A}; font-weight:900; margin-top:10px; margin-bottom:0;'>{TODOS[1]}</p>", unsafe_allow_html=True)
            s2 = st.number_input(TODOS[1], 0, 10, v[1], key=f"s2_h{h}", label_visibility="collapsed")
        with c_der:
            st.markdown(f"<p style='color:{COLOR_B}; font-weight:900; margin-bottom:0;'>{TODOS[2]}</p>", unsafe_allow_html=True)
            s3 = st.number_input(TODOS[2], 0, 10, v[2], key=f"s3_h{h}", label_visibility="collapsed")
            st.markdown(f"<p style='color:{COLOR_B}; font-weight:900; margin-top:10px; margin-bottom:0;'>{TODOS[3]}</p>", unsafe_allow_html=True)
            s4 = st.number_input(TODOS[3], 0, 10, v[3], key=f"s4_h{h}", label_visibility="collapsed")
        
        if ya_guardado: st.button("✅ Hoyo Registrado", disabled=True, use_container_width=True)
        else:
            if st.button("💾 Guardar Hoyo", type="primary", use_container_width=True): ejecutar_guardado_automatico(); st.rerun()

        # --- MARCADOR MATCH (DISEÑO GRANDE) ---
        pts_a = sum(v['pts'][0] for v in g['logs'].values())
        pts_b = sum(v['pts'][1] for v in g['logs'].values())
        m_a, m_b = max(0, pts_a - pts_b), max(0, pts_b - pts_a)
        
        st.markdown(f"<h4 style='text-align:center; color:#666; margin-top:15px;'>Marcador Match (Hoy)</h4>", unsafe_allow_html=True)
        st.markdown(f"""<div style="display:flex; gap:10px; justify-content:center; margin-bottom:20px;">
            <div style="flex:1; border:3px solid {COLOR_A}; border-radius:15px; padding:10px; text-align:center; background:#f1f8f1;">
            <span style="font-weight:900; color:{COLOR_A}; font-size:0.8em;">{TODOS[0]}/{TODOS[1]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_A};">{m_a:g}</div></div>
            <div style="flex:1; border:3px solid {COLOR_B}; border-radius:15px; padding:10px; text-align:center; background:#fef2f2;">
            <span style="font-weight:900; color:{COLOR_B}; font-size:0.8em;">{TODOS[2]}/{TODOS[3]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_B};">{m_b:g}</div></div></div>""", unsafe_allow_html=True)

        if ya_guardado:
            h_pts = g['logs'][str(h)]['pts']
            st.markdown(f"""<div style="background:#f0f2f6; border-radius:10px; padding:12px; margin-bottom:15px; text-align:center;">
                <div style="font-size:0.85em; color:#555; font-weight:bold;">PUNTOS HOYO {h}</div>
                <div style="display:flex; justify-content:space-around; font-size:1.3em;"><b>{h_pts[0]:g}</b> — <b>{h_pts[1]:g}</b></div></div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            with st.popover("🎯 MVP Hoyo", use_container_width=True):
                if ya_guardado:
                    df_h = pd.DataFrame([{"Jugador": TODOS[i], "Pts": g['logs'][str(h)]['mvp'][f"p{i+1}"]} for i in range(4)]).sort_values("Pts", ascending=False)
                    st.table(df_h.style.format({"Pts": "{:.1f}"}))
                else: st.info("Hoyo no guardado.")
        with c2:
            with st.popover("🏆 MVP Partido", use_container_width=True):
                p_mvp = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
                df_p = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in p_mvp.items()]).sort_values("Pts", ascending=False)
                st.table(df_p.style.format({"Pts": "{:.1f}"}))

        st.divider()
        if g['logs']: st.download_button("📱 Compartir WhatsApp", generar_texto_whatsapp(g), use_container_width=True)
        if st.button("🏁 Finalizar Partida", type="secondary", use_container_width=True): del st.session_state.game; st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas")
    df = leer_datos()
    if df.empty: st.info("No hay datos.")
    else:
        mvp_partidos = df.groupby('partido_id').agg({'p1_pts':'sum', 'p2_pts':'sum', 'p3_pts':'sum', 'p4_pts':'sum'})
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
            stats.append({"Jugador": jug, "MVP": conteo_mvp[jug], "Birdie": len(temp[temp['diff'] == -1]), "Par": len(temp[temp['diff'] == 0]), "Bogey": len(temp[temp['diff'] == 1])})
        df_final = pd.DataFrame(stats).set_index("Jugador")
        st.dataframe(df_final, use_container_width=True)
        st.divider()
        c1, c2 = st.columns(2)
        max_b = df_final['Birdie'].max()
        reyes_b = df_final[df_final['Birdie'] == max_b].index.tolist()
        c1.metric("Rey del Birdie 🐥", ", ".join(reyes_b), f"{max_b} Birdies")
        max_m = df_final['MVP'].max()
        reyes_m = df_final[df_final['MVP'] == max_m].index.tolist()
        c2.metric("Más MVP 🏆", ", ".join(reyes_m), f"{max_m} Veces")

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Admin")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id]
            with st.expander(f"📅 {dp['fecha'].iloc[0]}"):
                if st.button("🗑️ Borrar Partida", key=f"del_{p_id}"):
                    st.connection("gsheets", type=GSheetsConnection).update(worksheet="historial", data=df[df['partido_id'] != p_id])
                    st.cache_data.clear(); st.rerun()
