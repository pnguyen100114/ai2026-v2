from typing import Any, Dict, List

try:
    from backend.rag.retriever import build_roadmap_from_curriculum, get_curriculum_from_rag
except ImportError:  # pragma: no cover
    from rag.retriever import build_roadmap_from_curriculum, get_curriculum_from_rag


def get_curriculum(subject: str, grade: int) -> List[Dict[str, Any]]:
    return get_curriculum_from_rag(subject, grade)


def build_roadmap(curriculum: List[Dict[str, Any]], subject: str, grade: int) -> Dict[str, Any]:
    return build_roadmap_from_curriculum(curriculum, subject=subject, grade=grade)


__all__ = ['get_curriculum', 'build_roadmap']
