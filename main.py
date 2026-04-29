import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse  # Para formatear el mensaje de WhatsApp

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,5])}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
COLOR_A, COLOR_B = "#2e7d32", "#c62828"
COLUMNAS_DB = ['id', 'partido_id', 'hoyo', 'fecha', 'temporada', 'resultado_a', 'resultado_b', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts', 's0', 's1', 's2', 's3']

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
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNAS_DB)
        df.columns = [c.lower().strip() for c in df.columns]
        for col in COLUMNAS_DB:
            if col not in df.columns: df[col] = None
        df = df.dropna(subset=['id'])
        df['id'] = df['id'].astype(str).str.strip()
        df = df.sort_values(by=['id']).drop_duplicates(subset=['id'], keep='last')
        cols_num = ['s0', 's1', 's2', 's3', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts', 'hoyo', 'resultado_a', 'resultado_b', 'temporada']
        for col in cols_num:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=COLUMNAS_DB)

def calcular_puntos_hoyo(scores, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    v = [int(s) if s > 0 else 99 for s in scores]
    ba, wa, bb, wb = min(v[0], v[1]), max(v[0], v[1]), min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    for i, s in enumerate(v):
        if s == 99: continue
        p_bonus = 2.0 if s <= par - 2 else (1.0 if s == par - 1 else 0)
        if i < 2: pa += p_bonus 
        else: pb += p_bonus
    mvp = {f"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}
    for i in range(4):
        if v[i] == 99: continue
        for j in range(4):
            if i != j and v[j] != 99 and v[i] < v[j]: mvp[f"p{i+1}"] += 0.5
        if v[i] <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif v[i] == par - 1: mvp[f"p{i+1}"] += 1.5
        elif v[i] == par: mvp[f"p{i+1}"] += 0.5
    return pa, pb, mvp

def ejecutar_guardado_automatico():
    if 'game' not in st.session_state: return
    g = st.session_state.game
    h = int(g['h_sel'])
    s = [int(st.session_state[f"s{i+1}_h{h}"]) for i in range(4)]
    pa, pb, mi = calcular_puntos_hoyo(s, h)
    g['logs'][str(h)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
    anio_int = int(datetime.strptime(g['fecha'], "%d/%m/%Y").year)
    fila_id = f"{g['id']}_H{h}"
    nueva_fila = pd.DataFrame([{"id": fila_id, "partido_id": g['id'], "hoyo": h, "fecha": g['fecha'], "temporada": anio_int, "resultado_a": pa, "resultado_b": pb, "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4'], "s0": s[0], "s1": s[1], "s2": s[2], "s3": s[3]}])
    conn = st.connection("gsheets", type=GSheetsConnection)
    st.cache_data.clear()
    df_actual = leer_datos()
    df_actual = df_actual[df_actual["id"] != fila_id]
    df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
    conn.update(worksheet="historial", data=df_final)
    st.cache_data.clear()

# --- 3. FUNCIÓN WHATSAPP ---
def boton_whatsapp(p_a, p_b, fecha):
    ganador = f"🏆 Ganadores: {TODOS[0]}/{TODOS[1]}" if p_a > p_b else (f"🏆 Ganadores: {TODOS[2]}/{TODOS[3]}" if p_b > p_a else "🤝 ¡Empate!")
    texto = f"⛳ *RESULTADO CAÑITA BRAVA*\n📅 Fecha: {fecha}\n\n🟢 {TODOS[0]}/{TODOS[1]}: *{p_a:g} pts*\n🔴 {TODOS[2]}/{TODOS[3]}: *{p_b:g} pts*\n\n{ganador}\n\n_Enviado desde Cañita App_"
    texto_url = urllib.parse.quote(texto)
    st.link_button("📲 Compartir en WhatsApp", f"https://wa.me/?text={texto_url}", use_container_width=True)

# --- 4. PANTALLAS ---
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    temps = sorted(df['temporada'].unique().astype(int).tolist(), reverse=True) if not df.empty else [2026]
    sel_temp = st.selectbox("Temporada:", temps)
    pa_total, pb_total = 3.5, 3.5
    if not df.empty:
        df_t = df[df['temporada'] == int(sel_temp)]
        partidos = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
        for _, r in partidos.iterrows():
            if r['resultado_a'] > r['resultado_b']: pa_total += 1
            elif r['resultado_b'] > r['resultado_a']: pb_total += 1
            else: pa_total += 0.5; pb_total += 0.5
    st.markdown(f"""<div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;">
        <h3>MARCADOR ACUMULADO {sel_temp}</h3><div style="display:flex;justify-content:space-around;">
        <div><h2 style="color:{COLOR_A};">{TODOS[0]}/{TODOS[1]}</h2><h1>{pa_total:g}</h1></div>
        <div><h2 style="color:{COLOR_B};">{TODOS[2]}/{TODOS[3]}</h2><h1>{pb_total:g}</h1></div></div></div>""", unsafe_allow_html=True)

elif st.session_state.menu_seleccionado == "Jugar/Editar":
    if 'game' not in st.session_state:
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': datetime.now().strftime("%Y%m%d%H%M%S")}
            st.rerun()
    else:
        g = st.session_state.game; h = int(g['h_sel']); ya = str(h) in g['logs']
        st.markdown(f"<h3 style='text-align:center;'>HOYO {h} (PAR {PAR_RIA_VIGO[h]})</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("⬅️", use_container_width=True): g['h_sel'] = max(1, h-1); st.rerun()
        if c2.button("➡️", use_container_width=True): g['h_sel'] = min(18, h+1); st.rerun()
        v_old = [int(x) for x in g['logs'][str(h)]['s']] if ya else [int(PAR_RIA_VIGO[h])]*4
        ci, cd = st.columns(2)
        s1 = ci.number_input(TODOS[0], 0, 10, v_old[0], key=f"s1_{h}")
        s2 = ci.number_input(TODOS[1], 0, 10, v_old[1], key=f"s2_{h}")
        s3 = cd.number_input(TODOS[2], 0, 10, v_old[2], key=f"s3_{h}")
        s4 = cd.number_input(TODOS[3], 0, 10, v_old[3], key=f"s4_{h}")
        if ya:
            pha, phb = g['logs'][str(h)]['pts']
            st.markdown(f"<p style='text-align:center;'>Puntos Hoyo: {pha:g} - {phb:g}</p>", unsafe_allow_html=True)
        if not ya:
            if st.button("💾 Guardar", type="primary", use_container_width=True): ejecutar_guardado_automatico(); st.rerun()
        elif [s1, s2, s3, s4] != v_old:
            if st.button("🔄 Actualizar", type="primary", use_container_width=True): ejecutar_guardado_automatico(); st.rerun()
        
        # MARCADOR EN VIVO Y WHATSAPP
        p_a = sum(v['pts'][0] for v in g['logs'].values()); p_b = sum(v['pts'][1] for v in g['logs'].values())
        st.markdown(f"<h2 style='text-align:center;'>{p_a:g} — {p_b:g}</h2>", unsafe_allow_html=True)
        
        # Botón de WhatsApp siempre visible para compartir el estado actual
        boton_whatsapp(p_a, p_b, g['fecha'])
        
        if st.button("🏁 Finalizar Partida", type="secondary", use_container_width=True): del st.session_state.game; st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Histórico")
    df = leer_datos()
    if not df.empty:
        df_clean = df.drop_duplicates(subset=['id'])
        partidos = df_clean.groupby('partido_id').agg({'p1_pts':'sum','p2_pts':'sum','p3_pts':'sum','p4_pts':'sum'})
        mvps = {j: 0 for j in TODOS}
        for _, f_p in partidos.iterrows():
            m = f_p.max()
            if m > 0:
                for idx in f_p[f_p == m].index: mvps[TODOS[int(idx[1])-1]] += 1
        res = []
        for i, jug in enumerate(TODOS):
            col = f's{i}'; t = df_clean[df_clean[col] > 0].copy()
            t['dif'] = t[col] - t['hoyo'].map(PAR_RIA_VIGO)
            res.append({"Jugador": jug, "MVP": int(mvps[jug]), "Eagle": len(t[t['dif'] <= -2]), "Birdie": len(t[t['dif'] == -1]), "Par": len(t[t['dif'] == 0])})
        st.table(pd.DataFrame(res).set_index("Jugador"))

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Admin")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id].sort_values('hoyo')
            with st.expander(f"📅 {dp['fecha'].iloc[0]}"):
                c1, c2, c3 = st.columns(3)
                if c1.button("✏️", key=f"e_{p_id}"):
                    rec = {str(int(f['hoyo'])): {'s':[int(f['s0']),int(f['s1']),int(f['s2']),int(f['s3'])], 'pts':(f['resultado_a'],f['resultado_b']), 'mvp':{'p1':f['p1_pts'],'p2':f['p2_pts'],'p3':f['p3_pts'],'p4':f['p4_pts']}} for _, f in dp.iterrows()}
                    st.session_state.game = {'fecha': dp['fecha'].iloc[0], 'h_sel': 1, 'logs': rec, 'id': str(p_id)}; st.session_state.menu_seleccionado = "Jugar/Editar"; st.rerun()
                with c2:
                    with st.popover("🗑️"):
                        if st.button("Confirmar", key=f"d_{p_id}"):
                            st.connection("gsheets", type=GSheetsConnection).update(worksheet="historial", data=df[df['partido_id'] != p_id])
                            st.cache_data.clear(); st.rerun()
                with c3: # Botón de WhatsApp para partidos antiguos
                    p_a, p_b = dp['resultado_a'].sum(), dp['resultado_b'].sum()
                    texto_ant = urllib.parse.quote(f"⛳ *RESUMEN GOLF*\n📅 {dp['fecha'].iloc[0]}\n🟢 {p_a:g} pts\n🔴 {p_b:g} pts")
                    st.link_button("📲", f"https://wa.me/?text={texto_ant}")
