# adubacao/exporters.py
import pandas as pd
import io
from .models import AnaliseSolo, Recomendacao, Cultura, Sistema
from .interpretation import classificar_p, classificar_k, classificar_micronutriente, interpretar_ph

def gerar_excel_bytes(analise: AnaliseSolo, recomendacao: Recomendacao,
                      cultura: Cultura, sistema: Sistema,
                      produtividade: float, historico_soja: bool) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Dados de entrada
        dados_entrada = [
            ['Parâmetro', 'Valor', 'Unidade'],
            ['pH (água)', analise.ph_h2o, ''],
            ['Fósforo (P)', analise.p_melich, 'mg/dm³'],
            ['Potássio (K)', analise.k_melich, 'mg/dm³'],
            ['Cálcio (Ca)', analise.ca, 'cmolc/dm³'],
            ['Magnésio (Mg)', analise.mg, 'cmolc/dm³'],
            ['Alumínio (Al)', analise.al, 'cmolc/dm³'],
            ['H+Al', analise.h_al, 'cmolc/dm³'],
            ['Matéria orgânica', analise.mo, 'g/dm³'],
            ['Argila', analise.argila, '%'],
            ['CTC', round(analise.ctc, 2), 'cmolc/dm³'],
            ['Zinco (Zn)', analise.zn, 'mg/dm³'],
            ['Cobre (Cu)', analise.cu, 'mg/dm³'],
            ['Boro (B)', analise.b, 'mg/dm³'],
            ['Manganês (Mn)', analise.mn, 'mg/dm³'],
            ['Ferro (Fe)', analise.fe, 'mg/dm³'],
            ['Enxofre (S)', analise.s, 'mg/dm³'],
            ['Cultura', cultura.value, ''],
            ['Sistema', sistema.value, ''],
            ['Produtividade', produtividade, 't/ha'],
            ['Histórico soja', 'Sim' if historico_soja else 'Não', ''],
        ]
        df_entrada = pd.DataFrame(dados_entrada[1:], columns=dados_entrada[0])
        df_entrada.to_excel(writer, sheet_name='Dados de Entrada', index=False)

        # Classificação
        classificacao = [
            ['Nutriente', 'Valor', 'Classe'],
            ['pH', analise.ph_h2o, interpretar_ph(analise.ph_h2o)],
            ['Fósforo', analise.p_melich, classificar_p(analise.p_melich, analise.argila)],
            ['Potássio', analise.k_melich, classificar_k(analise.k_melich, analise.ctc)],
            ['Cálcio', analise.ca, 'Baixo' if analise.ca < 1.5 else ('Médio' if analise.ca < 3 else 'Alto')],
            ['Magnésio', analise.mg, 'Baixo' if analise.mg < 0.5 else ('Médio' if analise.mg < 1 else 'Alto')],
            ['Alumínio', analise.al, 'Baixo' if analise.al < 0.2 else ('Médio' if analise.al < 0.5 else 'Alto')],
            ['Matéria orgânica', analise.mo, 'Baixo' if analise.mo < 20 else ('Médio' if analise.mo < 40 else 'Alto')],
        ]
        for elem in ['Zn', 'Cu', 'B', 'Mn', 'Fe', 'S']:
            valor = getattr(analise, elem.lower())
            if valor is not None:
                classificacao.append([elem, valor, classificar_micronutriente(valor, elem)])
        df_class = pd.DataFrame(classificacao[1:], columns=classificacao[0])
        df_class.to_excel(writer, sheet_name='Classificação', index=False)

        # Recomendações
        rec_data = [
            ['Prática', 'Dose'],
            ['Calagem (t/ha)', recomendacao.calagem_t_ha if recomendacao.calagem_t_ha else 0],
            ['Gesso (kg/ha)', recomendacao.gesso_kg_ha if recomendacao.gesso_kg_ha else 0],
            ['Nitrogênio (N) (kg/ha)', recomendacao.n_kg_ha or 0],
            ['Fósforo (P₂O₅) (kg/ha)', recomendacao.p2o5_kg_ha or 0],
            ['Potássio (K₂O) (kg/ha)', recomendacao.k2o_kg_ha or 0],
        ]
        for elem, dose in recomendacao.micronutrientes.items():
            rec_data.append([f'{elem} (kg/ha)', dose])

        df_rec = pd.DataFrame(rec_data[1:], columns=rec_data[0])
        df_rec.to_excel(writer, sheet_name='Recomendações', index=False)

        # Fertilizantes sugeridos
        fert_data = [['Nutriente', 'Fertilizante', 'Teor (%)', 'Quantidade (kg/ha)']]
        if recomendacao.n_kg_ha:
            qtd = recomendacao.n_kg_ha / 0.45
            fert_data.append(['N', 'Ureia', 45, round(qtd, 1)])
        if recomendacao.p2o5_kg_ha:
            qtd = recomendacao.p2o5_kg_ha / 0.48
            fert_data.append(['P₂O₅', 'MAP', 48, round(qtd, 1)])
        if recomendacao.k2o_kg_ha:
            qtd = recomendacao.k2o_kg_ha / 0.60
            fert_data.append(['K₂O', 'KCl', 60, round(qtd, 1)])
        df_fert = pd.DataFrame(fert_data[1:], columns=fert_data[0])
        df_fert.to_excel(writer, sheet_name='Fertilizantes', index=False)

    output.seek(0)
    return output.getvalue()