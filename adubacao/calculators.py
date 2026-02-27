# adubacao/calculators.py
from .models import AnaliseSolo, Cultura, Sistema, Recomendacao
from . import config, interpretation as interp
from typing import Optional

def calcular_calagem(analise: AnaliseSolo, cultura: Cultura, sistema: Sistema, prnt: float = 100) -> Optional[float]:
    if cultura == Cultura.PASTAGEM:
        v2 = 35
    elif sistema == Sistema.IRRIGADO:
        v2 = 60
    else:
        v2 = 50

    v1 = analise.saturacao_bases
    if v1 >= v2:
        return None
    nc = (v2 - v1) * analise.ctc / prnt
    return round(nc, 1)

def calcular_gessagem(analise: AnaliseSolo, cultura: Cultura) -> Optional[float]:
    if analise.al > 0.5 or analise.ca < 1.5:
        if cultura in (Cultura.MILHO, Cultura.SOJA):
            return 50 * analise.argila
        else:
            return 75 * analise.argila
    return None

def calcular_npk(analise: AnaliseSolo, cultura: Cultura, sistema: Sistema,
                 produtividade_t_ha: float, historico_soja: bool = False) -> dict:
    if cultura == Cultura.MILHO:
        n_final = config.N_FIXO_MILHO

        classe_p = interp.classificar_p(analise.p_melich, analise.argila)
        dose_p_corretiva = 0
        tabela_p = config.DOSE_P_CORRETIVO_IRRIGADO if sistema == Sistema.IRRIGADO else config.DOSE_P_CORRETIVO
        for (amin, amax), doses in tabela_p.items():
            if amin <= analise.argila <= amax:
                dose_p_corretiva = doses.get(classe_p, 0)
                break

        classe_k = interp.classificar_k(analise.k_melich, analise.ctc)
        dose_k_corretiva = 0
        for ctc_min, ctc_max, classe, dose in config.DOSE_K_CORRETIVO:
            if ctc_min <= analise.ctc < ctc_max and classe == classe_k:
                dose_k_corretiva = dose
                break

        if historico_soja:
            n_final = max(n_final - 30, 0)

        return {
            'N': n_final,
            'P2O5': dose_p_corretiva,
            'K2O': dose_k_corretiva
        }
    else:
        return {'N': 0, 'P2O5': 0, 'K2O': 0}

def calcular_micronutrientes(analise: AnaliseSolo) -> dict:
    recomendacoes = {}
    for elem in ['Zn', 'Cu', 'B', 'Mn', 'Fe', 'S']:  # Incluímos S
        valor = getattr(analise, elem.lower(), None)
        if valor is None:
            continue
        classe = interp.classificar_micronutriente(valor, elem)
        dose = config.REC_MICRO[elem].get(classe.lower(), 0)
        if dose > 0:
            recomendacoes[elem] = dose
    return recomendacoes

def recomendar_tudo(analise: AnaliseSolo, cultura: Cultura, sistema: Sistema,
                    produtividade_t_ha: float, historico_soja: bool = False,
                    prnt: float = 100) -> Recomendacao:
    calagem = calcular_calagem(analise, cultura, sistema, prnt)
    gesso = calcular_gessagem(analise, cultura)
    npk = calcular_npk(analise, cultura, sistema, produtividade_t_ha, historico_soja)
    micro = calcular_micronutrientes(analise)
    return Recomendacao(
        calagem_t_ha=calagem,
        gesso_kg_ha=gesso,
        n_kg_ha=npk['N'],
        p2o5_kg_ha=npk['P2O5'],
        k2o_kg_ha=npk['K2O'],
        micronutrientes=micro
    )