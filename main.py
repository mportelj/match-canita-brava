import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# CSS para el selector de hoyo (Grande y Negrita)
st.markdown("""
    <style>
    div[data-baseweb="select"] > div {
        font-size: 1.3rem !important;
        font-weight: bold !important;
    }
    label p { font-weight: bold !important; font-size: 1.1rem !important; }
    </style>
""", unsafe_allow_html=True)

# Datos de campo y jugadores
PAR_RIA_VIGO = {i: p for i, p in zip(range(1, 19), [4,5,3,4,4,5,3,4,4,4,3,4,3,5,4,5,4,4])}
TODOS = ["MANU", "JOSE", "ROGE", "LALO"] 
EQUIPO_A_NOMBRES = f"{TODOS[0]} & {TODOS[1]}"
EQUIPO_B_NOMBRES = f"{TODOS[2]} & {TODOS[3]}"
COLOR_A, COLOR_B = "#2e7d32", "#c62828"

if "menu_seleccionado" not in st.session_state: st.session_state.menu_seleccionado = "Inicio"

def cambiar_menu(): st.session_state.menu_seleccionado = st.session_state.radio_menu

menu = st.sidebar.radio("Ir a:", ["Inicio", "Jugar/Editar", "Estadísticas", "Admin"], 
                        index=["Inicio", "Jugar/Editar", "Estadísticas", "Admin"].index(st.session_state.menu_seleccionado),
                        key="radio_menu", on_change=cambiar_menu)

# --- 2. FUNCIONES DE DATOS ---
def leer_datos():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="historial", ttl=0) 
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [c.lower().strip() for c in df.columns]
        for col in ['temporada', 'hoyo', 's0', 's1', 's2', 's3']:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df.drop_duplicates(subset=['partido_id', 'hoyo'], keep='last')
    except: return pd.DataFrame()

