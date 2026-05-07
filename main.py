import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# Corregido: Par del campo según tu lista
PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,5])}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
EQUIPO_A_NOMBRES = f"{TODOS[0]}/{TODOS[1]}"
EQUIPO_B_NOMBRES = f"{TODOS[2]}/{TODOS[3]}"
COLOR_A, COLOR_B = "#2e7d32", "#c62828"
COL_NECESARIAS = ['id', 'partido_id', 'hoyo', 'fecha', 'temporada', 'resultado_a', 'resultado_b', 'p1_pts', 'p2_pts', 'p3_pts', 'p4_pts', 's0', 's1', 's2', 's3']

# Conexión global para evitar NameError
conn = st.connection("gsheets", type=GSheetsConnection)

if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu():
    st.session_state.menu_seleccionado = st.session_state.radio_menu

# --- 2. FUNCIONES DE DATOS ---
def leer_datos():
    try:
        # Forzamos ttl=0 para leer siempre lo último de la nube
        df = conn.read(worksheet="historial", ttl=0) 
        if df is None or df.empty: 
            return pd.DataFrame(columns=COL_NECESARIAS)
        
        # Normalización de columnas a minúsculas para evitar KeyError
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Asegurar tipos de datos para filtros de Pandas
        df['partido_id'] = df['partido_id'].astype(str)
        df['hoyo'] = pd.to_numeric(df['hoyo'], errors='coerce').fillna(0).astype(int)
        df['temporada'] = pd.to_numeric(df['temporada'], errors='coerce').fillna(0).astype(int)
        df['fecha'] = df['fecha'].astype(str)
        
        return df.drop_duplicates(subset=['partido_id', 'hoyo'], keep='last')
    except:
        return pd.DataFrame(columns=COL_NECESARIAS)

def calcular_puntos_hoyo(scores, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    v = [int(s) for s in scores]
    # Lógica Match Play Parejas
    ba, wa, bb, wb = min(v[0], v[1]), max(v[0], v[1]), min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    
    # Bonus Birdie/Eagle para el equipo
    for i, s in enumerate(v):
        p_bonus = 2.0 if s <= par - 2 else (1.0 if s == par - 1 else 0)
        if i < 2: pa += p_bonus 
        else: pb += p_bonus
        
    # Puntos MVP Individuales
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
    # Recuperamos los valores de los inputs usando las keys dinámicas
    s = [
        int(st.session_state[f"s1_h{h}_r{st.session_state.get('refresco_id',0)}"]),
        int(st.session_state[f"s2_h{h}_r{st.session_state.get('refresco_id',0)}"]), 
        int(st.session_state[f"s3_h{h}_r{st.session_state.get('refresco_id',0)}"]),
        int(st.session_state[f"s4_h{h}_r{st.session_state.get('refresco_id',0)}"])
    ]
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
    
    df_actual = leer_datos()
    # Eliminar si ya existe para sobreescribir
    df_actual = df_actual[~((df_actual['partido_id'] == p_id) & (df_actual['hoyo'] == h))]
    df_final = pd.concat([df_actual, pd.DataFrame([nueva_fila])], ignore_index=True)
    
    conn.update(worksheet="historial", data=df_final)
    st.cache_data.clear()

# --- 3. NAVEGACIÓN ---
menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Estadísticas", "Admin"], 
                       index=["Inicio", "Jugar/Editar", "Estadísticas", "Admin"].index(st.session_state.menu_seleccionado),
                       key="radio_menu", on_change=cambiar_menu)

