import streamlit as st
import sqlite3
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
                  pareja_a TEXT, pareja_b TEXT, resultado_a REAL, resultado_b REAL, mvp TEXT,
                  p1_pts REAL, p2_pts REAL, p3_pts REAL, p4_pts REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS backup_partida 
                 (id INTEGER PRIMARY KEY, datos_json TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- PERSISTENCIA ---
def guardar_backup(game_dict):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO backup_partida (id, datos_json) VALUES (1, ?)", (json.dumps(game_dict),))
    conn.commit(); conn.close()

def cargar_backup():
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT datos_json FROM backup_partida WHERE id = 1")
    res = c.fetchone()
    conn.close()
    return json.loads(res[0]) if res else None

def borrar_backup():
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM backup_partida WHERE id = 1")
    conn.commit(); conn.close()

# --- LÓGICA DE CÁLCULO ---
def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    v = [s1 if s1 > 0 else 99, s2 if s2 > 0 else 99, s3 if s3 > 0 else 99, s4 if s4 > 0 else 99]
    best_a, worst_a = (v[0], v[1]) if v[0] <= v[1] else (v[1], v[0])
    best_b, worst_b = (v[2], v[3]) if v[2] <= v[3] else (v[3], v[2])
    pts_match_a, pts_match_b = 0.0, 0.0
    mvp_inc = {"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}

    # MATCH
    if best_a < best_b: pts_match_a += 1.0
    elif best_b < best_a: pts_match_b += 1.0
    if worst_a < worst_b: pts_match_a += 1.0
    elif worst_b < worst_a: pts_match_b += 1.0

    # MVP
    if v[0] == v[1] == v[2] == v[3] and v[0] != 99:
        for i in range(4): mvp_inc[f"p{i+1}"] = 0.5
    else:
        if best_a < best_b: mvp_inc["p1" if v[0] == best_a else "p2"] += 1.0
        elif best_b < best_a: mvp_inc["p3" if v[2] == best_b else "p4"] += 1.0
        elif best_a == best_b and best_a != 99:
            for i, val in enumerate(v):
                if val == best_a: mvp_inc[f"p{i+1}"] += 0.5
        if worst_a < worst_b: mvp_inc["p1" if v[0] == worst_a else "p2"] += 0.5
        elif worst_b < worst_a: mvp_inc["p3" if v[2] == worst_b else "p4"] += 0.5
        elif worst_a == worst_b and worst_a != 99:
            if worst_a != best_a:
                for i, val in enumerate(v):
                    if val == worst_a: mvp_inc[f"p{i+1}"] += 0.25
        
    for i, s in enumerate([s1, s2, s3, s4]):
        if s > 0:
            bonus = 1.0 if s == par - 1 else (2.0 if s <= par - 2 else 0.0)
            if bonus > 0:
                mvp_inc[f"p{i+1}"] += bonus
                if i < 2: pts_match_a += bonus
                else: pts_match_b += bonus
    return pts_match_a, pts_match_b, mvp_inc

# --- INTERFAZ ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳")
st.title("⛳ CAÑITA BRAVA")

menu = st.sidebar.radio("Menú", ["Inicio", "Jugar Partido", "Admin"])

if menu == "Inicio":
    conn = get_connection()
    try: anios = pd.read_sql_query("SELECT DISTINCT temporada FROM historial", conn)['temporada'].tolist()
    except: anios = []
    anio_act = str(datetime.now().year)
    if anio_act not in anios: anios.append(anio_act)
    anios.sort(reverse=True)
    c_t, c_s = st.columns([2, 1])
    c_t.subheader("📊 RESULTADOS") 
    temp_sel = c_s.selectbox("Año", anios)
    st.divider()
    df_h = pd.read_sql_query(f"SELECT resultado_a, resultado_b FROM historial WHERE temporada = '{temp_sel}'", conn)
    wins_a, wins_b = len(df_h[df_h['resultado_a'] > df_h['resultado_b']]), len(df_h[df_h['resultado_b'] > df_h['resultado_a']])
    col1, col2 = st.columns(2)
    col1.metric("M & J", f"{HISTORICO_PUNTOS + wins_a} Pts")
    col2.metric("R & L", f"{HISTORICO_PUNTOS + wins_b} Pts")
    df_mvp = pd.read_sql_query(f"SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM puntos_anuales WHERE temporada = '{temp_sel}' ORDER BY Puntos DESC", conn)
    if not df_mvp.empty: st.table(df_mvp)
    conn.close()

elif menu == "Jugar Partido":
    backup = cargar_backup()
    if 'game' not in st.session_state:
        if backup:
            st.warning("⚠️ Partida interrumpida detectada.")
            c1, c2 = st.columns(2)
            if c1.button("🔄 Recuperar"):
                backup['logs'] = {int(k): v for k, v in backup['logs'].items()}
                st.session_state.game = backup; st.rerun()
            if c2.button("🗑️ Nueva"): borrar_backup(); st.rerun()
        else:
            f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
            if st.button("🚀 Iniciar"):
                st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'h_sel': 1, 'logs': {}}
                st.rerun()
    else:
        g = st.session_state.game
        
        # --- NAVEGACIÓN DE HOYOS ---
        col_prev, col_h, col_next = st.columns([1, 2, 1])
        if col_prev.button("⬅️ Ant.") and g['h_sel'] > 1:
            g['h_sel'] -= 1; st.rerun()
        
        h_idx = g['h_sel']
        col_h.markdown(f"<h3 style='text-align: center;'>Hoyo {h_idx} (Par {PAR_RIA_VIGO[h_idx]})</h3>", unsafe_allow_html=True)
        
        if col_next.button("Sig. ➡️") and g['h_sel'] < 18:
            g['h_sel'] += 1; st.rerun()

        # --- SCORE ACUMULADO MATCH ---
        total_a = sum(v['pts'][0] for v in g['logs'].values())
        total_b = sum(v['pts'][1] for v in g['logs'].values())
        diff = int(total_a - total_b)
        
        st.markdown("#### 🏆 Clasificación Match Acumulada")
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("M&J", f"+{diff}" if diff > 0 else "0")
        c_m2.metric("R&L", f"+{abs(diff)}" if diff < 0 else "0")
        st.divider()

        # --- INPUT DE GOLPES ---
        v_def = g['logs'][h_idx]['s'] if h_idx in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        with st.container(border=True):
            st.write(f"**Introducir resultados Hoyo {h_idx}:**")
            c = st.columns(4)
            s1 = c[0].number_input("MANUEL", 0, 10, v_def[0])
            s2 = c[1].number_input("JOSE", 0, 10, v_def[1])
            s3 = c[2].number_input("ROGE", 0, 10, v_def[2])
            s4 = c[3].number_input("LALO", 0, 10, v_def[3])
            
            if st.button("✅ Confirmar y Ver Resultado Hoyo", use_container_width=True, type="primary"):
                pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, h_idx)
                g['logs'][h_idx] = {'s': [s1, s2, s3, s4], 'pts': (pa, pb), 'mvp': mi}
                guardar_backup(g); st.rerun()

        # --- FEEDBACK DEL HOYO JUGADO ---
        if h_idx in g['logs']:
            log = g['logs'][h_idx]
            st.success(f"**Resultado del Hoyo {h_idx}:**")
            f1, f2 = st.columns(2)
            f1.write(f"Match M&J: **+{log['pts'][0]}**")
            f2.write(f"Match R&L: **+{log['pts'][1]}**")
            
            st.write("**Puntos MVP ganados en este hoyo:**")
            m1, m2, m3, m4 = st.columns(4)
            m1.caption(f"MANUEL: {log['mvp']['p1']}")
            m2.caption(f"JOSE: {log['mvp']['p2']}")
            m3.caption(f"ROGE: {log['mvp']['p3']}")
            m4.caption(f"LALO: {log['mvp']['p4']}")

        # --- RANKING MVP PARTIDO ---
        if g['logs']:
            st.divider()
            st.subheader("⭐ MVP Acumulado del Partido")
            cur_mvp = {p: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i, p in enumerate(TODOS)}
            st.table(pd.DataFrame([{"Jugador": p, "Puntos": cur_mvp[p]} for p in TODOS]).sort_values(by="Puntos", ascending=False))

            if st.button("💾 FINALIZAR Y GUARDAR PARTIDO", use_container_width=True):
                conn = get_connection(); cur = conn.cursor()
                mvp_w = max(cur_mvp, key=cur_mvp.get)
                cur.execute("INSERT INTO historial (fecha, temporada, pareja_a, pareja_b, resultado_a, resultado_b, mvp, p1_pts, p2_pts, p3_pts, p4_pts) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (g['fecha'], g['temp'], "M&J", "R&L", total_a, total_b, mvp_w, cur_mvp["MANUEL"], cur_mvp["JOSE"], cur_mvp["ROGE"], cur_mvp["LALO"]))
                for p in TODOS:
                    cur.execute("INSERT OR IGNORE INTO puntos_anuales (nombre, temporada) VALUES (?,?)", (p, g['temp']))
                    cur.execute("UPDATE puntos_anuales SET partidos = partidos+1, puntos_mvp = puntos_mvp+? WHERE nombre=? AND temporada=?", (cur_mvp[p], p, g['temp']))
                conn.commit(); conn.close(); borrar_backup(); del st.session_state.game
                st.balloons(); st.rerun()

elif menu == "Admin":
    conn = get_connection()
    st.subheader("⚙️ Gestión")
    try:
        df = pd.read_sql_query("SELECT * FROM historial ORDER BY id DESC", conn)
        for _, r in df.iterrows():
            if st.button(f"🗑️ Eliminar {r['fecha']} ({int(r['resultado_a'])}-{int(r['resultado_b'])})", key=r['id']):
                cur = conn.cursor()
                p_map = {"MANUEL": r['p1_pts'], "JOSE": r['p2_pts'], "ROGE": r['p3_pts'], "LALO": r['p4_pts']}
                for p, pts in p_map.items():
                    cur.execute("UPDATE puntos_anuales SET partidos = partidos-1, puntos_mvp = puntos_mvp-? WHERE nombre=? AND temporada=?", (pts, p, r['temporada']))
                cur.execute("DELETE FROM historial WHERE id=?", (r['id'],))
                conn.commit(); st.rerun()
    except: st.write("Sin historial")
    conn.close()
