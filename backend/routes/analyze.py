from fastapi import APIRouter

from backend.models import AnalyzeRequest, RepositoryProfile
from backend.services.analyzer import RepositoryAnalyzer

router = APIRouter()
analyzer = RepositoryAnalyzer()


@router.post("/analyze", response_model=RepositoryProfile)
def analyze(request: AnalyzeRequest) -> RepositoryProfile:
    return analyzer.analyze(str(request.repository_url))
