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

INICIO_2026_A = 3.5  # MANUEL & JOSE
INICIO_2026_B = 3.5  # ROGE & LALO

st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# --- FUNCIONES DE BASE DE DATOS ---
def leer_datos():
    st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts"])
        df = df.dropna(subset=['id'])
        df['temporada'] = df['temporada'].astype(str)
        return df
    except:
        return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts"])

def guardar_hoyo(df_fila):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = leer_datos()
        id_hoyo = str(df_fila["id"].iloc[0])
        if not df_existente.empty:
            df_existente['id'] = df_existente['id'].astype(str)
            df_final = df_existente[df_existente["id"] != id_hoyo].copy()
            df_final = pd.concat([df_final, df_fila], ignore_index=True)
        else:
            df_final = df_fila
        conn.update(worksheet="historial", data=df_final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    scores = [s1, s2, s3, s4]
    v = [s if s > 0 else 99 for s in scores]
    ba, wa = min(v[0], v[1]), max(v[0], v[1])
    bb, wb = min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    for s in [s1, s2]:
        if 0 < s <= par - 2: pa += 2.0
        elif 0 < s == par - 1: pa += 1.0
    for s in [s3, s4]:
        if 0 < s <= par - 2: pb += 2.0
        elif 0 < s == par - 1: pb += 1.0
    mvp = {f"p{i+1}": 0.0 for i in range(4)}
    for i in range(4):
        if scores[i] <= 0: continue
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]: mvp[f"p{i+1}"] += 0.5
        if scores[i] <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif scores[i] == par - 1: mvp[f"p{i+1}"] += 1.5
        elif scores[i] == par: mvp[f"p{i+1}"] += 0.5
    return pa, pb, mvp

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("Menú", ["Inicio", "Jugar/Editar", "Admin"])