# --- 4. PANTALLAS ---
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    anio_actual = 2026
    temps = sorted(df['temporada'].unique().tolist(), reverse=True) if not df.empty else [anio_actual]
    
    sel_temp = st.selectbox("Temporada:", temps)
    
    pa_t, pb_t = 3.5, 3.5 # Ventaja histórica inicial
    if not df.empty:
        df_t = df[df['temporada'] == int(sel_temp)]
        partidos = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
        for _, r in partidos.iterrows():
            if r['resultado_a'] > r['resultado_b']: pa_t += 1
            elif r['resultado_b'] > r['resultado_a']: pb_t += 1
            else: pa_t += 0.5; pb_t += 0.5
            
    st.markdown(f"""
        <div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;margin-top:10px;">
            <h3 style="margin:0;">MATCH {sel_temp}</h3>
            <div style="display:flex;justify-content:space-around; align-items:center; margin-top:15px;">
                <div><h2 style="color:{COLOR_A}; margin:0; font-size:1.2em;">{EQUIPO_A_NOMBRES}</h2><h1 style="font-size:3.5em; margin:0;">{pa_t:g}</h1></div>
                <div style="font-size:1.5em; font-weight:bold; color:#777;">VS</div>
                <div><h2 style="color:{COLOR_B}; margin:0; font-size:1.2em;">{EQUIPO_B_NOMBRES}</h2><h1 style="font-size:3.5em; margin:0;">{pb_t:g}</h1></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

elif st.session_state.menu_seleccionado == "Jugar/Editar":
    if 'refresco_id' not in st.session_state: st.session_state.refresco_id = 0

    if 'game' not in st.session_state:
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': datetime.now().strftime("%Y%m%d%H%M%S")}
            st.rerun()
    else:
        g = st.session_state.game; h = int(g['h_sel'])
        # Cargar datos de la nube para este hoyo si existen
        df_edit = leer_datos()
        fila_hoyo = df_edit[(df_edit['partido_id'] == str(g['id'])) & (df_edit['hoyo'] == h)]
        ya = not fila_hoyo.empty

        st.markdown(f"<h2 style='text-align:center; background:#2c3e50; color:white; border-radius:10px; padding:10px;'>HOYO {h} (PAR {PAR_RIA_VIGO[h]})</h2>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        if c1.button("⬅️ Anterior", use_container_width=True): 
            g['h_sel'] = max(1, h-1)
            st.session_state.refresco_id += 1
            st.rerun()
        if c2.button("Siguiente ➡️", use_container_width=True): 
            g['h_sel'] = min(18, h+1)
            st.session_state.refresco_id += 1
            st.rerun()

        # Determinar valores de los inputs
        if ya:
            v_old = [int(fila_hoyo.iloc[0]['s0']), int(fila_hoyo.iloc[0]['s1']), int(fila_hoyo.iloc[0]['s2']), int(fila_hoyo.iloc[0]['s3'])]
        else:
            v_old = [int(PAR_RIA_VIGO[h])]*4

        ci, cd = st.columns(2)
        # IMPORTANTE: La KEY incluye el refresco_id para forzar a Streamlit a actualizar el valor visual
        rid = st.session_state.refresco_id
        s1 = ci.number_input(TODOS[0], 1, 15, v_old[0], key=f"s1_h{h}_r{rid}")
        s2 = ci.number_input(TODOS[1], 1, 15, v_old[1], key=f"s2_h{h}_r{rid}")
        s3 = cd.number_input(TODOS[2], 1, 15, v_old[2], key=f"s3_h{h}_r{rid}")
        s4 = cd.number_input(TODOS[3], 1, 15, v_old[3], key=f"s4_h{h}_r{rid}")

        if st.button("💾 Guardar Hoyo", type="primary", use_container_width=True):
            ejecutar_guardado_automatico()
            st.success("Hoyo guardado")
            st.rerun()

        # Resumen del partido actual
        df_p = leer_datos()
        df_p = df_p[df_p['partido_id'] == str(g['id'])]
        pts_a = df_p['resultado_a'].sum()
        pts_b = df_p['resultado_b'].sum()
        
        ma, mb = max(0, pts_a-pts_b), max(0, pts_b-pts_a)
        st.markdown(f"""<div style="display:flex; gap:10px; justify-content:center; margin-top:20px;">
            <div style="flex:1; border:3px solid {COLOR_A}; border-radius:15px; padding:10px; text-align:center; background:#f1f8f1;">
            <span style="font-weight:900; color:{COLOR_A}; font-size:0.8em;">{EQUIPO_A_NOMBRES}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_A};">{ma:g}</div></div>
            <div style="flex:1; border:3px solid {COLOR_B}; border-radius:15px; padding:10px; text-align:center; background:#fef2f2;">
            <span style="font-weight:900; color:{COLOR_B}; font-size:0.8em;">{EQUIPO_B_NOMBRES}</span><div style="font-size:2.5em; font-weight:900; color:{COLOR_B};">{mb:g}</div></div></div>""", unsafe_allow_html=True)

        if st.button("🏁 Finalizar Partida", use_container_width=True):
            if 'game' in st.session_state: del st.session_state.game
            st.rerun()

elif st.session_state.menu_seleccionado == "Estadísticas":
    st.title("📊 Estadísticas Temporada")
    df = leer_datos()
    if not df.empty:
        # Lógica de MVPs y Medias corregida para nombres en minúsculas
        res = []
        for i, jug in enumerate(TODOS):
            col_s = f's{i}'
            t = df[df[col_s] > 0].copy()
            t['dif'] = t[col_s] - t['hoyo'].map(PAR_RIA_VIGO)
            tot = len(t)
            def fmt(c): return f"{len(t[c])} ({len(t[c])/tot:.0%})" if tot>0 else "0"
            res.append({"Jugador": jug, "Eag": fmt(t['dif']<=-2), "Bir": fmt(t['dif']==-1), "Par": fmt(t['dif']==0), "Bog": fmt(t['dif']==1), "Dbg": fmt(t['dif']==2)})
        st.dataframe(pd.DataFrame(res).set_index("Jugador"), use_container_width=True)

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Administración")
    df = leer_datos()
    
    if not df.empty:
        # Obtenemos los IDs únicos y los recorremos
        ids_unicos = [pid for pid in df['partido_id'].unique() if pid and str(pid).strip() != ""]
        
        for p_id in ids_unicos[::-1]:
            dp = df[df['partido_id'] == p_id].sort_values('hoyo')
            
            # --- CORRECCIÓN CRÍTICA AQUÍ ---
            if dp.empty:
                continue # Si el partido no tiene filas, saltamos al siguiente
                
            # Ahora es seguro usar iloc[0]
            fecha_p = str(dp['fecha'].iloc[0])
            temp_p = int(dp['temporada'].iloc[0]) if 'temporada' in dp.columns else 2026
            
            with st.expander(f"📅 {fecha_p} (ID: {p_id})"):
                c1, c2 = st.columns(2)
                
                if c1.button("✏️ Editar", key=f"edit_{p_id}"):
                    st.session_state.game = {'fecha': fecha_p, 'h_sel': 1, 'logs': {}, 'id': str(p_id)}
                    st.session_state.menu_seleccionado = "Jugar/Editar"
                    st.rerun()
                
                if c2.button("🗑️ Borrar Partido", key=f"del_{p_id}", type="primary"):
                    df_new = df[df['partido_id'] != p_id]
                    conn.update(worksheet="historial", data=df_new)
                    st.cache_data.clear()
                    st.success(f"Partido {p_id} eliminado")
                    st.rerun()
    else:
        st.info("No hay partidos registrados en el historial.")
