import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y CONEXIÓN
# ==========================================
st.set_page_config(page_title="Match Canita Brava", page_icon="🏌️", layout="wide")

# Conexión global (evita NameError)
conn = st.connection("gsheets", type=GSheetsConnection)

# Constantes del Campo
TODOS = ["Jugador 1", "Jugador 2", "Jugador 3", "Jugador 4"]
PAR_RIA_VIGO = {
    1: 4, 2: 3, 3: 5, 4: 4, 5: 4, 6: 4, 7: 3, 8: 5, 9: 4,
    10: 4, 11: 4, 12: 3, 13: 5, 14: 4, 15: 4, 16: 3, 17: 5, 18: 4
}

# ==========================================
# 2. FUNCIONES NÚCLEO (CORE)
# ==========================================
def leer_datos():
    """Lee de Google Sheets y normaliza columnas a mayúsculas."""
    try:
        df = conn.read()
        # Limpieza crítica para evitar KeyError
        df.columns = [str(c).strip().upper() for c in df.columns]
        # Eliminar filas totalmente vacías
        df = df.dropna(how='all', axis=0)
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

def calcular_puntos_jornada(par, lista_golpes):
    """Calcula el reparto de puntos (0.5, 1.0) y bonus por hoyo."""
    pts_finales = [0.0, 0.0, 0.0, 0.0]
    # Comparación entre jugadores
    for i in range(len(lista_golpes)):
        for j in range(len(lista_golpes)):
            if i != j:
                if lista_golpes[i] < lista_golpes[j]:
                    pts_finales[i] += 1.0
                elif lista_golpes[i] == lista_golpes[j]:
                    pts_finales[i] += 0.5
    # Bonus calidad vs Par
    for i, g in enumerate(lista_golpes):
        diff = g - par
        if diff <= -2: pts_finales[i] += 1.0      # Eagle o mejor
        elif diff == -1: pts_finales[i] += 0.5    # Birdie
    return pts_finales

# ==========================================
# 3. ESTADO DE LA SESIÓN (SESSION STATE)
# ==========================================
if "refresco_id" not in st.session_state:
    st.session_state.refresco_id = 0
if "ultima_sincro" not in st.session_state:
    st.session_state.ultima_sincro = "No sincronizado"

# ==========================================
# 4. BARRA LATERAL (MENU)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1099/1099680.png", width=100)
    st.title("Canita Brava v3.0")
    menu = st.radio("Navegación", ["Jugar/Editar", "Estadísticas", "Histórico", "Configuración"])
    st.write("---")
    st.info(f"Sincro: {st.session_state.ultima_sincro}")

