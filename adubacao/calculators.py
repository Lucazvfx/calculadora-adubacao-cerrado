from .models import AnaliseSolo, Cultura, Sistema, Recomendacao
from . import config, interpretation as interp
from typing import Optional, List

def arredondar_dose(valor: float) -> float:
    """Arredonda a dose conforme configuração global."""
    return round(valor / config.METODOLOGIA['parametros_globais']['arredondamento_doses']) * config.METODOLOGIA['parametros_globais']['arredondamento_doses']

def calcular_calagem(analise: AnaliseSolo, cultura: Cultura, sistema: Sistema,
                     prnt: float = 100, tipo_pastagem: str = 'padrao',
                     log: Optional[List[str]] = None) -> Optional[float]:
    if log is None:
        log = []
    if cultura == Cultura.PASTAGEM:
        if tipo_pastagem == 'exigente':
            v2 = config.V2_PASTAGEM_EXIGENTE
            log.append(f"Pastagem exigente: V2 = {v2}%")
        elif tipo_pastagem == 'pouco_exigente':
            v2 = config.V2_PASTAGEM_POUCO_EXIGENTE
            log.append(f"Pastagem pouco exigente: V2 = {v2}%")
        else:
            v2 = config.V2_PASTAGEM_PADRAO
            log.append(f"Pastagem padrão: V2 = {v2}%")
    elif sistema == Sistema.IRRIGADO:
        v2 = 60
        log.append("Sistema irrigado: V2 = 60%")
    else:
        v2 = 50
        log.append("Sistema sequeiro: V2 = 50%")

    v1 = analise.saturacao_bases
    log.append(f"Saturação por bases atual: V1 = {v1:.2f}%")
    if v1 >= v2:
        log.append("Não há necessidade de calagem (V1 >= V2).")
        return None
    nc = (v2 - v1) * analise.ctc / prnt
    nc_arred = arredondar_dose(nc)
    log.append(f"Necessidade de calcário: ({v2} - {v1:.2f}) * {analise.ctc:.2f} / {prnt} = {nc:.2f} t/ha (arredondado para {nc_arred} t/ha)")
    return nc_arred

def calcular_gessagem(analise: AnaliseSolo, cultura: Cultura,
                      log: Optional[List[str]] = None) -> Optional[float]:
    if log is None:
        log = []
    if analise.al > 0.5 or analise.ca < 1.5:
        motivo = []
        if analise.al > 0.5:
            motivo.append(f"Al = {analise.al} > 0.5")
        if analise.ca < 1.5:
            motivo.append(f"Ca = {analise.ca} < 1.5")
        log.append(f"Gessagem recomendada devido a: {' e '.join(motivo)}")
        if cultura in (Cultura.MILHO, Cultura.SOJA):
            dose = 50 * analise.argila
            log.append(f"Dose = 50 * argila ({analise.argila}) = {dose} kg/ha")
        else:
            dose = 75 * analise.argila
            log.append(f"Cultura perene: dose = 75 * argila ({analise.argila}) = {dose} kg/ha")
        return dose
    else:
        log.append("Gessagem não necessária (Al ≤ 0,5 e Ca ≥ 1,5).")
        return None

def verificar_magnesio(analise: AnaliseSolo, log: Optional[List[str]] = None) -> Optional[str]:
    if log is None:
        log = []
    if analise.mg < config.MG_MINIMO_RECOMENDADO:
        msg = (f"Teor de Mg ({analise.mg:.2f} cmolc/dm³) abaixo do mínimo recomendado "
               f"({config.MG_MINIMO_RECOMENDADO} cmolc/dm³). Utilize calcário dolomítico "
               "ou magnesiano na calagem, ou aplique uma fonte de magnésio (ex.: sulfato de magnésio).")
        log.append(msg)
        return msg
    return None

