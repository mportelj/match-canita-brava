def calcular_puntos_hoyo(s1, s2, s3, s4, hoyo_num):
    par = PAR_RIA_VIGO[hoyo_num]
    pts_a, pts_b = 0, 0
    mvp_inc = {"p1": 0, "p2": 0, "p3": 0, "p4": 0}

    # 1. Identificar Mejores y Peores scores de cada pareja
    best_a, worst_a = (s1, s2) if s1 <= s2 else (s2, s1)
    best_b, worst_b = (s3, s4) if s3 <= s4 else (s4, s3)

    # 2. Puntos por Match Play (Scratch)
    # Mejor Bola: +2 puntos al MVP del que la hace
    if best_a < best_b: 
        pts_a += 1
        mvp_inc["p1" if s1 == best_a else "p2"] += 2
    elif best_b < best_a: 
        pts_b += 1
        mvp_inc["p3" if s3 == best_b else "p4"] += 2

    # Peor Bola: +1 punto al MVP del que la salva
    if worst_a < worst_b: 
        pts_a += 1
        mvp_inc["p1" if s1 == worst_a else "p2"] += 1
    elif worst_b < worst_a: 
        pts_b += 1
        mvp_inc["p3" if s3 == worst_b else "p4"] += 1

    # 3. Bonos por Birdie y Eagle (1 y 2 puntos extra respectivamente)
    scores = [s1, s2, s3, s4]
    p_ids = ["p1", "p2", "p3", "p4"]
    for i, s in enumerate(scores):
        if s == par - 1: # BIRDIE
            mvp_inc[p_ids[i]] += 1 # +1 MVP
            if i < 2: pts_a += 1   # +1 Bando A
            else: pts_b += 1       # +1 Bando B
        elif s <= par - 2: # EAGLE
            mvp_inc[p_ids[i]] += 2 # +2 MVP
            if i < 2: pts_a += 2   # +2 Bando A
            else: pts_b += 2       # +2 Bando B
            
    return pts_a, pts_b, mvp_inc
