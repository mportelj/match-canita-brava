import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# Configuración de pares - Hoyo 18 corregido a PAR 4
PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,4])}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
EQUIPO_A_NOMBRES = f"{TODOS[0]}/{TODOS[1]}"
EQUIPO_B_NOMBRES = f"{TODOS[2]}/{TODOS[3]}"
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

def calc_scratch(golpes, par):
    if golpes <= 0: return 0
    dif = golpes - par
    if dif <= -3: return 5 # Albatros
    if dif == -2: return 4 # Eagle
    if dif == -1: return 3 # Birdie
    if dif == 0:  return 2 # Par
    if dif == 1:  return 1 # Bogey
    return 0 # Doble+

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
    mvp = {f"p1": 0.0, f"p2": 0.0, f"p3": 0.0, f"p4": 0.0}
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
        <h3 style="margin:0;">MATCH {sel_temp}</h3>
        <div style="display:flex;justify-content:space-around; align-items:center; margin-top:15px;">
        <div><h2 style="color:{COLOR_A}; margin:0; font-size:1.2em;">{EQUIPO_A_NOMBRES}</h2><h1 style="font-size:3.5em; margin:0;">{pa_t:g}</h1></div>
        <div style="font-size:1.5em; font-weight:bold; color:#777;">VS</div>
        <div><h2 style="color:{COLOR_B}; margin:0; font-size:1.2em;">{EQUIPO_B_NOMBRES}</h2><h1 style="font-size:3.5em; margin:0;">{pb_t:g}</h1></div></div></div>""", unsafe_allow_html=True)

elif st.session_state.menu_seleccionado == "Jugar/Editar":
    if 'game' not in st.session_state:
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': datetime.now().strftime("%Y%m%d%H%M%S")}
            st.rerun()
    else:
        g = st.session_state.game
        opciones_hoyo = [f"Hoyo {i} (Par {PAR_RIA_VIGO[i]})" for i in range(1, 19)]
        seleccion = st.selectbox("Seleccionar Hoyo:", opciones_hoyo, index=int(g['h_sel'])-1)
        h = int(seleccion.split(" ")[1])
        g['h_sel'] = h
        
        ya = str(h) in g['logs']
        v_old = [int(x) for x in g['logs'][str(h)]['s']] if ya else [int(PAR_RIA_VIGO[h])]*4
        
        ci, cd = st.columns(2)
        s1 = ci.number_input(TODOS[0], 0, 15, v_old[0], key=f"s1_h{h}")
        s2 = ci.number_input(TODOS[1], 0, 15, v_old[1], key=f"s2_h{h}")
        s3 = cd.number_input(TODOS[2], 0, 15, v_old[2], key=f"s3_h{h}")
        s4 = cd.number_input(TODOS[3], 0, 15, v_old[3], key=f"s4_h{h}")
        
        if st.button("💾 Guardar Hoyo", type="primary", use_container_width=True):
            ejecutar_guardado_automatico()
            st.success(f"Hoyo {h} guardado")
            
        if ya:
            pts_a = sum(v['pts'][0] for v in g['logs'].values())
            pts_b = sum(v['pts'][1] for v in g['logs'].values())
            ma, mb = max(0, pts_a-pts_b), max(0, pts_b-pts_a)
            st.markdown(f"""<div style="display:flex; gap:10px; justify-content:center; margin-top:20px;">
                <div style="flex:1; border:3px solid {COLOR_A}; border-radius:15px; padding:10px; text-align:center; background:#f1f8f1;">
                <span style="font-weight:900; color:{COLOR_A}; font-size:0.8em;">{EQUIPO_A_NOMBRES}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_A};">{ma:g}</div></div>
                <div style="flex:1; border:3px solid {COLOR_B}; border-radius:15px; padding:10px; text-align:center; background:#fef2f2;">
                <span style="font-weight:900; color:{COLOR_B}; font-size:0.8em;">{EQUIPO_B_NOMBRES}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_B};">{mb:g}</div></div></div>""", unsafe_allow_html=True)
        
        st.write("---")
        if st.button("🏁 Finalizar Partida", use_container_width=True):
            del st.session_state.game
            st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Orden de Mérito")
    df = leer_datos()
    if not df.empty:
        res = []
        for i, jug in enumerate(TODOS):
            col = f's{i}'; t = df[df[col] > 0].copy()
            if t.empty: continue
            
            t['dif'] = t[col] - t['hoyo'].map(PAR_RIA_VIGO)
            tot = len(t)
            t['scr'] = t.apply(lambda r: calc_scratch(r[col], PAR_RIA_VIGO[r['hoyo']]), axis=1)
            
            # CORRECCIÓN AQUÍ: Forzamos a entero antes del formato
            dif_total = int(t['dif'].sum())
            txt_dif = f"{dif_total:+d}" if dif_total != 0 else "E"
            
            def fmt(c): return f"{len(t[c])} ({len(t[c])/tot:.0%})" if tot>0 else "0"
            res.append({"Jugador": jug, "+/- Par": txt_dif, "Scratch": int(t['scr'].sum()), 
                        "Bir": fmt(t['dif']==-1), "Par": fmt(t['dif']==0), "Bog": fmt(t['dif']==1), "T+": fmt(t['dif']>=2),
                        "_sort": dif_total})
        
        if res:
            st.dataframe(pd.DataFrame(res).sort_values("_sort").drop(columns=["_sort"]).set_index("Jugador"), use_container_width=True)
        else:
            st.info("Aún no hay datos para mostrar estadísticas.")

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Administración")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id].sort_values('hoyo')
            fecha_p = dp['fecha'].iloc[0]; temp_p = int(dp['temporada'].iloc[0])
            with st.expander(f"📅 {fecha_p}"):
                c1, c2, c3 = st.columns(3)
                if c3.button("📲 WhatsApp", key=f"wa_{p_id}", use_container_width=True):
                    df_t = df[df['temporada'] == temp_p]
                    res_wa = []
                    for i, jug in enumerate(TODOS):
                        col = f's{i}'
                        th = dp[dp[col] > 0].copy(); th['dif'] = th[col] - th['hoyo'].map(PAR_RIA_VIGO)
                        tt = df_t[df_t[col] > 0].copy(); tt['dif'] = tt[col] - tt['hoyo'].map(PAR_RIA_VIGO)
                        
                        d_h = int(th['dif'].sum()) if not th.empty else 0
                        d_t = int(tt['dif'].sum()) if not tt.empty else 0
                        txt_h = f"{d_h:+d}" if d_h != 0 else "E"
                        txt_t = f"{d_t:+d}" if d_t != 0 else "E"
                        
                        def l(d, t, txt):
                            if t == 0: return "Sin datos"
                            b = len(d[d['dif']==-1]); p = len(d[d['dif']==0]); bog = len(d[d['dif']==1]); tp = len(d[d['dif']>=2])
                            return (f"SCORE: {txt}\nB:{b} | P:{p} | Bog:{bog} | T+:{tp}")
                        
                        res_wa.append(f"👤 *{jug}*\n📍 *HOY*: {l(th, len(th), txt_h)}\n🌍 *TEMP*: {l(tt, len(tt), txt_t)}")

                    p_a, p_b = dp['resultado_a'].sum(), dp['resultado_b'].sum()
                    msg = (f"⛳ *CAÑITA BRAVA*\n📅 {fecha_p}\n\n"
                           f"🏆 *MATCH DIA*: 🟢{p_a:g} vs 🔴{p_b:g}\n\n"
                           f"🏅 *STATS (+/- PAR)*\n\n" + "\n\n".join(res_wa))
                    
                    wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                    st.link_button("Abrir WhatsApp", wa_url, use_container_width=True)
