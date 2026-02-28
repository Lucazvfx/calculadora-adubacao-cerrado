# mistura.py
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from scipy.optimize import lsq_linear
from fertilizante import Fertilizante

@dataclass
class ResultadoMistura:
    """Resultado do cálculo da mistura."""
    sucesso: bool
    quantidades: Dict[str, float] = field(default_factory=dict)  # kg por tonelada
    formula_final: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # N, P2O5, K2O em %
    inerte_kg: float = 0.0
    erro_nutrientes: float = 0.0  # erro percentual médio
    custo_tonelada: float = 0.0
    custo_kg: float = 0.0
    mensagem: str = ""


class Mistura:
    """
    Calcula a combinação ótima de fertilizantes para atingir uma meta nutricional.

    A meta pode ser expressa em:
        - kg/ha de N, P2O5, K2O (convertidos internamente para kg por tonelada)
        - fórmula percentual desejada (ex: 08-28-16)
    """

    def __init__(self, fertilizantes: List[Fertilizante]):
        """
        Inicializa a mistura com a lista de fertilizantes disponíveis.

        Args:
            fertilizantes: lista de objetos Fertilizante
        """
        self.fertilizantes = fertilizantes
        self._validar_fertilizantes()

    def _validar_fertilizantes(self):
        """Verifica se há pelo menos um fertilizante com cada nutriente."""
        tem_n = any(f.n > 0 for f in self.fertilizantes)
        tem_p = any(f.p2o5 > 0 for f in self.fertilizantes)
        tem_k = any(f.k2o > 0 for f in self.fertilizantes)
        if not (tem_n and tem_p and tem_k):
            raise ValueError("É necessário pelo menos um fertilizante com N, um com P2O5 e um com K2O.")

    def _meta_para_nutrientes(self,
                              meta_n: Optional[float] = None,
                              meta_p2o5: Optional[float] = None,
                              meta_k2o: Optional[float] = None,
                              formula: Optional[str] = None,
                              eficiencia_n: float = 100.0) -> Tuple[float, float, float]:
        """
        Converte a meta fornecida em valores de N, P2O5, K2O em kg por tonelada.
        Se a meta for uma fórmula percentual, converte para kg/t considerando que
        a mistura final tem 1000 kg.
        A eficiência do N é aplicada: necessidade_real = necessidade_meta * (100 / eficiencia)
        """
        if formula is not None:
            # formato esperado: "08-28-16" ou "8-28-16"
            partes = formula.replace('%', '').strip().split('-')
            if len(partes) != 3:
                raise ValueError("Fórmula deve estar no formato N-P2O5-K2O (ex: 08-28-16)")
            n = float(partes[0]) * 10  # converte % para kg/t
            p = float(partes[1]) * 10
            k = float(partes[2]) * 10
        else:
            if meta_n is None or meta_p2o5 is None or meta_k2o is None:
                raise ValueError("Forneça meta_n, meta_p2o5, meta_k2o OU formula.")
            n = meta_n
            p = meta_p2o5
            k = meta_k2o

        # Ajusta pela eficiência do N (apenas para N)
        if eficiencia_n != 100.0:
            n = n * (100.0 / eficiencia_n)

        return n, p, k

    def _construir_matriz(self) -> Tuple[np.ndarray, List[str]]:
        """
        Constrói a matriz A onde cada coluna representa um fertilizante e cada linha
        representa um nutriente (N, P2O5, K2O). O valor é o teor em kg do nutriente por kg do fertilizante.
        Retorna também a lista de nomes dos fertilizantes na ordem das colunas.
        """
        n_fert = len(self.fertilizantes)
        A = np.zeros((3, n_fert))
        nomes = []
        for i, f in enumerate(self.fertilizantes):
            A[0, i] = f.n / 100.0   # kg N por kg de fertilizante
            A[1, i] = f.p2o5 / 100.0 # kg P2O5 por kg de fertilizante
            A[2, i] = f.k2o / 100.0  # kg K2O por kg de fertilizante
            nomes.append(f.nome)
        return A, nomes

    def calcular(self,
                 meta_n: Optional[float] = None,
                 meta_p2o5: Optional[float] = None,
                 meta_k2o: Optional[float] = None,
                 formula: Optional[str] = None,
                 eficiencia_n: float = 100.0,
                 permitir_inerte: bool = True) -> ResultadoMistura:
        """
        Calcula as quantidades de cada fertilizante para compor 1000 kg de mistura.

        Args:
            meta_n, meta_p2o5, meta_k2o: necessidades em kg/ha (ou kg/t se for para mistura)
            formula: string no formato "08-28-16"
            eficiencia_n: % de eficiência do nitrogênio (default 100)
            permitir_inerte: se True, permite adicionar material inerte para completar 1000 kg.

        Returns:
            ResultadoMistura com os dados da formulação.
        """
        # Obtém a meta em kg por tonelada
        try:
            n_alvo, p_alvo, k_alvo = self._meta_para_nutrientes(meta_n, meta_p2o5, meta_k2o, formula, eficiencia_n)
        except ValueError as e:
            return ResultadoMistura(sucesso=False, mensagem=str(e))

        # Constrói a matriz de teores
        A, nomes = self._construir_matriz()
        b = np.array([n_alvo, p_alvo, k_alvo])

        n_fert = len(self.fertilizantes)

        # Caso 1: número de fertilizantes igual ao número de nutrientes (3) - sistema exato
        if n_fert == 3:
            try:
                x = np.linalg.solve(A, b)
                quantidades = {nomes[i]: x[i] for i in range(n_fert)}
                erro = 0.0
            except np.linalg.LinAlgError:
                return ResultadoMistura(sucesso=False, mensagem="Sistema singular: fertilizantes linearmente dependentes.")

        # Caso 2: mais fertilizantes que nutrientes - usar mínimos quadrados com restrição de não negatividade
        elif n_fert > 3:
            res = lsq_linear(A, b, bounds=(0, np.inf), method='bvls')
            x = res.x
            quantidades = {nomes[i]: x[i] for i in range(n_fert)}
            erro = res.cost

        # Caso 3: menos fertilizantes que nutrientes - impossível, mas tentamos resolver por mínimos quadrados
        else:
            res = lsq_linear(A, b, bounds=(0, np.inf), method='bvls')
            x = res.x
            quantidades = {nomes[i]: x[i] for i in range(n_fert)}
            erro = res.cost

        # Calcula a soma total das quantidades
        soma_kg = sum(quantidades.values())

        # Se permitir inerte e a soma for diferente de 1000 kg, ajusta
        inerte = 0.0
        if permitir_inerte:
            if soma_kg < 1000.0:
                inerte = 1000.0 - soma_kg
            elif soma_kg > 1000.0:
                # Redimensiona proporcionalmente para somar 1000 kg
                fator = 1000.0 / soma_kg
                for k in quantidades:
                    quantidades[k] *= fator
                inerte = 0.0
                # Recalcula erro
                x_ajustado = np.array(list(quantidades.values()))
                b_calc = A @ x_ajustado
                erro = np.linalg.norm(b_calc - b)

        # Calcula a fórmula percentual final
        x_final = np.array(list(quantidades.values()))
        b_final = A @ x_final
        n_final = b_final[0] * 10   # converte kg/t para %
        p_final = b_final[1] * 10
        k_final = b_final[2] * 10

        # Cálculo de custos
        custo_tonelada = sum(quantidades[f.nome] * f.preco_total_kg for f in self.fertilizantes)
        custo_kg = custo_tonelada / 1000.0

        mensagem = "Cálculo realizado com sucesso."
        sucesso = True

        return ResultadoMistura(
            sucesso=sucesso,
            quantidades={nome: round(q, 2) for nome, q in quantidades.items()},
            formula_final=(round(n_final, 2), round(p_final, 2), round(k_final, 2)),
            inerte_kg=round(inerte, 2),
            erro_nutrientes=round(erro, 4),
            custo_tonelada=round(custo_tonelada, 2),
            custo_kg=round(custo_kg, 4),
            mensagem=mensagem
        )

    def calcular_por_hectare(self, resultado: ResultadoMistura, dose_kg_ha: float, area_ha: float) -> Dict:
        """
        A partir de um resultado de mistura, calcula custos por hectare e total.

        Args:
            resultado: objeto ResultadoMistura
            dose_kg_ha: quantidade da mistura a ser aplicada por hectare (kg/ha)
            area_ha: área total em hectares

        Returns:
            dicionário com custo_por_ha, custo_total, e quantidades por ha de cada fertilizante.
        """
        # Quantidade de cada fertilizante por hectare
        quant_ha = {}
        for nome, q_ton in resultado.quantidades.items():
            quant_ha[nome] = round((q_ton / 1000.0) * dose_kg_ha, 2)

        # Inerte por hectare
        inerte_ha = round((resultado.inerte_kg / 1000.0) * dose_kg_ha, 2) if resultado.inerte_kg > 0 else 0.0

        # Custo por hectare
        custo_ha = resultado.custo_kg * dose_kg_ha

        # Custo total
        custo_total = custo_ha * area_ha

        return {
            'quantidades_ha': quant_ha,
            'inerte_ha': inerte_ha,
            'custo_ha': round(custo_ha, 2),
            'custo_total': round(custo_total, 2)
        }

