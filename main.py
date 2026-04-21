import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN OFICIAL GOLF RÍA DE VIGO ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}

# JUGADORES FIJOS
PAREJA_A = ["MANUEL", "JOSE"]
PAREJA_B = ["ROGE", "LALO"]
TODOS = PAREJA_A + PAREJA_B

def get_connection():
    return sqlite3.connect('canita_brava_v3.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jugadores 
                 (nombre TEXT PRIMARY KEY, partidos INTEGER DEFAULT 0, puntos_mvp INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, pareja_a TEXT, pareja_b TEXT, 
                  resultado_a INTEGER, resultado_b INTEGER, mvp TEXT)''')
    # Inicializar a los 4 fantásticos si no existen
    for p in TODOS:
        c.execute("INSERT OR IGNORE INTO jugadores (nombre) VALUES (?)", (p,))
    conn.commit()

init_db()

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    pts_a, pts_b = 0, 0
    mvp_inc = {"p1": 0, "p2": 0, "p3": 0, "p4": 0}

    best_a, worst_a = (s1, s2) if s1 <= s2 else (s2, s1)
    best_b, worst_b = (s3, s4) if s3 <= s4 else (s4, s3)

    # Mejor Bola: +2 MVP
    if best_a < best_b: 
        pts_a += 1
        mvp_inc["p1" if s1 == best_a else "p2"] += 2
    elif best_b < best_a: 
        pts_b += 1
        mvp_inc["p3" if s3 == best_b else "p4"] += 2

    # Peor Bola: +1 MVP
    if worst_a < worst_b: 
        pts_a += 1
        mvp_inc["p1" if s1 == worst_a else "p2"] += 1
    elif worst_b < worst_a: 
        pts_b += 1
        mvp_inc["p3" if s3 == worst_b else "p4"] += 1

    # Bonos Calidad: Birdie +1 / Eagle +2
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
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="🍻")
st.title("🍻 CAÑITA BRAVA")

menu = st.sidebar.radio("Menú", ["Partido", "Ranking MVP", "Historial"])

if menu == "Partido":
    if 'game' not in st.session_state:
        st.subheader("Preparar Jornada")
        st.info(f"Parejas: **{PAREJA_A[0]} & {PAREJA_A[1]}** vs **{PAREJA_B[0]} & {PAREJA_B[1]}**")
        salida = st.selectbox("Hoyo de inicio:", [1, 10])
        
        if st.button("🚀 Lanzar Partido"):
            st.session_state.game = {
                'players': TODOS, 'hoyo': salida,
                'score_a': 0, 'score_b': 0,
                'mvp': {p: 0 for p in TODOS},
                'logs': [], 'last_res': None
            }
            st.rerun()
    else:
        g = st.session_state.game
        par_h = PAR_RIA_VIGO[g['hoyo']]
        
        st.subheader(f"Hoyo {g['hoyo']} (Par {par_h})")
        
        c = st.columns(4)
        s1 = c[0].number_input(f"{g['players'][0]}", 1, 15, par_h)
        s2 = c[1].number_input(f"{g['players'][1]}", 1, 15, par_h)
        s3 = c[2].number_input(f"{g['players'][2]}", 1, 15, par_h)
        s4 = c[3].number_input(f"{g['players'][3]}", 1, 15, par_h)

        if st.button("🎯 Anotar Hoyo"):
            pa, pb, minc = calcular_puntos_hoyo(s1, s2, s3, s4, g['hoyo'])
            res_hoyo = {'h': g['hoyo'], 'p_match': (pa, pb), 'p_mvp': minc}
            g['logs'].append(res_hoyo)
            g['last_res'] = f"Último hoyo ({g['hoyo']}): A +{pa} | B +{pb}"
            
            g['score_a'] += pa
            g['score_b'] += pb
            for i, p in enumerate(g['players']):
                g['mvp'][p] += minc[f"p{i+1}"]
            
            g['hoyo'] = g['hoyo'] + 1 if g['hoyo'] < 18 else 1
            st.rerun()

        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("MANUEL & JOSE", g['score_a'])
        m2.metric("ROGE & LALO", g['score_b'])

        if g['last_res']:
            st.success(g['last_res'])

        st.divider()
        c_atras, c_fin = st.columns(2)
        if c_atras.button("🔙 Deshacer"):
            if g['logs']:
                l = g['logs'].pop()
                g['score_a'] -= l['p_match'][0]
                g['score_b'] -= l['p_match'][1]
                for i, p in enumerate(g['players']):
                    g['mvp'][p] -= l['p_mvp'][f"p{i+1}"]
                g['hoyo'] = l['h']
                st.rerun()

        if c_fin.button("💾 Guardar y Finalizar"):
            conn = get_connection()
            cur = conn.cursor()
            mvp_partido = max(g['mvp'], key=g['mvp'].get)
            cur.execute("INSERT INTO historial (fecha, pareja_a, pareja_b, resultado_a, resultado_b, mvp) VALUES (?,?,?,?,?,?)",
                      (datetime.now().strftime("%d/%m/%Y"), "M&J", "R&L", g['score_a'], g['score_b'], mvp_partido))
            for p, pts in g['mvp'].items():
                cur.execute("UPDATE jugadores SET partidos = partidos + 1, puntos_mvp = puntos_mvp + ? WHERE nombre = ?", (pts, p))
            conn.commit()
            del st.session_state.game
            st.balloons()

elif menu == "Ranking MVP":
    st.header("🏆 Ranking CAÑITA BRAVA")
    df = pd.read_sql_query("SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM jugadores ORDER BY Puntos DESC", get_connection())
    st.table(df)

elif menu == "Historial":
    st.header("📜 Archivo de Partidos")
    df = pd.read_sql_query("SELECT fecha, pareja_a, pareja_b, resultado_a as 'M&J', resultado_b as 'R&L', mvp FROM historial ORDER BY id DESC", get_connection())
    st.dataframe(df, use_container_width=True)
