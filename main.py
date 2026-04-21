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
    return sqlite3.connect('canita_brava_2026_final.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jugadores 
                 (nombre TEXT PRIMARY KEY, puntos_mvp INTEGER DEFAULT 0, 
                  birdies_totales INTEGER DEFAULT 0, eagles_totales INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS temporada 
                 (equipo TEXT PRIMARY KEY, puntos_ganados REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, res_mj INTEGER, res_rl INTEGER, 
                  puntos_temporada_mj REAL, puntos_temporada_rl REAL, mvp TEXT,
                  p1_inc INTEGER, p2_inc INTEGER, p3_inc INTEGER, p4_inc INTEGER,
                  b1_inc INTEGER, b2_inc INTEGER, b3_inc INTEGER, b4_inc INTEGER,
                  e1_inc INTEGER, e2_inc INTEGER, e3_inc INTEGER, e4_inc INTEGER)''')
    
    c.execute("SELECT COUNT(*) FROM temporada")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO temporada VALUES ('MANUEL_JOSE', 3.5)")
        c.execute("INSERT INTO temporada VALUES ('ROGE_LALO', 3.5)")
    conn.commit()

init_db()

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    pts_a, pts_b = 0, 0
    mvp_inc = {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}
    birdies_inc = {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}
    eagles_inc = {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0}
    
    b_a, w_a = (s1, s2) if s1 <= s2 else (s2, s1)
    b_b, w_b = (s3, s4) if s3 <= s4 else (s4, s3)

    if b_a < b_b: 
        pts_a += 1
        mvp_inc["MANUEL" if s1 == b_a else "JOSE"] += 2
    elif b_b < b_a: 
        pts_b += 1
        mvp_inc["ROGE" if s3 == b_b else "LALO"] += 2

    if w_a < w_b: 
        pts_a += 1
        mvp_inc["MANUEL" if s1 == w_a else "JOSE"] += 1
    elif w_b < w_a: 
        pts_b += 1
        mvp_inc["ROGE" if s3 == w_b else "LALO"] += 1

    js = ["MANUEL", "JOSE", "ROGE", "LALO"]
    for i, s in enumerate([s1, s2, s3, s4]):
        if s == par - 1:
            mvp_inc[js[i]] += 1
            birdies_inc[js[i]] += 1
            if i < 2: pts_a += 1
            else: pts_b += 1
        elif s <= par - 2:
            mvp_inc[js[i]] += 2
            eagles_inc[js[i]] += 1
            if i < 2: pts_a += 2
            else: pts_b += 2
            
    return pts_a, pts_b, mvp_inc, birdies_inc, eagles_inc

# --- INTERFAZ ---
st.set_page_config(page_title="MATCH CAÑITA BRAVA 2026", page_icon="🍺")
st.title("🍺 MATCH CAÑITA BRAVA 2026")

menu = st.sidebar.radio("Ir a:", ["Marcador Temporada", "Jugar Partido", "Historial", "Administración"])

if menu == "Marcador Temporada":
    st.header("🏆 Clasificación General 2026")
    df_temp = pd.read_sql_query("SELECT equipo as Equipo, puntos_ganados as Puntos FROM temporada", get_connection())
    df_temp['Puntos'] = df_temp['Puntos'].map('{:.1f}'.format)
    st.table(df_temp)
    
    st.subheader("🥇 Ranking MVP")
    df_mvp = pd.read_sql_query("""SELECT nombre as Jugador, puntos_mvp as Puntos, 
                                  eagles_totales as Eagles, birdies_totales as Birdies 
                                  FROM jugadores 
                                  ORDER BY puntos_mvp DESC, eagles_totales DESC, birdies_totales DESC""", get_connection())
    st.table(df_mvp)

elif menu == "Jugar Partido":
    if 'match' not in st.session_state:
        salida = st.selectbox("Hoyo de salida:", [1, 10])
        if st.button("Comenzar Partido"):
            st.session_state.match = {
                'hoyo': salida, 'score_mj': 0, 'score_rl': 0, 
                'mvp': {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0},
                'birdies': {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0},
                'eagles': {"MANUEL": 0, "JOSE": 0, "ROGE": 0, "LALO": 0},
                'logs': []
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

        if st.button("Anotar Hoyo"):
            pa, pb, minc, binc, einc = calcular_puntos_hoyo(s1, s2, s3, s4, m['hoyo'])
            m['logs'].append({'h': m['hoyo'], 'pts': (pa, pb), 'mvp': minc, 'birdies': binc, 'eagles': einc})
            m['score_mj'] += pa
            m['score_rl'] += pb
            for p in minc:
                m['mvp'][p] += minc[p]
                m['birdies'][p] += binc[p]
                m['eagles'][p] += einc[p]
            m['hoyo'] = m['hoyo'] + 1 if m['hoyo'] < 18 else 1
            st.rerun()

        st.metric("Resultado Hoy", f"M&J: {m['score_mj']} | R&L: {m['score_rl']}")

        if st.button("💾 Finalizar y Guardar"):
            conn = get_connection()
            cur = conn.cursor()
            p_mj, p_rl = (1.0, 0.0) if m['score_mj'] > m['score_rl'] else (0.0, 1.0) if m['score_rl'] > m['score_mj'] else (0.5, 0.5)
            
            mvp_win = max(m['mvp'], key=m['mvp'].get)
            cur.execute("""INSERT INTO historial (fecha, res_mj, res_rl, puntos_temporada_mj, puntos_temporada_rl, mvp,
                           p1_inc, p2_inc, p3_inc, p4_inc, b1_inc, b2_inc, b3_inc, b4_inc, e1_inc, e2_inc, e3_inc, e4_inc) 
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (datetime.now().strftime("%d/%m/%Y"), m['score_mj'], m['score_rl'], p_mj, p_rl, mvp_win,
                       m['mvp']["MANUEL"], m['mvp']["JOSE"], m['mvp']["ROGE"], m['mvp']["LALO"],
                       m['birdies']["MANUEL"], m['birdies']["JOSE"], m['birdies']["ROGE"], m['birdies']["LALO"],
                       m['eagles']["MANUEL"], m['eagles']["JOSE"], m['eagles']["ROGE"], m['eagles']["LALO"]))
            
            cur.execute("UPDATE temporada SET puntos_ganados = puntos_ganados + ? WHERE equipo = 'MANUEL_JOSE'", (p_mj,))
            cur.execute("UPDATE temporada SET puntos_ganados = puntos_ganados + ? WHERE equipo = 'ROGE_LALO'", (p_rl,))
            
            for p in ["MANUEL", "JOSE", "ROGE", "LALO"]:
                cur.execute("INSERT OR IGNORE INTO jugadores (nombre) VALUES (?,0,0,0)", (p,))
                cur.execute("UPDATE jugadores SET puntos_mvp = puntos_mvp + ?, birdies_totales = birdies_totales + ?, eagles_totales = eagles_totales + ? WHERE nombre = ?", (m['mvp'][p], m['birdies'][p], m['eagles'][p], p))
            
            conn.commit()
            del st.session_state.match
            st.success("¡Partido guardado!")
            st.rerun()

elif menu == "Historial":
    st.header("📅 Historial Temporada 2026")
    df_h = pd.read_sql_query("SELECT fecha as Fecha, res_mj as 'Hoy M/J', res_rl as 'Hoy R/L', puntos_temporada_mj as 'Temp M/J', puntos_temporada_rl as 'Temp R/L', mvp as MVP FROM historial ORDER BY id DESC", get_connection())
    df_h['Temp M/J'] = df_h['Temp M/J'].map('{:.1f}'.format)
    df_h['Temp R/L'] = df_h['Temp R/L'].map('{:.1f}'.format)
    st.table(df_h)

elif menu == "Administración":
    st.header("⚙️ Zona de Control")
    st.write("Selecciona qué partido deseas eliminar permanentemente.")
    
    conn = get_connection()
    # Cargamos todos los partidos para el selector
    df_hist = pd.read_sql_query("SELECT id, fecha, res_mj, res_rl FROM historial ORDER BY id DESC", conn)
    
    if not df_hist.empty:
        # Creamos una lista de opciones descriptivas para el selectbox
        opciones = {row['id']: f"ID: {row['id']} | {row['fecha']} | MJ: {row['res_mj']} - RL: {row['res_rl']}" for index, row in df_hist.iterrows()}
        seleccion_id = st.selectbox("Partido a borrar:", options=list(opciones.keys()), format_func=lambda x: opciones[x])
        
        # Mostrar detalle del seleccionado
        partido_selec = df_hist[df_hist['id'] == seleccion_id].iloc[0]
        st.info(f"Vas a eliminar el partido del día {partido_selec['fecha']}.")
        
        confirmar = st.checkbox("Confirmo que quiero borrar este partido y revertir sus puntos.")
        
        if st.button("🗑️ Eliminar Partido Seleccionado"):
            if confirmar:
                cur = conn.cursor()
                # Obtener los datos completos de ese partido para revertir
                datos_partido = pd.read_sql_query(f"SELECT * FROM historial WHERE id = {seleccion_id}", conn).iloc[0]
                
                # 1. Revertir puntos temporada
                cur.execute("UPDATE temporada SET puntos_ganados = puntos_ganados - ? WHERE equipo = 'MANUEL_JOSE'", (float(datos_partido['puntos_temporada_mj']),))
                cur.execute("UPDATE temporada SET puntos_ganados = puntos_ganados - ? WHERE equipo = 'ROGE_LALO'", (float(datos_partido['puntos_temporada_rl']),))
                
                # 2. Revertir estadísticas jugadores
                nombres = ["MANUEL", "JOSE", "ROGE", "LALO"]
                for i, p in enumerate(nombres):
                    cur.execute(f"UPDATE jugadores SET puntos_mvp = puntos_mvp - ?, birdies_totales = birdies_totales - ?, eagles_totales = eagles_totales - ? WHERE nombre = ?", 
                                (int(datos_partido[f'p{i+1}_inc']), int(datos_partido[f'b{i+1}_inc']), int(datos_partido[f'e{i+1}_inc']), p))
                
                # 3. Borrar de la tabla historial
                cur.execute("DELETE FROM historial WHERE id = ?", (seleccion_id,))
                conn.commit()
                st.success(f"Partido {seleccion_id} eliminado con éxito.")
                st.rerun()
            else:
                st.warning("Debes marcar la casilla de confirmación.")
    else:
        st.info("No hay partidos en el historial.")
