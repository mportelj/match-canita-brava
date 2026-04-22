import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import json

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
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # ttl=0 es vital para que no lea datos viejos de la memoria
        df = conn.read(worksheet="historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "logs_json"])
        return df
    except:
        return pd.DataFrame(columns=["id", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "logs_json"])

def guardar_partida(df_partida):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Volvemos a leer justo antes de guardar para tener la versión más reciente
        df_existente = leer_datos()
        
        # ID que queremos guardar (ej: "20240422")
        id_nuevo = str(df_partida["id"].iloc[0]).strip()
        
        if not df_existente.empty:
            # Aseguramos que la columna ID sea texto para comparar bien
            df_existente['id'] = df_existente['id'].astype(str).str.strip()
            # FILTRADO: Mantener solo lo que NO sea el ID actual
            df_final = df_existente[df_existente["id"] != id_nuevo]
            # Añadimos la nueva fila
            df_final = pd.concat([df_final, df_partida], ignore_index=True)
        else:
            df_final = df_partida

        # Actualizamos la hoja completa
        conn.update(worksheet="historial", data=df_final)
        
        # LIMPIEZA DE CACHÉ INTERNA DE STREAMLIT
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- MOTOR DE CÁLCULO (Match + Bonus Birdie/Eagle) ---
def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    scores = [s1, s2, s3, s4]
    v = [s if s > 0 else 99 for s in scores]
    
    # 1. Puntos de Match (Mejor y Peor bola)
    best_a, worst_a = min(v[0], v[1]), max(v[0], v[1])
    best_b, worst_b = min(v[2], v[3]), max(v[2], v[3])
    
    p_match_a = (1.0 if best_a < best_b else 0.0) + (1.0 if worst_a < worst_b else 0.0)
    p_match_b = (1.0 if best_b < best_a else 0.0) + (1.0 if worst_b < worst_a else 0.0)
    
    # 2. Bonus Birdie/Eagle para el marcador de EQUIPO
    bonus_a = 0.0
    for s in [s1, s2]:
        if 0 < s <= par - 2: bonus_a += 2.0
        elif 0 < s == par - 1: bonus_a += 1.0
        
    bonus_b = 0.0
    for s in [s3, s4]:
        if 0 < s <= par - 2: bonus_b += 2.0
        elif 0 < s == par - 1: bonus_b += 1.0

    total_hoyo_a = p_match_a + bonus_a
    total_hoyo_b = p_match_b + bonus_b

    # 3. Puntos MVP Individuales
    mvp = {"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}
    for i in range(4):
        if scores[i] <= 0: continue
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]: mvp[f"p{i+1}"] += 0.5
        if scores[i] <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif scores[i] == par - 1: mvp[f"p{i+1}"] += 1.5
        elif scores[i] == par: mvp[f"p{i+1}"] += 0.5
        
    return total_hoyo_a, total_hoyo_b, mvp

# --- LÓGICA DE INTERFAZ ---
menu = st.sidebar.radio("Menú", ["Inicio", "Jugar/Editar", "Admin"])

if menu == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    if not df.empty:
        # Usamos solo la última versión de cada ID para evitar duplicados visuales
        df_view = df.sort_values('id').groupby('id').tail(1)
        
        wins_a = len(df_view[df_view['resultado_a'].astype(float) > df_view['resultado_b'].astype(float)])
        wins_b = len(df_view[df_view['resultado_b'].astype(float) > df_view['resultado_a'].astype(float)])
        
        c1, c2 = st.columns(2)
        c1.metric("MANU & JOSE", f"{HISTORICO_PUNTOS + wins_a}")
        c2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b}")
        
        st.subheader("⭐ Ranking MVP Temporada")
        mvp_tot = {TODOS[i]: df_view[f"p{i+1}_pts"].astype(float).sum() for i in range(4)}
        st.table(pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in mvp_tot.items()]).sort_values("Pts", ascending=False))

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
        
        # Navegación hoyos
        c_nav = st.columns([1, 2, 1])
        if c_nav[0].button("⬅️") and h_idx > 1: g['h_sel'] -= 1; st.rerun()
        c_nav[1].markdown(f"<h3 style='text-align:center;'>Hoyo {h_idx}</h3>", unsafe_allow_html=True)
        if c_nav[2].button("➡️") and h_idx < 18: g['h_sel'] += 1; st.rerun()

        # Input de golpes
        v_def = g['logs'][str(h_idx)]['s'] if str(h_idx) in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        cols = st.columns(4)
        s = [cols[i].number_input(TODOS[i][:3], 0, 10, v_def[i], key=f"s{i}_{h_idx}") for i in range(4)]
        
        ya_guardado = str(h_idx) in g['logs'] and g['logs'][str(h_idx)]['s'] == s
        if st.button("💾 Guardar Hoyo", type="primary", disabled=ya_guardado, use_container_width=True):
            pa, pb, mi = calcular_puntos_hoyo(s[0], s[1], s[2], s[3], h_idx)
            g['logs'][str(h_idx)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
            
            # Recalcular totales de TODA la partida
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
                st.toast("Marcador Sincronizado!")
                st.rerun()

        # Marcador en tiempo real
        if g['logs']:
            t_a = sum(v['pts'][0] for v in g['logs'].values())
            t_b = sum(v['pts'][1] for v in g['logs'].values())
            st.divider()
            st.markdown(f"<h2 style='text-align:center;'>🏆 {int(t_a)} - {int(t_b)}</h2>", unsafe_allow_html=True)
            
        if st.button("🏁 Finalizar Jornada"):
            del st.session_state.game
            st.rerun()

elif menu == "Admin":
    st.subheader("⚙️ Admin")
    df = leer_datos()
    if not df.empty:
        for idx, r in df.iterrows():
            with st.expander(f"📅 {r['fecha']} (ID: {r['id']})"):
                if st.button("🗑️ Eliminar", key=f"del_{idx}"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="historial", data=df.drop(idx))
                    st.rerun()
