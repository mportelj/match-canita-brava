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
        for col in COL_NECESARIAS:
            if col not in df.columns: df[col] = 0
            
        # Limpiar IDs y eliminar duplicados estrictamente
        df['id'] = df['id'].astype(str).str.strip()
        df = df.drop_duplicates(subset=['id'], keep='last')
        return df
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
    if 'game' not in st.session_state: return
    g = st.session_state.game
    h = int(g['h_sel'])
    s = [int(st.session_state[f"s{i+1}_h{h}"]) for i in range(4)]
    pa, pb, mi = calcular_puntos_hoyo(s, h)
    
    # Actualizar estado en sesión
    g['logs'][str(h)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
    anio_int = int(datetime.strptime(g['fecha'], "%d/%m/%Y").year)
    fila_id = f"{g['id']}_H{h}"
    
    # Crear la fila nueva
    nueva_fila = {
        "id": fila_id, "partido_id": str(g['id']), "hoyo": h, "fecha": g['fecha'], 
        "temporada": anio_int, "resultado_a": pa, "resultado_b": pb, 
        "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4'], 
        "s0": s[0], "s1": s[1], "s2": s[2], "s3": s[3]
    }
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_actual = leer_datos()
    
    # ELIMINACIÓN REAL: Quitamos cualquier fila que coincida con este ID antes de insertar
    df_actual = df_actual[df_actual["id"] != fila_id].copy()
    
    # Insertar y limpiar duplicados una vez más por seguridad
    df_final = pd.concat([df_actual, pd.DataFrame([nueva_fila])], ignore_index=True)
    df_final = df_final.drop_duplicates(subset=['id'], keep='last')
    
    conn.update(worksheet="historial", data=df_final)
    st.cache_data.clear()

# --- 3. PANTALLAS ---
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    if not df.empty:
        temps = sorted(df['temporada'].unique().astype(int).tolist(), reverse=True)
        sel_temp = st.selectbox("Temporada:", temps)
        df_t = df[df['temporada'] == int(sel_temp)]
        
        pa_t, pb_t = 3.5, 3.5
        partidos = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
        for _, r in partidos.iterrows():
            if r['resultado_a'] > r['resultado_b']: pa_t += 1
            elif r['resultado_b'] > r['resultado_a']: pb_t += 1
            else: pa_t += 0.5; pb_t += 0.5
            
        st.markdown(f"""<div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;">
            <h3>MARCADOR ACUMULADO {sel_temp}</h3><div style="display:flex;justify-content:space-around;">
            <div><h2 style="color:{COLOR_A};">{TODOS[0]}/{TODOS[1]}</h2><h1>{pa_t:g}</h1></div>
            <div><h2 style="color:{COLOR_B};">{TODOS[2]}/{TODOS[3]}</h2><h1>{pb_t:g}</h1></div></div></div>""", unsafe_allow_html=True)

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

        pts_a = sum(v['pts'][0] for v in g['logs'].values()); pts_b = sum(v['pts'][1] for v in g['logs'].values())
        ma, mb = max(0, pts_a-pts_b), max(0, pts_b-pts_a)
        st.markdown(f"""<div style="display:flex; gap:10px; justify-content:center; margin-top:20px;">
            <div style="flex:1; border:3px solid {COLOR_A}; border-radius:15px; padding:10px; text-align:center;">
            <span style="color:{COLOR_A};">{TODOS[0]}/{TODOS[1]}</span><h1>{ma:g}</h1></div>
            <div style="flex:1; border:3px solid {COLOR_B}; border-radius:15px; padding:10px; text-align:center;">
            <span style="color:{COLOR_B};">{TODOS[2]}/{TODOS[3]}</span><h1>{mb:g}</h1></div></div>""", unsafe_allow_html=True)
        
        if st.button("🏁 Finalizar Partida", use_container_width=True): del st.session_state.game; st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas")
    df = leer_datos()
    if not df.empty:
        partidos = df.groupby('partido_id').agg({'p1_pts':'sum','p2_pts':'sum','p3_pts':'sum','p4_pts':'sum'})
        mvps = {j: 0 for j in TODOS}
        for _, f_p in partidos.iterrows():
            m = f_p.max()
            if m > 0:
                for idx in f_p[f_p == m].index: mvps[TODOS[int(idx[1])-1]] += 1
        
        res = []
        for i, jug in enumerate(TODOS):
            col = f's{i}'
            # Solo contamos hoyos donde el jugador realmente jugó (golpes > 0)
            t = df[df[col] > 0].copy()
            t['dif'] = t[col] - t['hoyo'].map(PAR_RIA_VIGO)
            res.append({
                "Jugador": jug, "MVP": int(mvps[jug]), 
                "Eagle": len(t[t['dif'] <= -2]), "Birdie": len(t[t['dif'] == -1]), "Par": len(t[t['dif'] == 0])
            })
        st.table(pd.DataFrame(res).set_index("Jugador"))

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Admin")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id].sort_values('hoyo')
            with st.expander(f"📅 Partida: {dp['fecha'].iloc[0]}"):
                if st.button("✏️ Editar", key=f"e_{p_id}"):
                    rec = {str(int(f['hoyo'])): {'s':[f['s0'],f['s1'],f['s2'],f['s3']], 'pts':(f['resultado_a'],f['resultado_b']), 'mvp':{'p1':f['p1_pts'],'p2':f['p2_pts'],'p3':f['p3_pts'],'p4':f['p4_pts']}} for _, f in dp.iterrows()}
                    st.session_state.game = {'fecha': dp['fecha'].iloc[0], 'h_sel': 1, 'logs': rec, 'id': str(p_id)}
                    st.session_state.menu_seleccionado = "Jugar/Editar"; st.rerun()
                if st.button("🗑️ Borrar", key=f"d_{p_id}"):
                    st.connection("gsheets", type=GSheetsConnection).update(worksheet="historial", data=df[df['partido_id'] != p_id])
                    st.cache_data.clear(); st.rerun()
