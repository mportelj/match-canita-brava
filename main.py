import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

st.markdown("""
    <style>
    div[data-baseweb="select"] > div {
        font-size: 1.3rem !important;
        font-weight: bold !important;
    }
    label p { font-weight: bold !important; font-size: 1.1rem !important; }
    </style>
""", unsafe_allow_html=True)

PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,4])}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
EQUIPO_A_NOMBRES, EQUIPO_B_NOMBRES = f"{TODOS[0]}/{TODOS[1]}", f"{TODOS[2]}/{TODOS[3]}"
COLOR_A, COLOR_B = "#2e7d32", "#c62828"

if "menu_seleccionado" not in st.session_state: st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu(): st.session_state.menu_seleccionado = st.session_state.radio_menu

menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Estadísticas", "Admin"], 
                        index=["Inicio", "Jugar/Editar", "Estadísticas", "Admin"].index(st.session_state.menu_seleccionado),
                        key="radio_menu", on_change=cambiar_menu)

# --- 2. FUNCIONES DE DATOS ---
def leer_datos():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0) 
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [c.lower().strip() for c in df.columns]
        for col in ['temporada', 'hoyo', 's0', 's1', 's2', 's3']:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df.drop_duplicates(subset=['partido_id', 'hoyo'], keep='last')
    except: return pd.DataFrame()

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

