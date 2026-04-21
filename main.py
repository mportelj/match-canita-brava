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
    # Actualizado a v10 para asegurar que los cambios de estructura previos se mantengan
    return sqlite3.connect('canita_brava_v10.db', check_same_thread=False)

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

# --- CAMBIO DE TEXTOS EN EL MENÚ ---
menu = st.sidebar.radio("Menú", ["Inicio", "Jugar Partido", "Admin"])

if menu == "Inicio":
    conn = get_connection()
    anios_db = pd.read_sql_query("SELECT DISTINCT temporada FROM historial", conn)['temporada'].tolist()
    anio_actual_str = str(datetime.now().year)
    if anio_actual_str not in anios_db:
        anios_db.append(anio_actual_str)
    anios_db.sort(reverse=True)
    
    col_tit, col_sel = st.columns([2, 1])
    col_tit.subheader("📊 Estadísticas")
    temp_seleccionada = col_sel.selectbox("Seleccionar Año", anios_db, index=0)

    st.divider()

    df_h = pd.read_sql_query(f"SELECT resultado_a, resultado_b FROM historial WHERE temporada = '{temp_seleccionada}'", conn)
    wins_a = len(df_h[df_h['resultado_a'] > df_h['resultado_b']])
    wins_b = len(df_h[df_h['resultado_b'] > df_h['resultado_a']])
    
    st.write(f"**Balance Match {temp_seleccionada}:**")
    c1, c2 = st.columns(2)
    c1.metric("MANUEL & JOSE", f"{HISTORICO_PUNTOS + wins_a} Pts")
    c2.metric("ROGE & LALO", f"{HISTORICO_PUNTOS + wins_b} Pts")
    
    st.subheader(f"🏆 Ranking MVP {temp_seleccionada}")
    df_mvp = pd.read_sql_query(f"SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM puntos_anuales WHERE temporada = '{temp_seleccionada}' ORDER BY Puntos DESC", conn)
    
    if not df_mvp.empty:
        st.table(df_mvp)
    else:
        st.info(f"No hay registros para la temporada {temp_seleccionada}.")

elif menu == "Jugar Partido":
    if 'game' not in st.session_state:
        st.subheader("Datos del Partido")
        # Formato de visualización de fecha dd/mm/aaaa en el selector
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        h = st.selectbox("Inicio:", [1, 10])
        if st.button("🚀 Iniciar"):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'hoyo': h, 'logs': {}}
            st.rerun()
    else:
        g = st.session_state.game
        cur_match_a = sum(v['pts'][0] for v in g['logs'].values())
        cur_match_b = sum(v['pts'][1] for v in g['logs'].values())
        cur_mvp = {p: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i, p in enumerate(TODOS)}
        
        st.markdown(f"### Hoyo {g['hoyo']} (Par {PAR_RIA_VIGO[g['hoyo']]})")
        m1, m2 = st.columns(2)
        m1.metric("M&J", cur_match_a)
        m2.metric("R&L", cur_match_b)
        
        with st.container(border=True):
            # --- CAMBIO DE TEXTO: INTRODUCIR GOLPES ---
            st.write("**Introducir golpes:**")
            c = st.columns(4)
            s1 = c[0].number_input("MANUEL", 1, 10, PAR_RIA_VIGO[g['hoyo']])
            s2 = c[1].number_input("JOSE", 1, 10, PAR_RIA_VIGO[g['hoyo']])
            s3 = c[2].number_input("ROGE", 1, 10, PAR_RIA_VIGO[g['hoyo']])
            s4 = c[3].number_input("LALO", 1, 10, PAR_RIA_VIGO[g['hoyo']])
            
            if st.button("🎯 Confirmar Hoyo", use_container_width=True):
                pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, g['hoyo'])
                g['logs'][g['hoyo']] = {'s': [s1, s2, s3, s4], 'pts': (pa, pb), 'mvp': mi}
                g['hoyo'] = g['hoyo'] + 1 if g['hoyo'] < 18 else 1
                st.rerun()

        if g['logs']:
            st.subheader("⭐ MVP del Partido (Actual)")
            df_live_mvp = pd.DataFrame([{"Jugador": p, "Puntos": cur_mvp[p]} for p in TODOS]).sort_values(by="Puntos", ascending=False)
            st.dataframe(df_live_mvp, hide_index=True, use_container_width=True)

            if st.button("💾 GUARDAR Y FINALIZAR PARTIDO", type="primary", use_container_width=True):
                conn = get_connection()
                cur = conn.cursor()
                mvp_win = max(cur_mvp, key=cur_mvp.get)
                cur.execute("INSERT INTO historial (fecha, temporada, pareja_a, pareja_b, resultado_a, resultado_b, mvp, p1_pts, p2_pts, p3_pts, p4_pts) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                           (g['fecha'], g['temp'], "M&J", "R&L", cur_match_a, cur_match_b, mvp_win, cur_mvp["MANUEL"], cur_mvp["JOSE"], cur_mvp["ROGE"], cur_mvp["LALO"]))
                for p in TODOS:
                    cur.execute("INSERT OR IGNORE INTO puntos_anuales (nombre, temporada) VALUES (?,?)", (p, g['temp']))
                    cur.execute("UPDATE puntos_anuales SET partidos = partidos + 1, puntos_mvp = puntos_mvp + ? WHERE nombre = ? AND temporada = ?", (cur_mvp[p], p, g['temp']))
                conn.commit()
                del st.session_state.game
                st.balloons()
                st.rerun()

elif menu == "Admin":
    conn = get_connection()
    st.subheader("⚙️ Administración de Partidos")
    df = pd.read_sql_query("SELECT * FROM historial ORDER BY id DESC", conn)
    
    if df.empty:
        st.write("No hay partidos registrados.")
    
    for index, row in df.iterrows():
        # La fecha ya se guarda como dd/mm/aaaa en el proceso de guardado
        with st.expander(f"📅 {row['fecha']} | M&J {row['resultado_a']} - {row['resultado_b']} R&L"):
            st.write(f"**MVP:** {row['mvp']} | Año: {row['temporada']}")
            if st.button(f"🗑️ Eliminar Partido", key=f"del_{row['id']}"):
                cur = conn.cursor()
                pts_map = {"MANUEL": row['p1_pts'], "JOSE": row['p2_pts'], "ROGE": row['p3_pts'], "LALO": row['p4_pts']}
                for p, pts in pts_map.items():
                    cur.execute("UPDATE puntos_anuales SET partidos = partidos - 1, puntos_mvp = puntos_mvp - ? WHERE nombre = ? AND temporada = ?", (pts, p, row['temporada']))
                cur.execute("DELETE FROM historial WHERE id = ?", (row['id'],))
                conn.commit()
                st.rerun()
