import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}
TODOS = ["MANUEL", "JOSE", "ROGE", "LALO"]
HISTORICO_PUNTOS = 3.5

def get_connection():
    return sqlite3.connect('canita_brava_v7.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS puntos_anuales 
                 (nombre TEXT, temporada TEXT, partidos INTEGER DEFAULT 0, puntos_mvp INTEGER DEFAULT 0,
                  PRIMARY KEY (nombre, temporada))''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, temporada TEXT, 
                  pareja_a TEXT, pareja_b TEXT, resultado_a INTEGER, resultado_b INTEGER, mvp TEXT,
                  p1_pts INTEGER, p2_pts INTEGER, p3_pts INTEGER, p4_pts INTEGER)''')
    conn.commit()

init_db()

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    pts_a, pts_b = 0, 0
    mvp_inc = {"p1": 0, "p2": 0, "p3": 0, "p4": 0}
    best_a, worst_a = (s1, s2) if s1 <= s2 else (s2, s1)
    best_b, worst_b = (s3, s4) if s3 <= s4 else (s4, s3)
    if best_a < best_b: 
        pts_a += 1
        mvp_inc["p1" if s1 == best_a else "p2"] += 2
    elif best_b < best_a: 
        pts_b += 1
        mvp_inc["p3" if s3 == best_b else "p4"] += 2
    if worst_a < worst_b: 
        pts_a += 1
        mvp_inc["p1" if s1 == worst_a else "p2"] += 1
    elif worst_b < worst_a: 
        pts_b += 1
        mvp_inc["p3" if s3 == worst_b else "p4"] += 1
    scores = [s1, s2, s3, s4]
    p_ids = ["p1", "p2", "p3", "p4"]
    for i, s in enumerate(scores):
        if s == par - 1:
            mvp_inc[p_ids[i]] += 1
            if i < 2: pts_a += 1
            else: pts_b += 1
        elif s <= par - 2:
            mvp_inc[p_ids[i]] += 2
            if i < 2: pts_a += 2
            else: pts_b += 2
    return pts_a, pts_b, mvp_inc

st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳")
st.title("⛳ CAÑITA BRAVA")

menu = st.sidebar.radio("Menú", ["Inicio", "Anotar Partido", "Historial / Borrar"])

if menu == "Inicio":
    conn = get_connection()
    anio_actual = str(datetime.now().year)
    st.subheader(f"📊 Balance Temporada {anio_actual}")
    df_h = pd.read_sql_query(f"SELECT resultado_a, resultado_b FROM historial WHERE temporada = '{anio_actual}'", conn)
    wins_a = len(df_h[df_h['resultado_a'] > df_h['resultado_b']])
    wins_b = len(df_h[df_h['resultado_b'] > df_h['resultado_a']])
    c1, c2 = st.columns(2)
    c1.metric("MANUEL & JOSE", f"{HISTORICO_PUNTOS + wins_a} Pts")
    c2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b} Pts")
    st.subheader(f"🏆 Ranking MVP {anio_actual}")
    df_mvp = pd.read_sql_query(f"SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM puntos_anuales WHERE temporada = '{anio_actual}' ORDER BY Puntos DESC", conn)
    st.table(df_mvp)

elif menu == "Anotar Partido":
    if 'game' not in st.session_state:
        st.subheader("Datos del Partido")
        f = st.date_input("Fecha:", datetime.now())
        h = st.selectbox("Inicio:", [1, 10])
        if st.button("🚀 Iniciar"):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'hoyo': h, 'logs': {}}
            st.rerun()
    else:
        g = st.session_state.game
        st.subheader(f"Hoyo Actual: {g['hoyo']} (Par {PAR_RIA_VIGO[g['hoyo']]})")
        c = st.columns(4)
        s1 = c[0].number_input("MANUEL", 1, 10, PAR_RIA_VIGO[g['hoyo']])
        s2 = c[1].number_input("JOSE", 1, 10, PAR_RIA_VIGO[g['hoyo']])
        s3 = c[2].number_input("ROGE", 1, 10, PAR_RIA_VIGO[g['hoyo']])
        s4 = c[3].number_input("LALO", 1, 10, PAR_RIA_VIGO[g['hoyo']])
        
        if st.button("🎯 Anotar Hoyo"):
            pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, g['hoyo'])
            g['logs'][g['hoyo']] = {'s': [s1, s2, s3, s4], 'pts': (pa, pb), 'mvp': mi}
            g['hoyo'] = g['hoyo'] + 1 if g['hoyo'] < 18 else 1
            st.rerun()

        if g['logs']:
            st.divider()
            st.subheader("📝 Hoyos Jugados (Pulsa para editar)")
            # Recalcular totales en tiempo real
            total_a = sum(v['pts'][0] for v in g['logs'].values())
            total_b = sum(v['pts'][1] for v in g['logs'].values())
            st.write(f"**Marcador: M&J {total_a} - {total_b} R&L**")
            
            for h_num in sorted(g['logs'].keys()):
                col_h, col_ed = st.columns([3, 1])
                datos = g['logs'][h_num]
                col_h.write(f"Hoyo {h_num}: Golpes {datos['s']} (Pts: {datos['pts']})")
                if col_ed.button("Editar", key=f"ed_{h_num}"):
                    g['hoyo'] = h_num
                    st.rerun()

            if st.button("💾 GUARDAR TODO EL PARTIDO"):
                conn = get_connection()
                cur = conn.cursor()
                final_mvp_pts = {p: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i, p in enumerate(TODOS)}
                mvp_win = max(final_mvp_pts, key=final_mvp_pts.get)
                cur.execute("INSERT INTO historial (fecha, temporada, pareja_a, pareja_b, resultado_a, resultado_b, mvp, p1_pts, p2_pts, p3_pts, p4_pts) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (g['fecha'], g['temp'], "M&J", "R&L", total_a, total_b, mvp_win, final_mvp_pts["MANUEL"], final_mvp_pts["JOSE"], final_mvp_pts["ROGE"], final_mvp_pts["LALO"]))
                for p in TODOS:
                    cur.execute("INSERT OR IGNORE INTO puntos_anuales (nombre, temporada) VALUES (?,?)", (p, g['temp']))
                    cur.execute("UPDATE puntos_anuales SET partidos = partidos + 1, puntos_mvp = puntos_mvp + ? WHERE nombre = ? AND temporada = ?", (final_mvp_pts[p], p, g['temp']))
                conn.commit()
                del st.session_state.game
                st.balloons()
                st.rerun()

elif menu == "Historial / Borrar":
    conn = get_connection()
    st.subheader("📜 Historial de Partidos")
    df = pd.read_sql_query("SELECT * FROM historial ORDER BY id DESC", conn)
    for index, row in df.iterrows():
        with st.expander(f"📅 {row['fecha']} | M&J {row['resultado_a']} - {row['resultado_b']} R&L"):
            st.write(f"MVP: {row['mvp']}")
            if st.button(f"🗑️ Eliminar Partido {row['id']}", key=f"del_{row['id']}"):
                cur = conn.cursor()
                # Restar puntos de la tabla anual
                pts_map = {"MANUEL": row['p1_pts'], "JOSE": row['p2_pts'], "ROGE": row['p3_pts'], "LALO": row['p4_pts']}
                for p, pts in pts_map.items():
                    cur.execute("UPDATE puntos_anuales SET partidos = partidos - 1, puntos_mvp = puntos_mvp - ? WHERE nombre = ? AND temporada = ?", (pts, p, row['temporada']))
                cur.execute("DELETE FROM historial WHERE id = ?", (row['id'],))
                conn.commit()
                st.warning("Partido eliminado. Recargando...")
                st.rerun()
