from .models import AnaliseSolo, Cultura, Sistema, Recomendacao
from . import config, interpretation as interp
from typing import Optional, List


# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def arredondar_dose(valor: float) -> float:
    return round(
        valor / config.METODOLOGIA['parametros_globais']['arredondamento_doses']
    ) * config.METODOLOGIA['parametros_globais']['arredondamento_doses']


# ==========================================================
# CALAGEM
# ==========================================================

def calcular_calagem(analise: AnaliseSolo, cultura: Cultura,
                     sistema: Sistema, prnt: float = 100,
                     tipo_pastagem: str = 'padrao',
                     log: Optional[List[str]] = None) -> Optional[float]:

    if log is None:
        log = []

    if cultura == Cultura.PASTAGEM:
        if tipo_pastagem == 'exigente':
            v2 = config.V2_PASTAGEM_EXIGENTE
        elif tipo_pastagem == 'pouco_exigente':
            v2 = config.V2_PASTAGEM_POUCO_EXIGENTE
        else:
            v2 = config.V2_PASTAGEM_PADRAO

    elif sistema == Sistema.IRRIGADO:
        v2 = 60
    else:
        v2 = 50

    v1 = analise.saturacao_bases

    if v1 >= v2:
        return None

    nc = (v2 - v1) * analise.ctc / prnt
    return arredondar_dose(nc)


# ==========================================================
# GESSAGEM
# ==========================================================

def calcular_gessagem(analise: AnaliseSolo,
                      cultura: Cultura,
                      log: Optional[List[str]] = None) -> Optional[float]:

    if analise.al > 0.5 or analise.ca < 1.5:

        if cultura in (Cultura.MILHO, Cultura.SOJA):
            return 50 * analise.argila
        else:
            return 75 * analise.argila

    return None


# ==========================================================
# NITROGÊNIO MILHO
# ==========================================================

def calcular_n_milho(analise: AnaliseSolo,
                     produtividade_t_ha: float,
                     historico_soja: bool = False,
                     plantio_direto_primeiros_anos: bool = False,
                     log: Optional[List[str]] = None) -> float:

    requerimento = produtividade_t_ha * config.REQUERIMENTO_N_POR_TONELADA

    if config.METODOLOGIA['parametros_globais']['considerar_mo_no_nitrogenio']:
        mo_percent = analise.mo / 10
        suprimento = mo_percent * config.N_MINERALIZADO_MO
    else:
        suprimento = 0

    necessidade = max(0, requerimento - suprimento)
    necessidade *= config.METODOLOGIA['parametros_globais']['fator_eficiencia_n']

    n_cobertura = necessidade - config.N_PLANTIO_MILHO
    n_cobertura = max(0, n_cobertura)

    if historico_soja:
        n_cobertura *= config.FATOR_SOJA_HISTORICO

    if plantio_direto_primeiros_anos:
        n_cobertura *= config.FATOR_PLANTIO_DIRETO

    return arredondar_dose(n_cobertura)


# ==========================================================
# POTÁSSIO MANUTENÇÃO
# ==========================================================

def calcular_k_manutencao(cultura: Cultura,
                          produtividade_t_ha: float,
                          classe_k: str) -> float:

    if cultura == Cultura.MILHO:
        taxa = config.EXPORTACAO_K2O['milho']
    elif cultura == Cultura.SOJA:
        taxa = config.EXPORTACAO_K2O['soja']
    else:
        return 0.0

    return taxa * produtividade_t_ha


# ==========================================================
# CÁLCULO NPK PRINCIPAL
# ==========================================================

def calcular_npk(analise: AnaliseSolo,
                 cultura: Cultura,
                 sistema: Sistema,
                 produtividade_t_ha: float,
                 historico_soja: bool = False,
                 plantio_direto_primeiros_anos: bool = False,
                 log: Optional[List[str]] = None) -> dict:

    if cultura not in (Cultura.MILHO, Cultura.SOJA):
        return {'N': 0, 'P2O5': 0, 'K2O': 0}

    # N
    if cultura == Cultura.MILHO:
        n_final = calcular_n_milho(
            analise,
            produtividade_t_ha,
            historico_soja,
            plantio_direto_primeiros_anos
        )
        exportacao_p = 2.5
    else:
        n_final = 0
        exportacao_p = 15.6

    # P
    classe_p = interp.classificar_p(analise.p_melich, analise.argila)

    tabela_p = (
        config.DOSE_P_CORRETIVO_IRRIGADO
        if sistema == Sistema.IRRIGADO
        else config.DOSE_P_CORRETIVO
    )

    dose_p_corretiva = 0
    for (amin, amax), doses in tabela_p.items():
        if amin <= analise.argila <= amax:
            dose_p_corretiva = doses.get(classe_p, 0)
            break

    p_manutencao = exportacao_p * produtividade_t_ha
    p2o5_final = arredondar_dose(dose_p_corretiva + p_manutencao)

    # K
    classe_k = interp.classificar_k(analise.k_melich, analise.ctc)

    dose_k_corretiva = 0
    for ctc_min, ctc_max, classe, dose in config.DOSE_K_CORRETIVO:
        if ctc_min <= analise.ctc < ctc_max and classe == classe_k:
            dose_k_corretiva = dose
            break

    k_manutencao = calcular_k_manutencao(cultura, produtividade_t_ha, classe_k)
    k2o_final = arredondar_dose(dose_k_corretiva + k_manutencao)

    return {
        'N': n_final,
        'P2O5': p2o5_final,
        'K2O': k2o_final
    }


# ==========================================================
# MICRONUTRIENTES
# ==========================================================

def calcular_micronutrientes(analise: AnaliseSolo) -> dict:
    recomendacoes = {}

    for elem in ['Zn', 'Cu', 'B', 'Mn', 'Fe', 'S']:
        valor = getattr(analise, elem.lower(), None)
        if valor is None:
            continue

        classe = interp.classificar_micronutriente(valor, elem)
        dose = config.REC_MICRO[elem].get(classe.lower(), 0)

        if dose > 0:
            recomendacoes[elem] = dose

    return recomendacoes


# ==========================================================
# FUNÇÃO FINAL
# ==========================================================

def recomendar_tudo(analise: AnaliseSolo,
                    cultura: Cultura,
                    sistema: Sistema,
                    produtividade_t_ha: float,
                    historico_soja: bool = False,
                    plantio_direto_primeiros_anos: bool = False,
                    prnt: float = 100,
                    tipo_pastagem: str = 'padrao') -> Recomendacao:

    calagem = calcular_calagem(
        analise, cultura, sistema, prnt, tipo_pastagem
    )

    gesso = calcular_gessagem(analise, cultura)

    npk = calcular_npk(
        analise,
        cultura,
        sistema,
        produtividade_t_ha,
        historico_soja,
        plantio_direto_primeiros_anos
    )

    micro = calcular_micronutrientes(analise)

    return Recomendacao(
        calagem_t_ha=calagem,
        gesso_kg_ha=gesso,
        n_kg_ha=npk['N'],
        p2o5_kg_ha=npk['P2O5'],
        k2o_kg_ha=npk['K2O'],
        micronutrientes=micro,
        log=[]
    )