# Exemplo de uso quando executado diretamente
if __name__ == "__main__":
    from fertilizante import Fertilizante

    # 1. Definir fertilizantes disponíveis (com preços fictícios em R$/kg)
    fertilizantes = [
        Fertilizante("Ureia", 45, 0, 0, 3.50),
        Fertilizante("MAP", 10, 48, 0, 4.20),
        Fertilizante("DAP", 18, 46, 0, 4.80),
        Fertilizante("Super Simples", 0, 18, 0, 2.10),
        Fertilizante("Super Triplo", 0, 41, 0, 3.00),
        Fertilizante("KCl", 0, 0, 60, 3.80),
        Fertilizante("Sulfato de Amônio", 20, 0, 0, 2.90),
        Fertilizante("04-30-10", 4, 30, 10, 2.50),
    ]

    # 2. Criar o motor de mistura
    mistura = Mistura(fertilizantes)

    # 3. Definir uma meta: queremos uma fórmula 08-28-16 (kg/ha)
    resultado = mistura.calcular(formula="08-28-16", eficiencia_n=85.0)

    if resultado.sucesso:
        print("="*60)
        print("RESULTADO DA FORMULAÇÃO")
        print("="*60)
        print(f"Fórmula final obtida: {resultado.formula_final[0]:.2f}-{resultado.formula_final[1]:.2f}-{resultado.formula_final[2]:.2f}")
        print(f"Custo da tonelada: R$ {resultado.custo_tonelada:.2f}")
        print(f"Custo por kg: R$ {resultado.custo_kg:.4f}")
        print(f"Erro nutricional: {resultado.erro_nutrientes:.4f}")
        print("\nCOMPOSIÇÃO DA TONELADA:")
        for nome, kg in resultado.quantidades.items():
            print(f"  {nome}: {kg:.2f} kg")
        if resultado.inerte_kg > 0:
            print(f"  Carga inerte: {resultado.inerte_kg:.2f} kg")
        else:
            print("  Sem carga inerte.")

        # 4. Calcular para aplicação em um talhão
        dose_ha = 400  # kg/ha da mistura
        area = 50      # hectares
        custos = mistura.calcular_por_hectare(resultado, dose_ha, area)

        print("\n" + "="*60)
        print("APLICAÇÃO NO TALHÃO")
        print("="*60)
        print(f"Dose: {dose_ha} kg/ha")
        print(f"Área: {area} ha")
        print(f"Custo por hectare: R$ {custos['custo_ha']:.2f}")
        print(f"Custo total: R$ {custos['custo_total']:.2f}")
        print("\nQuantidades por hectare:")
        for nome, kg in custos['quantidades_ha'].items():
            print(f"  {nome}: {kg:.2f} kg")
        if custos['inerte_ha'] > 0:
            print(f"  Inerte: {custos['inerte_ha']:.2f} kg")
    else:
        print(f"Erro: {resultado.mensagem}")