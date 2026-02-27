# adubacao/interpretation.py
from . import config

def classificar_p(p: float, argila: float) -> str:
    for (amin, amax, mb, ba, me, ad) in config.LIMITES_P:
        if amin <= argila <= amax:
            if p <= mb:
                return "Muito baixo"
            elif p <= ba:
                return "Baixo"
            elif p <= me:
                return "Médio"
            else:
                return "Adequado"
    return "Argila fora da faixa"

def classificar_k(k: float, ctc: float) -> str:
    for (ctc_min, ctc_max, baixo_max, medio_max, adequado_max, _) in config.LIMITES_K:
        if ctc_min <= ctc < ctc_max:
            if k <= baixo_max:
                return "Baixo"
            elif k <= medio_max:
                return "Médio"
            elif k <= adequado_max:
                return "Adequado"
            else:
                return "Alto"
    return "CTC fora da faixa"

def classificar_micronutriente(valor: float, elemento: str) -> str:
    limites = config.LIMITES_MICRO.get(elemento)
    if not limites:
        return "Desconhecido"
    if valor < limites['baixo']:
        return "Baixo"
    elif valor < limites['medio']:
        return "Médio"
    else:
        return "Alto"

def interpretar_ph(ph: float) -> str:
    if ph < 5.0:
        return "Acidez alta"
    elif ph < 6.0:
        return "Acidez média"
    else:
        return "Acidez baixa/adequada"