def calcular_n_milho(analise: AnaliseSolo, produtividade_t_ha: float,
                     historico_soja: bool = False, plantio_direto_primeiros_anos: bool = False,
                     log: Optional[List[str]] = None) -> float:
    if log is None:
        log = []
    requerimento = produtividade_t_ha * config.REQUERIMENTO_N_POR_TONELADA
    log.append(f"Requerimento de N: {produtividade_t_ha} t/ha * {config.REQUERIMENTO_N_POR_TONELADA} = {requerimento} kg/ha")

    if config.METODOLOGIA['parametros_globais']['considerar_mo_no_nitrogenio']:
        mo_percent = analise.mo / 10
        suprimento = mo_percent * config.N_MINERALIZADO_MO
        log.append(f"Suprimento de N pela MO: {mo_percent:.2f}% * {config.N_MINERALIZADO_MO} = {suprimento} kg/ha")
    else:
        suprimento = 0
        log.append("Suprimento de N pela MO desconsiderado (configuração).")

    necessidade_liquida = max(0, requerimento - suprimento)
    log.append(f"Necessidade líquida: {necessidade_liquida} kg/ha")

    fator_eficiencia = config.METODOLOGIA['parametros_globais']['fator_eficiencia_n']
    necessidade_eficiencia = necessidade_liquida * fator_eficiencia
    log.append(f"Aplicando fator de eficiência {fator_eficiencia}: {necessidade_eficiencia} kg/ha")

    n_cobertura = necessidade_eficiencia - config.N_PLANTIO_MILHO
    if n_cobertura < 0:
        n_cobertura = 0
        log.append("N de cobertura negativo, ajustado para 0.")
    else:
        log.append(f"Subtraindo N do plantio ({config.N_PLANTIO_MILHO}): {n_cobertura} kg/ha")

    if historico_soja:
        n_cobertura *= config.FATOR_SOJA_HISTORICO
        log.append(f"Histórico com soja: aplicando fator {config.FATOR_SOJA_HISTORICO} -> {n_cobertura} kg/ha")
    if plantio_direto_primeiros_anos:
        n_cobertura *= config.FATOR_PLANTIO_DIRETO
        log.append(f"Primeiros anos de plantio direto: aplicando fator {config.FATOR_PLANTIO_DIRETO} -> {n_cobertura} kg/ha")

    n_arred = arredondar_dose(n_cobertura)
    log.append(f"Dose final de N (cobertura): {n_arred} kg/ha")
    return n_arred

def calcular_k_manutencao(cultura: Cultura, produtividade_t_ha: float, classe_k: str,
                          log: Optional[List[str]] = None) -> float:
    if log is None:
        log = []
    if cultura == Cultura.MILHO:
        taxa = config.EXPORTACAO_K2O['milho']
        nome_cultura = "milho"
    elif cultura == Cultura.SOJA:
        taxa = config.EXPORTACAO_K2O['soja']
        nome_cultura = "soja"
    else:
        log.append("Cultura não reconhecida para K, manutenção = 0")
        return 0.0

    dose_base = taxa * produtividade_t_ha
    log.append(f"Exportação de K2O para {nome_cultura}: {taxa} kg/t * {produtividade_t_ha} t/ha = {dose_base} kg/ha")
    fator = config.FATOR_K_MANUTENCAO.get(classe_k, 1.0)
    if fator < 1.0:
        log.append(f"Classe de K '{classe_k}' → fator de manutenção {fator}")
    dose_final = dose_base * fator
    return dose_final

def calcular_npk(analise: AnaliseSolo, cultura: Cultura, sistema: Sistema,
                 produtividade_t_ha: float, historico_soja: bool = False,
                 plantio_direto_primeiros_anos: bool = False,
                 log: Optional[List[str]] = None) -> dict:
    if log is None:
        log = []
    if cultura == Cultura.MILHO:
        log.append("=== Cálculo para MILHO ===")
        n_final = calcular_n_milho(analise, produtividade_t_ha, historico_soja, plantio_direto_primeiros_anos, log)

        # P
        classe_p = interp.classificar_p(analise.p_melich, analise.argila)
        log.append(f"Classe de P: {classe_p} (P = {analise.p_melich}, argila = {analise.argila}%)")
        dose_p_corretiva = 0
        tabela_p = config.DOSE_P_CORRETIVO_IRRIGADO if sistema == Sistema.IRRIGADO else config.DOSE_P_CORRETIVO
        for (amin, amax), doses in tabela_p.items():
            if amin <= analise.argila <= amax:
                dose_p_corretiva = doses.get(classe_p, 0)
                break
        log.append(f"Dose corretiva de P2O5: {dose_p_corretiva} kg/ha")

        # Manutenção de P
        if cultura == Cultura.MILHO:
            extracao_p = 5.8
        elif cultura == Cultura.SOJA:
            extracao_p = 15.6
        else:
            extracao_p = 0
        p_manutencao = extracao_p * produtividade_t_ha
        log.append(f"Manutenção de P2O5 (extração): {extracao_p} * {produtividade_t_ha} = {p_manutencao} kg/ha")
        p2o5_final = dose_p_corretiva + p_manutencao
        p2o5_final = arredondar_dose(p2o5_final)
        log.append(f"Dose total de P2O5: {p2o5_final} kg/ha")

        # K
        classe_k = interp.classificar_k(analise.k_melich, analise.ctc)
        log.append(f"Classe de K: {classe_k} (K = {analise.k_melich})")
        dose_k_corretiva = 0
        for ctc_min, ctc_max, classe, dose in config.DOSE_K_CORRETIVO:
            if ctc_min <= analise.ctc < ctc_max and classe == classe_k:
                dose_k_corretiva = dose
                break
        log.append(f"Dose corretiva de K2O: {dose_k_corretiva} kg/ha")
        k_manutencao = calcular_k_manutencao(cultura, produtividade_t_ha, classe_k, log)
        k2o_final = dose_k_corretiva + k_manutencao
        p2o5_final = round(p2o5_final, 1) # Arredondamento intermediário para evitar erros de precisão
        k2o_final = arredondar_dose(k2o_final)
        log.append(f"Dose total de K2O: {k2o_final} kg/ha")

        return {
            'N': n_final,
            'P2O5': p2o5_final,
            'K2O': k2o_final
        }
    else:
        log.append("Cultura diferente de milho: NPK não calculado (apenas corretivos).")
        return {'N': 0, 'P2O5': 0, 'K2O': 0}

