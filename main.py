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
COLOR_A = "#2e7d32" # Verde
COLOR_B = "#c62828" # Rojo
INICIO_2026_A = 3.5  
INICIO_2026_B = 3.5  

st.set_page_config(page_title="CAÑITA BRAVA", page_icon="⛳", layout="centered")

# --- FUNCIÓN DE LECTURA SIN CACHÉ ---
def leer_datos_frescos():
    # Eliminamos cualquier rastro de datos antiguos en la memoria
    st.cache_data.clear() 
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # ttl=0 es clave: le dice a Streamlit que no guarde los datos ni 1 segundo
        df = conn.read(worksheet="historial", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "s0", "s1", "s2", "s3"])
        return df.dropna(subset=['id'])
    except:
        return pd.DataFrame(columns=["id", "partido_id", "hoyo", "fecha", "temporada", "resultado_a", "resultado_b", "p1_pts", "p2_pts", "p3_pts", "p4_pts", "s0", "s1", "s2", "s3"])

# --- RESTO DE FUNCIONES ---
def estilo_tabla(row):
    color = COLOR_A if row['Jugador'] in ["MANUEL", "JOSE"] else COLOR_B
    return [f'color: {color}; font-weight: bold'] * len(row)

def guardar_hoyo(df_fila):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existente = leer_datos_frescos()
        id_hoyo = str(df_fila["id"].iloc[0])
        if not df_existente.empty:
            df_existente['id'] = df_existente['id'].astype(str)
            df_final = df_existente[df_existente["id"] != id_hoyo].copy()
            df_final = pd.concat([df_final, df_fila], ignore_index=True)
        else:
            df_final = df_fila
        conn.update(worksheet="historial", data=df_final)
        st.cache_data.clear() # Limpiar después de escribir
        return True
    except:
        return False

# --- NAVEGACIÓN ---
if 'menu' not in st.session_state:
    st.session_state.menu = "Inicio"

def ir_a(pagina):
    st.session_state.menu = pagina
    st.rerun()

with st.sidebar:
    st.title("⛳ Menú")
    # Al pulsar Inicio, forzamos recarga de la página
    if st.button("Inicio", use_container_width=True): 
        st.cache_data.clear()
        ir_a("Inicio")
    if st.button("Jugar/Editar", use_container_width=True): ir_a("Jugar/Editar")
    if st.button("Admin", use_container_width=True): ir_a("Admin")

# --- PANTALLA INICIO ---
if st.session_state.menu == "Inicio":
    st.markdown("<h1 style='text-align: center;'>⛳ CAÑITA BRAVA 2026</h1>", unsafe_allow_html=True)
    
    # Leemos datos cada vez que entramos a Inicio
    df = leer_datos_frescos()
    df_2026 = df[df['temporada'].astype(str) == "2026"]
    
    pts_a, pts_b = INICIO_2026_A, INICIO_2026_B
    
    if not df_2026.empty:
        # Importante: Asegurar que los puntos son numéricos
        df_2026['resultado_a'] = pd.to_numeric(df_2026['resultado_a'], errors='coerce').fillna(0)
        df_2026['resultado_b'] = pd.to_numeric(df_2026['resultado_b'], errors='coerce').fillna(0)
        
        resumen = df_2026.groupby('partido_id').agg({'resultado_a':'sum','resultado_b':'sum'}).reset_index()
        
        for _, r in resumen.iterrows():
            if r['resultado_a'] > r['resultado_b']: pts_a += 1
            elif r['resultado_b'] > r['resultado_a']: pts_b += 1
            elif (r['resultado_a'] + r['resultado_b']) > 0: # Si hay empate pero han jugado
                pts_a += 0.5; pts_b += 0.5
    
    st.markdown(f"""
        <div style="border:2px solid #ccc;border-radius:15px;padding:20px;background:#f9f9f9;text-align:center;margin-bottom:25px;">
            <h2 style="color:#333;margin:0;">TEMPORADA 2026</h2>
            <div style="display:flex;justify-content:space-around;align-items:center;">
                <div><h4 style="color:{COLOR_A};margin:0;">M & J</h4><h1 style="color:{COLOR_A};margin:0;">{pts_a:g}</h1></div>
                <h2 style="margin:0;color:#999;">VS</h2>
                <div><h4 style="color:{COLOR_B};margin:0;">R & L</h4><h1 style="color:{COLOR_B};margin:0;">{pts_b:g}</h1></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if not df_2026.empty:
        st.markdown("<h3 style='text-align:center;'>⭐ Clasificación MVP</h3>", unsafe_allow_html=True)
        mvps = {TODOS[i]: df_2026[f"p{i+1}_pts"].sum() for i in range(4)}
        df_mvp = pd.DataFrame([{"Jugador": k, "Pts": v} for k, v in mvps.items()]).sort_values("Pts", ascending=False)
        st.table(df_mvp.style.apply(estilo_tabla, axis=1).format({"Pts": "{:.1f}"}))

# (El resto de las pantallas Jugar/Editar y Admin se mantienen como en la versión anterior)