# ==========================================
# SECCIÓN: JUGAR / EDITAR (MOTOR PRINCIPAL)
# ==========================================
elif menu == "Jugar/Editar":
    st.header("🏌️ Entrada de Golpes")
    
    # 1. Gestión de Refresco y Sincronización
    col_ref1, col_ref2 = st.columns([3, 1])
    col_ref1.info(f"☁️ **Última Sincro:** {st.session_state.ultima_sincro}")
    
    if col_ref2.button("🔄 REFRESCAR HOYO", use_container_width=True):
        st.cache_data.clear()
        # Incrementamos el ID para forzar a los widgets de golpes a reiniciarse
        st.session_state.refresco_id += 1
        st.session_state.ultima_sincro = datetime.now().strftime("%H:%M:%S")
        st.rerun()

    st.write("---")

    # 2. Selección de Hoyo con Persistencia en Session State
    # Usamos una key fija para que Streamlit "recuerde" el hoyo al refrescar
    st.number_input(
        "Selecciona el Hoyo:", 
        min_value=1, 
        max_value=18, 
        step=1, 
        key="hoyo_selector_persistente"
    )
    
    # Definimos la variable única para evitar NameError
    hoyo_id = int(st.session_state.hoyo_selector_persistente)
    par_hoyo = int(PAR_RIA_VIGO[hoyo_id])

    # 3. Carga de Datos y Filtrado por Fecha y Hoyo
    df_actual = leer_datos()
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    datos_hoyo_especifico = pd.DataFrame()
    
    if not df_actual.empty:
        # Aseguramos que los tipos coincidan para el filtro
        df_actual['HOYO'] = pd.to_numeric(df_actual['HOYO'], errors='coerce')
        df_actual['FECHA'] = df_actual['FECHA'].astype(str)
        
        # Filtramos la fila exacta del día de hoy y el hoyo seleccionado
        datos_hoyo_especifico = df_actual[
            (df_actual['FECHA'] == fecha_hoy) & 
            (df_actual['HOYO'] == hoyo_id)
        ]

    # 4. Interfaz Visual de los 4 Jugadores
    st.subheader(f"⛳ Hoyo {hoyo_id} | Par {par_hoyo}")
    
    cols_jug = st.columns(4)
    golpes_finales = []
    campos_s = ['S0', 'S1', 'S2', 'S3'] # Nombres de columnas en tu Excel

    for i, jug en enumerate(TODOS):
        # Por defecto cargamos el Par del hoyo
        valor_defecto = par_hoyo
        
        # Si existen datos previos en la nube para este hoyo, los extraemos
        if not datos_hoyo_especifico.empty:
            col_s = campos_s[i]
            if col_s in datos_hoyo_especifico.columns:
                val_celda = datos_hoyo_especifico.iloc[0][col_s]
                if pd.notna(val_celda):
                    try:
                        valor_defecto = int(float(val_celda))
                    except:
                        valor_defecto = par_hoyo
        
        # TRUCO: La key incluye 'refresco_id' y 'hoyo_id' para forzar a la UI
        # a mostrar los golpes correctos y no quedarse "atascada" en el hoyo 1.
        clave_input = f"input_h{hoyo_id}_j{i}_rid{st.session_state.refresco_id}"
        
        g = cols_jug[i].number_input(
            f"{jug}", 
            min_value=1, 
            max_value=15, 
            value=valor_defecto, 
            key=clave_input
        )
        golpes_finales.append(g)

    st.write("---")

    # 5. Botón de Guardado y Sincronización con Google Sheets
    if st.button("💾 GUARDAR HOYO Y SUBIR", type="primary", use_container_width=True):
        with st.spinner("Sincronizando con Google Sheets..."):
            try:
                # Calculamos el reparto de puntos
                puntos_calculados = calcular_puntos_jornada(par_hoyo, golpes_finales)
                
                # Preparamos la estructura de datos (Mayúsculas obligatorias)
                nueva_fila = {
                    'FECHA': fecha_hoy,
                    'HOYO': int(hoyo_id),
                    'PAR': int(par_hoyo),
                    'TEMPORADA': 2024.0,
                    'PARTIDO_ID': float(fecha_hoy.replace("-", "")),
                    'S0': int(golpes_finales[0]),
                    'S1': int(golpes_finales[1]),
                    'S2': int(golpes_finales[2]),
                    'S3': int(golpes_finales[3]),
                    'P1_PTS': float(puntos_calculados[0]),
                    'P2_PTS': float(puntos_calculados[1]),
                    'P3_PTS': float(puntos_calculados[2]),
                    'P4_PTS': float(puntos_calculados[3])
                }
                
                # Buscamos si el hoyo ya existía en el DataFrame para sobreescribirlo
                mascara = (df_actual['FECHA'] == fecha_hoy) & (df_actual['HOYO'] == hoyo_id)
                
                if mascara.any():
                    idx = df_actual.index[mascara][0]
                    for col, val in nueva_fila.items():
                        if col in df_actual.columns:
                            df_actual.at[idx, col] = val
                else:
                    # Si es un hoyo nuevo en el partido, lo añadimos al final
                    df_actual = pd.concat([df_actual, pd.DataFrame([nueva_fila])], ignore_index=True)
                
                # Enviamos el DataFrame completo de vuelta a la nube
                conn.update(data=df_actual)
                
                # Feedback y limpieza
                st.cache_data.clear()
                st.session_state.refresco_id += 1 # Limpiamos la UI para el siguiente paso
                st.session_state.ultima_sincro = datetime.now().strftime("%H:%M:%S")
                st.success(f"✅ ¡Éxito! Datos del hoyo {hoyo_id} guardados.")
                st.balloons()
                st.rerun()
                
            except Exception as e:
                st.error(f"Hubo un error al guardar: {e}")

# ==========================================
# 6. SECCIÓN: ESTADÍSTICAS (CORREGIDA)
# ==========================================
elif menu == "Estadísticas":
    st.header("📊 Análisis de Temporada")
    df_stats = leer_datos()
    
    if not df_stats.empty:
        # Selección de Temporada (Mayúsculas corregido)
        if 'TEMPORADA' in df_stats.columns:
            temps = sorted(df_stats['TEMPORADA'].unique().tolist(), reverse=True)
        else:
            temps = [2024]
        
        temp_sel = st.selectbox("Elija temporada:", temps)
        df_temp = df_stats[df_stats['TEMPORADA'] == temp_sel]
        
        # Dashboard Visual
        col1, col2 = st.columns(2)
        
        # Puntos Totales
        puntos_cols = ['P1_PTS', 'P2_PTS', 'P3_PTS', 'P4_PTS']
        totales = df_temp[puntos_cols].sum().values
        fig_pts = px.bar(x=TODOS, y=totales, title="Puntos Acumulados", labels={'x':'Jugador', 'y':'Puntos'})
        col1.plotly_chart(fig_pts, use_container_width=True)
        
        # Media de Golpes
        golpes_cols = ['S0', 'S1', 'S2', 'S3']
        medias = df_temp[golpes_cols].mean().values
        fig_gol = px.line(x=TODOS, y=medias, title="Media de Golpes por Hoyo")
        col2.plotly_chart(fig_gol, use_container_width=True)
        
        st.subheader("📋 Datos Brutos de la Temporada")
        st.dataframe(df_temp, use_container_width=True)
    else:
        st.warning("No hay datos disponibles en la base de datos.")

# ==========================================
# 7. SECCIÓN: HISTÓRICO
# ==========================================
elif menu == "Histórico":
    st.header("📜 Historial de Partidos")
    df_hist = leer_datos()
    if not df_hist.empty:
        # Agrupar por fecha y Partido_ID para ver totales diarios
        resumen = df_hist.groupby(['FECHA', 'PARTIDO_ID'])[['P1_PTS', 'P2_PTS', 'P3_PTS', 'P4_PTS']].sum().reset_index()
        st.table(resumen)
    else:
        st.write("El historial está vacío.")

# ==========================================
# 8. CONFIGURACIÓN
# ==========================================
elif menu == "Configuración":
    st.header("⚙️ Ajustes")
    st.write("Configuración de la App y Base de Datos")
    if st.button("Limpiar toda la caché de la App"):
        st.cache_data.clear()
        st.success("Caché limpia.")
