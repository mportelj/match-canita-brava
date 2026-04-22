import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
PAR_RIA_VIGO = {
    1: 4, 2: 5, 3: 3, 4: 4, 5: 4, 6: 5, 7: 3, 8: 4, 9: 4,
    10: 4, 11: 3, 12: 4, 13: 3, 14: 5, 15: 4, 16: 5, 17: 4, 18: 5
}
TODOS = ["MANUEL", "JOSE", "ROGE", "LALO"]

# Colores Corporativos
COLOR_A = "#2e7d32" # Verde (M&J)
COLOR_B = "#c62828" # Rojo (R&L)

# Marcador inicial Temporada 2026
INICIO_2026_A = 3.5  
INICIO_2026_B = 3.5  

st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# --- FUNCIÓN DE ESTILO GLOBAL (Para evitar el NameError) ---
def estilo_tabla(row):
    color = COLOR_A if row['Jugador'] in ["MANUEL", "JOSE"] else COLOR_B
    # Aplicamos el color tanto al texto del nombre como al de la puntuación
    return [f'color: {color}; font-weight: bold'] * len(row)

# --- FUNCIONES DE BASE DE DATOS ---
def leer_datos():
    st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts"])
        df = df.dropna(subset=['id'])
        df['temporada'] = df['temporada'].astype(str)
        return df
    except:
        return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts"])

def guardar_hoyo(df_fila):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = leer_datos()
        id_hoyo = str(df_fila["id"].iloc[0])
        if not df_existente.empty:
            df_existente['id'] = df_existente['id'].astype(str)
            df_final = df_existente[df_existente["id"] != id_hoyo].copy()
            df_final = pd.concat([df_final, df_fila], ignore_index=True)
        else:
            df_final = df_fila
        conn.update(worksheet="historial", data=df_final)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    scores = [s1, s2, s3, s4]
    v = [s if s > 0 else 99 for s in scores]
    ba, wa = min(v[0], v[1]), max(v[0], v[1])
    bb, wb = min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    for s in [s1, s2]:
        if 0 < s <= par - 2: pa += 2.0
        elif 0 < s == par - 1: pa += 1.0
    for s in [s3, s4]:
        if 0 < s <= par - 2: pb += 2.0
        elif 0 < s == par - 1: pb += 1.0
    mvp = {f"p{i+1}": 0.0 for i in range(4)}
    for i in range(4):
        if scores[i] <= 0: continue
        for j in range(4):
            if i != j and scores[j] > 0 and scores[i] < scores[j]: mvp[f"p{i+1}"] += 0.5
        if scores[i] <= par - 2: mvp[f"p{i+1}"] += 3.0
        elif scores[i] == par - 1: mvp[f"p{i+1}"] += 1.5
        elif scores[i] == par: mvp[f"p{i+1}"] += 0.5
    return pa, pb, mvp

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("Menú", ["Inicio", "Jugar/Editar", "Admin"])

