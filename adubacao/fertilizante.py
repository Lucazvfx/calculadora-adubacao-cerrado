# fertilizante.py
from dataclasses import dataclass

@dataclass
class Fertilizante:
    """
    Representa um fertilizante comercial com seus teores e preço.

    Atributos:
        nome: str - Nome comercial
        n: float - % de N (0-100)
        p2o5: float - % de P2O5 (0-100)
        k2o: float - % de K2O (0-100)
        preco_kg: float - preço por quilo em R$
        custo_adicional: float - custo extra por kg (frete, etc.) opcional
    """
    nome: str
    n: float
    p2o5: float
    k2o: float
    preco_kg: float
    custo_adicional: float = 0.0

    @property
    def preco_total_kg(self) -> float:
        return self.preco_kg + self.custo_adicional

    def __repr__(self):
        return f"{self.nome} ({self.n:.1f}-{self.p2o5:.1f}-{self.k2o:.1f})"