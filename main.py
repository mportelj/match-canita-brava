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
# ==========================================
# SECCIÓN: INICIO (Marcador de Temporada)
# ==========================================
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    
    # Definimos la temporada actual
    anio_actual = 2026
    temps = sorted(df['temporada'].unique().tolist(), reverse=True) if not df.empty else [anio_actual]
    if anio_actual not in temps: temps.insert(0, anio_actual)
    
    sel_temp = st.selectbox("Temporada:", temps)
    
    # Lógica de puntos acumulados de la temporada
    pa_t, pb_t = 3.5, 3.5  # Ventaja histórica inicial
    if not df.empty:
        df_t = df[df['temporada'] == int(sel_temp)]
        partidos = df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'})
        for _, r in partidos.iterrows():
            if r['resultado_a'] > r['resultado_b']: pa_t += 1
            elif r['resultado_b'] > r['resultado_a']: pb_t += 1
            else: pa_t += 0.5; pb_t += 0.5
            
    # Diseño de tarjeta de marcador de temporada
    st.markdown(f"""
        <div style="border: 2px solid #ccc; border-radius: 15px; padding: 20px; text-align: center; background: #f9f9f9; margin-top: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
            <h3 style="margin: 0; color: #555; text-transform: uppercase; letter-spacing: 2px;">MATCH {sel_temp}</h3>
            <div style="display: flex; justify-content: space-around; align-items: center; margin-top: 15px;">
                <div style="flex: 1;">
                    <h2 style="color: {COLOR_A}; margin: 0; font-size: 1.2em;">{EQUIPO_A_NOMBRES}</h2>
                    <h1 style="font-size: 4em; margin: 0; color: #333;">{pa_t:g}</h1>
                </div>
                <div style="font-size: 1.5em; font-weight: bold; color: #999;">VS</div>
                <div style="flex: 1;">
                    <h2 style="color: {COLOR_B}; margin: 0; font-size: 1.2em;">{EQUIPO_B_NOMBRES}</h2>
                    <h1 style="font-size: 4em; margin: 0; color: #333;">{pb_t:g}</h1>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# SECCIÓN: JUGAR / EDITAR (Modo Match Play)
# ==========================================
elif st.session_state.menu_seleccionado == "Jugar/Editar":
    # 1. Limpieza de seguridad: Si no hay juego en session_state, forzamos que no lea datos
    if 'game' not in st.session_state:
        st.subheader("🏁 Nueva Partida")
        st.info("No hay ninguna partida activa. Selecciona una fecha para empezar o edita una existente en Administración.")
        
        f = st.date_input("Fecha de la partida:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partida", use_container_width=True):
            # Creamos el nuevo ID único
            nuevo_id = datetime.now().strftime("%Y%m%d%H%M%S")
            st.session_state.game = {
                'fecha': f.strftime("%d/%m/%Y"), 
                'h_sel': 1, 
                'logs': {}, 
                'id': nuevo_id
            }
            st.rerun()
    
    # 2. Solo si existe 'game' en session_state, mostramos el marcador y los hoyos
    else:
        g = st.session_state.game
        df_p = leer_datos()
        
        # Filtramos estrictamente por el ID que tenemos en memoria
        df_partido_actual = df_p[df_p['partido_id'] == str(g['id'])]
        
        # --- A partir de aquí sigue el resto de tu código del marcador ---
        pts_a_total = df_partido_actual['resultado_a'].sum()
        pts_b_total = df_partido_actual['resultado_b'].sum()
        
        # ... (resto del código igual) ...

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
        # Filtrar IDs válidos
        ids_unicos = [pid for pid in df['partido_id'].unique() if pid and str(pid).strip() != ""]
        
        for p_id in ids_unicos[::-1]:
            dp = df[df['partido_id'] == p_id].sort_values('hoyo')
            
            if dp.empty:
                continue
                
            fecha_p = str(dp['fecha'].iloc[0])
            num_hoyos = len(dp)
            
            # Título limpio
            titulo_expander = f"📅 {fecha_p} — ({num_hoyos} hoyos jugados)"
            
            with st.expander(titulo_expander):
                c1, c2, c3 = st.columns([1, 1, 2])
                
                # --- BOTÓN EDITAR ---
                if c1.button("✏️ Editar", key=f"edit_{p_id}", use_container_width=True):
                    st.session_state.game = {
                        'fecha': fecha_p, 
                        'h_sel': 1, 
                        'logs': {}, 
                        'id': str(p_id)
                    }
                    st.session_state.menu_seleccionado = "Jugar/Editar"
                    st.rerun()
                
                # --- BOTÓN BORRAR CON CONFIRMACIÓN ---
                with c2:
                    # El popover actúa como el primer paso de seguridad
                    with st.popover("🗑️ Borrar", use_container_width=True):
                        st.warning("¿Estás seguro?")
                        if st.button("Sí, eliminar", key=f"conf_del_{p_id}", type="primary", use_container_width=True):
                            # Lógica de borrado
                            df_new = df[df['partido_id'] != p_id]
                            conn.update(worksheet="historial", data=df_new)
                            st.cache_data.clear()
                            st.success("Partido eliminado.")
                            st.rerun()
                
                with c3:
                    st.write("") 

    else:
        st.info("No hay datos en el historial.")
