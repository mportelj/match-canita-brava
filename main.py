import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import json

# --- CONFIGURACIÓN ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}
TODOS = ["MANUEL", "JOSE", "ROGE", "LALO"]
HISTORICO_PUNTOS = 3.5 # Ventaja histórica inicial

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
                  p1_pts REAL, p2_pts REAL, p3_pts REAL, p4_pts REAL, logs_json TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS backup_partida 
                 (id INTEGER PRIMARY KEY, datos_json TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- LÓGICA DE CÁLCULO ---
def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    scores = [s1, s2, s3, s4]
    v = [s if s > 0 else 99 for s in scores]
    
    best_a, worst_a = min(v[0], v[1]), max(v[0], v[1])
    best_b, worst_b = min(v[2], v[3]), max(v[2], v[3])
    pts_match_a = (1.0 if best_a < best_b else 0.0) + (1.0 if worst_a < worst_b else 0.0)
    pts_match_b = (1.0 if best_b < best_a else 0.0) + (1.0 if worst_b < worst_a else 0.0)

    mvp_inc = {"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}
    for i in range(4):
        if scores[i] <= 0: continue
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]:
                mvp_inc[f"p{i+1}"] += 0.5
        golpes = scores[i]
        if golpes <= par - 2: mvp_inc[f"p{i+1}"] += 3.0
        elif golpes == par - 1: mvp_inc[f"p{i+1}"] += 1.5
        elif golpes == par: mvp_inc[f"p{i+1}"] += 0.5
            
    return pts_match_a, pts_match_b, mvp_inc

# --- FUNCIONES DE BASE DE DATOS ---
def eliminar_partida_db(partida_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM historial WHERE id=?", (partida_id,))
    r = cur.fetchone()
    if r:
        # Restar puntos de la clasificación antes de borrar
        p_map = {"MANUEL": r[8], "JOSE": r[9], "ROGE": r[10], "LALO": r[11]}
        for p, pts in p_map.items():
            cur.execute("UPDATE puntos_anuales SET partidos = partidos-1, puntos_mvp = puntos_mvp-? WHERE nombre=? AND temporada=?", (pts, p, r[2]))
        cur.execute("DELETE FROM historial WHERE id=?", (partida_id,))
    conn.commit(); conn.close()

# --- INTERFAZ ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳")
st.title("⛳ CAÑITA BRAVA")

menu = st.sidebar.radio("Menú", ["Inicio", "Jugar/Editar", "Admin"])
# --- BOTÓN DE EMERGENCIA PARA BORRAR BASE DE DATOS ---
if st.sidebar.button("⚠️ Resetear Base de Datos"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS historial")
    c.execute("DROP TABLE IF EXISTS puntos_anuales")
    c.execute("DROP TABLE IF EXISTS backup_partida")
    conn.commit()
    conn.close()
    st.sidebar.success("Base de datos borrada. Reiniciando...")
    st.rerun()
if menu == "Inicio":
    conn = get_connection()
    anios = pd.read_sql_query("SELECT DISTINCT temporada FROM historial", conn)['temporada'].tolist()
    anio_act = str(datetime.now().year)
    if anio_act not in anios: anios.append(anio_act)
    anios.sort(reverse=True)
    
    temp_sel = st.sidebar.selectbox("Temporada", anios)
    
    st.header(f"📊 Temporada {temp_sel}")
    df_h = pd.read_sql_query(f"SELECT resultado_a, resultado_b FROM historial WHERE temporada = '{temp_sel}'", conn)
    wins_a = len(df_h[df_h['resultado_a'] > df_h['resultado_b']])
    wins_b = len(df_h[df_h['resultado_b'] > df_h['resultado_a']])
    
    c1, c2 = st.columns(2)
    c1.metric("M & J", f"{HISTORICO_PUNTOS + wins_a} Pts")
    c2.metric("R & L", f"{HISTORICO_PUNTOS + wins_b} Pts")
    
    st.subheader("⭐ Clasificación MVP Acumulada")
    df_mvp = pd.read_sql_query(f"SELECT nombre as Jugador, partidos as PJ, puntos_mvp as Puntos FROM puntos_anuales WHERE temporada = '{temp_sel}' ORDER BY Puntos DESC", conn)
    if not df_mvp.empty:
        st.table(df_mvp)
    else:
        st.info("Aún no hay partidos registrados en esta temporada.")
    conn.close()

elif menu == "Jugar/Editar":
    # Inicialización de estado
    if 'game' not in st.session_state:
        st.subheader("Nueva Partida o Editar")
        f = st.date_input("Fecha:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Nueva"):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'h_sel': 1, 'logs': {}, 'edit_id': None}
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']
        
        if g['edit_id']:
            st.warning(f"📝 Editando partido del {g['fecha']}")

        # Navegación
        cp, ch, cn = st.columns([1, 2, 1])
        if cp.button("⬅️") and h_idx > 1: g['h_sel'] -= 1; st.rerun()
        ch.markdown(f"<h3 style='text-align:center;'>Hoyo {h_idx} (Par {PAR_RIA_VIGO[h_idx]})</h3>", unsafe_allow_html=True)
        if cn.button("➡️") and h_idx < 18: g['h_sel'] += 1; st.rerun()

        # Input
        v_def = g['logs'][h_idx]['s'] if h_idx in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        with st.container(border=True):
            cols = st.columns(4)
            s1 = cols[0].number_input("MAN", 0, 10, v_def[0], key=f"s1_{h_idx}")
            s2 = cols[1].number_input("JOS", 0, 10, v_def[1], key=f"s2_{h_idx}")
            s3 = cols[2].number_input("ROG", 0, 10, v_def[2], key=f"s3_{h_idx}")
            s4 = cols[3].number_input("LAL", 0, 10, v_def[3], key=f"s4_{h_idx}")
            
            if st.button("✅ Confirmar Hoyo", use_container_width=True):
                pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, h_idx)
                g['logs'][h_idx] = {'s': [s1, s2, s3, s4], 'pts': (pa, pb), 'mvp': mi}
                st.rerun()

        # Resumen Match actual
        t_a = sum(v['pts'][0] for v in g['logs'].values())
        t_b = sum(v['pts'][1] for v in g['logs'].values())
        st.write(f"**Marcador actual:** M&J: {t_a} | R&L: {t_b}")

        if st.button("💾 GUARDAR TODO", type="primary", use_container_width=True):
            if g['edit_id']:
                eliminar_partida_db(g['edit_id']) # Borramos la versión vieja antes de insertar la nueva
            
            conn = get_connection(); cur = conn.cursor()
            cur_mvp = {p: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i, p in enumerate(TODOS)}
            
            # Guardar en historial
            cur.execute("INSERT INTO historial (fecha, temporada, pareja_a, pareja_b, resultado_a, resultado_b, p1_pts, p2_pts, p3_pts, p4_pts, logs_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (g['fecha'], g['temp'], "M&J", "R&L", t_a, t_b, cur_mvp["MANUEL"], cur_mvp["JOSE"], cur_mvp["ROGE"], cur_mvp["LALO"], json.dumps(g['logs'])))
            
            # Actualizar Ranking Anual
            for p in TODOS:
                cur.execute("INSERT OR IGNORE INTO puntos_anuales (nombre, temporada) VALUES (?,?)", (p, g['temp']))
                cur.execute("UPDATE puntos_anuales SET partidos = partidos+1, puntos_mvp = puntos_mvp+? WHERE nombre=? AND temporada=?", (cur_mvp[p], p, g['temp']))
            
            conn.commit(); conn.close()
            del st.session_state.game
            st.success("¡Datos actualizados correctamente!"); st.balloons(); st.rerun()

elif menu == "Admin":
    st.subheader("⚙️ Gestión y Configuración")
    
    # --- SECCIÓN DE EDICIÓN/ELIMINACIÓN DE PARTIDOS ---
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, fecha, resultado_a, resultado_b, logs_json FROM historial ORDER BY id DESC", conn)
    
    if not df.empty:
        st.write("### Historial de Partidos")
        for _, r in df.iterrows():
            with st.expander(f"📅 {r['fecha']} | M&J: {r['resultado_a']} - R&L: {r['resultado_b']}"):
                c1, c2 = st.columns(2)
                if c1.button("📝 Editar", key=f"ed_{r['id']}"):
                    st.session_state.game = {
                        'fecha': r['fecha'], 
                        'temp': r['fecha'].split('/')[-1], 
                        'h_sel': 1, 
                        'logs': {int(k): v for k, v in json.loads(r['logs_json']).items()},
                        'edit_id': r['id']
                    }
                    st.info("Partido cargado. Ve a la pestaña 'Jugar/Editar' para modificarlo.")
                
                if c2.button("🗑️ Eliminar", key=f"del_{r['id']}"):
                    eliminar_partida_db(r['id'])
                    st.rerun()
    else:
        st.info("No hay partidos grabados.")

    st.divider()

    # --- SECCIÓN DE RESETEO SEGURO (Doble Confirmación) ---
    st.write("### Zona de Peligro")
    
    # Inicializar el estado de confirmación si no existe
    if 'reset_step' not in st.session_state:
        st.session_state.reset_step = 0

    if st.session_state.reset_step == 0:
        if st.button("🔴 Resetear Base de Datos"):
            st.session_state.reset_step = 1
            st.rerun()

    elif st.session_state.reset_step == 1:
        st.warning("¿Estás seguro de que quieres resetear todas las tablas?")
        c1, c2 = st.columns(2)
        if c1.button("SÍ, CONTINUAR"):
            st.session_state.reset_step = 2
            st.rerun()
        if c2.button("CANCELAR"):
            st.session_state.reset_step = 0
            st.rerun()

    elif st.session_state.reset_step == 2:
        st.error("❗ SE VAN A BORRAR TODOS LOS DATOS DEFINITIVAMENTE (Partidos y Rankings)")
        c1, c2 = st.columns(2)
        if c1.button("🔥 BORRAR TODO AHORA"):
            c = conn.cursor()
            c.execute("DROP TABLE IF EXISTS historial")
            c.execute("DROP TABLE IF EXISTS puntos_anuales")
            c.execute("DROP TABLE IF EXISTS backup_partida")
            conn.commit()
            st.session_state.reset_step = 0
            st.success("Base de datos borrada. Reiniciando...")
            st.rerun()
        if c2.button("VOLVER ATRÁS"):
            st.session_state.reset_step = 0
            st.rerun()
            
    conn.close()
            
            if c2.button("🗑️ Eliminar", key=f"del_{r['id']}"):
                eliminar_partida_db(r['id'])
                st.rerun()
    conn.close()
