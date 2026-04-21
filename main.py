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
    return sqlite3.connect('canita_brava_v14.db', check_same_thread=False)

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

init_db()

def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    pts_match_a, pts_match_b = 0.0, 0.0
    mvp_inc = {"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}
    
    best_a, worst_a = (s1, s2) if s1 <= s2 else (s2, s1)
    best_b, worst_b = (s3, s4) if s3 <= s4 else (s4, s3)
    
    # --- LÓGICA MATCH (Solo gana el que hace menos golpes) ---
    if best_a < best_b: pts_match_a += 1.0
    elif best_b < best_a: pts_match_b += 1.0
    
    if worst_a < worst_b: pts_match_a += 1.0
    elif worst_b < worst_a: pts_match_b += 1.0

    # --- LÓGICA MVP (Gana o Empata suma) ---
    # Mejor bola MVP
    if best_a <= best_b: mvp_inc["p1" if s1 == best_a else "p2"] += 1.0
    if best_b <= best_a: mvp_inc["p3" if s3 == best_b else "p4"] += 1.0
    # Peor bola MVP
    if worst_a <= worst_b: mvp_inc["p1" if s1 == worst_a else "p2"] += 0.5
    if worst_b <= worst_a: mvp_inc["p3" if s3 == worst_b else "p4"] += 0.5
        
    # --- BONUS CALIDAD (Suman a ambos) ---
    scores = [s1, s2, s3, s4]
    p_ids = ["p1", "p2", "p3", "p4"]
    for i, s in enumerate(scores):
        bonus = 0.0
        if s == par - 1: bonus = 1.0   # Birdie
        elif s <= par - 2: bonus = 2.0 # Eagle
        
        if bonus > 0:
            mvp_inc[p_ids[i]] += bonus
            if i < 2: pts_match_a += bonus
            else: pts_match_b += bonus
            
    return pts_match_a, pts_match_b, mvp_inc

# [Interfaz de Streamlit igual a la v13 pero con la nueva función calcular_puntos_hoyo]
# ... (Se mantiene el resto del código de navegación y visualización de la v13)
