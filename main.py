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
    conn.commit()
    conn.close()

init_db()

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    # Normalización: 0 es bola levantada (valor 99 para comparaciones)
    v = [s1 if s1 > 0 else 99, s2 if s2 > 0 else 99, s3 if s3 > 0 else 99, s4 if s4 > 0 else 99]
    
    best_a, worst_a = (v[0], v[1]) if v[0] <= v[1] else (v[1], v[0])
    best_b, worst_b = (v[2], v[3]) if v[2] <= v[3] else (v[3], v[2])
    
    pts_match_a, pts_match_b = 0.0, 0.0
    mvp_inc = {"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}

    # --- LÓGICA MATCH PLAY ---
    if best_a < best_b: pts_match_a += 1.0
    elif best_b < best_a: pts_match_b += 1.0
    if worst_a < worst_b: pts_match_a += 1.0
    elif worst_b < worst_a: pts_match_b += 1.0

    # --- LÓGICA MVP ---
    # Caso 1: Empate absoluto de los 4 jugadores
    if v[0] == v[1] == v[2] == v[3] and v[0] != 99:
        for i in range(4): mvp_inc[f"p{i+1}"] = 0.5
    
    else:
        # 1. MEJOR BOLA MVP
        if best_a < best_b:
            mvp_inc["p1" if v[0] == best_a else "p2"] += 1.0
        elif best_b < best_a:
            mvp_inc["p3" if v[2] == best_b else "p4"] += 1.0
        elif best_a == best_b and best_a != 99:
            # Empate mejores: 0.5 a cada uno que tenga el golpe ganador
            if v[0] == best_a: mvp_inc["p1"] += 0.5
            if v[1] == best_a: mvp_inc["p2"] += 0.5
            if v[2] == best_b: mvp_inc["p3"] += 0.5
            if v[3] == best_b: mvp_inc["p4"] += 0.5

        # 2. PEOR BOLA MVP
        if worst_a < worst_b:
            mvp_inc["p1" if v[0] == worst_a else "p2"] += 0.5
        elif worst_b < worst_a:
            mvp_inc["p3" if v[2] == worst_b else "p4"] += 0.5
        elif worst_a == worst_b and worst_a != 99:
            # Empate peores (y no es el mismo resultado que la mejor ya puntuada)
            # Solo sumamos 0.25 si la peor bola es distinta a la mejor
            if worst_a != best_a or worst_b != best_b:
                if v[0] == worst_a: mvp_inc["p1"] += 0.25
                if v[1] == worst_a: mvp_inc["p2"] += 0.25
                if v[2] == worst_b: mvp_inc["p3"] += 0.25
                if v[3] == worst_b: mvp_inc["p4"] += 0.25
        
    # --- BONUS CALIDAD (Birdie/Eagle) ---
    for i, s in enumerate([s1, s2, s3, s4]):
        if s > 0:
            bonus = 1.0 if s == par - 1 else (2.0 if s <= par - 2 else 0.0)
            if bonus > 0:
                mvp_inc[f"p{i+1}"] += bonus
                if i < 2: pts_match_a += bonus
                else: pts_match_b += bonus
            
    return pts_match_a, pts_match_b, mvp_inc

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳")
st.title("⛳ CAÑITA BRAVA")

menu = st.sidebar.radio("Menú", ["Inicio", "Jugar Partido", "Admin"])

if menu == "Inicio":
    conn = get_connection()
    try:
        anios = pd.read_sql_query("SELECT DISTINCT temporada FROM historial", conn)['temporada'].tolist()
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
    col1.metric("MANUEL & JOSE", f"{HISTORICO_PUNTOS + wins_a} Pts")
    col2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b} Pts")
    
    st.subheader(f"🏆 Ranking MVP {temp_sel}")
    df_mvp = pd.read_sql_query(f"SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM puntos_anuales WHERE temporada = '{temp_sel}' ORDER BY Puntos DESC", conn)
    if not df_mvp.empty: st.table(df_mvp)
    conn.close()

elif menu == "Jugar Partido":
    if 'game' not in st.session_state:
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Partido"):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'h_sel': 1, 'logs': {}}
            st.rerun()
    else:
        g = st.session_state.game
        nuevo_h = st.selectbox("Hoyo:", list(range(1, 19)), format_func=lambda x: f"Hoyo {x} {'✅' if x in g['logs'] else ''}", index=g['h_sel']-1)
        if nuevo_h != g['h_sel']: 
            g['h_sel'] = nuevo_h
            st.rerun()

        total_a = sum(v['pts'][0] for v in g['logs'].values())
        total_b = sum(v['pts'][1] for v in g['logs'].values())
        diff = int(total_a - total_b)
        
        st.markdown(f"### Hoyo {g['h_sel']} (Par {PAR_RIA_VIGO[g['h_sel']]})")
        c1, c2 = st.columns(2)
        c1.metric("M&J", f"+{diff}" if diff > 0 else "0")
        c2.metric("R&L", f"+{abs(diff)}" if diff < 0 else "0")

        v_def = g['logs'][g['h_sel']]['s'] if g['h_sel'] in g['logs'] else [PAR_RIA_VIGO[g['h_sel']]]*4
        with st.container(border=True):
            st.write("Golpes (0 = '-')")
            c = st.columns(4)
            s1 = c[0].number_input("MANUEL", 0, 10, v_def[0])
            s2 = c[1].number_input("JOSE", 0, 10, v_def[1])
            s3 = c[2].number_input("ROGE", 0, 10, v_def[2])
            s4 = c[3].number_input("LALO", 0, 10, v_def[3])
            
            if st.button("Confirmar Hoyo", use_container_width=True, type="primary"):
                pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, g['h_sel'])
                g['logs'][g['h_sel']] = {'s': [s1, s2, s3, s4], 'pts': (pa, pb), 'mvp': mi}
                if g['h_sel'] < 18: g['h_sel'] += 1
                st.rerun()

        if g['logs']:
            st.subheader("⭐ MVP Provisional")
            cur_mvp = {p: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i, p in enumerate(TODOS)}
            st.table(pd.DataFrame([{"Jugador": p, "Puntos": cur_mvp[p]} for p in TODOS]).sort_values(by="Puntos", ascending=False))

            if st.button("💾 FINALIZAR Y GUARDAR", use_container_width=True):
                conn = get_connection(); cur = conn.cursor()
                mvp_w = max(cur_mvp, key=cur_mvp.get)
                cur.execute("INSERT INTO historial (fecha, temporada, pareja_a, pareja_b, resultado_a, resultado_b, mvp, p1_pts, p2_pts, p3_pts, p4_pts) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (g['fecha'], g['temp'], "M&J", "R&L", total_a, total_b, mvp_w, cur_mvp["MANUEL"], cur_mvp["JOSE"], cur_mvp["ROGE"], cur_mvp["LALO"]))
                for p in TODOS:
                    cur.execute("INSERT OR IGNORE INTO puntos_anuales (nombre, temporada) VALUES (?,?)", (p, g['temp']))
                    cur.execute("UPDATE puntos_anuales SET partidos = partidos+1, puntos_mvp = puntos_mvp+? WHERE nombre=? AND temporada=?", (cur_mvp[p], p, g['temp']))
                conn.commit(); conn.close(); del st.session_state.game
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
