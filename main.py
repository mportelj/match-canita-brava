import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN OFICIAL GOLF RÍA DE VIGO ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}

PAREJA_A = ["MANUEL", "JOSE"]
PAREJA_B = ["ROGE", "LALO"]
TODOS = PAREJA_A + PAREJA_B

# PUNTUACIÓN HISTÓRICA INICIAL
HISTORICO_PUNTOS = 3.5

def get_connection():
    return sqlite3.connect('canita_brava_v6.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Tabla de puntos por jugador y año
    c.execute('''CREATE TABLE IF NOT EXISTS puntos_anuales 
                 (nombre TEXT, temporada TEXT, partidos INTEGER DEFAULT 0, puntos_mvp INTEGER DEFAULT 0,
                  PRIMARY KEY (nombre, temporada))''')
    # Tabla de historial con la fecha del partido
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, temporada TEXT, 
                  pareja_a TEXT, pareja_b TEXT, resultado_a INTEGER, resultado_b INTEGER, mvp TEXT)''')
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

# --- INTERFAZ ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳")
st.title("⛳ CAÑITA BRAVA")

menu = st.sidebar.radio("Navegación", ["Inicio", "Anotar Partido", "Historial"])

if menu == "Inicio":
    conn = get_connection()
    anio_actual = str(datetime.now().year)
    st.subheader(f"📊 Balance Temporada {anio_actual}")
    
    df_h = pd.read_sql_query(f"SELECT resultado_a, resultado_b FROM historial WHERE temporada = '{anio_actual}'", conn)
    wins_a_db = len(df_h[df_h['resultado_a'] > df_h['resultado_b']])
    wins_b_db = len(df_h[df_h['resultado_b'] > df_h['resultado_a']])
    
    c1, c2 = st.columns(2)
    c1.metric("MANUEL & JOSE", f"{HISTORICO_PUNTOS + wins_a_db} Pts")
    c2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b_db} Pts")
    
    st.subheader(f"🏆 Ranking MVP {anio_actual}")
    df_mvp = pd.read_sql_query(f"SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM puntos_anuales WHERE temporada = '{anio_actual}' ORDER BY Puntos DESC", conn)
    st.table(df_mvp)

elif menu == "Anotar Partido":
    if 'game' not in st.session_state:
        st.subheader("Datos del Partido")
        # --- ENTRADA DE FECHA ---
        fecha_partido = st.date_input("¿Qué día se juega?", datetime.now())
        hoyo_inicio = st.selectbox("Empezamos en el hoyo:", [1, 10])
        
        if st.button("🚀 Iniciar Partido"):
            st.session_state.game = {
                'fecha_str': fecha_partido.strftime("%d/%m/%Y"),
                'temporada': str(fecha_partido.year),
                'hoyo': hoyo_inicio,
                'score_a': 0, 'score_b': 0,
                'mvp': {p: 0 for p in TODOS},
                'logs': []
            }
            st.rerun()
    else:
        g = st.session_state.game
        par_h = PAR_RIA_VIGO[g['hoyo']]
        st.subheader(f"Hoyo {g['hoyo']} (Par {par_h}) - {g['fecha_str']}")
        
        c = st.columns(4)
        s1 = c[0].number_input(f"MANUEL", 1, 15, par_h)
        s2 = c[1].number_input(f"JOSE", 1, 15, par_h)
        s3 = c[2].number_input(f"ROGE", 1, 15, par_h)
        s4 = c[3].number_input(f"LALO", 1, 15, par_h)

        if st.button("🎯 Anotar Hoyo"):
            pa, pb, minc = calcular_puntos_hoyo(s1, s2, s3, s4, g['hoyo'])
            g['logs'].append({'h': g['hoyo'], 'pts': (pa, pb), 'mvp_h': minc})
            g['score_a'] += pa
            g['score_b'] += pb
            for i, p in enumerate(TODOS): g['mvp'][p] += minc[f"p{i+1}"]
            g['hoyo'] = g['hoyo'] + 1 if g['hoyo'] < 18 else 1
            st.rerun()

        st.divider()
        st.write(f"**Marcador Actual:** M&J {g['score_a']} - {g['score_b']} R&L")
        
        if st.button("💾 Finalizar y Guardar"):
            conn = get_connection()
            cur = conn.cursor()
            mvp_ganador = max(g['mvp'], key=g['mvp'].get)
            
            cur.execute("INSERT INTO historial (fecha, temporada, pareja_a, pareja_b, resultado_a, resultado_b, mvp) VALUES (?,?,?,?,?,?,?)",
                       (g['fecha_str'], g['temporada'], "M&J", "R&L", g['score_a'], g['score_b'], mvp_ganador))
            
            for p, pts in g['mvp'].items():
                cur.execute("INSERT OR IGNORE INTO puntos_anuales (nombre, temporada) VALUES (?,?)", (p, g['temporada']))
                cur.execute("UPDATE puntos_anuales SET partidos = partidos + 1, puntos_mvp = puntos_mvp + ? WHERE nombre = ? AND temporada = ?", 
                           (pts, p, g['temporada']))
            
            conn.commit()
            del st.session_state.game
            st.success(f"Partido del {g['fecha_str']} guardado.")
            st.balloons()

elif menu == "Historial":
    conn = get_connection()
    st.subheader("📜 Historial de Partidos")
    df = pd.read_sql_query("SELECT fecha, resultado_a as 'M&J', resultado_b as 'R&L', mvp as 'MVP' FROM historial ORDER BY id DESC", conn)
    st.dataframe(df, use_container_width=True)
