import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- PARES OFICIALES RÍA DE VIGO (SEGÚN TU INDICACIÓN) ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}

def get_connection():
    return sqlite3.connect('golf_ria_vigo_final.db', check_same_thread=False)

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

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    pts_a, pts_b = 0, 0
    mvp_inc = {"p1": 0, "p2": 0, "p3": 0, "p4": 0}

    best_a, worst_a = (s1, s2) if s1 <= s2 else (s2, s1)
    best_b, worst_b = (s3, s4) if s3 <= s4 else (s4, s3)

    # Mejor Bola (+2 MVP)
    if best_a < best_b: 
        pts_a += 1
        mvp_inc["p1" if s1 == best_a else "p2"] += 2
    elif best_b < best_a: 
        pts_b += 1
        mvp_inc["p3" if s3 == best_b else "p4"] += 2

    # Peor Bola (+1 MVP)
    if worst_a < worst_b: 
        pts_a += 1
        mvp_inc["p1" if s1 == worst_a else "p2"] += 1
    elif worst_b < worst_a: 
        pts_b += 1
        mvp_inc["p3" if s3 == worst_b else "p4"] += 1

    # Bonos Birdie (+1) / Eagle (+2)
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
st.title("🏌️‍♂️ Ría de Vigo: Match Tracker")

menu = st.sidebar.radio("Navegación", ["Partido", "Clasificación MVP", "Historial"])

if menu == "Partido":
    if 'game' not in st.session_state:
        st.subheader("Configurar Nuevo Match")
        col1, col2 = st.columns(2)
        p1 = col1.text_input("Pareja A - J1", "Jugador 1")
        p2 = col1.text_input("Pareja A - J2", "Jugador 2")
        p3 = col2.text_input("Pareja B - J1", "Jugador 3")
        p4 = col2.text_input("Pareja B - J2", "Jugador 4")
        start_h = st.selectbox("Hoyo de salida:", [1, 10])
        
        if st.button("🏁 Empezar"):
            st.session_state.game = {
                'players': [p1, p2, p3, p4], 'hoyo': start_h,
                'score_a': 0, 'score_b': 0,
                'mvp': {p1: 0, p2: 0, p3: 0, p4: 0}, 
                'last_action': None, 'logs': []
            }
            st.rerun()
    else:
        g = st.session_state.game
        par_actual = PAR_RIA_VIGO[g['hoyo']]
        
        st.subheader(f"Hoyo {g['hoyo']} (Par {par_actual})")
        
        # Entrada de golpes con el PAR por defecto
        c = st.columns(4)
        s1 = c[0].number_input(f"{g['players'][0]}", 1, 15, par_actual)
        s2 = c[1].number_input(f"{g['players'][1]}", 1, 15, par_actual)
        s3 = c[2].number_input(f"{g['players'][2]}", 1, 15, par_actual)
        s4 = c[3].number_input(f"{g['players'][3]}", 1, 15, par_actual)

        if st.button("➕ Confirmar Hoyo"):
            pa, pb, minc = calcular_puntos_hoyo(s1, s2, s3, s4, g['hoyo'])
            
            # Guardamos el detalle del hoyo para poder deshacer
            detalle = {
                'num_hoyo': g['hoyo'],
                'golpes': [s1, s2, s3, s4],
                'puntos_match': (pa, pb),
                'puntos_mvp': minc
            }
            g['logs'].append(detalle)
            g['last_action'] = detalle
            
            # Actualizamos totales
            g['score_a'] += pa
            g['score_b'] += pb
            for i, p in enumerate(g['players']):
                g['mvp'][p] += minc[f"p{i+1}"]
            
            # Siguiente hoyo
            g['hoyo'] = g['hoyo'] + 1 if g['hoyo'] < 18 else 1
            st.rerun()

        # Visualización del Marcador
        st.divider()
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("PAREJA A", g['score_a'])
        col_m2.metric("PAREJA B", g['score_b'])

        # SECCIÓN: ÚLTIMO HOYO JUGADO (Nueva)
        if g['last_action']:
            la = g['last_action']
            with st.expander(f"Ver detalle Hoyo {la['num_hoyo']}", expanded=True):
                st.write(f"**Resultado Match:** A: +{la['puntos_match'][0]} | B: +{la['puntos_match'][1]}")
                st.write(f"**MVP del hoyo:** {la['puntos_mvp']}")

        # Botones de Control
        st.divider()
        c_undo, c_save = st.columns(2)
        
        if c_undo.button("🔙 Corregir / Deshacer"):
            if g['logs']:
                last = g['logs'].pop()
                g['score_a'] -= last['puntos_match'][0]
                g['score_b'] -= last['puntos_match'][1]
                for i, p in enumerate(g['players']):
                    g['mvp'][p] -= last['puntos_mvp'][f"p{i+1}"]
                g['hoyo'] = last['num_hoyo']
                g['last_action'] = g['logs'][-1] if g['logs'] else None
                st.rerun()

        if c_save.button("🏆 Finalizar Partido"):
            conn = get_connection()
            cur = conn.cursor()
            mvp_win = max(g['mvp'], key=g['mvp'].get)
            cur.execute("INSERT INTO historial (fecha, pareja_a, pareja_b, resultado_a, resultado_b, mvp) VALUES (?,?,?,?,?,?)",
                      (datetime.now().strftime("%d/%m/%Y"), f"{g['players'][0]}/{g['players'][1]}", f"{g['players'][2]}/{g['players'][3]}", g['score_a'], g['score_b'], mvp_win))
            for p, pts in g['mvp'].items():
                cur.execute("INSERT OR IGNORE INTO jugadores (nombre) VALUES (?)", (p,))
                cur.execute("UPDATE jugadores SET partidos = partidos + 1, puntos_mvp = puntos_mvp + ? WHERE nombre = ?", (pts, p))
            conn.commit()
            del st.session_state.game
            st.success("Partido guardado con éxito.")
            st.balloons()

elif menu == "Clasificación MVP":
    st.header("🏆 Clasificación MVP Acumulada")
    df = pd.read_sql_query("SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM jugadores ORDER BY puntos_mvp DESC", get_connection())
    st.dataframe(df, use_container_width=True)

elif menu == "Historial":
    st.header("📜 Historial de Matches")
    df = pd.read_sql_query("SELECT * FROM historial ORDER BY id DESC", get_connection())
    st.table(df)
