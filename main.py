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
    scores = [s1, s2, s3, s4]
    v = [s if s > 0 else 99 for s in scores]
    
    # --- MATCH (Sigue siendo por parejas) ---
    best_a, worst_a = min(v[0], v[1]), max(v[0], v[1])
    best_b, worst_b = min(v[2], v[3]), max(v[2], v[3])
    pts_match_a = (1.0 if best_a < best_b else 0.0) + (1.0 if worst_a < worst_b else 0.0)
    pts_match_b = (1.0 if best_b < best_a else 0.0) + (1.0 if worst_b < worst_a else 0.0)

    # --- MVP INDIVIDUAL PURO ---
    mvp_inc = {"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}
    
    for i in range(4):
        if scores[i] <= 0: continue # Saltamos si no hay resultado
        
        # 1. Puntos por ganar a otros jugadores (0.5 por cada uno)
        for j in range(4):
            if i != j and scores[j] > 0:
                if scores[i] < scores[j]:
                    mvp_inc[f"p{i+1}"] += 0.5
        
        # 2. Bonus por el campo (vs Par)
        golpes = scores[i]
        if golpes <= par - 2: # Eagle o mejor
            mvp_inc[f"p{i+1}"] += 3.0
        elif golpes == par - 1: # Birdie
            mvp_inc[f"p{i+1}"] += 1.5
        elif golpes == par: # Par
            mvp_inc[f"p{i+1}"] += 0.5
            
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
        h_idx = g['h_sel']

        # --- NAVEGACIÓN ---
        col_prev, col_h, col_next = st.columns([1, 2, 1])
        if col_prev.button("⬅️ Ant.") and h_idx > 1:
            g['h_sel'] -= 1; st.rerun()
        col_h.markdown(f"<h3 style='text-align: center;'>Hoyo {h_idx} (Par {PAR_RIA_VIGO[h_idx]})</h3>", unsafe_allow_html=True)
        if col_next.button("Sig. ➡️") and h_idx < 18:
            g['h_sel'] += 1; st.rerun()

        # --- MARCADOR MATCH ---
        total_a = sum(v['pts'][0] for v in g['logs'].values())
        total_b = sum(v['pts'][1] for v in g['logs'].values())
        diff = int(total_a - total_b)
        st.markdown("#### 🏆 Marcador Match")
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("M&J", f"+{diff}" if diff > 0 else "0")
        c_m2.metric("R&L", f"+{abs(diff)}" if diff < 0 else "0")

        # --- ENTRADA DE DATOS ---
        v_def = g['logs'][h_idx]['s'] if h_idx in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        with st.container(border=True):
            st.write(f"**Introducir golpes Hoyo {h_idx}:**")
            c = st.columns(4)
            s1 = c[0].number_input("MANUEL", 0, 10, v_def[0], key=f"s1_{h_idx}")
            s2 = c[1].number_input("JOSE", 0, 10, v_def[1], key=f"s2_{h_idx}")
            s3 = c[2].number_input("ROGE", 0, 10, v_def[2], key=f"s3_{h_idx}")
            s4 = c[3].number_input("LALO", 0, 10, v_def[3], key=f"s4_{h_idx}")
            
            # Lógica de deshabilitar botón
            current_s = [s1, s2, s3, s4]
            btn_disabled = (h_idx in g['logs'] and current_s == g['logs'][h_idx]['s'])
            
            if st.button("✅ Confirmar Hoyo", use_container_width=True, type="primary", disabled=btn_disabled):
                pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, h_idx)
                g['logs'][h_idx] = {'s': current_s, 'pts': (pa, pb), 'mvp': mi}
                guardar_backup(g); st.rerun()

        # --- RESULTADO DEL HOYO ---
        if h_idx in g['logs']:
            log = g['logs'][h_idx]
            st.info(f"**Resultado Hoyo {h_idx}:** M&J +{log['pts'][0]} | R&L +{log['pts'][1]}")
            m = log['mvp']
            st.write(f"**MVP Hoyo:** M: {m['p1']} | J: {m['p2']} | R: {m['p3']} | L: {m['p4']}")

        # --- RANKING MVP ---
        if g['logs']:
            st.divider()
            cur_mvp = {p: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i, p in enumerate(TODOS)}
            st.subheader("⭐ Ranking MVP del Partido")
            st.table(pd.DataFrame([{"Jugador": p, "Puntos": cur_mvp[p]} for p in TODOS]).sort_values(by="Puntos", ascending=False))

            if st.button("💾 GUARDAR PARTIDO FINAL", use_container_width=True):
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
