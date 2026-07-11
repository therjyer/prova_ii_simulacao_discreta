import simpy
from typing import Optional

class Aeroporto:
    """
    Classe que implementa o padrão Singleton para gerenciar o ambiente 
    de simulação de eventos discretos (SimPy) e os recursos do sistema.
    
    Garante que todos os processos em execução durante uma rodada da simulação
    compartilhem a mesma instância dos recursos (Pistas, Plataformas, Hangares).
    """
    
    _instancia = None

    def __new__(cls, *args, **kwargs):
        """
        Intercepta a criação da classe. Se uma instância já existir, 
        retorna a existente, caso contrário, cria uma nova.
        """
        if cls._instancia is None:
            cls._instancia = super(Aeroporto, cls).__new__(cls)
        return cls._instancia

    def __init__(self):
        """
        Inicialização das variáveis. O controle 'hasattr' garante que 
        os atributos não sejam sobrescritos acidentalmente caso a classe
        seja instanciada novamente no meio de uma simulação.
        """
        if not hasattr(self, '_inicializado'):
            self.env: Optional[simpy.Environment] = None
            self.pistas_p: Optional[simpy.Resource] = None
            self.pistas_g: Optional[simpy.Resource] = None
            self.plataformas: Optional[simpy.Resource] = None
            self.hangares: Optional[simpy.Resource] = None
            self._inicializado = True

    def configurar(self, env: simpy.Environment, num_plataformas: int = 5, 
                   num_hangares: int = 3, num_pistas_p: int = 2, num_pistas_g: int = 1):
        """
        Configura e inicializa (ou reseta) os recursos para uma nova rodada
        de simulação. Os valores padrão refletem o Cenário Base descrito na prova.
        
        Args:
            env (simpy.Environment): O motor de tempo da simulação atual.
            num_plataformas (int): Quantidade de plataformas de embarque/desembarque.
            num_hangares (int): Quantidade de hangares para preparação.
            num_pistas_p (int): Quantidade de pistas exclusivas para aviões de Pequeno Porte (P).
            num_pistas_g (int): Quantidade de pistas exclusivas para aviões de Grande Porte (G).
        """
        self.env = env
        
        # Alocação dos recursos do SimPy com base nas capacidades passadas (ou default)
        self.pistas_p = simpy.Resource(env, capacity=num_pistas_p)
        self.pistas_g = simpy.Resource(env, capacity=num_pistas_g)
        self.plataformas = simpy.Resource(env, capacity=num_plataformas)
        self.hangares = simpy.Resource(env, capacity=num_hangares)

    def obter_pista(self, tipo_aeronave: str) -> simpy.Resource:
        """
        Função utilitária para retornar a fila de pista correta de 
        acordo com o porte da aeronave (P ou G).
        
        Args:
            tipo_aeronave (str): 'P' para pequeno porte, 'G' para grande porte.
            
        Returns:
            simpy.Resource: O recurso de pista correspondente.
        """
        tipo_upper = str(tipo_aeronave).strip().upper()
        
        if tipo_upper == 'P':
            return self.pistas_p
        elif tipo_upper == 'G':
            return self.pistas_g
        else:
            raise ValueError(f"Erro: Tipo de aeronave desconhecido '{tipo_aeronave}' ao solicitar pista.")