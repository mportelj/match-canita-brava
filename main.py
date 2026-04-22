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
        return conn.read(worksheet="historial", ttl=0)
    except:
        return pd.DataFrame(columns=["id", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "logs_json"])

def guardar_partida(df_partida):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = leer_datos()
        
        if not df_partida["id"].isna().all():
            id_actual = str(df_partida["id"].iloc[0])
            df_existente = df_existente[df_existente["id"].astype(str) != id_actual]
        
        df_final = pd.concat([df_existente, df_partida], ignore_index=True)
        conn.update(worksheet="historial", data=df_final)
        return True
    except Exception as e:
        st.error(f"Error al grabar: {e}")
        return False

# --- LÓGICA DE CÁLCULO ---
def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    scores = [s1, s2, s3, s4]
    v = [s if s > 0 else 99 for s in scores]
    best_a, worst_a = min(v[0], v[1]), max(v[0], v[1])
    best_b, worst_b = min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if best_a < best_b else 0.0) + (1.0 if worst_a < worst_b else 0.0)
    pb = (1.0 if best_b < best_a else 0.0) + (1.0 if worst_b < worst_a else 0.0)
    mvp = {"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}
    for i in range(4):
        if scores[i] <= 0: continue
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]: mvp[f"p{i+1}"] += 0.5
        g = scores[i]
        if g <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif g == par - 1: mvp[f"p{i+1}"] += 1.5
        elif g == par: mvp[f"p{i+1}"] += 0.5
    return pa, pb, mvp

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("Menú", ["Inicio", "Jugar/Editar", "Admin"])

if menu == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    
    anio_act = str(datetime.now().year)
    anios = sorted(df["temporada"].unique().tolist() if not df.empty else [anio_act], reverse=True)
    temp_sel = st.sidebar.selectbox("Temporada", anios)
    
    st.header(f"📊 Temporada {temp_sel}")
    if not df.empty:
        df_temp = df[df["temporada"].astype(str) == str(temp_sel)]
        if not df_temp.empty:
            wins_a = len(df_temp[df_temp['resultado_a'].astype(float) > df_temp['resultado_b'].astype(float)])
            wins_b = len(df_temp[df_temp['resultado_b'].astype(float) > df_temp['resultado_a'].astype(float)])
            
            c1, c2 = st.columns(2)
            c1.metric("MANU & JOSE", f"{HISTORICO_PUNTOS + wins_a} Pts")
            c2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b} Pts")
            
            st.subheader("⭐ MVP Acumulado")
            mvp_tot = {
                "MANUEL": df_temp["p1_pts"].astype(float).sum(),
                "JOSE": df_temp["p2_pts"].astype(float).sum(),
                "ROGE": df_temp["p3_pts"].astype(float).sum(),
                "LALO": df_temp["p4_pts"].astype(float).sum()
            }
            df_mvp = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in mvp_tot.items()]).sort_values("Pts", ascending=False)
            st.table(df_mvp)

elif menu == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.subheader("Nueva Partida")
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partido", use_container_width=True):
            st.session_state.game = {
                'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 
                'h_sel': 1, 'logs': {}, 'edit_id': datetime.now().strftime("%Y%m%d")
            }
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']
        
        cp, ch, cn = st.columns([1, 2, 1])
        if cp.button("⬅️") and h_idx > 1: g['h_sel'] -= 1; st.rerun()
        ch.markdown(f"<h3 style='text-align:center;'>Hoyo {h_idx} (Par {PAR_RIA_VIGO[h_idx]})</h3>", unsafe_allow_html=True)
        if cn.button("➡️") and h_idx < 18: g['h_sel'] += 1; st.rerun()

        # Entrada de golpes
        v_def = g['logs'][str(h_idx)]['s'] if str(h_idx) in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        with st.container(border=True):
            cols = st.columns(4)
            s = [cols[i].number_input(TODOS[i][:3], 0, 10, v_def[i], key=f"s{i}_{h_idx}") for i in range(4)]
            
            # Lógica de botón sincronizado
            ya_guardado = str(h_idx) in g['logs'] and g['logs'][str(h_idx)]['s'] == s
            texto_btn = "✅ Hoyo Sincronizado" if ya_guardado else "💾 Confirmar y Grabar Hoyo"
            
            if st.button(texto_btn, key=f"save_{h_idx}", use_container_width=True, type="primary", disabled=ya_guardado):
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
                    st.toast("Datos en la nube ☁️")
                    st.rerun()

        # Marcadores y Clasificaciones
        if g['logs']:
            t_a = sum(v['pts'][0] for v in g['logs'].values())
            t_b = sum(v['pts'][1] for v in g['logs'].values())
            st.divider()
            st.markdown("<h3 style='text-align: center;'>🏆 MARCADOR MATCH</h3>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns([2, 1, 2])
            m1.metric("MANU & JOSE", int(t_a))
            m2.markdown("<h2 style='text-align:center;'>VS</h2>", unsafe_allow_html=True)
            m3.metric("ROGE & LALO", int(t_b))
            
            st.write("### 📈 Clasificaciones MVP")
            c1, c2 = st.columns(2)
            with c1:
                if str(h_idx) in g['logs']:
                    with st.popover("🎯 Puntos Hoyo", use_container_width=True):
                        l = g['logs'][str(h_idx)]
                        df_h = pd.DataFrame([{"Jugador": TODOS[i], "Pts": l['mvp'][f"p{i+1}"]} for i in range(4)])
                        st.table(df_h)
                else:
                    st.button("🎯 Puntos Hoyo (Vacío)", disabled=True, use_container_width=True)
            with c2:
                with st.popover("🏆 Ranking Partido", use_container_width=True):
                    cur_mvp = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
                    df_r = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in cur_mvp.items()]).sort_values("Pts", ascending=False)
                    st.table(df_r)

        st.divider()
        if st.button("🏁 Finalizar y Salir", use_container_width=True):
            del st.session_state.game
            st.rerun()

elif menu == "Admin":
    st.subheader("⚙️ Gestión")
    df = leer_datos()
    if not df.empty:
        # CORRECCIÓN ERROR DE DUPLICADOS EN ADMIN
        for idx, r in df.iterrows():
            titulo = f"📅 {r['fecha']} | Match: {r['resultado_a']} - {r['resultado_b']}"
            with st.expander(titulo):
                if st.button("🗑️ Eliminar Partida", key=f"del_{r['id']}_{idx}"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_new = df.drop(idx)
                    conn.update(worksheet="historial", data=df_new)
                    st.success("Partida eliminada.")
                    st.rerun()
    else:
        st.info("No hay partidas registradas.")
