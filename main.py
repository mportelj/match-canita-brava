import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN OFICIAL RÍA DE VIGO (Tus pares) ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}

def get_connection():
    return sqlite3.connect('canita_brava.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jugadores 
                 (nombre TEXT PRIMARY KEY, partidos INTEGER DEFAULT 0, puntos_mvp INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, resultado_a INTEGER, resultado_b INTEGER, mvp TEXT)''')
    conn.commit()

init_db()

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    pts_a, pts_b, mvp_inc = 0, 0, {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}

    # Mejores y peores
    b_a, w_a = (s1, s2) if s1 <= s2 else (s2, s1)
    b_b, w_b = (s3, s4) if s3 <= s4 else (s4, s3)

    # Mejor Bola: +2 MVP
    if b_a < b_b: 
        pts_a += 1
        mvp_inc["MANUEL" if s1 == b_a else "JOSE"] += 2
    elif b_b < b_a: 
        pts_b += 1
        mvp_inc["ROGE" if s3 == b_b else "LALO"] += 2

    # Peor Bola: +1 MVP
    if w_a < w_b: 
        pts_a += 1
        mvp_inc["MANUEL" if s1 == w_a else "JOSE"] += 1
    elif w_b < w_a: 
        pts_b += 1
        mvp_inc["ROGE" if s3 == w_b else "LALO"] += 1

    # Bonos Birdie (+1) y Eagle (+2)
    sc = [s1, s2, s3, s4]
    js = ["MANUEL", "JOSE", "ROGE", "LALO"]
    for i, s in enumerate(sc):
        if s == par - 1: # Birdie
            mvp_inc[js[i]] += 1
            if i < 2: pts_a += 1
            else: pts_b += 1
        elif s <= par - 2: # Eagle
            mvp_inc[js[i]] += 2
            if i < 2: pts_a += 2
            else: pts_b += 2
            
    return pts_a, pts_b, mvp_inc

# --- INTERFAZ ---
st.set_page_config(page_title="MATCH CAÑITA BRAVA", page_icon="🍺")
st.title("🍺 MATCH CAÑITA BRAVA")

menu = st.sidebar.radio("Menú", ["Partido", "Ranking MVP", "Historial"])

if menu == "Partido":
    if 'match' not in st.session_state:
        st.subheader("Nuevo Enfrentamiento")
        st.write("**MANUEL & JOSE** vs **ROGE & LALO**")
        salida = st.selectbox("Salida por el hoyo:", [1, 10])
        if st.button("🚀 Empezar Match"):
            st.session_state.match = {
                'hoyo': salida, 'score_a': 0, 'score_b': 0,
                'mvp': {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}, 'logs': []
            }
            st.rerun()
    else:
        m = st.session_state.match
        par = PAR_RIA_VIGO[m['hoyo']]
        st.subheader(f"Hoyo {m['hoyo']} (Par {par})")
        
        c1, c2 = st.columns(2)
        s1 = c1.number_input("MANUEL", 1, 10, par)
        s2 = c1.number_input("JOSE", 1, 10, par)
        s3 = c2.number_input("ROGE", 1, 10, par)
        s4 = c2.number_input("LALO", 1, 10, par)

        if st.button("➕ Anotar Hoyo"):
            pa, pb, minc = calcular_puntos_hoyo(s1, s2, s3, s4, m['hoyo'])
            m['logs'].append({'h': m['hoyo'], 'pts': (pa, pb), 'mvp': minc})
            m['score_a'] += pa
            m['score_b'] += pb
            for p in ["MANUEL", "JOSE", "ROGE", "LALO"]:
                m['mvp'][p] += minc[p]
            m['hoyo'] = m['hoyo'] + 1 if m['hoyo'] < 18 else 1
            st.rerun()

        st.metric("Marcador", f"MANUEL/JOSE: {m['score_a']} | ROGE/LALO: {m['score_b']}")
        
        col1, col2 = st.columns(2)
        if col1.button("🔙 Deshacer"):
            if m['logs']:
                last = m['logs'].pop()
                m['score_a'] -= last['pts'][0]
                m['score_b'] -= last['pts'][1]
                for p in ["MANUEL", "JOSE", "ROGE", "LALO"]:
                    m['mvp'][p] -= last['mvp'][p]
                m['hoyo'] = last['h']
                st.rerun()

        if col2.button("💾 Guardar"):
            conn = get_connection()
            cur = conn.cursor()
            mvp_win = max(m['mvp'], key=m['mvp'].get)
            cur.execute("INSERT INTO historial (fecha, resultado_a, resultado_b, mvp) VALUES (?,?,?,?)",
                      (datetime.now().strftime("%d/%m/%Y"), m['score_a'], m['score_b'], mvp_win))
            for p, pts in m['mvp'].items():
                cur.execute("INSERT OR IGNORE INTO jugadores (nombre) VALUES (?)", (p,))
                cur.execute("UPDATE jugadores SET partidos = partidos + 1, puntos_mvp = puntos_mvp + ? WHERE nombre = ?", (pts, p))
            conn.commit()
            del st.session_state.match
            st.success(f"Guardado. MVP: {mvp_win}")
            st.balloons()

elif menu == "Ranking MVP":
    st.header("🏆 Ranking Acumulado")
    df = pd.read_sql_query("SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM jugadores ORDER BY puntos_mvp DESC", get_connection())
    st.table(df)

elif menu == "Historial":
    st.header("📜 Últimos Matches")
    df = pd.read_sql_query("SELECT fecha, resultado_a as 'M/J', resultado_b as 'R/L', mvp FROM historial ORDER BY id DESC", get_connection())
    st.table(df)
