from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import os

# Importações simuladas dos módulos internos da arquitetura definida
# Em tempo de execução, essas funções residiriam em backend/src/simulation/
try:
    from src.simulation.core import executar_simulacao
    from src.simulation.monitor import obter_metricas, limpar_metricas
except ImportError:
    # Fallback para evitar erros estáticos caso os arquivos ainda não existam.
    # Na implementação real, os módulos core.py e monitor.py devem estar criados.
    def executar_simulacao(*args, **kwargs):
        pass
    def obter_metricas():
        return {}
    def limpar_metricas():
        pass

# Instanciação do Router do FastAPI
router = APIRouter(
    prefix="/api/simulacao",
    tags=["Simulação de Aeroporto"]
)

# ==============================================================================
# Modelos de Dados (Pydantic)
# Validam estritamente a entrada e saída de dados da API
# ==============================================================================

class AeroportoConfig(BaseModel):
    """
    Define a capacidade do aeroporto para a simulação.
    Os valores padrão correspondem ao Cenário Base descrito na Prova II.
    """
    num_plataformas: int = Field(default=5, ge=1, description="Número de plataformas de embarque/desembarque")
    num_hangares: int = Field(default=3, ge=1, description="Número de hangares para preparativos")
    num_pistas_p: int = Field(default=2, ge=1, description="Número de pistas para aeronaves de pequeno porte (P)")
    num_pistas_g: int = Field(default=1, ge=1, description="Número de pistas para aeronaves de grande porte (G)")

class CenarioRequest(BaseModel):
    """
    Requisição para rodar um cenário específico.
    """
    nome: str = Field(default="Cenário Base", description="Nome do cenário simulado")
    config: AeroportoConfig = Field(default_factory=AeroportoConfig)

# ==============================================================================
# Endpoints da API
# ==============================================================================

@router.post("/executar", response_model=Dict[str, Any])
async def simular_cenario(cenario: CenarioRequest) -> Dict[str, Any]:
    """
    Executa a simulação discreta do aeroporto para um determinado cenário.
    
    Lê a base de `chegadas.csv`, configura os recursos no SimPy de acordo com 
    o payload recebido e retorna o tempo final de processamento junto com as 
    métricas para identificação de gargalos.
    """
    # Caminho do arquivo referenciado na arquitetura
    caminho_csv = os.path.join(os.path.dirname(__file__), "../../data/chegadas.csv")
    
    if not os.path.exists(caminho_csv):
        raise HTTPException(
            status_code=404, 
            detail="Arquivo chegadas.csv não encontrado no diretório backend/data/"
        )

    try:
        # 1. Garante que o monitorador de eventos do SimPy inicie zerado
        limpar_metricas()

        # 2. Chama a execução do motor SimPy passando os parâmetros
        tempo_final = executar_simulacao(
            csv_path=caminho_csv,
            plataformas=cenario.config.num_plataformas,
            hangares=cenario.config.num_hangares,
            pistas_p=cenario.config.num_pistas_p,
            pistas_g=cenario.config.num_pistas_g
        )

        # 3. Coleta os resultados registrados via padrão Observer
        metricas_geradas = obter_metricas()

        # 4. Formata o payload de resposta esperado pelo front-end em React
        return {
            "status": "sucesso",
            "cenario": cenario.nome,
            "resultados": {
                "tempo_total_simulacao_minutos": tempo_final,
                "metricas": metricas_geradas
            }
        }
    except Exception as e:
        # Captura e retorna falhas ocorridas durante a execução do SimPy/Pandas
        raise HTTPException(status_code=500, detail=f"Erro interno na simulação: {str(e)}")

@router.get("/cenarios-recomendados", response_model=List[CenarioRequest])
async def listar_cenarios_pre_definidos():
    """
    Retorna uma lista de cenários pré-configurados que podem ser escolhidos 
    pela interface gráfica para avaliar o impacto econômico e gargalos.
    """
    return [
        CenarioRequest(
            nome="Cenário Base (Original)",
            config=AeroportoConfig(num_plataformas=5, num_hangares=3, num_pistas_p=2, num_pistas_g=1)
        ),
        CenarioRequest(
            nome="Cenário A (+1 Hangar)",
            config=AeroportoConfig(num_plataformas=5, num_hangares=4, num_pistas_p=2, num_pistas_g=1)
        ),
        CenarioRequest(
            nome="Cenário B (+1 Plataforma e +1 Hangar)",
            config=AeroportoConfig(num_plataformas=6, num_hangares=4, num_pistas_p=2, num_pistas_g=1)
        )
    ]