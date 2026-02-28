from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import pandas as pd
import io
import os
import json
import logging
from datetime import datetime
from weasyprint import HTML

from adubacao import config
from adubacao.models import AnaliseSolo, Cultura, Sistema
from adubacao.calculators import recomendar_tudo
from adubacao.interpretation import (
    classificar_p,
    classificar_k,
    classificar_micronutriente,
    interpretar_ph
)
from adubacao.exporters import gerar_excel_bytes

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'chave-secreta-para-flash'

# Carregar base de fertilizantes
with open('fertilizantes.json', 'r', encoding='utf-8') as f:
    FERTILIZANTES_DB = json.load(f)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_csv_robust(file):
    content = file.read()
    file.seek(0)
    attempts = [ (',', '.'), (';', ','), ('\t', '.'), (',', ',') ]
    from io import StringIO
    for sep, decimal in attempts:
        try:
            for encoding in ['utf-8', 'utf-8-sig', 'latin1']:
                try:
                    decoded = content.decode(encoding)
                    df = pd.read_csv(StringIO(decoded), sep=sep, decimal=decimal)
                    if not df.empty:
                        return df
                except:
                    continue
        except:
            continue
    raise ValueError("Não foi possível ler o arquivo CSV. Verifique o formato e encoding.")

def parse_upload_first_line(file):
    ext = file.filename.rsplit('.', 1)[1].lower()
    try:
        if ext == 'csv':
            df = read_csv_robust(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        raise ValueError(f"Erro ao ler arquivo: {e}")
    if df.empty:
        return {}
    data = df.iloc[0].to_dict()
    synonyms = {
        'ph_h2o': ['ph', 'ph agua', 'ph água', 'ph_h2o', 'ph_cacl2'],
        'p': ['p', 'fosforo', 'fósforo', 'p_melich'],
        'k': ['k', 'potassio', 'potássio', 'k_melich'],
        'ca': ['ca', 'calcio', 'cálcio'],
        'mg': ['mg', 'magnesio', 'magnésio'],
        'al': ['al', 'aluminio', 'alumínio'],
        'h_al': ['h_al', 'h+al', 'acidez potencial'],
        'mo': ['mo', 'materia organica', 'matéria orgânica'],
        'argila': ['argila', 'argila %'],
        'zn': ['zn', 'zinco'],
        'cu': ['cu', 'cobre'],
        'b': ['b', 'boro'],
        'mn': ['mn', 'manganes', 'manganês'],
        'fe': ['fe', 'ferro'],
        's': ['s', 'enxofre'],
    }
    mapping = {}
    for field, names in synonyms.items():
        for name in names:
            mapping[name] = field
    clean = {}
    for col_name, value in data.items():
        normalized = col_name.strip().lower()
        normalized = normalized.replace('(', '').replace(')', '').replace(' ', '_')
        if normalized in mapping:
            field = mapping[normalized]
        else:
            simple = normalized.split('(')[0].strip().rstrip('_')
            if simple in mapping:
                field = mapping[simple]
            else:
                field = normalized
        try:
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
                if value == '':
                    val = None
                else:
                    val = float(value)
            else:
                val = value
        except:
            val = value
        clean[field] = val
    if 'cultura' not in clean:
        clean['cultura'] = 'milho'
    if 'sistema' not in clean:
        clean['sistema'] = 'sequeiro'
    return clean

def processar_lote(file):
    ext = file.filename.rsplit('.', 1)[1].lower()
    try:
        if ext == 'csv':
            df = read_csv_robust(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        raise ValueError(f"Erro ao ler arquivo: {e}")
    synonyms = {
        'ph_h2o': ['ph', 'ph agua', 'ph água', 'ph_h2o', 'ph_cacl2'],
        'p': ['p', 'fosforo', 'fósforo', 'p_melich'],
        'k': ['k', 'potassio', 'potássio', 'k_melich'],
        'ca': ['ca', 'calcio', 'cálcio'],
        'mg': ['mg', 'magnesio', 'magnésio'],
        'al': ['al', 'aluminio', 'alumínio'],
        'h_al': ['h_al', 'h+al', 'acidez potencial'],
        'mo': ['mo', 'materia organica', 'matéria orgânica'],
        'argila': ['argila', 'argila %'],
        'zn': ['zn', 'zinco'],
        'cu': ['cu', 'cobre'],
        'b': ['b', 'boro'],
        'mn': ['mn', 'manganes', 'manganês'],
        'fe': ['fe', 'ferro'],
        's': ['s', 'enxofre'],
    }
    mapping = {}
    for field, names in synonyms.items():
        for name in names:
            mapping[name] = field
    resultados = []
    for idx, row in df.iterrows():
        dados_linha = row.to_dict()
        clean = {}
        for col_name, value in dados_linha.items():
            normalized = col_name.strip().lower()
            normalized = normalized.replace('(', '').replace(')', '').replace(' ', '_')
            if normalized in mapping:
                field = mapping[normalized]
            else:
                simple = normalized.split('(')[0].strip().rstrip('_')
                if simple in mapping:
                    field = mapping[simple]
                else:
                    field = normalized
            try:
                if pd.isna(value):
                    val = None
                else:
                    val = float(str(value).replace(',', '.'))
            except:
                val = value
            clean[field] = val
        cultura = Cultura.MILHO
        sistema = Sistema.SEQUEIRO
        produtividade = 9
        historico_soja = False
        prnt = 100
        if 'cultura' in clean and clean['cultura'] in ['milho', 'soja', 'pastagem']:
            cultura = Cultura(clean['cultura'])
        if 'sistema' in clean and clean['sistema'] in ['sequeiro', 'irrigado']:
            sistema = Sistema(clean['sistema'])
        if 'produtividade' in clean and clean['produtividade'] is not None:
            produtividade = float(clean['produtividade'])
        if 'historico_soja' in clean and clean['historico_soja'] in [1, '1', 'sim', 'true']:
            historico_soja = True
        if 'prnt' in clean and clean['prnt'] is not None:
            prnt = float(clean['prnt'])
        analise = AnaliseSolo(
            ph_h2o=clean.get('ph_h2o', 0),
            p_melich=clean.get('p', 0) or clean.get('fosforo', 0),
            k_melich=clean.get('k', 0) or clean.get('potassio', 0),
            ca=clean.get('ca', 0),
            mg=clean.get('mg', 0),
            al=clean.get('al', 0),
            h_al=clean.get('h_al', 0) or clean.get('h+al', 0),
            mo=clean.get('mo', 0) or clean.get('materia_organica', 0),
            argila=clean.get('argila', 0),
            zn=clean.get('zn', None),
            cu=clean.get('cu', None),
            b=clean.get('b', None),
            mn=clean.get('mn', None),
            fe=clean.get('fe', None),
            s=clean.get('s', None),
        )
        recomendacao = recomendar_tudo(analise, cultura, sistema, produtividade, historico_soja, prnt=prnt)
        rec_dict = {
            'Amostra': idx + 1,
            'pH': analise.ph_h2o,
            'P (mg/dm³)': analise.p_melich,
            'K (mg/dm³)': analise.k_melich,
            'Argila (%)': analise.argila,
            'Classe P': classificar_p(analise.p_melich, analise.argila),
            'Classe K': classificar_k(analise.k_melich, analise.ctc),
            'Calagem (t/ha)': recomendacao.calagem_t_ha or 0,
            'Gesso (kg/ha)': recomendacao.gesso_kg_ha or 0,
            'N (kg/ha)': recomendacao.n_kg_ha or 0,
            'P2O5 (kg/ha)': recomendacao.p2o5_kg_ha or 0,
            'K2O (kg/ha)': recomendacao.k2o_kg_ha or 0,
        }
        for elem in ['Zn', 'Cu', 'B', 'Mn', 'Fe', 'S']:
            valor = getattr(analise, elem.lower())
            if valor is not None:
                rec_dict[f'{elem} (mg/dm³)'] = valor
                rec_dict[f'{elem} classe'] = classificar_micronutriente(valor, elem)
                if elem in recomendacao.micronutrientes:
                    rec_dict[f'{elem} dose (kg/ha)'] = recomendacao.micronutrientes[elem]
        resultados.append(rec_dict)
    df_resultados = pd.DataFrame(resultados)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_resultados.to_excel(writer, sheet_name='Recomendações', index=False)
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='recomendacoes_lote.xlsx')

def to_float(value, default=0.0):
    if value in (None, ''):
        return default
    try:
        return float(value)
    except:
        return default

# ===================== NOVA FUNÇÃO DE RECOMENDAÇÃO =====================
def recomendar_adubacao_plantio(n_nec, p_nec, k_nec, limite_kg_ha=600):
    """
    Recomenda um formulado para suprir P e depois complementa N e K com adubos simples.
    Retorna um dicionário com a recomendação completa ou None se não encontrar opção viável.
    """
    formulados = FERTILIZANTES_DB['adubos_plantio_npk']
    simples = {s['nome']: s for s in FERTILIZANTES_DB['adubos_simples_correcao']}

    melhor_opcao = None
    menor_desvio_apos_complemento = float('inf')
    receita_final = None

    for adubo in formulados:
        # Quantidade para suprir P (limitada pelo máximo)
        qtd_base = (p_nec / adubo['p2o5']) * 100
        if qtd_base > limite_kg_ha:
            continue  # ultrapassa o limite, inviável

        # Nutrientes fornecidos pelo formulado
        n_fornecido = (qtd_base * adubo['n']) / 100
        k_fornecido = (qtd_base * adubo['k2o']) / 100

        # Calcular déficits de N e K
        deficit_n = max(0, n_nec - n_fornecido)
        deficit_k = max(0, k_nec - k_fornecido)

        complementos = []
        n_complementar = 0
        k_complementar = 0

        # Complementar N com ureia (45% N)
        if deficit_n > 0:
            ureia = simples.get('Ureia')
            if ureia:
                qtd_ureia = (deficit_n / ureia['n']) * 100
                complementos.append({
                    'adubo': 'Ureia',
                    'quantidade_kg_ha': round(qtd_ureia, 1),
                    'n': round((qtd_ureia * ureia['n'])/100, 1),
                    'k': 0
                })
                n_complementar = (qtd_ureia * ureia['n']) / 100

        # Complementar K com KCl (60% K2O)
        if deficit_k > 0:
            kcl = simples.get('Cloreto de Potássio (KCl)')
            if kcl:
                qtd_kcl = (deficit_k / kcl['k2o']) * 100
                complementos.append({
                    'adubo': 'KCl',
                    'quantidade_kg_ha': round(qtd_kcl, 1),
                    'n': 0,
                    'k': round((qtd_kcl * kcl['k2o'])/100, 1)
                })
                k_complementar = (qtd_kcl * kcl['k2o']) / 100

        # Totais finais
        n_total = n_fornecido + n_complementar
        p_total = p_nec  # exato por construção
        k_total = k_fornecido + k_complementar

        desvio = abs(n_nec - n_total) + abs(k_nec - k_total)

        if desvio < menor_desvio_apos_complemento:
            menor_desvio_apos_complemento = desvio
            receita_final = {
                'formulado': {
                    'nome': adubo['nome'],
                    'quantidade_kg_ha': round(qtd_base, 0),
                    'n': round(n_fornecido, 1),
                    'p2o5': round((qtd_base * adubo['p2o5'])/100, 1),
                    'k2o': round(k_fornecido, 1)
                },
                'complementos': complementos,
                'totais': {
                    'n': round(n_total, 1),
                    'p2o5': round(p_total, 1),
                    'k2o': round(k_total, 1)
                },
                'desvio': round(desvio, 1)
            }

    return receita_final

# ===================== ROTA PRINCIPAL =====================
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'arquivo' in request.files:
            file = request.files['arquivo']
            if file and allowed_file(file.filename):
                if 'preencher' in request.form:
                    try:
                        dados_upload = parse_upload_first_line(file)
                        return render_template('index.html', dados=dados_upload, calcular=False)
                    except Exception as e:
                        logger.exception("Erro no upload")
                        flash(f'Erro ao processar arquivo: {e}', 'danger')
                        return redirect(url_for('index'))
                elif 'processar_lote' in request.form:
                    try:
                        return processar_lote(file)
                    except Exception as e:
                        logger.exception("Erro no processamento de lote")
                        flash(f'Erro ao processar lote: {e}', 'danger')
                        return redirect(url_for('index'))
            else:
                flash('Tipo de arquivo não permitido. Use CSV ou Excel.', 'warning')
                return redirect(url_for('index'))
        try:
            ph_h2o = to_float(request.form.get('ph_h2o'))
            p = to_float(request.form.get('p'))
            k = to_float(request.form.get('k'))
            ca = to_float(request.form.get('ca'))
            mg = to_float(request.form.get('mg'))
            al = to_float(request.form.get('al'))
            h_al = to_float(request.form.get('h_al'))
            mo = to_float(request.form.get('mo'))
            argila = to_float(request.form.get('argila'))
            zn = to_float(request.form.get('zn'), None) if request.form.get('zn') else None
            cu = to_float(request.form.get('cu'), None) if request.form.get('cu') else None
            b = to_float(request.form.get('b'), None) if request.form.get('b') else None
            mn = to_float(request.form.get('mn'), None) if request.form.get('mn') else None
            fe = to_float(request.form.get('fe'), None) if request.form.get('fe') else None
            s = to_float(request.form.get('s'), None) if request.form.get('s') else None
            cultura_value = request.form.get('cultura')
            sistema_value = request.form.get('sistema')
            if not cultura_value or not sistema_value:
                flash("Selecione cultura e sistema.", "warning")
                return redirect(url_for('index'))
            cultura = Cultura(cultura_value)
            sistema = Sistema(sistema_value)
            produtividade = to_float(request.form.get('produtividade'), 9)
            prnt = to_float(request.form.get('prnt'), 100)
            area = to_float(request.form.get('area'), 1)
            espacamento = to_float(request.form.get('espacamento'), 0.8)
            historico_soja = 'historico_soja' in request.form
            # Captura tipo de pastagem e plantio direto (se vierem do formulário)
            tipo_pastagem = request.form.get('tipo_pastagem', 'padrao')
            plantio_direto = 'plantio_direto' in request.form
            analise = AnaliseSolo(
                ph_h2o=ph_h2o,
                p_melich=p,
                k_melich=k,
                ca=ca,
                mg=mg,
                al=al,
                h_al=h_al,
                mo=mo,
                argila=argila,
                zn=zn,
                cu=cu,
                b=b,
                mn=mn,
                fe=fe,
                s=s,
            )
            recomendacao = recomendar_tudo(
                analise, cultura, sistema, produtividade, historico_soja,
                plantio_direto_primeiros_anos=plantio_direto, prnt=prnt, tipo_pastagem=tipo_pastagem
            )
            classes = {
                'pH': interpretar_ph(analise.ph_h2o),
                'P': classificar_p(analise.p_melich, analise.argila),
                'K': classificar_k(analise.k_melich, analise.ctc),
                'Ca': 'Baixo' if analise.ca < 1.5 else ('Médio' if analise.ca < 3 else 'Alto'),
                'Mg': 'Baixo' if analise.mg < 0.5 else ('Médio' if analise.mg < 1 else 'Alto'),
                'Al': 'Baixo' if analise.al < 0.2 else ('Médio' if analise.al < 0.5 else 'Alto'),
                'MO': 'Baixo' if analise.mo < 20 else ('Médio' if analise.mo < 40 else 'Alto'),
            }
            for elem in ['Zn', 'Cu', 'B', 'Mn', 'Fe', 'S']:
                valor = getattr(analise, elem.lower())
                if valor is not None:
                    classes[elem] = classificar_micronutriente(valor, elem)
            ureia_kg = (recomendacao.n_kg_ha / 0.45) if recomendacao.n_kg_ha else 0
            map_kg = (recomendacao.p2o5_kg_ha / 0.48) if recomendacao.p2o5_kg_ha else 0
            kcl_kg = (recomendacao.k2o_kg_ha / 0.60) if recomendacao.k2o_kg_ha else 0
            area_250m = (250 * espacamento) / 10000
            fert = {
                'ureia_kg_ha': round(ureia_kg, 1),
                'map_kg_ha': round(map_kg, 1),
                'kcl_kg_ha': round(kcl_kg, 1),
                'ureia_total': round(ureia_kg * area, 1),
                'map_total': round(map_kg * area, 1),
                'kcl_total': round(kcl_kg * area, 1),
                'ureia_250m': round(ureia_kg * area_250m, 2),
                'map_250m': round(map_kg * area_250m, 2),
                'kcl_250m': round(kcl_kg * area_250m, 2),
            }
            return render_template('index.html', dados=request.form, analise=analise, cultura=cultura,
                                   sistema=sistema, produtividade=produtividade, historico_soja=historico_soja,
                                   prnt=prnt, area=area, espacamento=espacamento, recomendacao=recomendacao,
                                   classes=classes, fert=fert, calcular=True)
        except Exception as e:
            logger.exception("Erro no processamento do formulário")
            flash(f'Erro nos dados do formulário: {str(e)}', 'danger')
            return redirect(url_for('index'))
    return render_template('index.html', calcular=False, dados={})

@app.route('/download_excel')
def download_excel():
    try:
        args = request.args
        analise = AnaliseSolo(
            ph_h2o=to_float(args.get('ph_h2o')),
            p_melich=to_float(args.get('p')),
            k_melich=to_float(args.get('k')),
            ca=to_float(args.get('ca')),
            mg=to_float(args.get('mg')),
            al=to_float(args.get('al')),
            h_al=to_float(args.get('h_al')),
            mo=to_float(args.get('mo')),
            argila=to_float(args.get('argila')),
            zn=to_float(args.get('zn'), None) if args.get('zn') else None,
            cu=to_float(args.get('cu'), None) if args.get('cu') else None,
            b=to_float(args.get('b'), None) if args.get('b') else None,
            mn=to_float(args.get('mn'), None) if args.get('mn') else None,
            fe=to_float(args.get('fe'), None) if args.get('fe') else None,
            s=to_float(args.get('s'), None) if args.get('s') else None,
        )
        cultura = Cultura(args.get('cultura'))
        sistema = Sistema(args.get('sistema'))
        produtividade = to_float(args.get('produtividade'))
        historico_soja = args.get('historico_soja') == 'True'
        prnt = to_float(args.get('prnt'), 100)
        recomendacao = recomendar_tudo(analise, cultura, sistema, produtividade, historico_soja, prnt=prnt)
        excel_bytes = gerar_excel_bytes(analise, recomendacao, cultura, sistema, produtividade, historico_soja)
        return send_file(io.BytesIO(excel_bytes), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name='recomendacao.xlsx')
    except Exception as e:
        logger.exception("Erro ao gerar Excel")
        return f"Erro ao gerar Excel: {e}", 400

@app.route('/gerar_pdf')
def gerar_pdf():
    try:
        args = request.args
        analise = AnaliseSolo(
            ph_h2o=to_float(args.get('ph_h2o')),
            p_melich=to_float(args.get('p')),
            k_melich=to_float(args.get('k')),
            ca=to_float(args.get('ca')),
            mg=to_float(args.get('mg')),
            al=to_float(args.get('al')),
            h_al=to_float(args.get('h_al')),
            mo=to_float(args.get('mo')),
            argila=to_float(args.get('argila')),
            zn=to_float(args.get('zn'), None) if args.get('zn') else None,
            cu=to_float(args.get('cu'), None) if args.get('cu') else None,
            b=to_float(args.get('b'), None) if args.get('b') else None,
            mn=to_float(args.get('mn'), None) if args.get('mn') else None,
            fe=to_float(args.get('fe'), None) if args.get('fe') else None,
            s=to_float(args.get('s'), None) if args.get('s') else None,
        )
        cultura = Cultura(args.get('cultura'))
        sistema = Sistema(args.get('sistema'))
        produtividade = to_float(args.get('produtividade'))
        historico_soja = args.get('historico_soja') == 'True'
        prnt = to_float(args.get('prnt'), 100)
        area = to_float(args.get('area'), 1)
        espacamento = to_float(args.get('espacamento'), 0.8)
        recomendacao = recomendar_tudo(analise, cultura, sistema, produtividade, historico_soja, prnt=prnt)
        classes = {
            'pH': interpretar_ph(analise.ph_h2o),
            'P': classificar_p(analise.p_melich, analise.argila),
            'K': classificar_k(analise.k_melich, analise.ctc),
            'Ca': 'Baixo' if analise.ca < 1.5 else ('Médio' if analise.ca < 3 else 'Alto'),
            'Mg': 'Baixo' if analise.mg < 0.5 else ('Médio' if analise.mg < 1 else 'Alto'),
            'Al': 'Baixo' if analise.al < 0.2 else ('Médio' if analise.al < 0.5 else 'Alto'),
            'MO': 'Baixo' if analise.mo < 20 else ('Médio' if analise.mo < 40 else 'Alto'),
        }
        for elem in ['Zn', 'Cu', 'B', 'Mn', 'Fe', 'S']:
            valor = getattr(analise, elem.lower())
            if valor is not None:
                classes[elem] = classificar_micronutriente(valor, elem)
        ureia_kg = (recomendacao.n_kg_ha / 0.45) if recomendacao.n_kg_ha else 0
        map_kg = (recomendacao.p2o5_kg_ha / 0.48) if recomendacao.p2o5_kg_ha else 0
        kcl_kg = (recomendacao.k2o_kg_ha / 0.60) if recomendacao.k2o_kg_ha else 0
        fert = {
            'ureia_kg_ha': round(ureia_kg, 1),
            'map_kg_ha': round(map_kg, 1),
            'kcl_kg_ha': round(kcl_kg, 1),
            'ureia_total': round(ureia_kg * area, 1),
            'map_total': round(map_kg * area, 1),
            'kcl_total': round(kcl_kg * area, 1),
        }
        html = render_template('relatorio_pdf.html', analise=analise, cultura=cultura, sistema=sistema,
                               produtividade=produtividade, historico_soja=historico_soja, prnt=prnt,
                               area=area, espacamento=espacamento, recomendacao=recomendacao,
                               classes=classes, fert=fert, now=datetime.now())
        pdf = HTML(string=html).write_pdf()
        return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                         download_name='relatorio_tecnico.pdf')
    except Exception as e:
        logger.exception("Erro ao gerar PDF")
        return f"Erro ao gerar PDF: {e}", 400

