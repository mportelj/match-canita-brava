import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import json
import time

# --- CONFIGURACIÓN ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}
TODOS = ["MANUEL", "JOSE", "ROGE", "LALO"]
HISTORICO_PUNTOS = 3.5

st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# --- FUNCIONES DE BASE DE DATOS ---
def leer_datos():
    # Forzamos la limpieza de caché de Streamlit antes de leer
    st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "logs_json"])
        df = df.dropna(subset=['id'])
        df['id'] = df['id'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame(columns=["id", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "logs_json"])

def guardar_partida(df_partida):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 1. Leer lo que hay ahora mismo
        df_actual = leer_datos()
        id_nuevo = str(df_partida["id"].iloc[0]).strip()
        
        # 2. Filtrar: Quitamos cualquier fila que tenga nuestro ID
        if not df_actual.empty:
            df_final = df_actual[df_actual["id"] != id_nuevo].copy()
            df_final = pd.concat([df_final, df_partida], ignore_index=True)
        else:
            df_final = df_partida

        # 3. ELIMINAR DUPLICADOS (Seguro por si el filtro falló)
        df_final = df_final.drop_duplicates(subset=['id'], keep='last')

        # 4. ACTUALIZAR
        conn.update(worksheet="historial", data=df_final)
        
        # 5. ESPERA DE SEGURIDAD (Para que Google Sheets se actualice)
        time.sleep(1) 
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- MOTOR DE CÁLCULO ---
def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    scores = [s1, s2, s3, s4]
    v = [s if s > 0 else 99 for s in scores]
    
    # Match
    ba, wa = min(v[0], v[1]), max(v[0], v[1])
    bb, wb = min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    
    # Bonus
    for s in [s1, s2]:
        if 0 < s <= par - 2: pa += 2.0
        elif 0 < s == par - 1: pa += 1.0
    for s in [s3, s4]:
        if 0 < s <= par - 2: pb += 2.0
        elif 0 < s == par - 1: pb += 1.0

    # MVP
    mvp = {f"p{i+1}": 0.0 for i in range(4)}
    for i in range(4):
        if scores[i] <= 0: continue
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]: mvp[f"p{i+1}"] += 0.5
        if scores[i] <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif scores[i] == par - 1: mvp[f"p{i+1}"] += 1.5
        elif scores[i] == par: mvp[f"p{i+1}"] += 0.5
    return pa, pb, mvp

# --- UI ---
menu = st.sidebar.radio("Menú", ["Inicio", "Jugar/Editar", "Admin"])

if menu == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    if not df.empty:
        # Agrupación final de seguridad
        df_u = df.sort_values('id').groupby('id').tail(1)
        wins_a = len(df_u[df_u['resultado_a'].astype(float) > df_u['resultado_b'].astype(float)])
        wins_b = len(df_u[df_u['resultado_b'].astype(float) > df_u['resultado_a'].astype(float)])
        
        st.subheader("Marcador Temporada")
        c1, c2 = st.columns(2)
        c1.metric("MANU & JOSE", f"{HISTORICO_PUNTOS + wins_a}")
        c2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b}")
        
        mvps = {TODOS[i]: df_u[f"p{i+1}_pts"].astype(float).sum() for i in range(4)}
        st.table(pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in mvps.items()]).sort_values("Pts", ascending=False))

elif menu == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.subheader("Nueva Partida")
        f = st.date_input("Fecha:", datetime.now())
        if st.button("🚀 Iniciar"):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'h_sel': 1, 'logs': {}, 'edit_id': f.strftime("%Y%m%d")}
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']
        
        cols_nav = st.columns([1, 2, 1])
        if cols_nav[0].button("⬅️") and h_idx > 1: g['h_sel'] -= 1; st.rerun()
        cols_nav[1].markdown(f"<h3 style='text-align:center;'>Hoyo {h_idx}</h3>", unsafe_allow_html=True)
        if cols_nav[2].button("➡️") and h_idx < 18: g['h_sel'] += 1; st.rerun()

        v_def = g['logs'][str(h_idx)]['s'] if str(h_idx) in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        c = st.columns(4)
        s = [c[i].number_input(TODOS[i][:3], 0, 10, v_def[i], key=f"s{i}_{h_idx}") for i in range(4)]
        
        ya_save = str(h_idx) in g['logs'] and g['logs'][str(h_idx)]['s'] == s
        if st.button("💾 Grabar Hoyo", type="primary", disabled=ya_save, use_container_width=True):
            pa, pb, mi = calcular_puntos_hoyo(s[0], s[1], s[2], s[3], h_idx)
            g['logs'][str(h_idx)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
            
            t_a = sum(v['pts'][0] for v in g['logs'].values())
            t_b = sum(v['pts'][1] for v in g['logs'].values())
            m_pts = [sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)]
            
            nueva_fila = pd.DataFrame([{
                "id": g['edit_id'], "fecha": g['fecha'], "temporada": g['temp'],
                "resultado_a": t_a, "resultado_b": t_b,
                "p1_pts": m_pts[0], "p2_pts": m_pts[1], "p3_pts": m_pts[2], "p4_pts": m_pts[3],
                "logs_json": json.dumps(g['logs'])
            }])
            if guardar_partida(nueva_fila):
                st.toast("Guardado!")
                st.rerun()

        if g['logs']:
            ta = sum(v['pts'][0] for v in g['logs'].values())
            tb = sum(v['pts'][1] for v in g['logs'].values())
            st.header(f"{int(ta)} - {int(tb)}")

elif menu == "Admin":
    st.subheader("Admin")
    df = leer_datos()
    if not df.empty:
        for idx, r in df.iterrows():
            with st.expander(f"{r['fecha']}"):
                if st.button("Borrar", key=f"d_{idx}"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="historial", data=df.drop(idx))
                    st.rerun()