if menu == "Inicio":
    st.markdown("<h1 style='text-align: center;'>⛳ CAÑITA BRAVA 2026</h1>", unsafe_allow_html=True)
    df = leer_datos()
    df_2026 = df[df['temporada'] == "2026"]
    
    # Inicializamos con el acarreo de la temporada anterior
    puntos_totales_a = INICIO_2026_A
    puntos_totales_b = INICIO_2026_B
    
    if not df_2026.empty:
        # Agrupamos por partido para ver quién ganó cada jornada
        resumen = df_2026.groupby('partido_id').agg({
            'resultado_a': 'sum', 
            'resultado_b': 'sum'
        }).reset_index()
        
        # Lógica de reparto de puntos de temporada
        for _, row in resumen.iterrows():
            if row['resultado_a'] > row['resultado_b']:
                puntos_totales_a += 1.0
            elif row['resultado_b'] > row['resultado_a']:
                puntos_totales_b += 1.0
            else:
                # Empate en el partido: 0,5 para cada uno
                puntos_totales_a += 0.5
                puntos_totales_b += 0.5
    
    # MARCADOR TEMPORADA ACTUALIZADO
    st.markdown(f"""
        <div style="border: 2px solid #ccc; border-radius: 15px; padding: 20px; background-color: #f9f9f9; text-align: center; margin-bottom: 25px;">
            <h2 style="margin-bottom: 10px; color: #333;">TEMPORADA 2026</h2>
            <div style="display: flex; justify-content: space-around; align-items: center;">
                <div>
                    <h4 style="margin: 0; color: {COLOR_A};">MANUEL & JOSE</h4>
                    <h1 style="color: {COLOR_A}; margin: 0;">{puntos_totales_a:g}</h1>
                </div>
                <h2 style="margin: 0; color: #999;">VS</h2>
                <div>
                    <h4 style="margin: 0; color: {COLOR_B};">ROGE & LALO</h4>
                    <h1 style="color: {COLOR_B}; margin: 0;">{puntos_totales_b:g}</h1>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # ... (el resto del código de la clasificación MVP se mantiene igual)

elif menu == "Jugar/Editar":
    if 'game' not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>Nueva Partida</h2>", unsafe_allow_html=True)
        f = st.date_input("Fecha:", datetime.now())
        if st.button("🚀 Iniciar Partido", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'temp': str(f.year), 'h_sel': 1, 'logs': {}, 'partido_id': f.strftime("%Y%m%d")}
            st.rerun()
    else:
        g = st.session_state.game
        h_idx = g['h_sel']

        st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 5px; border-radius: 10px; text-align: center; margin-bottom: 15px; border: 1px solid #ddd;">
                <h3 style="margin: 0; color: #333;">Hoyo {h_idx} <span style="font-size: 0.7em; color: #666;">(Par {PAR_RIA_VIGO[h_idx]})</span></h3>
            </div>
        """, unsafe_allow_html=True)

        v_def = g['logs'][str(h_idx)]['s'] if str(h_idx) in g['logs'] else [PAR_RIA_VIGO[h_idx]]*4
        
        # --- ENTRADA DE GOLPES (UN JUGADOR POR LÍNEA CON COLORES) ---
        st.markdown(f"<p style='margin-bottom:-15px; color:{COLOR_A}; font-weight:bold;'>{TODOS[0]}</p>", unsafe_allow_html=True)
        s1 = st.number_input("", 0, 10, v_def[0], key=f"s0_{h_idx}")
        
        st.markdown(f"<p style='margin-bottom:-15px; color:{COLOR_A}; font-weight:bold;'>{TODOS[1]}</p>", unsafe_allow_html=True)
        s2 = st.number_input("", 0, 10, v_def[1], key=f"s1_{h_idx}")
        
        st.markdown(f"<p style='margin-bottom:-15px; color:{COLOR_B}; font-weight:bold;'>{TODOS[2]}</p>", unsafe_allow_html=True)
        s3 = st.number_input("", 0, 10, v_def[2], key=f"s2_{h_idx}")
        
        st.markdown(f"<p style='margin-bottom:-15px; color:{COLOR_B}; font-weight:bold;'>{TODOS[3]}</p>", unsafe_allow_html=True)
        s4 = st.number_input("", 0, 10, v_def[3], key=f"s3_{h_idx}")
        
        s = [s1, s2, s3, s4]
        
        ya_guardado = str(h_idx) in g['logs'] and g['logs'][str(h_idx)]['s'] == s
        btn_txt = "✅ Sincronizado" if ya_guardado else "💾 Guardar Hoyo"
        
        if st.button(btn_txt, type="primary", use_container_width=True, disabled=ya_guardado):
            pa, pb, mi = calcular_puntos_hoyo(s1, s2, s3, s4, h_idx)
            g['logs'][str(h_idx)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
            nueva_fila = pd.DataFrame([{"id": f"{g['partido_id']}_H{h_idx}", "partido_id": g['partido_id'], "hoyo": h_idx, "fecha": g['fecha'], "temporada": g['temp'], "resultado_a": pa, "resultado_b": pb, "p1_pts": mi['p1'], "p2_pts": mi['p2'], "p3_pts": mi['p3'], "p4_pts": mi['p4']}])
            if guardar_hoyo(nueva_fila):
                st.toast(f"Hoyo {h_idx} guardado")
                st.rerun()

        c_nav = st.columns(2)
        if c_nav[0].button("⬅️ Anterior", use_container_width=True):
            g['h_sel'] = max(1, h_idx - 1); st.rerun()
        if c_nav[1].button("Siguiente ➡️", use_container_width=True):
            g['h_sel'] = min(18, h_idx + 1); st.rerun()

        if g['logs']:
            total_match_a = sum(v['pts'][0] for v in g['logs'].values())
            total_match_b = sum(v['pts'][1] for v in g['logs'].values())
            
            st.markdown(f"""
                <div style="border: 2px solid #ccc; border-radius: 12px; padding: 10px; background-color: #ffffff; text-align: center; margin-top: 15px;">
                    <div style="display: flex; justify-content: space-around; align-items: center;">
                        <div>
                            <p style="margin: 0; font-weight: bold; font-size: 0.8em; color: {COLOR_A};">MANUEL & JOSE</p>
                            <h2 style="margin: 0; color: {COLOR_A};">{int(total_match_a)}</h2>
                        </div>
                        <h3 style="margin: 0; color: #999;">—</h3>
                        <div>
                            <p style="margin: 0; font-weight: bold; font-size: 0.8em; color: {COLOR_B};">ROGE & LALO</p>
                            <h2 style="margin: 0; color: {COLOR_B};">{int(total_match_b)}</h2>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            m1, m2 = st.columns(2)
            with m1:
                with st.popover("🎯 MVP Hoyo", use_container_width=True):
                    pts_h = g['logs'][str(h_idx)]['mvp']
                    df_h = pd.DataFrame([{"Jugador": TODOS[i], "Pts": round(float(pts_h[f"p{i+1}"]), 1)} for i in range(4)])
                    st.table(df_h.style.apply(estilo_tabla, axis=1).format({"Pts": "{:.1f}"}))
            with m2:
                with st.popover("🏆 MVP Total", use_container_width=True):
                    ranking = {TODOS[i]: sum(v['mvp'][f"p{i+1}"] for v in g['logs'].values()) for i in range(4)}
                    df_r = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in ranking.items()]).sort_values("Pts", ascending=False)
                    st.table(df_r.style.apply(estilo_tabla, axis=1).format({"Pts": "{:.1f}"}))

        if st.button("🏁 Finalizar y Salir", use_container_width=True):
            del st.session_state.game; st.rerun()

elif menu == "Admin":
    st.markdown("<h2 style='text-align: center;'>Administración</h2>", unsafe_allow_html=True)
    df = leer_datos()
    
    if not df.empty:
        # Ordenamos por fecha/id descendente para ver lo último primero
        partidos = df['partido_id'].unique()[::-1]
        
        for p_id in partidos:
            datos_partido = df[df['partido_id'] == p_id]
            fecha_p = datos_partido['fecha'].iloc[0]
            
            with st.expander(f"📅 Partido: {fecha_p} (ID: {p_id})"):
                col_adm1, col_adm2 = st.columns(2)
                
                # --- BOTÓN EDITAR ---
                if col_adm1.button("✏️ Editar Partida", key=f"edit_{p_id}", use_container_width=True):
                    # 1. Convertir los datos de la hoja en el formato del log de juego
                    logs_recuperados = {}
                    for _, fila in datos_partido.iterrows():
                        h_num = str(int(fila['hoyo']))
                        # Reconstruimos la lista de golpes (s) y los puntos calculados
                        logs_recuperados[h_num] = {
                            's': [fila.get('s0', 0), fila.get('s1', 0), fila.get('s2', 0), fila.get('s3', 0)], # Asegúrate de que tu tabla tiene s0, s1...
                            'pts': (fila['resultado_a'], fila['resultado_b']),
                            'mvp': {
                                'p1': fila['p1_pts'], 'p2': fila['p2_pts'], 
                                'p3': fila['p3_pts'], 'p4': fila['p4_pts']
                            }
                        }
                    
                    # 2. Cargar en session_state
                    st.session_state.game = {
                        'fecha': fecha_p,
                        'temp': str(datos_partido['temporada'].iloc[0]),
                        'h_sel': 1,
                        'logs': logs_recuperados,
                        'partido_id': p_id
                    }
                    st.success("Cargando datos... Ve a 'Jugar/Editar'")
                    st.rerun()

                # --- BOTÓN BORRAR ---
                if col_adm2.button("🗑️ Borrar Todo", key=f"del_{p_id}", use_container_width=True):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    nuevo_df = df[df['partido_id'] != p_id]
                    conn.update(worksheet="historial", data=nuevo_df)
                    st.cache_data.clear()
                    st.rerun()
                
                # Mostrar resumen rápido de la jornada
                total_a = datos_partido['resultado_a'].sum()
                total_b = datos_partido['resultado_b'].sum()
                st.write(f"Resultado final: {int(total_a)} - {int(total_b)}")
    else:
        st.info("No hay partidas registradas en el historial.")