def calcular_puntos_hoyo(scores, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    v = [int(s) for s in scores]
    ba, wa, bb, wb = min(v[0], v[1]), max(v[0], v[1]), min(v[2], v[3]), max(v[2], v[3])
    pa = (1.0 if ba < bb else 0.0) + (1.0 if wa < wb else 0.0)
    pb = (1.0 if bb < ba else 0.0) + (1.0 if wb < wa else 0.0)
    for i, s in enumerate(v):
        p_bonus = 2.0 if s <= par - 2 else (1.0 if s == par - 1 else 0)
        if i < 2: pa += p_bonus 
        else: pb += p_bonus
    mvp = {f"p{i+1}": sum(0.5 for j in range(4) if i!=j and v[i]<v[j]) + (3.0 if v[i]<=par-2 else 1.5 if v[i]==par-1 else 0.5 if v[i]==par else 0) for i in range(4)}
    return pa, pb, mvp

def ejecutar_guardado_automatico():
    g = st.session_state.game
    h = int(g['h_sel'])
    s = [int(st.session_state[f"s1_h{h}_{g['id']}"]), int(st.session_state[f"s2_h{h}_{g['id']}"]),
         int(st.session_state[f"s3_h{h}_{g['id']}"]), int(st.session_state[f"s4_h{h}_{g['id']}"])]
    pa, pb, mi = calcular_puntos_hoyo(s, h)
    
    anio_int = int(datetime.strptime(g['fecha'], "%d/%m/%Y").year)
    p_id = str(g['id'])
    nueva_fila = {"id": f"{p_id}_H{h}", "partido_id": p_id, "hoyo": h, "fecha": g['fecha'], "temporada": anio_int, 
                  "resultado_a": pa, "resultado_b": pb, **{f"p{i+1}_pts": mi[f"p{i+1}"] for i in range(4)},
                  "s0": s[0], "s1": s[1], "s2": s[2], "s3": s[3]}
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = leer_datos()
    df = pd.concat([df[~((df['partido_id']==p_id) & (df['hoyo']==h))], pd.DataFrame([nueva_fila])], ignore_index=True)
    conn.update(worksheet="historial", data=df)
    st.cache_data.clear()
    
    st.session_state.game['logs'][str(h)] = {'s': s, 'pts': (pa, pb), 'mvp': mi}
    if h < 18: st.session_state.game['h_sel'] = h + 1

# --- 3. PANTALLAS ---
if st.session_state.menu_seleccionado == "Inicio":
    st.title("⛳ CAÑITA BRAVA")
    df = leer_datos()
    temps = sorted(df['temporada'].unique().tolist(), reverse=True) if not df.empty else [2026]
    sel_temp = st.selectbox("Temporada:", temps, format_func=lambda x: str(int(x)))
    
    pa_t, pb_t = 3.5, 3.5 # Puntuación inicial histórica
    if not df.empty:
        df_t = df[df['temporada'] == int(sel_temp)]
        for _, r in df_t.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'}).iterrows():
            if r['resultado_a'] > r['resultado_b']: pa_t += 1
            elif r['resultado_b'] > r['resultado_a']: pb_t += 1
            else: pa_t += 0.5; pb_t += 0.5
            
    st.markdown(f"""<div style="border:2px solid #ccc;border-radius:15px;padding:20px;text-align:center;background:#f9f9f9;">
        <h3>MATCH {int(sel_temp)}</h3><div style="display:flex;justify-content:space-around;">
        <div><h2 style="color:{COLOR_A};">{EQUIPO_A_NOMBRES}</h2><h1>{pa_t:g}</h1></div>
        <div style="font-size:2em; align-self:center;">VS</div>
        <div><h2 style="color:{COLOR_B};">{EQUIPO_B_NOMBRES}</h2><h1>{pb_t:g}</h1></div></div></div>""", unsafe_allow_html=True)

elif st.session_state.menu_seleccionado == "Jugar/Editar":
    if 'game' not in st.session_state or st.session_state.game is None:
        st.subheader("No hay partida activa")
        f = st.date_input("Fecha de la partida:", datetime.now(), format="DD/MM/YYYY")
        if st.button("🚀 Iniciar Nueva Partida", use_container_width=True):
            st.session_state.game = {'fecha': f.strftime("%d/%m/%Y"), 'h_sel': 1, 'logs': {}, 'id': datetime.now().strftime("%Y%m%d%H%M%S")}
            st.rerun()
    else:
        g = st.session_state.game
        
        # --- 1. MARCADOR MATCH JORNADA ---
        pts_a_tot = sum(l['pts'][0] for l in g['logs'].values())
        pts_b_tot = sum(l['pts'][1] for l in g['logs'].values())
        diff_a, diff_b = (pts_a_tot - pts_b_tot, 0) if pts_a_tot >= pts_b_tot else (0, pts_b_tot - pts_a_tot)
        
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding:20px; border-radius:20px; text-align:center; margin-bottom:25px; border: 2px solid #2e7d32; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);">
                <div style="display:flex; justify-content:space-around; align-items:center;">
                    <div style="color:{COLOR_A}; flex:1;">
                        <b style="font-size:1.1rem; display:block; margin-bottom:5px;">{EQUIPO_A_NOMBRES}</b>
                        <span style="font-size:45px; font-weight:900;">{diff_a:g}</span>
                    </div>
                    <div style="font-size:22px; font-weight:bold; color:#555; background:white; width:40px; height:40px; border-radius:50%; display:flex; align-items:center; justify-content:center; border: 2px solid #ddd;">VS</div>
                    <div style="color:{COLOR_B}; flex:1;">
                        <b style="font-size:1.1rem; display:block; margin-bottom:5px;">{EQUIPO_B_NOMBRES}</b>
                        <span style="font-size:45px; font-weight:900;">{diff_b:g}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- 2. NAVEGACIÓN Y SELECTOR (SIN ETIQUETA) ---
        opciones = [f"Hoyo {i} (Par {PAR_RIA_VIGO[i]})" for i in range(1, 19)]
        
        col_prev, col_next = st.columns(2)
        if col_prev.button("← Anterior", use_container_width=True, disabled=(g['h_sel'] <= 1)):
            st.session_state.game['h_sel'] -= 1
            st.rerun()
        if col_next.button("Siguiente →", use_container_width=True, disabled=(g['h_sel'] >= 18)):
            st.session_state.game['h_sel'] += 1
            st.rerun()

        # Selector sin el texto "Ir al hoyo" (label="") y con key dinámica
        seleccion_manual = st.selectbox(
            label="Selector de Hoyo",
            label_visibility="collapsed", # Oculta la línea de texto
            options=opciones, 
            index=g['h_sel'] - 1, 
            key=f"sb_h_{g['h_sel']}_{g['id']}" 
        )
        
        h_nueva = int(seleccion_manual.split(" ")[1])
        if h_nueva != g['h_sel']:
            st.session_state.game['h_sel'] = h_nueva
            st.rerun()
        
        h = g['h_sel']
        ya_guardado = str(h) in g['logs']

        # --- 3. MARCADOR DEL HOYO ---
        if ya_guardado:
            h_pts = g['logs'][str(h)]['pts']
            h_diff_a, h_diff_b = (h_pts[0]-h_pts[1], 0) if h_pts[0]>=h_pts[1] else (0, h_pts[1]-h_pts[0])
            color_h = COLOR_A if h_diff_a > h_diff_b else COLOR_B if h_diff_b > h_diff_a else "#666"
            texto_h = "EMPATE" if h_diff_a == h_diff_b else f"GANA {EQUIPO_A_NOMBRES if h_diff_a > h_diff_b else EQUIPO_B_NOMBRES}"
            
            st.markdown(f"""
                <div style="text-align:center; background-color: #fff; border: 1px solid #eee; border-radius:12px; padding:12px; margin-top:10px; margin-bottom:20px; box-shadow: inset 0 0 5px rgba(0,0,0,0.02);">
                    <span style="color:#888; font-size:0.9rem; font-weight:bold; text-transform:uppercase;">Resultado del hoyo {h}</span><br>
                    <span style="color:{color_h}; font-size:1.8rem; font-weight:900;">{h_diff_a:g} — {h_diff_b:g}</span><br>
                    <small style="color:{color_h}; font-weight:bold;">{texto_h}</small>
                </div>
            """, unsafe_allow_html=True)

        # --- 4. ENTRADA DE GOLPES ---
        v_inicio = [int(x) for x in g['logs'][str(h)]['s']] if ya_guardado else [int(PAR_RIA_VIGO[h])]*4
        
        c1, c2 = st.columns(2)
        s1 = c1.number_input(TODOS[0], 0, 15, v_inicio[0], step=1, key=f"s1_h{h}_{g['id']}")
        s2 = c1.number_input(TODOS[1], 0, 15, v_inicio[1], step=1, key=f"s2_h{h}_{g['id']}")
        s3 = c2.number_input(TODOS[2], 0, 15, v_inicio[2], step=1, key=f"s3_h{h}_{g['id']}")
        s4 = c2.number_input(TODOS[3], 0, 15, v_inicio[3], step=1, key=f"s4_h{h}_{g['id']}")
        
        v_actuales = [s1, s2, s3, s4]
        hubo_cambios = v_actuales != v_inicio
        boton_desactivado = ya_guardado and not hubo_cambios
        texto_boton = "🔄 Actualizar Hoyo" if ya_guardado else "💾 Guardar Hoyo"
        
        if st.button(texto_boton, type="primary", use_container_width=True, disabled=boton_desactivado):
            ejecutar_guardado_automatico()
            st.rerun()
            
        # --- 5. CLASIFICACIÓN MVP ---
        if ya_guardado:
            st.write("")
            with st.expander("⭐ Clasificaciones MVP"):
                col_btn1, col_btn2 = st.columns(2)
                if "mvp_view" not in st.session_state: st.session_state.mvp_view = "Hoyo"
                
                if col_btn1.button("MVP del Hoyo", use_container_width=True): st.session_state.mvp_view = "Hoyo"
                if col_btn2.button("MVP de la Jornada", use_container_width=True): st.session_state.mvp_view = "Jornada"

                ranking = []
                for i, jug in enumerate(TODOS):
                    pts = g['logs'][str(h)]['mvp'][f'p{i+1}'] if st.session_state.mvp_view == "Hoyo" else sum(l['mvp'][f'p{i+1}'] for l in g['logs'].values())
                    ranking.append({"nombre": jug, "puntos": pts})
                
                ranking = sorted(ranking, key=lambda x: x['puntos'], reverse=True)
                for r in ranking:
                    st.write(f"**{r['nombre']}**: {r['puntos']:g} pts")

        st.divider()
        if st.button("🏁 Guardar Partida", use_container_width=True):
            st.session_state.game = None
            st.rerun()
            
elif st.session_state.menu_seleccionado == "Estadísticas":
    st.header("🏆 Orden de Mérito")
    
    df_historico = leer_datos() 
    
    if df_historico is None or df_historico.empty:
        st.info("No hay datos registrados en la Orden de Mérito.")
    else:
        # 1. NORMALIZACIÓN CRÍTICA DE COLUMNAS
        # Convertimos todo a mayúsculas y quitamos espacios para que coincida siempre
        df_historico.columns = [str(c).strip().upper() for c in df_historico.columns]
        
        # Detectar la columna de fecha (buscamos 'FECHA')
        col_fecha = 'FECHA' if 'FECHA' in df_historico.columns else df_historico.columns[0]

        # 2. PROCESAMIENTO
        stats = {jug: {
            "Scratch": 0, "Albatros": 0, "Eagles": 0, "Birdies": 0,
            "Pares": 0, "Bogey": 0, "D.Bogey+": 0, "Hoyos": 0
        } for jug in TODOS}
        
        for _, fila in df_historico.iterrows():
            try:
                # Validar que HOYO sea numérico
                h_val = fila.get('HOYO')
                if pd.isna(h_val): continue
                h_num = int(h_val)
                par_hoyo = int(PAR_RIA_VIGO[h_num])
                
                for i, jug in enumerate(TODOS):
                    # Intentar leer S1, S2... o s1, s2...
                    col_golpes = f'S{i+1}'
                    col_mvp = f'MVP{i+1}'
                    
                    val_golpes = fila.get(col_golpes)
                    if pd.isna(val_golpes) or str(val_golpes).strip() == "": continue
                    
                    golpes = int(float(val_golpes))
                    if golpes <= 0: continue
                    
                    diff = golpes - par_hoyo
                    stats[jug]["Hoyos"] += 1
                    
                    # Clasificación
                    if diff <= -3: stats[jug]["Albatros"] += 1
                    elif diff == -2: stats[jug]["Eagles"] += 1
                    elif diff == -1: stats[jug]["Birdies"] += 1
                    elif diff == 0: stats[jug]["Pares"] += 1
                    elif diff == 1: stats[jug]["Bogey"] += 1
                    else: stats[jug]["D.Bogey+"] += 1
                    
                    # Scratch: Par=1, Birdie=2, Eagle=3, Albatros=4
                    stats[jug]["Scratch"] += max(0, 1 - diff)
            except Exception as e:
                # Descomenta la siguiente línea si quieres ver errores específicos en la consola
                # print(f"Error procesando fila: {e}")
                continue

        # 3. CONSTRUCCIÓN DE LA TABLA
        datos_tabla = []
        for jug in TODOS:
            d = stats[jug]
            total = d["Hoyos"] if d["Hoyos"] > 0 else 1
            
            def fmt_con_pct(valor):
                pct = (valor / total) * 100
                return f"{valor} <br> <small style='color:gray;'>{pct:.1f}%</small>"

            datos_tabla.append({
                "Jugador": jug,
                "Scratch": d["Scratch"],
                "Albatros": fmt_con_pct(d["Albatros"]),
                "Eagles": fmt_con_pct(d["Eagles"]),
                "Birdies": fmt_con_pct(d["Birdies"]),
                "Pares": fmt_con_pct(d["Pares"]),
                "Bogey": fmt_con_pct(d["Bogey"]),
                "D.Bogey+": fmt_con_pct(d["D.Bogey+"]),
                "Hoyos": d["Hoyos"]
            })

        # 4. ESTILO Y RENDERIZADO
        st.markdown("""
            <style>
                th { text-align: center !important; background-color: #f0f2f6; font-weight: bold !important; }
                td { text-align: center !important; vertical-align: middle !important; border-bottom: 1px solid #eee; }
            </style>
        """, unsafe_allow_html=True)

        st.subheader("Resumen Acumulado")
        import pandas as pd
        df_mostrar = pd.DataFrame(datos_tabla)
        
        if stats[TODOS[0]]["Hoyos"] == 0:
            st.warning("⚠️ Los datos se leen pero no se encuentran registros válidos. Revisa que las columnas en Google Sheets se llamen 'Hoyo', 'S1', 'S2', 'S3' y 'S4'.")
        
        st.write(df_mostrar.to_html(escape=False, index=False), unsafe_allow_html=True)

        # 5. DETALLE JORNADA
        st.divider()
        st.subheader("🔍 Detalle por Jornada")
        fechas_disp = df_historico[col_fecha].unique().tolist()
        fecha_sel = st.selectbox("Seleccionar Jornada:", fechas_disp)
        
        df_jornada = df_historico[df_historico[col_fecha] == fecha_sel]
        resumen_jornada = []
        for i, jug in enumerate(TODOS):
            pts_j = 0
            for _, f in df_jornada.iterrows():
                try:
                    h_idx = int(f['HOYO'])
                    diff_j = int(float(f[f'S{i+1}'])) - int(PAR_RIA_VIGO[h_idx])
                    pts_j += max(0, 1 - diff_j)
                except: continue
            resumen_jornada.append({"Jugador": jug, "Scratch Jornada": pts_j})
        
        st.table(resumen_jornada)

elif st.session_state.menu_seleccionado == "Admin":
    st.title("⚙️ Gestión")
    df = leer_datos()
    if not df.empty:
        for p_id in df['partido_id'].unique()[::-1]:
            dp = df[df['partido_id'] == p_id]
            with st.expander(f"Partida {dp['fecha'].iloc[0]} ({len(dp)} hoyos)"):
                c1, c2 = st.columns(2)
                if c1.button("✏️ Editar", key=f"ed_{p_id}"):
                    logs = {str(r['hoyo']): {'s':[r['s0'],r['s1'],r['s2'],r['s3']], 'pts':(r['resultado_a'],r['resultado_b']), 
                            'mvp':{f'p{i+1}':r[f'p{i+1}_pts'] for i in range(4)}} for _,r in dp.iterrows()}
                    st.session_state.game = {'fecha':dp['fecha'].iloc[0], 'h_sel':1, 'logs':logs, 'id':p_id}
                    st.session_state.menu_seleccionado = "Jugar/Editar"
                    st.rerun()
                if c2.checkbox("Borrar", key=f"del_cb_{p_id}"):
                    if st.button("🗑️ Confirmar", key=f"del_btn_{p_id}", type="primary"):
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(worksheet="historial", data=df[df['partido_id'] != p_id])
                        st.cache_data.clear()
                        st.rerun()
