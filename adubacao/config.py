# adubacao/config.py
# Tabelas de referência baseadas no manual da Embrapa Cerrados (2004)

# ============================================
# INTERPRETAÇÃO DE FÓSFORO (Mehlich-1) - Tabela 3 (p. 154)
# ============================================
LIMITES_P = [
    (0, 15, 6.0, 12.0, 18.0, 25.0),          # argila ≤15%
    (16, 35, 4.0, 8.0, 12.0, 18.0),          # argila 16–35%
    (36, 60, 3.0, 6.0, 9.0, 13.0),            # argila 36–60%
    (61, 100, 2.0, 4.0, 6.0, 9.0),             # argila >60%
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
# INTERPRETAÇÃO DE POTÁSSIO - Tabela 5 (p. 181) [valores em mg/dm³]
# ============================================
LIMITES_K = [
    (0, float('inf'), 15, 30, 50, 80),        # usado apenas para compatibilidade; a classificação agora é baseada em níveis fixos
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
# MICRONUTRIENTES
# ============================================
LIMITES_MICRO = {
    'Zn': {'baixo': 1.0, 'medio': 1.6},
    'Cu': {'baixo': 0.4, 'medio': 0.8},
    'B': {'baixo': 0.2, 'medio': 0.5},
    'Mn': {'baixo': 1.9, 'medio': 5.0},
    'Fe': {'baixo': 10, 'medio': 20},
    'S': {'baixo': 4.0, 'medio': 10.0},   # baixo <4, médio 4–10, alto >10
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
# ALVOS DE SATURAÇÃO POR BASES (V2) PARA CALAGEM
# ============================================
V2_PASTAGEM_EXIGENTE = 45
V2_PASTAGEM_POUCO_EXIGENTE = 30
V2_PASTAGEM_PADRAO = 35
MG_MINIMO_RECOMENDADO = 0.5

# ============================================
# EXTRAÇÃO E EXPORTAÇÃO DE NUTRIENTES
# ============================================
EXPORTACAO_K2O = {
    'milho': 3.4,
    'soja': 20.0,
    'feijao': 14.0,
    'arroz': 3.0,
}

FATOR_K_MANUTENCAO = {
    'Muito baixo': 1.0,
    'Baixo': 1.0,
    'Médio': 1.0,
    'Adequado': 1.0,
    'Alto': 0.5,
}

# Parâmetros para N (milho)
N_PLANTIO_MILHO = 20
REQUERIMENTO_N_POR_TONELADA = 20
N_MINERALIZADO_MO = 30
FATOR_SOJA_HISTORICO = 0.6
FATOR_PLANTIO_DIRETO = 1.2

# ============================================
# CONFIGURAÇÕES DE METODOLOGIA (baseadas no JSON fornecido)
# ============================================
METODOLOGIA = {
    "metodologia_ativa": "Embrapa_Cerrado_2017",
    "parametros_globais": {
        "arredondamento_doses": 0.1,
        "limite_maximo_p2o5_sulco": 120,
        "limite_maximo_k2o_sulco": 60,
        "considerar_mo_no_nitrogenio": True,
        "fator_eficiencia_n": 1.33
    },
    "preferencias_exibicao": {
        "unidade_area": "hectare",
        "exibir_recomendacao_em": "kg_nutriente_ha",
        "sugerir_formulados_comerciais": True
    }
}

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