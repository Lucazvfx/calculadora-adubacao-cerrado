# adubacao/config.py
# Tabelas de referência baseadas no manual da Embrapa Cerrados (2004) e suas tabelas

# ============================================
# INTERPRETAÇÃO DE FÓSFORO (Mehlich-1) - Tabela 3
# ============================================
LIMITES_P = [
    (0, 15, 6.0, 12.0, 18.0, float('inf')),
    (16, 35, 5.0, 10.0, 15.0, float('inf')),
    (36, 60, 3.0, 5.0, 8.0, float('inf')),
    (61, 100, 2.0, 3.0, 4.0, float('inf')),
]

# ============================================
# ADUBAÇÃO FOSFATADA CORRETIVA (kg/ha P2O5) - Tabela 8
# ============================================
DOSE_P_CORRETIVO = {
    (0, 15): {'Muito baixo': 60, 'Baixo': 30, 'Médio': 15, 'Adequado': 0},
    (16, 35): {'Muito baixo': 100, 'Baixo': 50, 'Médio': 25, 'Adequado': 0},
    (36, 60): {'Muito baixo': 200, 'Baixo': 100, 'Médio': 50, 'Adequado': 0},
    (61, 100): {'Muito baixo': 280, 'Baixo': 140, 'Médio': 70, 'Adequado': 0},
}

DOSE_P_CORRETIVO_IRRIGADO = {
    (0, 15): {'Muito baixo': 90, 'Baixo': 45, 'Médio': 20, 'Adequado': 0},
    (16, 35): {'Muito baixo': 150, 'Baixo': 75, 'Médio': 40, 'Adequado': 0},
    (36, 60): {'Muito baixo': 300, 'Baixo': 150, 'Médio': 75, 'Adequado': 0},
    (61, 100): {'Muito baixo': 420, 'Baixo': 210, 'Médio': 105, 'Adequado': 0},
}

# ============================================
# INTERPRETAÇÃO DE POTÁSSIO - Tabela fornecida
# ============================================
LIMITES_K = [
    (0, 4, 15, 30, 40, float('inf')),
    (4, float('inf'), 25, 50, 80, float('inf')),
]

DOSE_K_CORRETIVO = [
    (0, 4, 'Baixo', 50),
    (0, 4, 'Médio', 25),
    (0, 4, 'Adequado', 0),
    (0, 4, 'Alto', 0),
    (4, float('inf'), 'Baixo', 100),
    (4, float('inf'), 'Médio', 50),
    (4, float('inf'), 'Adequado', 0),
    (4, float('inf'), 'Alto', 0),
]

# ============================================
# MICRONUTRIENTES - Suas tabelas
# ============================================
LIMITES_MICRO = {
    'Zn': {'baixo': 1.0, 'medio': 1.6},   # Baixo <1.0, Médio 1.1-1.6, Alto >1.6
    'Cu': {'baixo': 0.4, 'medio': 0.8},   # Baixo <0.4, Médio 0.5-0.8, Alto >0.8
    'B': {'baixo': 0.2, 'medio': 0.5},    # Baixo <0.2, Médio 0.3-0.5, Alto >0.5
    'Mn': {'baixo': 1.9, 'medio': 5.0},   # Baixo <1.9, Médio 2.0-5.0, Alto >5.0
    'Fe': {'baixo': 10, 'medio': 20},     # Ajuste se necessário
    'S': {'baixo': 5, 'medio': 10},       # Exemplo: Baixo <5, Médio 5-10, Alto >10
}

REC_MICRO = {
    'Zn': {'baixo': 6, 'medio': 3, 'alto': 0},
    'Cu': {'baixo': 4, 'medio': 2, 'alto': 0},
    'B': {'baixo': 2, 'medio': 1, 'alto': 0},
    'Mn': {'baixo': 6, 'medio': 3, 'alto': 0},
    'Fe': {'baixo': 10, 'medio': 5, 'alto': 0},
    'S': {'baixo': 30, 'medio': 20, 'alto': 0},
}

# ============================================
# NITROGÊNIO - Valor fixo (pode ser alterado)
# ============================================
N_FIXO_MILHO = 170

# ============================================
# FERTILIZANTES
# ============================================
FERTILIZANTES = {
    'Ureia': {'N': 45},
    'MAP': {'N': 10, 'P2O5': 48},
    'Superfosfato simples': {'P2O5': 18, 'Ca': 18, 'S': 11},
    'Superfosfato triplo': {'P2O5': 41, 'Ca': 12},
    'KCl': {'K2O': 60},
    'Gesso agrícola': {'Ca': 23, 'S': 15},
}