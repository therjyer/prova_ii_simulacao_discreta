import simpy
import pandas as pd
import os
import logging

from src.models.aeronave import AeronaveFactory
from src.models.aeroporto import Aeroporto

# Configuração básica de log para a simulação
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Fallback: Tenta importar o monitor (padrão Observer).
# Caso o ficheiro monitor.py ainda não exista, cria-se stubs vazios para não quebrar a execução.
try:
    from src.simulation.monitor import registrar_metricas_aeronave, atualizar_estado_fila
except ImportError:
    def registrar_metricas_aeronave(*args, **kwargs): pass
    def atualizar_estado_fila(*args, **kwargs): pass

# Constante adotada para os preparativos no hangar, visto que o PDF não especificou o tempo desta atividade
TEMPO_PREPARO_HANGAR_MINUTOS = 60


def processo_aeronave(env: simpy.Environment, aeronave, aeroporto: Aeroporto):
    """
    Define o ciclo de vida completo de uma aeronave dentro do aeroporto,
    passando pelos recursos: Pista (Pouso) -> Plataforma (Desembarque) -> 
    Hangar (Preparo) -> Plataforma (Embarque) -> Pista (Decolagem).
    """
    chegada_aeroporto = env.now
    
    # Identifica a pista adequada com base no porte da aeronave ('P' ou 'G')
    pista_adequada = aeroporto.obter_pista(aeronave.tipo)

    # ---------------------------------------------------------
    # 1. ETAPA DE POUSO
    # ---------------------------------------------------------
    chegada_fila_pouso = env.now
    atualizar_estado_fila("pouso", aeronave.tipo, 1)
    
    with pista_adequada.request() as req_pouso:
        yield req_pouso  # Aguarda até que a pista seja libertada
        
        atualizar_estado_fila("pouso", aeronave.tipo, -1)
        espera_pouso = env.now - chegada_fila_pouso
        
        # Realiza o pouso (tempo fixo por tipo de aeronave)
        yield env.timeout(aeronave.tempo_pouso_decolagem)

    # ---------------------------------------------------------
    # 2. ETAPA DE DESEMBARQUE
    # ---------------------------------------------------------
    chegada_fila_desembarque = env.now
    atualizar_estado_fila("desembarque", aeronave.tipo, 1)
    
    with aeroporto.plataformas.request() as req_desembarque:
        yield req_desembarque  # Aguarda uma plataforma disponível
        
        atualizar_estado_fila("desembarque", aeronave.tipo, -1)
        espera_desembarque = env.now - chegada_fila_desembarque
        
        # Realiza o desembarque
        yield env.timeout(aeronave.tempo_desembarque)

    # ---------------------------------------------------------
    # 3. ETAPA DE PREPARATIVOS NO HANGAR
    # ---------------------------------------------------------
    chegada_fila_hangar = env.now
    atualizar_estado_fila("hangar", aeronave.tipo, 1)
    
    with aeroporto.hangares.request() as req_hangar:
        yield req_hangar  # Aguarda um hangar disponível
        
        atualizar_estado_fila("hangar", aeronave.tipo, -1)
        espera_hangar = env.now - chegada_fila_hangar
        
        # Realiza os preparativos
        yield env.timeout(TEMPO_PREPARO_HANGAR_MINUTOS)

    # ---------------------------------------------------------
    # 4. ETAPA DE EMBARQUE
    # ---------------------------------------------------------
    chegada_fila_embarque = env.now
    atualizar_estado_fila("embarque", aeronave.tipo, 1)
    
    with aeroporto.plataformas.request() as req_embarque:
        yield req_embarque  # Aguarda uma plataforma disponível
        
        atualizar_estado_fila("embarque", aeronave.tipo, -1)
        espera_embarque = env.now - chegada_fila_embarque
        
        # Realiza o embarque
        yield env.timeout(aeronave.tempo_embarque)

    # ---------------------------------------------------------
    # 5. ETAPA DE DECOLAGEM
    # ---------------------------------------------------------
    chegada_fila_decolagem = env.now
    atualizar_estado_fila("decolagem", aeronave.tipo, 1)
    
    with pista_adequada.request() as req_decolagem:
        yield req_decolagem  # Aguarda a pista ser libertada
        
        atualizar_estado_fila("decolagem", aeronave.tipo, -1)
        espera_decolagem = env.now - chegada_fila_decolagem
        
        # Realiza a decolagem
        yield env.timeout(aeronave.tempo_pouso_decolagem)

    # ---------------------------------------------------------
    # FIM DO CICLO: Registo de Métricas
    # ---------------------------------------------------------
    tempo_total_sistema = env.now - chegada_aeroporto
    
    # Chama o módulo observador para persistir o tempo gasto em filas para esta aeronave
    registrar_metricas_aeronave(
        id_aeronave=aeronave.id_aeronave,
        tipo=aeronave.tipo,
        espera_pouso=espera_pouso,
        espera_desembarque=espera_desembarque,
        espera_hangar=espera_hangar,
        espera_embarque=espera_embarque,
        espera_decolagem=espera_decolagem,
        tempo_total=tempo_total_sistema
    )


