# adubacao/cli.py
import argparse
import csv
from .models import AnaliseSolo, Cultura, Sistema
from .calculators import recomendar_tudo
from .exporters import gerar_excel

def ler_csv(arquivo):
    """Lê dados de análise de solo de um arquivo CSV com cabeçalho."""
    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Converte tipos
            return AnaliseSolo(
                ph_ph_H2O=float(row['ph_ph_H2O']),
                p_melich=float(row['p_melich']),
                k_melich=float(row['k_melich']),
                ca=float(row['ca']),
                mg=float(row['mg']),
                al=float(row['al']),
                h_al=float(row['h_al']),
                mo=float(row['mo']),
                argila=float(row['argila']),
                zn=float(row.get('zn', 0)) or None,
                cu=float(row.get('cu', 0)) or None,
                b=float(row.get('b', 0)) or None,
                mn=float(row.get('mn', 0)) or None,
                fe=float(row.get('fe', 0)) or None,
            )

def main():
    parser = argparse.ArgumentParser(description='Calculadora de adubação para o Cerrado')
    parser.add_argument('--cultura', type=str, required=True, choices=['milho', 'soja', 'pastagem'],
                        help='Cultura alvo')
    parser.add_argument('--sistema', type=str, default='sequeiro', choices=['sequeiro', 'irrigado'],
                        help='Sistema de cultivo')
    parser.add_argument('--produtividade', type=float, required=True,
                        help='Produtividade esperada (t/ha)')
    parser.add_argument('--historico-soja', action='store_true',
                        help='Indica se a área teve soja no último ano')
    parser.add_argument('--prnt', type=float, default=100,
                        help='PRNT do calcário (padrão 100)')
    parser.add_argument('--arquivo', type=str, required=True,
                        help='Arquivo CSV com os dados da análise de solo')
    parser.add_argument('--saida', type=str, default='recomendacao.xlsx',
                        help='Nome do arquivo Excel de saída')

    args = parser.parse_args()

    # Ler análise
    try:
        analise = ler_csv(args.arquivo)
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        return

    cultura = Cultura(args.cultura)
    sistema = Sistema(args.sistema)

    # Calcular
    rec = recomendar_tudo(
        analise=analise,
        cultura=cultura,
        sistema=sistema,
        produtividade_t_ha=args.produtividade,
        historico_soja=args.historico_soja,
        prnt=args.prnt
    )

    # Gerar Excel
    gerar_excel(analise, rec, cultura, sistema, args.produtividade, args.historico_soja, args.saida)

if __name__ == '__main__':
    main()