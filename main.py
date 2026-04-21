def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    # Normalización: 0 -> 99 (bola levantada)
    scores = [s1 if s1 > 0 else 99, s2 if s2 > 0 else 99, 
              s3 if s3 > 0 else 99, s4 if s4 > 0 else 99]
    
    v1, v2, v3, v4 = scores
    best_a, worst_a = (v1, v2) if v1 <= v2 else (v2, v1)
    best_b, worst_b = (v3, v4) if v3 <= v4 else (v4, v3)
    
    pts_match_a, pts_match_b = 0.0, 0.0
    mvp_inc = {"p1": 0.0, "p2": 0.0, "p3": 0.0, "p4": 0.0}

    # --- MATCH ---
    if best_a < best_b: pts_match_a += 1.0
    elif best_b < best_a: pts_match_b += 1.0
    if worst_a < worst_b: pts_match_a += 1.0
    elif worst_b < worst_a: pts_match_b += 1.0

    # --- MVP ---
    # 1. Lógica Mejor Bola MVP
    if best_a < best_b:
        mvp_inc["p1" if v1 == best_a else "p2"] += 1.0
    elif best_b < best_a:
        mvp_inc["p3" if v3 == best_b else "p4"] += 1.0
    elif best_a == best_b and best_a != 99:
        # Empate entre bandos en la mejor: 0.5 para los que hicieron ese score
        if v1 == best_a: mvp_inc["p1"] += 0.5
        if v2 == best_a: mvp_inc["p2"] += 0.5
        if v3 == best_b: mvp_inc["p3"] += 0.5
        if v4 == best_b: mvp_inc["p4"] += 0.5

    # 2. Lógica Peor Bola MVP
    # Solo se calcula si la peor bola es distinta a la mejor o para ajustar el empate
    if worst_a < worst_b:
        mvp_inc["p1" if v1 == worst_a else "p2"] += 0.5
    elif worst_b < worst_a:
        mvp_inc["p3" if v3 == worst_b else "p4"] += 0.5
    elif worst_a == worst_b and worst_a != 99:
        # Si las 4 bolas son iguales, para que sumen 0.5 en total:
        # Como ya sumaron 0.5 en la "Mejor", aquí sumamos 0 para que el total sea 0.5
        # Si NO son las 4 iguales (ej. 4,4 vs 4,5), el de la peor (5) no suma.
        if not (v1 == v2 == v3 == v4):
            if v1 == worst_a: mvp_inc["p1"] += 0.25
            if v2 == worst_a: mvp_inc["p2"] += 0.25
            if v3 == worst_b: mvp_inc["p3"] += 0.25
            if v4 == worst_b: mvp_inc["p4"] += 0.25
        
    # --- BONUS CALIDAD ---
    for i, s in enumerate([s1, s2, s3, s4]):
        if s > 0:
            bonus = 0.0
            if s == par - 1: bonus = 1.0
            elif s <= par - 2: bonus = 2.0
            if bonus > 0:
                mvp_inc[f"p{i+1}"] += bonus
                if i < 2: pts_match_a += bonus
                else: pts_match_b += bonus
            
    return pts_match_a, pts_match_b, mvp_inc
