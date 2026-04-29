import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,5])}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
COLOR_A, COLOR_B = "#2e7d32", "#c62828"

if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu():
    st.session_state.menu_seleccionado = st.session_state.radio_menu

menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Estadísticas", "Admin"], 
                        index=["Inicio", "Jugar/Editar", "Estadísticas", "Admin"].index(st.session_state.menu_seleccionado),
                        key="radio_menu", on_change=cambiar_menu)

# --- 2. FUNCIONES DE DATOS (LIMPIEZA PROFUNDA) ---
def leer_datos():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0) 
        if df is None or df.empty: return pd.DataFrame()
        
        # Forzar tipos numéricos para evitar errores de mezcla (pantalla roja)
        cols_num = ['s0', 's1', 's2', 's3', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts', 'hoyo', 'resultado_a', 'resultado_b', 'temporada']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                if col in ['s0', 's1', 's2', 's3', 'hoyo', 'temporada']:
                    df[col] = df[col].astype(int)
        return df
    except: return pd.DataFrame()

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
    mvp = {f"p{i+1}": 0.0 for i in range(4)}
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
    fila = pd.DataFrame([{"id": f"{g['id']}_H{h}", "partido_id": g['id'], "hoyo": h, "fecha": g['fecha'], "temporada": anio_int, "resultado_a": pa, "resultado_b": pb, "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4'], "s0": s[0], "s1": s[1], "s2": s[2], "s3": s[3]}])
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    st.cache_data.clear() 
    df_actual = leer_datos()
    
    # Eliminamos el registro antiguo antes de insertar el nuevo (evita duplicidad)
    df_f = pd.concat([df_actual[df_actual["id"] != f"{g['id']}_H{h}"], fila], ignore_index=True) if not df_actual.empty else fila
    conn.update(worksheet="historial", data=df_f)
    st.cache_data.clear()

def generar_texto_whatsapp(partido_id):
    st.cache_data.clear()
    df_fresh = leer_datos()
    df_p = df_fresh[df_fresh['partido_id'] == partido_id]
    if df_p.empty: return "Actualizando..."
    
    f = df_p['fecha'].iloc[0]
    txt = f"⛳ *CAÑITA BRAVA - {f}*\n\n"
    pa_t, pb_t = df_p['resultado_a'].sum(), df_p['resultado_b'].sum()
    ma, mb = max(0, pa_t - pb_t), max(0, pb_t - pa_t)
    txt += f"🏆 *MATCH:* {TODOS[0]}/{TODOS[1]} *{ma:g}* vs *{mb:g}* {TODOS[2]}/{TODOS[3]}\n\n"
    
    txt += "🎖️ *MVP PARTIDO:*\n"
    mvps = {TODOS[i]: df_p[f'p{i+1}_pts'].sum() for i in range(4)}
    for j, (nom, p) in enumerate(sorted(mvps.items(), key=lambda x: x[1], reverse=True)):
        med = "🥇" if j==0 else "🥈" if j==1 else "🥉" if j==2 else "🎖️"
        txt += f"{med} {nom}: {p:g} pts\n"
        
    txt += "\n📊 *ESTADÍSTICAS:*\n"
    for i, jug in enumerate(TODOS):
        col = f's{i}'
        # Filtro de seguridad: s > 0 evita contar hoyos inexistentes o errores de edición
        t = df_p[df_p[col] > 0].copy()
        t['par_hoyo'] = t['hoyo'].map(PAR_RIA_VIGO)
        t['dif'] = t[col] - t['par_hoyo']
        e = len(t[t['dif'] <= -2]); b = len(t[t['dif'] == -1]); p = len(t[t['dif'] == 0])
        txt += f"• {jug}: {e}🦅 | {b}🐥 | {p}Par\n"
    return txt

# --- 3. PANTALLAS ---
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    temps = sorted(df['temporada'].unique().astype(int).tolist(), reverse=True) if not df.empty else [2026]
    sel_temp = st.selectbox("Temporada:", temps)
    pa_ini, pb_ini = 3.5, 3.5
    if not df.empty:
        df_t = df[df['temporada'] == int(sel_temp)]
        res = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
        for _, r in res.iterrows():
            if r['resultado_a'] > r['resultado_b']: pa_ini += 1
            elif r['resultado_b'] > r['resultado_a']: pb_ini += 1
            else: pa_ini += 0.5; pb_ini += 0.5
    st.markdown(f"""<div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;">
        <h3>MARCADOR {sel_temp}</h3><div style="display:flex;justify-content:space-around;">
        <div><h2 style="color:{COLOR_A};">{TODOS[0]}/{TODOS[1]}</h2><h1>{pa_ini:g}</h1></div>
        <div><h2 style="color:{COLOR_B};">{TODOS[2]}/{TODOS[3]}</h2><h1>{pb_ini:g}</h1></div></div></div>""", unsafe_allow_html=True)

elif st.session_state.menu_seleccionado == "Jugar/Editar":
    if 'game' not in st.session_state:
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': datetime.now().strftime("%Y%m%d%H%M%S")}
            st.rerun()
    else:
        g = st.session_state.game; h = int(g['h_sel']); ya = str(h) in g['logs']
        st.markdown(f"<h2 style='text-align:center; background:#2c3e50; color:white; border-radius:10px; padding:10px;'>HOYO {h} (PAR {PAR_RIA_VIGO[h]})</h2>", unsafe_allow_html=True)
        
        c_n1, c_n2 = st.columns(2)
        if c_n1.button("⬅️ Anterior", use_container_width=True): g['h_sel'] = max(1, h-1); st.rerun()
        if c_n2.button("Siguiente ➡️", use_container_width=True): g['h_sel'] = min(18, h+1); st.rerun()
        
        v_old = [int(x) for x in g['logs'][str(h)]['s']] if ya else [int(PAR_RIA_VIGO[h])]*4
        c_i, c_d = st.columns(2)
        s1 = c_i.number_input(TODOS[0], 0, 10, int(v_old[0]), key=f"s1_h{h}")
        s2 = c_i.number_input(TODOS[1], 0, 10, int(v_old[1]), key=f"s2_h{h}")
        s3 = c_d.number_input(TODOS[2], 0, 10, int(v_old[2]), key=f"s3_h{h}")
        s4 = c_d.number_input(TODOS[3], 0, 10, int(v_old[3]), key=f"s4_h{h}")
        
        # Lógica de botón inteligente
        if not ya:
            if st.button("💾 Guardar Hoyo", type="primary", use_container_width=True): ejecutar_guardado_automatico(); st.rerun()
        elif [s1, s2, s3, s4] != v_old:
            if st.button("🔄 Actualizar Cambios", type="primary", use_container_width=True): ejecutar_guardado_automatico(); st.rerun()
        else:
            st.button("✅ Guardado", disabled=True, use_container_width=True)

        # Marcador visual
        p_a = sum(v['pts'][0] for v in g['logs'].values()); p_b = sum(v['pts'][1] for v in g['logs'].values())
        ma, mb = max(0, p_a-p_b), max(0, p_b-p_a)
        st.markdown(f"""<div style="display:flex; gap:10px; justify-content:center; margin-top:20px;">
            <div style="flex:1; border:3px solid {COLOR_A}; border-radius:15px; padding:10px; text-align:center; background:#f1f8f1;">
            <span style="font-weight:900; color:{COLOR_A}; font-size:0.8em;">{TODOS[0]}/{TODOS[1]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_A};">{ma:g}</div></div>
            <div style="flex:1; border:3px solid {COLOR_B}; border-radius:15px; padding:10px; text-align:center; background:#fef2f2;">
            <span style="font-weight:900; color:{COLOR_B}; font-size:0.8em;">{TODOS[2]}/{TODOS[3]}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_B};">{mb:g}</div></div></div>""", unsafe_allow_html=True)
        
        if ya:
            st.write("---")
            c1, c2 = st.columns(2)
            with c1:
                with st.popover("🎯 MVP Hoyo", use_container_width=True):
                    df_h = pd.DataFrame([{"Jugador": TODOS[i], "Pts": g['logs'][str(h)]['mvp'][f"p{i+1}"]} for i in range(4)])
                    st.table(df_h.sort_values("Pts", ascending=False))
            with c2:
                with st.popover("🏆 MVP Acum", use_container_width=True):
                    mvp_ac = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
                    st.table(pd.DataFrame(mvp_ac.items(), columns=["Jugador", "Pts"]).sort_values("Pts", ascending=False))

        if st.button("🏁 Finalizar Partida", type="secondary", use_container_width=True): del st.session_state.game; st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Histórico")
    st.cache_data.clear()
    df = leer_datos()
    if df.empty: st.info("Sin datos.")
    else:
        partidos = df.groupby('partido_id').agg({'p1_pts':'sum','p2_pts':'sum','p3_pts':'sum','p4_pts':'sum'})
        mvps_c = {j: 0 for j in TODOS}
        for _, f_p in partidos.iterrows():
            m = f_p.max()
            if m > 0:
                for idx in f_p[f_p == m].index: mvps_c[TODOS[int(idx[1])-1]] += 1
        res = []
        for i, jug in enumerate(TODOS):
            col = f's{i}'; t = df[df[col] > 0].copy(); t['dif'] = t[col] - t['hoyo'].map(PAR_RIA_VIGO)
            res.append({"Jugador": jug, "MVP": int(mvps_c[jug]), "Eagle": len(t[t['dif'] <= -2]), "Birdie": len(t[t['dif'] == -1]), "Par": len(t[t['dif'] == 0])})
        st.table(pd.DataFrame(res).set_index("Jugador"))

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Admin")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id]
            with st.expander(f"📅 {dp['fecha'].iloc[0]}"):
                c1, c2, c3 = st.columns(3)
                c1.download_button("📱 WhatsApp", generar_texto_whatsapp(p_id), key=f"wa_{p_id}")
                if c2.button("✏️ Editar", key=f"ed_{p_id}"):
                    rec = {str(int(f['hoyo'])): {'s':[int(f['s0']),int(f['s1']),int(f['s2']),int(f['s3'])], 'pts':(f['resultado_a'],f['resultado_b']), 'mvp':{'p1':f['p1_pts'],'p2':f['p2_pts'],'p3':f['p3_pts'],'p4':f['p4_pts']}} for _, f in dp.iterrows()}
                    st.session_state.game = {'fecha': dp['fecha'].iloc[0], 'h_sel': 1, 'logs': rec, 'id': str(p_id)}; st.session_state.menu_seleccionado = "Jugar/Editar"; st.rerun()
                if st.button("🗑️ Borrar", key=f"del_{p_id}", type="primary"): 
                    st.connection("gsheets", type=GSheetsConnection).update(worksheet="historial", data=df[df['partido_id'] != p_id])
                    st.cache_data.clear(); st.rerun()
