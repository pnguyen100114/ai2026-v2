from __future__ import annotations

try:
    from backend.rag.retriever import get_curriculum_from_rag, search_knowledge
except ImportError:  # pragma: no cover
    from rag.retriever import get_curriculum_from_rag, search_knowledge


if __name__ == '__main__':
    subject = 'Toán'
    grade = 8
    query = 'Giải thích phương trình bậc nhất một ẩn'
    matches = search_knowledge(query, subject=subject, grade=grade, top_k=5)
    print('MATCHES', len(matches))
    if matches:
        print('FIRST_MATCH_SCORE', matches[0].get('score'))
        print('FIRST_MATCH_SOURCE', matches[0].get('source'))
        print('FIRST_MATCH_CHAPTER', matches[0].get('chapter'))
        print('FIRST_MATCH_LESSON', matches[0].get('lesson'))
    curriculum = get_curriculum_from_rag(subject, grade)
    print('CURRICULUM_COUNT', len(curriculum))
    if curriculum:
        print('CURRICULUM_FIRST', curriculum[0])
