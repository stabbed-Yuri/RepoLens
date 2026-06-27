from fastapi import APIRouter

from backend.models import AnalyzeRequest, KnowledgePack, RepositoryProfile
from backend.services.analyzer import RepositoryAnalyzer

router = APIRouter()
analyzer = RepositoryAnalyzer()


@router.post("/analyze", response_model=RepositoryProfile)
def analyze(request: AnalyzeRequest) -> RepositoryProfile:
    return analyzer.analyze(str(request.repository_url))


@router.post("/analyze/knowledge-pack", response_model=KnowledgePack)
def analyze_knowledge_pack(request: AnalyzeRequest) -> KnowledgePack:
    return analyzer.build_knowledge_pack(str(request.repository_url))
