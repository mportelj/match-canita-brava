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
    st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts"])
        return df.dropna(subset=['id'])
    except:
        return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts"])

def guardar_hoyo(df_fila):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = leer_datos()
        
        # ID ÚNICO: Fecha + Hoyo (ej: 20240422_H1)
        id_hoyo = str(df_fila["id"].iloc[0])
        
        if not df_existente.empty:
            # Si ya existe ese hoyo específico, lo actualizamos (borramos el viejo)
            df_existente['id'] = df_existente['id'].astype(str)
            df_final = df_existente[df_existente["id"] != id_hoyo].copy()
            df_final = pd.concat([df_final, df_fila], ignore_index=True)
        else:
            df_final = df_fila

        conn.update(worksheet="historial", data=df_final)
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
    
    # Match (Mejor y peor bola)
    ba, wa = min(v[0], v[1]), max(v[0], v[1])
    bb, wb = min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    
    # Bonus al Marcador Equipo
    for s in [s1, s2]:
        if 0 < s <= par - 2: pa += 2.0
        elif 0 < s == par - 1: pa += 1.0
    for s in [s3, s4]:
        if 0 < s <= par - 2: pb += 2.0
        elif 0 < s == par - 1: pb += 1.0

    # MVP Individual
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
        # Agrupamos por partido_id para sumar todos los hoyos de cada jornada
        resumen = df.groupby('partido_id').agg({
            'resultado_a': 'sum',
            'resultado_b': 'sum',
            'p1_pts': 'sum', 'p2_pts': 'sum', 'p3_pts': 'sum', 'p4_pts': 'sum'
        }).reset_index()
        
        wins_a = len(resumen[resumen['resultado_a'] > resumen['resultado_b']])
        wins_b = len(resumen[resumen['resultado_b'] > resumen['resultado_a']])
        
        c1, c2 = st.columns(2)
        c1.metric("MANU & JOSE", f"{HISTORICO_PUNTOS + wins_a}")
        c2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b}")
        
        st.subheader("⭐ MVP Acumulado")
        mvps = {TODOS[i]: resumen[f"p{i+1}_pts"].sum() for i in range(4)}
        st.table(pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in mvps.items()]).sort_values("Pts", ascending=False))

elif menu == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.subheader("Nueva Partida")
        f = st.date_input("Fecha:", datetime.now())
        if st.button("🚀 Iniciar"):
            # partido_id es constante para toda la jornada
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'h_sel': 1, 'logs': {}, 'partido_id': f.strftime("%Y%m%d")}
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']
        
        # Navegación
        nav = st.columns([1, 2, 1])
        if nav[0].button("⬅️") and h_idx > 1: g['h_sel'] -= 1; st.rerun()
        nav[1].markdown(f"<h3 style='text-align:center;'>Hoyo {h_idx}</h3>", unsafe_allow_html=True)
        if nav[2].button("➡️") and h_idx < 18: g['h_sel'] += 1; st.rerun()

        # Input
        v_def = g['logs'][str(h_idx)]['s'] if str(h_idx) in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        c = st.columns(4)
        s = [c[i].number_input(TODOS[i][:3], 0, 10, v_def[i], key=f"s{i}_{h_idx}") for i in range(4)]
        
        if st.button("💾 Grabar Hoyo", type="primary", use_container_width=True):
            pa, pb, mi = calcular_puntos_hoyo(s[0], s[1], s[2], s[3], h_idx)
            g['logs'][str(h_idx)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
            
            # Fila única para este hoyo
            nueva_fila = pd.DataFrame([{
                "id": f"{g['partido_id']}_H{h_idx}", 
                "partido_id": g['partido_id'],
                "hoyo": h_idx,
                "fecha": g['fecha'], "temporada": g['temp'],
                "resultado_a": pa, "resultado_b": pb,
                "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4']
            }])
            
            if guardar_hoyo(nueva_fila):
                st.toast(f"Hoyo {h_idx} guardado")
                st.rerun()

        # Marcadores Match y MVP (Hoyo y Total)
        if g['logs']:
            ta = sum(v['pts'][0] for v in g['logs'].values())
            tb = sum(v['pts'][1] for v in g['logs'].values())
            st.divider()
            st.markdown(f"<h2 style='text-align:center;'>Match: {int(ta)} - {int(tb)}</h2>", unsafe_allow_html=True)
            
            # Botones de clasificación que pediste al principio
            c1, c2 = st.columns(2)
            with c1:
                with st.popover("🎯 Hoyo", use_container_width=True):
                    if str(h_idx) in g['logs']:
                        pts_h = g['logs'][str(h_idx)]['mvp']
                        st.table(pd.DataFrame([{"Jugador": TODOS[i], "Pts": pts_h[f"p{i+1}"]} for i in range(4)]))
            with c2:
                with st.popover("🏆 Partido", use_container_width=True):
                    ranking = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
                    st.table(pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in ranking.items()]).sort_values("Pts", ascending=False))

        if st.button("🏁 Finalizar"):
            del st.session_state.game
            st.rerun()

elif menu == "Admin":
    st.subheader("Admin")
    df = leer_datos()
    if not df.empty:
        # Agrupamos por fecha para que sea más fácil de gestionar
        jornadas = df['partido_id'].unique()
        for j_id in jornadas:
            with st.expander(f"Jornada {j_id}"):
                if st.button("Borrar Jornada Completa", key=f"del_{j_id}"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_new = df[df['partido_id'] != j_id]
                    conn.update(worksheet="historial", data=df_new)
                    st.rerun()