def gerador_chegadas(env: simpy.Environment, aeroporto: Aeroporto, df_chegadas: pd.DataFrame):
    """
    Lê o ficheiro de chegadas (CSV) e injeta as aeronaves no ambiente de simulação 
    nos seus respetivos instantes de chegada.
    """
    for index, row in df_chegadas.iterrows():
        id_aeronave = int(row['id'])
        tipo = str(row['tipo']).strip()
        horario_chegada = int(row['horario_chegada'])
        
        # Aplicação do padrão Factory Method
        try:
            aeronave = AeronaveFactory.criar_aeronave(id_aeronave, tipo, horario_chegada)
        except ValueError as e:
            logging.error(f"Erro ao instanciar aeronave ID {id_aeronave}: {e}")
            continue

        # Calcula o tempo que falta para a aeronave chegar (se estivermos no instante 0 e ela chegar no minuto 10, espera 10)
        tempo_ate_chegada = horario_chegada - env.now
        
        if tempo_ate_chegada > 0:
            yield env.timeout(tempo_ate_chegada)
            
        # Quando o momento chega, injeta o processo da aeronave no simulador
        env.process(processo_aeronave(env, aeronave, aeroporto))


def executar_simulacao(csv_path: str, plataformas: int, hangares: int, pistas_p: int, pistas_g: int) -> int:
    """
    Ponto de entrada do motor de simulação.
    
    Inicializa o ambiente SimPy, aloca a capacidade dos recursos via Singleton,
    carrega os dados históricos via Pandas e orquestra a execução.
    
    Retorna:
        int: O tempo total do relógio da simulação em minutos após processar todas as aeronaves.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Ficheiro de dados não encontrado: {csv_path}")

    # Leitura otimizada do CSV utilizando Pandas
    df_chegadas = pd.read_csv(csv_path)
    
    # Ordena os dados cronologicamente apenas por segurança, garantindo a lógica do gerador
    df_chegadas = df_chegadas.sort_values(by='horario_chegada')

    # Inicializa o relógio/ambiente do SimPy
    env = simpy.Environment()
    
    # Obtenção da instância Singleton do Aeroporto
    aeroporto = Aeroporto()
    
    # Configura/Reinicializa o estado dos recursos físicos para o cenário submetido
    aeroporto.configurar(
        env=env, 
        num_plataformas=plataformas, 
        num_hangares=hangares, 
        num_pistas_p=pistas_p, 
        num_pistas_g=pistas_g
    )

    # Inicia o processo Master (Gerador de Chegadas)
    env.process(gerador_chegadas(env, aeroporto, df_chegadas))
    
    # Roda o simulador até a última aeronave terminar a decolagem e sair do sistema
    env.run()
    
    # Retorna o momento em que a simulação acabou de facto (o tempo de fechamento do aeroporto para a amostra)
    tempo_final_minutos = env.now
    logging.info(f"Simulação concluída. Tempo total da operação: {tempo_final_minutos} minutos.")
    
    return tempo_final_minutos