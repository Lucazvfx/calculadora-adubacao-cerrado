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
            elif p <= ad:
                return "Adequado"
            else:
                return "Alto"
    return "Argila fora da faixa"

def classificar_k(k: float, ctc: float) -> str:
    """
    Classifica o potássio conforme a Tabela 5 do manual.
    Retorna a classe (Baixo, Médio, Adequado, Alto).
    """
    if ctc < 4.0:
        if k <= 15:
            return "Baixo"
        elif k <= 30:
            return "Médio"
        elif k <= 40:
            return "Adequado"
        else:
            return "Alto"
    else:  # CTC >= 4.0
        if k <= 25:
            return "Baixo"
        elif k <= 50:
            return "Médio"
        elif k <= 80:
            return "Adequado"
        else:
            return "Alto"

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