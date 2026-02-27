from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import pandas as pd
import io
import os
from datetime import datetime
from weasyprint import HTML

from adubacao.models import AnaliseSolo, Cultura, Sistema
from adubacao.calculators import recomendar_tudo
from adubacao.interpretation import (
    classificar_p,
    classificar_k,
    classificar_micronutriente,
    interpretar_ph
)
from adubacao.exporters import gerar_excel_bytes

app = Flask(__name__)
app.secret_key = 'chave-secreta-para-flash'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def read_csv_robust(file):
    """Tenta ler CSV com diferentes separadores e decimais."""
    content = file.read()
    file.seek(0)

    attempts = [
        (',', '.'),   # vírgula como separador, ponto decimal
        (';', ','),   # ponto e vírgula como separador, vírgula decimal
        ('\t', '.'),  # tab como separador, ponto decimal
        (',', ','),   # vírgula como separador e decimal (caso incomum)
    ]

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
    """Lê a primeira linha do arquivo e retorna um dicionário com os dados (para preencher o formulário)."""
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

    # Valores padrão para cultura e sistema (caso não existam no arquivo)
    if 'cultura' not in clean:
        clean['cultura'] = 'milho'
    if 'sistema' not in clean:
        clean['sistema'] = 'sequeiro'

    return clean


def processar_lote(file):
    """Processa todas as linhas do arquivo e retorna um Excel com as recomendações."""
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

        # Valores padrão (podem vir do formulário ou de colunas)
        cultura = Cultura.MILHO
        sistema = Sistema.SEQUEIRO
        produtividade = 9
        historico_soja = False
        prnt = 100

        # Se houver colunas específicas, usa
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

        recomendacao = recomendar_tudo(analise, cultura, sistema, produtividade, historico_soja, prnt)

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

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='recomendacoes_lote.xlsx'
    )


def to_float(value, default=0.0):
    if value in (None, ''):
        return default
    try:
        return float(value)
    except:
        return default


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # =========================
        # UPLOAD DE ARQUIVO - duas ações
        # =========================
        if 'arquivo' in request.files:
            file = request.files['arquivo']
            if file and allowed_file(file.filename):
                # Verifica qual botão foi clicado
                if 'preencher' in request.form:  # Botão "Enviar e preencher"
                    try:
                        dados_upload = parse_upload_first_line(file)
                        return render_template(
                            'index.html',
                            dados=dados_upload,
                            calcular=False
                        )
                    except Exception as e:
                        flash(f'Erro ao processar arquivo: {e}', 'danger')
                        return redirect(url_for('index'))
                elif 'processar_lote' in request.form:  # Botão "Processar lote"
                    try:
                        return processar_lote(file)
                    except Exception as e:
                        flash(f'Erro ao processar lote: {e}', 'danger')
                        return redirect(url_for('index'))
            else:
                flash('Tipo de arquivo não permitido. Use CSV ou Excel.', 'warning')
                return redirect(url_for('index'))

        # =========================
        # FORMULÁRIO MANUAL (uma amostra)
        # =========================
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

            produtividade = to_float(request.form.get('produtividade'))
            prnt = to_float(request.form.get('prnt'), 100)
            area = to_float(request.form.get('area'), 1)
            espacamento = to_float(request.form.get('espacamento'), 0.8)

            historico_soja = 'historico_soja' in request.form

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
                analise,
                cultura,
                sistema,
                produtividade,
                historico_soja,
                prnt
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

            return render_template(
                'index.html',
                dados=request.form,
                analise=analise,
                cultura=cultura,
                sistema=sistema,
                produtividade=produtividade,
                historico_soja=historico_soja,
                prnt=prnt,
                area=area,
                espacamento=espacamento,
                recomendacao=recomendacao,
                classes=classes,
                fert=fert,
                calcular=True
            )

        except Exception as e:
            return f"ERRO REAL: {e}"

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

        recomendacao = recomendar_tudo(analise, cultura, sistema, produtividade, historico_soja, prnt)

        excel_bytes = gerar_excel_bytes(analise, recomendacao, cultura, sistema, produtividade, historico_soja)

        return send_file(
            io.BytesIO(excel_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='recomendacao.xlsx'
        )

    except Exception as e:
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

        recomendacao = recomendar_tudo(analise, cultura, sistema, produtividade, historico_soja, prnt)

        # Classificações
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

        # Fertilizantes
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

        # Renderiza o template do relatório
        html = render_template(
            'relatorio_pdf.html',
            analise=analise,
            cultura=cultura,
            sistema=sistema,
            produtividade=produtividade,
            historico_soja=historico_soja,
            prnt=prnt,
            area=area,
            espacamento=espacamento,
            recomendacao=recomendacao,
            classes=classes,
            fert=fert,
            now=datetime.now()
        )

        pdf = HTML(string=html).write_pdf()

        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='relatorio_tecnico.pdf'
        )

    except Exception as e:
        return f"Erro ao gerar PDF: {e}", 400


if __name__ == '__main__':
    app.run(debug=True)