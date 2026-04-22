import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import json

# --- CONFIGURACIÓN DEL CAMPO ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}
TODOS = ["MANUEL", "JOSE", "ROGE", "LALO"]
HISTORICO_PUNTOS = 3.5 # Ventaja histórica inicial para el match anual

# --- FUNCIONES DE BASE DE DATOS ---
def get_connection():
    return sqlite3.connect('canita_brava_vFinal.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS puntos_anuales 
                 (nombre TEXT, temporada TEXT, partidos INTEGER DEFAULT 0, puntos_mvp REAL DEFAULT 0,
                  PRIMARY KEY (nombre, temporada))''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, temporada TEXT, 
                  pareja_a TEXT, pareja_b TEXT, resultado_a REAL, resultado_b REAL,
                  p1_pts REAL, p2_pts REAL, p3_pts REAL, p4_pts REAL, logs_json TEXT)''')
    conn.commit()
    conn.close()

def eliminar_partida_db(partida_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM historial WHERE id=?", (partida_id,))
    r = cur.fetchone()
    if r:
        # Restar puntos de la clasificación anual antes de borrar el registro
        p_map = {"MANUEL": r[7], "JOSE": r[8], "ROGE": r[9], "LALO": r[10]}
        for p, pts in p_map.items():
            cur.execute("UPDATE puntos_anuales SET partidos = partidos-1, puntos_mvp = puntos_mvp-? WHERE nombre=? AND temporada=?", (pts, p, r[2]))
        cur.execute("DELETE FROM historial WHERE id=?", (partida_id,))
    conn.commit(); conn.close()

# --- LÓGICA DE CÁLCULO ---
def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    scores = [s1, s2, s3, s4]
    v = [s if s > 0 else 99 for s in scores]
    
    # Match Play
    best_a, worst_a = min(v[0], v[1]), max(v[0], v[1])
    best_b, worst_b = min(v[2], v[3]), max(v[2], v[3])
    pts_match_a = (1.0 if best_a < best_b else 0.0) + (1.0 if worst_a < worst_b else 0.0)
    pts_match_b = (1.0 if best_b < best_a else 0.0) + (1.0 if worst_b < worst_a else 0.0)

    # MVP Individual
    mvp_inc = {"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}
    for i in range(4):
        if scores[i] <= 0: continue
        # Oponentes batidos
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]:
                mvp_inc[f"p{i+1}"] += 0.5
        # Bonus Campo
        g = scores[i]
        if g <= par - 2: mvp_inc[f"p{i+1}"] += 3.0
        elif g == par - 1: mvp_inc[f"p{i+1}"] += 1.5
        elif g == par: mvp_inc[f"p{i+1}"] += 0.5
            
    return pts_match_a, pts_match_b, mvp_inc

# --- INICIO APP ---
init_db()
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

menu = st.sidebar.radio("Menú", ["Inicio", "Jugar/Editar", "Admin"])

if menu == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    conn = get_connection()
    try:
        anios = pd.read_sql_query("SELECT DISTINCT temporada FROM historial", conn)['temporada'].tolist()
    except: anios = []
    
    anio_act = str(datetime.now().year)
    if anio_act not in anios: anios.append(anio_act)
    anios.sort(reverse=True)
    temp_sel = st.sidebar.selectbox("Temporada", anios)
    
    # Marcador Match Anual
    st.header(f"📊 Temporada {temp_sel}")
    df_h = pd.read_sql_query(f"SELECT resultado_a, resultado_b FROM historial WHERE temporada = '{temp_sel}'", conn)
    wins_a = len(df_h[df_h['resultado_a'] > df_h['resultado_b']])
    wins_b = len(df_h[df_h['resultado_b'] > df_h['resultado_a']])
    
    c1, c2 = st.columns(2)
    c1.metric("MANU & JOSE", f"{HISTORICO_PUNTOS + wins_a} Pts")
    c2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b} Pts")
    
    st.subheader("⭐ Clasificación MVP Acumulada")
    df_mvp = pd.read_sql_query(f"SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM puntos_anuales WHERE temporada = '{temp_sel}' ORDER BY Puntos DESC", conn)
    if not df_mvp.empty:
        st.table(df_mvp)
    else:
        st.info("No hay datos para esta temporada.")
    conn.close()

elif menu == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.subheader("Nueva Partida")
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partido", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'h_sel': 1, 'logs': {}, 'edit_id': None}
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']
        
        # Cabecera Navegación
        cp, ch, cn = st.columns([1, 2, 1])
        if cp.button("⬅️") and h_idx > 1: g['h_sel'] -= 1; st.rerun()
        ch.markdown(f"<h3 style='text-align:center;'>Hoyo {h_idx} (Par {PAR_RIA_VIGO[h_idx]})</h3>", unsafe_allow_html=True)
        if cn.button("➡️") and h_idx < 18: g['h_sel'] += 1; st.rerun()

        # Entrada de Datos
        v_def = g['logs'][h_idx]['s'] if h_idx in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        with st.container(border=True):
            cols = st.columns(4)
            s1 = cols[0].number_input("MAN", 0, 10, v_def[0], key=f"s1_{h_idx}")
            s2 = cols[1].number_input("JOS", 0, 10, v_def[1], key=f"s2_{h_idx}")
            s3 = cols[2].number_input("ROG", 0, 10, v_def[2], key=f"s3_{h_idx}")
            s4 = cols[3].number_input("LAL", 0, 10, v_def[3], key=f"s4_{h_idx}")
            
            btn_disabled = (h_idx in g['logs'] and [s1, s2, s3, s4] == g['logs'][h_idx]['s'])
            if st.button("✅ Confirmar Hoyo", use_container_width=True, type="primary", disabled=btn_disabled):
                pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, h_idx)
                g['logs'][h_idx] = {'s': [s1, s2, s3, s4], 'pts': (pa, pb), 'mvp': mi}
                
                if g['edit_id']: eliminar_partida_db(g['edit_id'])
                conn = get_connection(); cur = conn.cursor()
                t_a = sum(v['pts'][0] for v in g['logs'].values())
                t_b = sum(v['pts'][1] for v in g['logs'].values())
                cur_mvp = {p: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i, p in enumerate(TODOS)}
                
                cur.execute("""INSERT INTO historial 
                    (id, fecha, temporada, pareja_a, pareja_b, resultado_a, resultado_b, p1_pts, p2_pts, p3_pts, p4_pts, logs_json) 
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (g['edit_id'], g['fecha'], g['temp'], "MANU & JOSE", "ROGE & LALO", t_a, t_b, 
                     cur_mvp["MANUEL"], cur_mvp["JOSE"], cur_mvp["ROGE"], cur_mvp["LALO"], json.dumps(g['logs'])))
                if not g['edit_id']: g['edit_id'] = cur.lastrowid
                for p in TODOS:
                    cur.execute("INSERT OR IGNORE INTO puntos_anuales (nombre, temporada) VALUES (?,?)", (p, g['temp']))
                    cur.execute("UPDATE puntos_anuales SET partidos = partidos+1, puntos_mvp = puntos_mvp+? WHERE nombre=? AND temporada=?", (cur_mvp[p], p, g['temp']))
                conn.commit(); conn.close()
                st.toast(f"Hoyo {h_idx} guardado", icon="💾")
                st.rerun()

        # --- AQUÍ ESTÁ LA NOVEDAD: CLASIFICACIONES ACCESIBLES ---
        if g['logs']:
            st.write("### 📈 Consultar Puntuaciones")
            col_mvp1, col_mvp2 = st.columns(2)
            
            with col_mvp1:
                with st.popover("🎯 Puntos Hoyo", use_container_width=True):
                    st.write(f"**Desglose Hoyo {h_idx}:**")
                    l = g['logs'][h_idx]
                    res_hoyo = [
                        {"Jugador": "MANUEL", "Golpes": l['s'][0], "Puntos": l['mvp']['p1']},
                        {"Jugador": "JOSE", "Golpes": l['s'][1], "Puntos": l['mvp']['p2']},
                        {"Jugador": "ROGE", "Golpes": l['s'][2], "Puntos": l['mvp']['p3']},
                        {"Jugador": "LALO", "Golpes": l['s'][3], "Puntos": l['mvp']['p4']}
                    ]
                    st.table(pd.DataFrame(res_hoyo))

            with col_mvp2:
                with st.popover("🏆 Ranking Total", use_container_width=True):
                    st.write("**MVP Acumulado del Partido:**")
                    cur_mvp = {p: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i, p in enumerate(TODOS)}
                    df_acumulado = pd.DataFrame([
                        {"Jugador": p, "Puntos Totales": cur_mvp[p]} for p in TODOS
                    ]).sort_values(by="Puntos Totales", ascending=False)
                    st.table(df_acumulado)

            # --- MARCADOR VISUAL MATCH ---
            t_a = sum(v['pts'][0] for v in g['logs'].values())
            t_b = sum(v['pts'][1] for v in g['logs'].values())
            st.divider()
            st.markdown("<h3 style='text-align: center; color: #1e3d59;'>🏆 MARCADOR MATCH</h3>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns([2, 1, 2])
            with m1:
                st.markdown(f"<div style='text-align:center;padding:15px;background-color:#e8f5e9;border-radius:15px;border:2px solid #2e7d32;'><p style='margin:0;font-weight:bold;color:#1b5e20;'>MANU & JOSE</p><h1 style='margin:0;font-size:45px;color:#2e7d32;'>{int(t_a)}</h1></div>", unsafe_allow_html=True)
            with m2:
                st.markdown("<h1 style='text-align:center;padding-top:25px;color:#999;'>VS</h1>", unsafe_allow_html=True)
            with m3:
                st.markdown(f"<div style='text-align:center;padding:15px;background-color:#e3f2fd;border-radius:15px;border:2px solid #1565c0;'><p style='margin:0;font-weight:bold;color:#0d47a1;'>ROGE & LALO</p><h1 style='margin:0;font-size:45px;color:#1565c0;'>{int(t_b)}</h1></div>", unsafe_allow_html=True)
            
            diff = t_a - t_b
            if diff > 0: st.success(f"🟢 MANU & JOSE lideran por {int(diff)}")
            elif diff < 0: st.info(f"🔵 ROGE & LALO lideran por {int(abs(diff))}")
            else: st.warning("⚪ Empate")

        st.divider()
        if st.button("🏁 Finalizar Jornada", use_container_width=True):
            del st.session_state.game
            st.success("¡Partida cerrada!"); st.balloons(); st.rerun()
elif menu == "Admin":
    st.subheader("⚙️ Gestión")
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT id, fecha, resultado_a, resultado_b, logs_json FROM historial ORDER BY id DESC", conn)
        if not df.empty:
            for _, r in df.iterrows():
                with st.expander(f"📅 {r['fecha']} | Match: {r['resultado_a']}-{r['resultado_b']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("📝 Editar", key=f"ed_{r['id']}", use_container_width=True):
                            st.session_state.game = {'fecha': r['fecha'], 'temp': r['fecha'].split('/')[-1], 'h_sel': 1, 'logs': {int(k): v for k, v in json.loads(r['logs_json']).items()}, 'edit_id': r['id']}
                            st.info("Cargado. Ve a 'Jugar/Editar'.")
                    with c2:
                        if st.button("🗑️ Eliminar", key=f"del_{r['id']}", use_container_width=True):
                            eliminar_partida_db(r['id']); st.rerun()
    except: st.error("Error de base de datos. Resetea abajo.")

    st.divider()
    st.write("### ⚠️ ATENCIÓN !!!")
    if 'reset_step' not in st.session_state: st.session_state.reset_step = 0
    
    if st.session_state.reset_step == 0:
        if st.button("🔴 Resetear Base de Datos", use_container_width=True):
            st.session_state.reset_step = 1; st.rerun()
    elif st.session_state.reset_step == 1:
        st.warning("¿Seguro?")
        c1, c2 = st.columns(2)
        if c1.button("SÍ", use_container_width=True): st.session_state.reset_step = 2; st.rerun()
        if c2.button("NO", use_container_width=True): st.session_state.reset_step = 0; st.rerun()
    elif st.session_state.reset_step == 2:
        st.error("❗ SE BORRARÁ TODO")
        if st.button("🔥 BORRAR DEFINITIVAMENTE", use_container_width=True):
            c = conn.cursor()
            c.execute("DROP TABLE IF EXISTS historial"); c.execute("DROP TABLE IF EXISTS puntos_anuales")
            conn.commit(); st.session_state.reset_step = 0; st.rerun()
    conn.close()