if menu == "Inicio":
    st.markdown("<h1 style='text-align: center;'>⛳ CAÑITA BRAVA 2026</h1>", unsafe_allow_html=True)
    df = leer_datos()
    df_2026 = df[df['temporada'] == "2026"]
    
    wins_a = 0
    wins_b = 0
    if not df_2026.empty:
        resumen = df_2026.groupby('partido_id').agg({'resultado_a': 'sum', 'resultado_b': 'sum'}).reset_index()
        wins_a = len(resumen[resumen['resultado_a'] > resumen['resultado_b']])
        wins_b = len(resumen[resumen['resultado_b'] > resumen['resultado_a']])
    
    st.markdown(f"""
        <div style="border: 2px solid #4CAF50; border-radius: 15px; padding: 20px; background-color: #f9f9f9; text-align: center; margin-bottom: 25px;">
            <h2 style="margin-bottom: 10px; color: #333;">TEMPORADA 2026</h2>
            <div style="display: flex; justify-content: space-around; align-items: center;">
                <div>
                    <h4 style="margin: 0;">MANUEL & JOSE</h4>
                    <h1 style="color: #2e7d32; margin: 0;">{INICIO_2026_A + wins_a}</h1>
                </div>
                <h2 style="margin: 0;">VS</h2>
                <div>
                    <h4 style="margin: 0;">ROGE & LALO</h4>
                    <h1 style="color: #c62828; margin: 0;">{INICIO_2026_B + wins_b}</h1>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align: center;'>⭐ Ranking MVP 2026</h3>", unsafe_allow_html=True)
    if not df_2026.empty:
        mvps = {TODOS[i]: df_2026[f"p{i+1}_pts"].sum() for i in range(4)}
        df_mvp_temp = pd.DataFrame([{"Jugador": k, "Pts": round(float(v), 1)} for k, v in mvps.items()]).sort_values("Pts", ascending=False)
        st.table(df_mvp_temp.style.format({"Pts": "{:.1f}"}))

elif menu == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>Nueva Partida</h2>", unsafe_allow_html=True)
        f = st.date_input("Fecha:", datetime.now())
        if st.button("🚀 Iniciar Partido", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'h_sel': 1, 'logs': {}, 'partido_id': f.strftime("%Y%m%d")}
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']
        
        # --- NAVEGACIÓN BLINDADA (FLEXBOX) ---
        # Este bloque obliga al navegador a mantener la línea horizontal
        st.markdown(f"""
            <div style="display: flex; justify-content: center; align-items: center; background-color: #f0f2f6; border-radius: 10px; padding: 10px; gap: 20px;">
                <div style="font-size: 1.5em;">⬅️</div>
                <div style="text-align: center; min-width: 120px;">
                    <h3 style="margin: 0; font-size: 1.2em;">Hoyo {h_idx}</h3>
                    <p style="margin: 0; font-size: 0.8em; color: gray;">Par {PAR_RIA_VIGO[h_idx]}</p>
                </div>
                <div style="font-size: 1.5em;">➡️</div>
            </div>
        """, unsafe_allow_html=True)

        # Botones de control reales (pequeños y en una sola fila)
        c_nav = st.columns(2)
        if c_nav[0].button("Anterior Hoyo", use_container_width=True):
            g['h_sel'] = max(1, h_idx - 1)
            st.rerun()
        if c_nav[1].button("Siguiente Hoyo", use_container_width=True):
            g['h_sel'] = min(18, h_idx + 1)
            st.rerun()

        st.write("---")

        # --- ENTRADA DE GOLPES (2x2) ---
        v_def = g['logs'][str(h_idx)]['s'] if str(h_idx) in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        
        # Agrupamos inputs para que ocupen lo mínimo
        c1, c2 = st.columns(2)
        s1 = c1.number_input(TODOS[0], 0, 10, v_def[0], key=f"s0_{h_idx}")
        s2 = c2.number_input(TODOS[1], 0, 10, v_def[1], key=f"s1_{h_idx}")
        s3 = c1.number_input(TODOS[2], 0, 10, v_def[2], key=f"s2_{h_idx}")
        s4 = c2.number_input(TODOS[3], 0, 10, v_def[3], key=f"s3_{h_idx}")
        
        s = [s1, s2, s3, s4]
        
        # --- BOTÓN GRABAR ---
        ya_guardado = str(h_idx) in g['logs'] and g['logs'][str(h_idx)]['s'] == s
        btn_txt = "✅ Sincronizado" if ya_guardado else "💾 Guardar Hoyo"
        
        if st.button(btn_txt, type="primary", use_container_width=True, disabled=ya_guardado):
            pa, pb, mi = calcular_puntos_hoyo(s[0], s[1], s[2], s[3], h_idx)
            g['logs'][str(h_idx)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
            nueva_fila = pd.DataFrame([{
                "id": f"{g['partido_id']}_H{h_idx}", "partido_id": g['partido_id'], "hoyo": h_idx,
                "fecha": g['fecha'], "temporada": g['temp'], "resultado_a": pa, "resultado_b": pb,
                "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4']
            }])
            if guardar_hoyo(nueva_fila):
                st.toast(f"Hoyo {h_idx} guardado")
                st.rerun()

        # Marcador discreto al final
        if g['logs']:
            total_match_a = sum(v['pts'][0] for v in g['logs'].values())
            total_match_b = sum(v['pts'][1] for v in g['logs'].values())
            st.markdown(f"""
                <div style="text-align: center; border-top: 1px solid #eee; padding-top: 10px;">
                    <span style="color: green; font-weight: bold;">{int(total_match_a)}</span> 
                    <span style="color: gray;"> vs </span> 
                    <span style="color: red; font-weight: bold;">{int(total_match_b)}</span>
                </div>
            """, unsafe_allow_html=True)

        if st.button("🏁 Finalizar", use_container_width=True):
            del st.session_state.game
            st.rerun()
            
elif menu == "Admin":
    st.markdown("<h2 style='text-align: center;'>Admin</h2>", unsafe_allow_html=True)
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique():
            with st.expander(f"Jornada {p_id}"):
                if st.button("Borrar Jornada", key=f"del_{p_id}"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="historial", data=df[df['partido_id'] != p_id])
                    st.rerun()
