from abc import ABC, abstractmethod

class Aeronave(ABC):
    """
    Classe abstrata base que define o contrato para todas as aeronaves
    que trafegam no aeroporto durante a simulação.
    """
    def __init__(self, id_aeronave: int, horario_chegada: int):
        self.id_aeronave = id_aeronave
        self.horario_chegada = horario_chegada

    @property
    @abstractmethod
    def tipo(self) -> str:
        """Retorna o tipo da aeronave ('P' ou 'G')."""
        pass

    @property
    @abstractmethod
    def tempo_pouso_decolagem(self) -> int:
        """Tempo em minutos necessário para operações na pista (pouso ou decolagem)."""
        pass

    @property
    @abstractmethod
    def tempo_desembarque(self) -> int:
        """Tempo em minutos necessário para o desembarque na plataforma."""
        pass

    @property
    @abstractmethod
    def tempo_embarque(self) -> int:
        """Tempo em minutos necessário para o embarque na plataforma."""
        pass

    def __str__(self):
        return f"Aeronave {self.tipo}-{self.id_aeronave} (Chegada: {self.horario_chegada})"


class AeronavePequena(Aeronave):
    """
    Representa uma aeronave de pequeno porte (P).
    Implementa polimorficamente os tempos específicos do problema.
    """
    @property
    def tipo(self) -> str:
        return "P"

    @property
    def tempo_pouso_decolagem(self) -> int:
        return 40

    @property
    def tempo_desembarque(self) -> int:
        return 20

    @property
    def tempo_embarque(self) -> int:
        return 30


class AeronaveGrande(Aeronave):
    """
    Representa uma aeronave de grande porte (G).
    Implementa polimorficamente os tempos específicos do problema.
    """
    @property
    def tipo(self) -> str:
        return "G"

    @property
    def tempo_pouso_decolagem(self) -> int:
        return 60

    @property
    def tempo_desembarque(self) -> int:
        return 40

    @property
    def tempo_embarque(self) -> int:
        return 60


class AeronaveFactory:
    """
    Fábrica responsável pela criação de instâncias de Aeronave.
    Aplica o padrão de projeto Factory Method para encapsular
    a lógica de instanciação.
    """
    @staticmethod
    def criar_aeronave(id_aeronave: int, tipo: str, horario_chegada: int) -> Aeronave:
        """
        Lê o tipo em formato string e retorna o objeto correto.
        
        Args:
            id_aeronave (int): Identificador numérico único da aeronave.
            tipo (str): O tipo ('P' para pequeno, 'G' para grande).
            horario_chegada (int): Tempo da simulação em que a aeronave chega no sistema.
            
        Returns:
            Aeronave: Uma instância de AeronavePequena ou AeronaveGrande.
            
        Raises:
            ValueError: Se o tipo for diferente de 'P' ou 'G'.
        """
        tipo_upper = str(tipo).strip().upper()
        
        if tipo_upper == 'P':
            return AeronavePequena(id_aeronave, horario_chegada)
        elif tipo_upper == 'G':
            return AeronaveGrande(id_aeronave, horario_chegada)
        else:
            raise ValueError(f"Tipo de aeronave desconhecido na criação: {tipo}")