import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN OFICIAL RÍA DE VIGO ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}

def get_connection():
    return sqlite3.connect('canita_brava_multianual.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Tabla de jugadores con año para separar estadísticas
    c.execute('''CREATE TABLE IF NOT EXISTS jugadores 
                 (nombre TEXT, anio INTEGER, puntos_mvp INTEGER DEFAULT 0, 
                  birdies_totales INTEGER DEFAULT 0, eagles_totales INTEGER DEFAULT 0,
                  PRIMARY KEY (nombre, anio))''')
    # Tabla de clasificación por temporada
    c.execute('''CREATE TABLE IF NOT EXISTS temporadas_global 
                 (equipo TEXT, anio INTEGER, puntos_ganados REAL DEFAULT 0,
                  PRIMARY KEY (equipo, anio))''')
    # Historial de partidos con año
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, anio INTEGER, 
                  res_mj INTEGER, res_rl INTEGER, puntos_temp_mj REAL, puntos_temp_rl REAL, mvp TEXT,
                  p1_inc INTEGER, p2_inc INTEGER, p3_inc INTEGER, p4_inc INTEGER,
                  b1_inc INTEGER, b2_inc INTEGER, b3_inc INTEGER, b4_inc INTEGER,
                  e1_inc INTEGER, e2_inc INTEGER, e3_inc INTEGER, e4_inc INTEGER)''')
    
    # Inicializar 2026 con vuestro 3.5 - 3.5
    c.execute("SELECT COUNT(*) FROM temporadas_global WHERE anio = 2026")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO temporadas_global VALUES ('MANUEL_JOSE', 2026, 3.5)")
        c.execute("INSERT INTO temporadas_global VALUES ('ROGE_LALO', 2026, 3.5)")
    conn.commit()

init_db()

# --- LÓGICA DE CÁLCULO ---
def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    pts_a, pts_b = 0, 0
    mvp_inc = {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}
    birdies_inc = {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}
    eagles_inc = {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}
    
    b_a, w_a = (s1, s2) if s1 <= s2 else (s2, s1)
    b_b, w_b = (s3, s4) if s3 <= s4 else (s4, s3)

    if b_a < b_b: pts_a += 1; mvp_inc["MANUEL" if s1 == b_a else "JOSE"] += 2
    elif b_b < b_a: pts_b += 1; mvp_inc["ROGE" if s3 == b_b else "LALO"] += 2

    if w_a < w_b: pts_a += 1; mvp_inc["MANUEL" if s1 == w_a else "JOSE"] += 1
    elif w_b < w_a: pts_b += 1; mvp_inc["ROGE" if s3 == w_b else "LALO"] += 1

    js = ["MANUEL", "JOSE", "ROGE", "LALO"]
    for i, s in enumerate([s1, s2, s3, s4]):
        if s == par - 1:
            mvp_inc[js[i]] += 1; birdies_inc[js[i]] += 1
            if i < 2: pts_a += 1
            else: pts_b += 1
        elif s <= par - 2:
            mvp_inc[js[i]] += 2; eagles_inc[js[i]] += 1
            if i < 2: pts_a += 2
            else: pts_b += 2
    return pts_a, pts_b, mvp_inc, birdies_inc, eagles_inc

# --- INTERFAZ ---
st.set_page_config(page_title="Match CAÑITA BRAVA", page_icon="🍺")
st.title("🍺 MATCH CAÑITA BRAVA")

# Selector de año en la barra lateral
anio_actual = st.sidebar.selectbox("Seleccionar Temporada:", [2026, 2027, 2028, 2029], index=0)
menu = st.sidebar.radio("Ir a:", ["Marcador Temporada", "Jugar Partido", "Historial", "Administración"])

conn = get_connection()

if menu == "Marcador Temporada":
    st.header(f"🏆 Temporada {anio_actual}")
    df_temp = pd.read_sql_query(f"SELECT equipo as Equipo, puntos_ganados as Puntos FROM temporadas_global WHERE anio = {anio_actual}", conn)
    if not df_temp.empty:
        df_temp['Puntos'] = df_temp['Puntos'].map('{:.1f}'.format)
        st.table(df_temp)
    else:
        st.info(f"La temporada {anio_actual} aún no ha comenzado.")

    st.subheader(f"🥇 MVP Individual {anio_actual}")
    df_mvp = pd.read_sql_query(f"SELECT nombre as Jugador, puntos_mvp as Puntos, eagles_totales as Eagles, birdies_totales as Birdies FROM jugadores WHERE anio = {anio_actual} ORDER BY puntos_mvp DESC, eagles_totales DESC", conn)
    st.table(df_mvp)

elif menu == "Jugar Partido":
    st.subheader(f"Registrar partido para {anio_actual}")
    if 'match' not in st.session_state:
        salida = st.selectbox("Hoyo de salida:", [1, 10])
        if st.button("Comenzar Partido"):
            st.session_state.match = {'hoyo': salida, 'score_mj': 0, 'score_rl': 0, 'mvp': {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}, 'birdies': {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}, 'eagles': {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}, 'logs': []}
            st.rerun()
    else:
        m = st.session_state.match
        par = PAR_RIA_VIGO[m['hoyo']]
        st.write(f"**Hoyo {m['hoyo']} (Par {par})**")
        c1, c2 = st.columns(2)
        s1, s2 = c1.number_input("MANUEL", 1, 10, par), c1.number_input("JOSE", 1, 10, par)
        s3, s4 = c2.number_input("ROGE", 1, 10, par), c2.number_input("LALO", 1, 10, par)

        if st.button("Anotar Hoyo"):
            pa, pb, minc, binc, einc = calcular_puntos_hoyo(s1, s2, s3, s4, m['hoyo'])
            m['logs'].append({'h': m['hoyo'], 'pts': (pa, pb), 'mvp': minc, 'birdies': binc, 'eagles': einc})
            m['score_mj'] += pa; m['score_rl'] += pb
            for p in minc: m['mvp'][p] += minc[p]; m['birdies'][p] += binc[p]; m['eagles'][p] += einc[p]
            m['hoyo'] = m['hoyo'] + 1 if m['hoyo'] < 18 else 1
            st.rerun()

        st.metric("Resultado Hoy", f"M&J: {m['score_mj']} | R&L: {m['score_rl']}")

        if st.button("💾 Finalizar y Guardar"):
            cur = conn.cursor()
            p_mj, p_rl = (1.0, 0.0) if m['score_mj'] > m['score_rl'] else (0.0, 1.0) if m['score_rl'] > m['score_mj'] else (0.5, 0.5)
            
            # Asegurar que existan los registros de temporada para el año seleccionado
            cur.execute("INSERT OR IGNORE INTO temporadas_global VALUES ('MANUEL_JOSE', ?, 0)", (anio_actual,))
            cur.execute("INSERT OR IGNORE INTO temporadas_global VALUES ('ROGE_LALO', ?, 0)", (anio_actual,))
            
            cur.execute("INSERT INTO historial (fecha, anio, res_mj, res_rl, puntos_temp_mj, puntos_temp_rl, mvp, p1_inc, p2_inc, p3_inc, p4_inc, b1_inc, b2_inc, b3_inc, b4_inc, e1_inc, e2_inc, e3_inc, e4_inc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (datetime.now().strftime("%d/%m/%Y"), anio_actual, m['score_mj'], m['score_rl'], p_mj, p_rl, max(m['mvp'], key=m['mvp'].get), m['mvp']["MANUEL"], m['mvp']["JOSE"], m['mvp']["ROGE"], m['mvp']["LALO"], m['birdies']["MANUEL"], m['birdies']["JOSE"], m['birdies']["ROGE"], m['birdies']["LALO"], m['eagles']["MANUEL"], m['eagles']["JOSE"], m['eagles']["ROGE"], m['eagles']["LALO"]))
            
            cur.execute("UPDATE temporadas_global SET puntos_ganados = puntos_ganados + ? WHERE equipo = 'MANUEL_JOSE' AND anio = ?", (p_mj, anio_actual))
            cur.execute("UPDATE temporadas_global SET puntos_ganados = puntos_ganados + ? WHERE equipo = 'ROGE_LALO' AND anio = ?", (p_rl, anio_actual))
            
            for p in ["MANUEL", "JOSE", "ROGE", "LALO"]:
                cur.execute("INSERT OR IGNORE INTO jugadores (nombre, anio, puntos_mvp, birdies_totales, eagles_totales) VALUES (?,?,
