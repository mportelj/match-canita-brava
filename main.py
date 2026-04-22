import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import json

# --- CONFIGURACIÓN CON TU URL REAL ---
URL_HOJA = "https://docs.google.com/spreadsheets/d/17mwvtZY-f6BWXOlDGkDdYur8l0ATvGYpbkshjv1sJAk/edit#gid=0"

PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}
TODOS = ["MANUEL", "JOSE", "ROGE", "LALO"]
HISTORICO_PUNTOS = 3.5

st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def leer_datos():
    try:
        # Forzamos la lectura de la hoja "historial"
        df = conn.read(spreadsheet=URL_HOJA, worksheet="historial", ttl="0")
        return df
    except Exception:
        # Si falla (por ser la primera vez o estar vacía), devolvemos estructura base
        return pd.DataFrame(columns=["id", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "logs_json"])

def guardar_partida(df_partida):
    df_existente = leer_datos()
    # Si estamos editando o sobreescribiendo el mismo partido de hoy, filtramos por ID
    if not df_partida["id"].isna().all():
        df_existente = df_existente[df_existente["id"].astype(str) != str(df_partida["id"].iloc[0])]
    
    df_final = pd.concat([df_existente, df_partida], ignore_index=True)
    conn.update(spreadsheet=URL_HOJA, worksheet="historial", data=df_final)

# --- LÓGICA DE CÁLCULO MVP ---
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
    if not df.empty and "temporada" in df.columns:
        df_temp = df[df["temporada"].astype(str) == str(temp_sel)]
        if not df_temp.empty:
            wins_a = len(df_temp[df_temp['resultado_a'].astype(float) > df_temp['resultado_b'].astype(float)])
            wins_b = len(df_temp[df_temp['resultado_b'].astype(float) > df_temp['resultado_a'].astype(float)])
            
            c1, c2 = st.columns(2)
            c1.metric("MANU & JOSE", f"{HISTORICO_PUNTOS + wins_a} Pts")
            c2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b} Pts")
            
            st.subheader("⭐ Clasificación MVP Acumulada")
            mvp_tot = {
                "MANUEL": df_temp["p1_pts"].astype(float).sum(),
                "JOSE": df_temp["p2_pts"].astype(float).sum(),
                "ROGE": df_temp["p3_pts"].astype(float).sum(),
                "LALO": df_temp["p4_pts"].astype(float).sum()
            }
            df_mvp = pd.DataFrame([{"Jugador": k, "Puntos": v} for k, v in mvp_tot.items()]).sort_values("Puntos", ascending=False)
            st.table(df_mvp)
        else:
            st.info("No hay datos para este año.")

elif menu == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.subheader("Nueva Partida")
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partido", use_container_width=True):
            st.session_state.game = {
                'fecha': f.strftime("%d/%m/%Y"), 
                'temp': str(f.year), 
                'h_sel': 1, 
                'logs': {}, 
                'edit_id': datetime.now().strftime("%Y%m%d") # ID basado en el día
            }
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']
        
        cp, ch, cn = st.columns([1, 2, 1])
        if cp.button("⬅️") and h_idx > 1: g['h_sel'] -= 1; st.rerun()
        ch.markdown(f"<h3 style='text-align:center;'>Hoyo {h_idx} (Par {PAR_RIA_VIGO[h_idx]})</h3>", unsafe_allow_html=True)
        if cn.button("➡️") and h_idx < 18: g['h_sel'] += 1; st.rerun()

        v_def = g['logs'][str(h_idx)]['s'] if str(h_idx) in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        with st.container(border=True):
            cols = st.columns(4)
            s = [cols[i].number_input(TODOS[i][:3], 0, 10, v_def[i], key=f"s{i}_{h_idx}") for i in range(4)]
            
            if st.button("✅ Confirmar Hoyo", use_container_width=True, type="primary"):
                pa, pb, mi = calcular_puntos_hoyo(s[0], s[1], s[2], s[3], h_idx)
                g['logs'][str(h_idx)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
                
                # CÁLCULOS TOTALES
                t_a = sum(v['pts'][0] for v in g['logs'].values())
                t_b = sum(v['pts'][1] for v in g['logs'].values())
                cur_mvp = [sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)]
                
                # GUARDAR EN GOOGLE SHEETS
                nueva_fila = pd.DataFrame([{
                    "id": g['edit_id'], "fecha": g['fecha'], "temporada": g['temp'],
                    "resultado_a": t_a, "resultado_b": t_b,
                    "p1_pts": cur_mvp[0], "p2_pts": cur_mvp[1], "p3_pts": cur_mvp[2], "p4_pts": cur_mvp[3],
                    "logs_json": json.dumps(g['logs'])
                }])
                guardar_partida(nueva_fila)
                st.toast("Guardado en la nube ☁️")
                st.rerun()

        if g['logs']:
            # MARCADOR MATCH
            t_a = sum(v['pts'][0] for v in g['logs'].values())
            t_b = sum(v['pts'][1] for v in g['logs'].values())
            st.divider()
            st.markdown("<h3 style='text-align: center; color: #1e3d59;'>🏆 MARCADOR MATCH</h3>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns([2, 1, 2])
            m1.markdown(f"<div style='text-align:center;padding:10px;background-color:#e8f5e9;border-radius:10px;border:2px solid #2e7d32;'><p style='margin:0;font-weight:bold;'>MANU & JOSE</p><h1 style='margin:0;'>{int(t_a)}</h1></div>", unsafe_allow_html=True)
            m2.markdown("<h1 style='text-align:center;padding-top:15px;'>VS</h1>", unsafe_allow_html=True)
            m3.markdown(f"<div style='text-align:center;padding:10px;background-color:#e3f2fd;border-radius:10px;border:2px solid #1565c0;'><p style='margin:0;font-weight:bold;'>ROGE & LALO</p><h1 style='margin:0;'>{int(t_b)}</h1></div>", unsafe_allow_html=True)
            
            # CLASIFICACIÓN MVP
            st.write("### 📈 Clasificación MVP")
            c_mvp1, c_mvp2 = st.columns(2)
            with c_mvp1:
                with st.popover("🎯 Puntos Hoyo", use_container_width=True):
                    l = g['logs'][str(h_idx)]
                    st.table(pd.DataFrame([{"Jugador": TODOS[i], "Pts": l['mvp'][f"p{i+1}"]} for i in range(4)]))
            with c_mvp2:
                with st.popover("🏆 Ranking Total", use_container_width=True):
                    cur_mvp_dict = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
                    st.table(pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in cur_mvp_dict.items()]).sort_values("Pts", ascending=False))

        st.divider()
        if st.button("🏁 Finalizar Jornada", use_container_width=True):
            del st.session_state.game
            st.rerun()

elif menu == "Admin":
    st.subheader("⚙️ Gestión (Cloud)")
    df = leer_datos()
    if not df.empty and "id" in df.columns:
        for _, r in df.iterrows():
            with st.expander(f"📅 {r['fecha']} | Match: {r['resultado_a']} - {r['resultado_b']}"):
                if st.button("🗑️ Eliminar Partida", key=f"del_{r['id']}"):
                    df_new = df[df["id"].astype(str) != str(r['id'])]
                    conn.update(spreadsheet=URL_HOJA, worksheet="historial", data=df_new)
                    st.success("Eliminado de la nube.")
                    st.rerun()
    else:
        st.write("No hay partidas grabadas en Google Sheets.")