# ===================== ROTA DE FORMULAÇÃO (ATUALIZADA) =====================
@app.route('/formulacao', methods=['GET', 'POST'])
def formulacao():
    resultado = None
    if request.method == 'POST':
        try:
            teores = {
                'ureia': config.FERTILIZANTES['Ureia']['N'] / 100,
                'map_n': config.FERTILIZANTES['MAP']['N'] / 100,
                'map_p2o5': config.FERTILIZANTES['MAP']['P2O5'] / 100,
                'kcl': config.FERTILIZANTES['KCl']['K2O'] / 100,
            }

            # MODO 3: Recomendação automática (Cerrado)
            if 'recomendar' in request.form:
                n_nec = to_float(request.form.get('n_nec'))
                p_nec = to_float(request.form.get('p_nec'))
                k_nec = to_float(request.form.get('k_nec'))
                limite = to_float(request.form.get('limite_kg'), 600)

                if n_nec == 0 and p_nec == 0 and k_nec == 0:
                    flash('Preencha pelo menos uma necessidade.', 'danger')
                    return redirect(url_for('formulacao'))

                recomendacao = recomendar_adubacao_plantio(n_nec, p_nec, k_nec, limite)
                if not recomendacao:
                    flash('Nenhuma recomendação viável encontrada. Tente aumentar o limite de kg/ha.', 'warning')
                    return redirect(url_for('formulacao'))

                resultado = {'modo': 'recomendacao', **recomendacao}

            # MODO 1: Calcular quantidades
            elif 'calcular_quantidades' in request.form:
                n_necessario = to_float(request.form.get('n_necessario'))
                p2o5_necessario = to_float(request.form.get('p2o5_necessario'))
                k2o_necessario = to_float(request.form.get('k2o_necessario'))
                formula = request.form.get('formula', '').strip()
                if formula:
                    partes = formula.replace('%', '').split('-')
                    if len(partes) == 3:
                        n_necessario = float(partes[0]) * 10
                        p2o5_necessario = float(partes[1]) * 10
                        k2o_necessario = float(partes[2]) * 10
                    else:
                        flash('Formato de fórmula inválido. Use N-P2O5-K2O (ex: 08-28-16)', 'danger')
                        return redirect(url_for('formulacao'))
                if n_necessario is None or p2o5_necessario is None or k2o_necessario is None:
                    flash('Preencha a fórmula ou os valores de N, P2O5 e K2O.', 'danger')
                    return redirect(url_for('formulacao'))
                map_kg = p2o5_necessario / teores['map_p2o5'] if p2o5_necessario else 0
                kcl_kg = k2o_necessario / teores['kcl'] if k2o_necessario else 0
                n_fornecido_map = map_kg * teores['map_n']
                n_restante = max(0, n_necessario - n_fornecido_map)
                ureia_kg = n_restante / teores['ureia'] if n_restante else 0
                resultado = {
                    'modo': 'quantidades',
                    'ureia_kg': round(ureia_kg, 2),
                    'map_kg': round(map_kg, 2),
                    'kcl_kg': round(kcl_kg, 2),
                    'n_total': round(n_fornecido_map + ureia_kg * teores['ureia'], 2),
                    'p2o5_total': round(map_kg * teores['map_p2o5'], 2),
                    'k2o_total': round(kcl_kg * teores['kcl'], 2),
                }

            # MODO 2: Calcular fórmula
            elif 'calcular_formula' in request.form:
                ureia_kg = to_float(request.form.get('ureia_kg'))
                map_kg = to_float(request.form.get('map_kg'))
                kcl_kg = to_float(request.form.get('kcl_kg'))
                if ureia_kg == 0 and map_kg == 0 and kcl_kg == 0:
                    flash('Pelo menos um fertilizante deve ter quantidade > 0.', 'danger')
                    return redirect(url_for('formulacao'))
                n_total = ureia_kg * teores['ureia'] + map_kg * teores['map_n']
                p2o5_total = map_kg * teores['map_p2o5']
                k2o_total = kcl_kg * teores['kcl']
                massa_total = ureia_kg + map_kg + kcl_kg
                n_perc = (n_total / massa_total) * 100
                p_perc = (p2o5_total / massa_total) * 100
                k_perc = (k2o_total / massa_total) * 100
                resultado = {
                    'modo': 'formula',
                    'n_perc': round(n_perc, 2),
                    'p_perc': round(p_perc, 2),
                    'k_perc': round(k_perc, 2),
                    'n_total': round(n_total, 2),
                    'p2o5_total': round(p2o5_total, 2),
                    'k2o_total': round(k2o_total, 2),
                    'massa_total': round(massa_total, 2),
                    'ureia_kg': round(ureia_kg, 2),
                    'map_kg': round(map_kg, 2),
                    'kcl_kg': round(kcl_kg, 2),
                }

        except Exception as e:
            logger.exception("Erro na formulação")
            flash(f'Erro no cálculo: {e}', 'danger')
            return redirect(url_for('formulacao'))

    return render_template('formulacao.html', resultado=resultado)

if __name__ == '__main__':
    app.run(debug=True)