def ejecutar_guardado_automatico():
    g = st.session_state.game
    h = int(g['h_sel'])
    s = [int(st.session_state[f"s{i+1}_h{h}"]) for i in range(4)]
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
    
    pa_t, pb_t = 3.5, 3.5 
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
    if 'game' not in st.session_state or st.session_state.game is None:
        st.subheader("No hay partida activa")
        f = st.date_input("Fecha de la partida:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Nueva Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': datetime.now().strftime("%Y%m%d%H%M%S")}
            st.rerun()
    else:
        g = st.session_state.game
        
        # --- 1. MARCADOR TOTAL DE LA JORNADA ---
        pts_a = sum(l['pts'][0] for l in g['logs'].values())
        pts_b = sum(l['pts'][1] for l in g['logs'].values())
        
        st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:10px; border-radius:10px; text-align:center; margin-bottom:20px;">
                <p style="margin:0; font-weight:bold; color:#555;">MARCADOR JORNADA</p>
                <div style="display:flex; justify-content:space-around; align-items:center;">
                    <div style="color:{COLOR_A};"><b>{EQUIPO_A_NOMBRES}</b><br><span style="font-size:25px;">{pts_a:g}</span></div>
                    <div style="font-size:20px; font-weight:bold;">VS</div>
                    <div style="color:{COLOR_B};"><b>{EQUIPO_B_NOMBRES}</b><br><span style="font-size:25px;">{pts_b:g}</span></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- 2. SELECCIÓN DE HOYO Y MARCADOR DEL HOYO ---
        opciones_hoyos = [f"Hoyo {i} (Par {PAR_RIA_VIGO[i]})" for i in range(1, 19)]
        seleccion = st.selectbox("**Hoyo:**", options=opciones_hoyos, index=g['h_sel'] - 1, key=f"h_act_{g['id']}")
        h = int(seleccion.split(" ")[1])
        st.session_state.game['h_sel'] = h
        
        ya = str(h) in g['logs']
        
        if ya:
            h_pts = g['logs'][str(h)]['pts']
            color_h = COLOR_A if h_pts[0] > h_pts[1] else COLOR_B if h_pts[1] > h_pts[0] else "#555"
            texto_h = "EMPATE" if h_pts[0] == h_pts[1] else f"GANA {EQUIPO_A_NOMBRES if h_pts[0]>h_pts[1] else EQUIPO_B_NOMBRES}"
            st.markdown(f"""<div style="text-align:center; color:{color_h}; font-weight:bold; border:1px solid {color_h}; border-radius:5px; margin-bottom:10px;">
                        Resultado Hoyo {h}: {h_pts[0]:g} - {h_pts[1]:g} ({texto_h})</div>""", unsafe_allow_html=True)

        # --- 3. ENTRADA DE GOLPES ---
        v_old = [int(x) for x in g['logs'][str(h)]['s']] if ya else [int(PAR_RIA_VIGO[h])]*4
        c1, c2 = st.columns(2)
        s1 = c1.number_input(TODOS[0], 0, 15, int(v_old[0]), step=1, key=f"s1_h{h}_{g['id']}")
        s2 = c1.number_input(TODOS[1], 0, 15, int(v_old[1]), step=1, key=f"s2_h{h}_{g['id']}")
        s3 = c2.number_input(TODOS[2], 0, 15, int(v_old[2]), step=1, key=f"s3_h{h}_{g['id']}")
        s4 = c2.number_input(TODOS[3], 0, 15, int(v_old[3]), step=1, key=f"s4_h{h}_{g['id']}")
        
        if st.button("💾 Guardar Hoyo", type="primary", use_container_width=True, disabled=ya):
            ejecutar_guardado_automatico()
            st.rerun()
            
        # --- 4. MVP DESPLEGABLE (BAJO BOTÓN) ---
        if ya:
            with st.expander("🏆 Ver Clasificación MVP"):
                df_hist = leer_datos()
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.caption("En este Hoyo")
                    for i, jug in enumerate(TODOS): st.write(f"**{jug}**: {g['logs'][str(h)]['mvp'][f'p{i+1}']:g}")
                with m2:
                    st.caption("Jornada")
                    for i, jug in enumerate(TODOS):
                        val = sum(l['mvp'][f'p{i+1}'] for l in g['logs'].values())
                        st.write(f"**{jug}**: {val:g}")
                with m3:
                    st.caption("Temporada")
                    for i, jug in enumerate(TODOS):
                        val = df_hist[f'p{i+1}_pts'].sum() if not df_hist.empty else 0
                        st.write(f"**{jug}**: {val:g}")

        st.divider()
        if st.button("🏁 Guardar Partida", use_container_width=True):
            st.session_state.game = None
            st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Orden de Mérito")
    df = leer_datos()
    if not df.empty:
        res = []
        for i, jug in enumerate(TODOS):
            t = df[df[f's{i}'] > 0].copy()
            if t.empty: continue
            pts = sum(5 if (r[f's{i}']-PAR_RIA_VIGO[r['hoyo']])<=-3 else 4 if (r[f's{i}']-PAR_RIA_VIGO[r['hoyo']])==-2 else 3 if (r[f's{i}']-PAR_RIA_VIGO[r['hoyo']])==-1 else 2 if (r[f's{i}']-PAR_RIA_VIGO[r['hoyo']])==0 else 1 if (r[f's{i}']-PAR_RIA_VIGO[r['hoyo']])==1 else 0 for _,r in t.iterrows())
            dif = (len(t)*2) - pts
            res.append({"Jugador": jug, "Hoyos": len(t), "MVP": round(t[f'p{i+1}_pts'].sum(),1), "+/- Par": f"{dif:+d}" if dif!=0 else "E", "Scratch": pts, "_s": dif})
        st.dataframe(pd.DataFrame(res).sort_values("_s").drop(columns="_s").set_index("Jugador"), use_container_width=True)

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Gestión")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id]
            with st.expander(f"Partida {dp['fecha'].iloc[0]} ({len(dp)} hoyos)"):
                c1, c2 = st.columns(2)
                if c1.button("✏️ Editar Partida", key=f"ed_{p_id}"):
                    logs = {str(r['hoyo']): {'s':[r['s0'],r['s1'],r['s2'],r['s3']], 'pts':(r['resultado_a'],r['resultado_b']), 
                            'mvp':{f'p{i+1}':r[f'p{i+1}_pts'] for i in range(4)}} for _,r in dp.iterrows()}
                    st.session_state.game = {'fecha':dp['fecha'].iloc[0], 'h_sel':1, 'logs':logs, 'id':p_id}
                    st.session_state.menu_seleccionado = "Jugar/Editar"
                    st.rerun()
                if c2.checkbox("Confirmar Borrado", key=f"del_cb_{p_id}"):
                    if st.button("🗑️ Eliminar", key=f"del_btn_{p_id}", type="primary"):
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(worksheet="historial", data=df[df['partido_id'] != p_id])
                        st.cache_data.clear()
                        st.rerun()
