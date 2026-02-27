# adubacao/models.py
from dataclasses import dataclass, field
from typing import Optional, Dict
from enum import Enum

class Cultura(Enum):
    MILHO = "milho"
    SOJA = "soja"
    PASTAGEM = "pastagem"

class Sistema(Enum):
    SEQUEIRO = "sequeiro"
    IRRIGADO = "irrigado"

@dataclass
class AnaliseSolo:
    ph_h2o: float
    p_melich: float
    k_melich: float
    ca: float
    mg: float
    al: float
    h_al: float
    mo: float
    argila: float
    ctc: Optional[float] = None
    zn: Optional[float] = None
    cu: Optional[float] = None
    b: Optional[float] = None
    mn: Optional[float] = None
    fe: Optional[float] = None
    s: Optional[float] = None

    def __post_init__(self):
        if self.ctc is None:
            soma_bases = self.ca + self.mg + (self.k_melich * 0.00256)
            self.ctc = soma_bases + self.h_al

    @property
    def soma_bases(self) -> float:
        return self.ca + self.mg + (self.k_melich * 0.00256)

    @property
    def saturacao_bases(self) -> float:
        if self.ctc > 0:
            return (self.soma_bases / self.ctc) * 100
        return 0.0

@dataclass
class Recomendacao:
    calagem_t_ha: Optional[float] = None
    gesso_kg_ha: Optional[float] = None
    n_kg_ha: Optional[float] = None
    p2o5_kg_ha: Optional[float] = None
    k2o_kg_ha: Optional[float] = None
    micronutrientes: Dict[str, float] = field(default_factory=dict)

    @property
    def n_total(self) -> float:
        return self.n_kg_ha or 0

    @property
    def p2o5_total(self) -> float:
        return self.p2o5_kg_ha or 0

    @property
    def k2o_total(self) -> float:
        return self.k2o_kg_ha or 0

    def to_dict(self):
        return {
            'calagem_t_ha': self.calagem_t_ha,
            'gesso_kg_ha': self.gesso_kg_ha,
            'n_kg_ha': self.n_kg_ha,
            'p2o5_kg_ha': self.p2o5_kg_ha,
            'k2o_kg_ha': self.k2o_kg_ha,
            **self.micronutrientes
        }