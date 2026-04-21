import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN OFICIAL GOLF RÍA DE VIGO ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}

# --- GESTIÓN DE BASE DE DATOS LOCAL ---
def get_connection():
    return sqlite3.connect('golf_ria_vigo_cañita_brava.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jugadores 
                 (nombre TEXT PRIMARY KEY, partidos INTEGER DEFAULT 0, puntos_mvp INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, pareja_a TEXT, pareja_b TEXT, 
                  resultado_a INTEGER, resultado_b INTEGER, mvp TEXT)''')
    conn.commit()

init_db()

# --- LÓGICA DE PUNTUACIÓN ---
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
        if s == par - 1: # Birdie
            mvp_inc[p_ids[i]] += 1
            if i < 2: pts_a += 1
            else: pts_b += 1
        elif s <= par - 2: # Eagle
            mvp_inc[p_ids[i]] += 2
            if i < 2: pts_a += 2
            else: pts_b += 2
            
    return pts_a, pts_b, mvp_inc

# --- INTERFAZ DE USUARIO ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="🍻")
st.title("🍻 CAÑITA BRAVA: Golf Tracker")

menu = st.sidebar.radio("Menú", ["Partido Actual", "Ranking MVP", "Historial"])

if menu == "Partido Actual":
    if 'game' not in st.session_state:
        st.subheader("Nuevo Duelo")
        col1, col2 = st.columns(2)
        j1 = col1.text_input("Pareja A - J1", "Jugador 1")
        j2 = col1.text_input("Pareja A - J2", "Jugador 2")
        j3 = col2.text_input("Pareja B - J1", "Jugador 3")
        j4 = col2.text_input("Pareja B - J2", "Jugador 4")
        salida = st.selectbox("Hoyo de inicio:", [1, 10])
        
        if st.button("🚀 Lanzar Partido"):
            st.session_state.game = {
                'players': [j1, j2, j3, j4], 'hoyo': salida,
                'score_a': 0, 'score_b': 0,
                'mvp': {j1: 0, j2: 0, j3: 0, j4: 0},
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
        m1.metric("PAREJA A", g['score_a'])
        m2.metric("PAREJA B", g['score_b'])

        if g['last_res']:
            st.success(g['last_res'])

        st.divider()
        col_atras, col_fin = st.columns(2)
        
        if col_atras.button("🔙 Deshacer Hoyo"):
            if g['logs']:
                l = g['logs'].pop()
                g['score_a'] -= l['p_match'][0]
                g['score_b'] -= l['p_match'][1]
                for i, p in enumerate(g['players']):
                    g['mvp'][p] -= l['p_mvp'][f"p{i+1}"]
                g['hoyo'] = l['h']
                g['last_res'] = "Hoyo corregido."
                st.rerun()

        if col_fin.button("💾 Guardar y Cerrar"):
            conn = get_connection()
            cur = conn.cursor()
            mvp_partido = max(g['mvp'], key=g['mvp'].get)
            
            cur.execute("INSERT INTO historial (fecha, pareja_a, pareja_b, resultado_a, resultado_b, mvp) VALUES (?,?,?,?,?,?)",
                      (datetime.now().strftime("%d/%m/%Y"), f"{g['players'][0]}/{g['players'][1]}", f"{g['players'][2]}/{g['players'][3]}", g['score_a'], g['score_b'], mvp_partido))
            
            for p, pts in g['mvp'].items():
                cur.execute("INSERT OR IGNORE INTO jugadores (nombre) VALUES (?)", (p,))
                cur.execute("UPDATE jugadores SET partidos = partidos + 1, puntos_mvp = puntos_mvp + ? WHERE nombre = ?", (pts, p))
            
            conn.commit()
            del st.session_state.game
            st.balloons()
            st.success(f"¡Victoria para el MVP: {mvp_partido}!")

elif menu == "Ranking MVP":
    st.header("🏆 Clasificación CAÑITA BRAVA")
    conn = get_connection()
    df = pd.read_sql_query("SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM jugadores ORDER BY Puntos DESC", conn)
    st.table(df)

elif menu == "Historial":
    st.header("📜 Archivo de Partidos")
    conn = get_connection()
    df = pd.read_sql_query("SELECT fecha, pareja_a as 'A', pareja_b as 'B', resultado_a as 'Res A', resultado_b as 'Res B', mvp as MVP FROM historial ORDER BY id DESC", conn)
    st.dataframe(df, use_container_width=True)
