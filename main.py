import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. ESTABLECER CONEXIÓN (Crítico: Debe estar aquí arriba)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DEFINIR CONSTANTES
TODOS = ["Jugador 1", "Jugador 2", "Jugador 3", "Jugador 4"]
PAR_RIA_VIGO = {
    1: 4, 2: 3, 3: 5, 4: 4, 5: 4, 6: 4, 7: 3, 8: 5, 9: 4,
    10: 4, 11: 4, 12: 3, 13: 5, 14: 4, 15: 4, 16: 3, 17: 5, 18: 4
}

# 3. FUNCIONES
def leer_datos():
    # conn se toma de la variable global definida arriba
    df = conn.read()
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def calcular_puntos_jornada(par, lista_golpes):
    pts_finales = [0.0, 0.0, 0.0, 0.0]
    for i in range(len(lista_golpes)):
        for j in range(len(lista_golpes)):
            if i != j:
                if lista_golpes[i] < lista_golpes[j]: pts_finales[i] += 1.0
                elif lista_golpes[i] == lista_golpes[j]: pts_finales[i] += 0.5
    for i, g in enumerate(lista_golpes):
        diff = g - par
        if diff <= -2: pts_finales[i] += 1.0
        elif diff == -1: pts_finales[i] += 0.5
    return pts_finales

# 4. LÓGICA DE NAVEGACIÓN
if "menu_seleccionado" not in st.session_state:
    st.session_state.menu_seleccionado = "Jugar/Editar"

# --- SECCIÓN: JUGAR / EDITAR ---
if st.session_state.menu_seleccionado == "Jugar/Editar":
    st.title("🏌️ JUGAR / EDITAR PARTIDO")

    if "refresco_id" not in st.session_state:
        st.session_state.refresco_id = 0
    if "ultima_sincro" not in st.session_state:
        st.session_state.ultima_sincro = "No sincronizado"

    col_info, col_btn = st.columns([3, 1])
    col_info.info(f"☁️ **Sincro:** {st.session_state.ultima_sincro}")
    
    if col_btn.button("🔄 REFRESCAR HOYO", use_container_width=True):
        st.cache_data.clear()
        st.session_state.refresco_id += 1
        st.session_state.ultima_sincro = datetime.now().strftime("%H:%M:%S")
        st.rerun()

    st.write("---")

    st.number_input("Selecciona el hoyo:", min_value=1, max_value=18, step=1, key="hoyo_selector_persistente")
    hoyo_actual_id = int(st.session_state.hoyo_selector_persistente)
    par_hoyo = int(PAR_RIA_VIGO[hoyo_actual_id])

    # Lectura y Filtrado (Aquí ya no dará NameError)
    df_actual = leer_datos()
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    df_actual['HOYO'] = pd.to_numeric(df_actual['HOYO'], errors='coerce')
    df_actual['FECHA'] = df_actual['FECHA'].astype(str)
    
    datos_hoyo = df_actual[(df_actual['FECHA'] == fecha_hoy) & (df_actual['HOYO'] == hoy_actual_id)]

    st.subheader(f"⛳ Hoyo {hoyo_actual_id} (Par {par_hoyo})")
    columnas_ui = st.columns(4)
    golpes_finales = []
    campos_s = ['S0', 'S1', 'S2', 'S3']

    for i, jug in enumerate(TODOS):
        valor_default = par_hoyo
        if not datos_hoyo.empty:
            col_target = campos_s[i]
            if col_target in datos_hoyo.columns:
                val_n = datos_hoyo.iloc[0][col_target]
                if pd.notna(val_n): valor_default = int(float(val_n))
        
        clave_w = f"in_h{hoyo_actual_id}_j{i}_rid{st.session_state.refresco_id}"
        g = columnas_ui[i].number_input(f"{jug}", min_value=1, max_value=15, value=valor_default, key=clave_w)
        golpes_finales.append(g)

    if st.button("💾 GUARDAR CAMBIOS Y SUBIR", type="primary", use_container_width=True):
        with st.spinner("Guardando..."):
            try:
                puntos = calcular_puntos_jornada(par_hoyo, golpes_finales)
                nueva_fila = {
                    'FECHA': fecha_hoy, 'HOYO': hoyo_actual_id, 'PAR': par_hoyo,
                    'TEMPORADA': 2024.0, 'PARTIDO_ID': float(fecha_hoy.replace("-", "")),
                    'S0': int(golpes_finales[0]), 'S1': int(golpes_finales[1]),
                    'S2': int(golpes_finales[2]), 'S3': int(golpes_finales[3]),
                    'P1_PTS': float(puntos[0]), 'P2_PTS': float(puntos[1]),
                    'P3_PTS': float(puntos[2]), 'P4_PTS': float(puntos[3])
                }
                
                mask = (df_actual['FECHA'] == fecha_hoy) & (df_actual['HOYO'] == hoyo_actual_id)
                if mask.any():
                    idx = df_actual.index[mask][0]
                    for c, v in nueva_fila.items():
                        if c in df_actual.columns: df_actual.at[idx, c] = v
                else:
                    df_actual = pd.concat([df_actual, pd.DataFrame([nueva_fila])], ignore_index=True)
                
                conn.update(data=df_actual)
                st.cache_data.clear()
                st.session_state.refresco_id += 1
                st.session_state.ultima_sincro = datetime.now().strftime("%H:%M:%S")
                st.success("¡Guardado!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