def calcular_micronutrientes(analise: AnaliseSolo, log: Optional[List[str]] = None) -> dict:
    if log is None:
        log = []
    recomendacoes = {}
    for elem in ['Zn', 'Cu', 'B', 'Mn', 'Fe', 'S']:
        valor = getattr(analise, elem.lower(), None)
        if valor is None:
            continue
        classe = interp.classificar_micronutriente(valor, elem)
        dose = config.REC_MICRO[elem].get(classe.lower(), 0)
        if dose > 0:
            recomendacoes[elem] = dose
            log.append(f"{elem}: teor {valor} mg/dm³ → classe {classe} → dose {dose} kg/ha")
        else:
            log.append(f"{elem}: teor {valor} mg/dm³ → classe {classe} → dispensado")
    return recomendacoes

def recomendar_tudo(analise: AnaliseSolo, cultura: Cultura, sistema: Sistema,
                    produtividade_t_ha: float, historico_soja: bool = False,
                    plantio_direto_primeiros_anos: bool = False,
                    prnt: float = 100, tipo_pastagem: str = 'padrao') -> Recomendacao:
    log = []
    log.append(f"=== RECOMENDAÇÃO PARA AMOSTRA ===")
    log.append(f"Cultura: {cultura.value}, Sistema: {sistema.value}, Produtividade: {produtividade_t_ha} t/ha")
    if historico_soja:
        log.append("Histórico: soja no último ano.")
    if plantio_direto_primeiros_anos:
        log.append("Primeiros anos de plantio direto.")

    calagem = calcular_calagem(analise, cultura, sistema, prnt, tipo_pastagem, log)
    gesso = calcular_gessagem(analise, cultura, log)
    npk = calcular_npk(analise, cultura, sistema, produtividade_t_ha,
                       historico_soja, plantio_direto_primeiros_anos, log)
    micro = calcular_micronutrientes(analise, log)

    # Verificação de magnésio
    mg_msg = verificar_magnesio(analise, log)
    if mg_msg:
        micro['Mg_obs'] = mg_msg

    # Verificar limites de sulco
    if npk['P2O5'] > config.METODOLOGIA['parametros_globais']['limite_maximo_p2o5_sulco']:
        msg = f"Dose de P₂O₅ ({npk['P2O5']} kg/ha) excede o limite recomendado para aplicação no sulco ({config.METODOLOGIA['parametros_globais']['limite_maximo_p2o5_sulco']} kg/ha). Considere parcelar ou aplicar a lanço."
        micro['P_obs'] = msg
        log.append(msg)
    if npk['K2O'] > config.METODOLOGIA['parametros_globais']['limite_maximo_k2o_sulco']:
        msg = f"Dose de K₂O ({npk['K2O']} kg/ha) excede o limite recomendado para aplicação no sulco ({config.METODOLOGIA['parametros_globais']['limite_maximo_k2o_sulco']} kg/ha). Considere parcelar ou aplicar a lanço."
        micro['K_obs'] = msg
        log.append(msg)

    log.append("=== FIM DA RECOMENDAÇÃO ===")

    return Recomendacao(
        calagem_t_ha=calagem,
        gesso_kg_ha=gesso,
        n_kg_ha=npk['N'],
        p2o5_kg_ha=npk['P2O5'],
        k2o_kg_ha=npk['K2O'],
        micronutrientes=micro,
        log=log
    )