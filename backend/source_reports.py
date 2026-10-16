"""Textbook pages students reported as wrong ("Trang này không đúng?"), most reported first.

Usage, from the project folder:
    .venv\\Scripts\\python.exe -m backend.source_reports

Uses the same DATABASE_URL as the backend (backend/.env), so it reads local SQLite or production Postgres.
A page reported often is usually a chunk that should not be in the store (cover, contents page, glossary)
or a page_offset that is off in backend/rag/books.py.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict

from backend import db

REASON_LABELS = {'wrong_page': 'sai trang', 'wrong_book': 'sai sách/lớp', 'unrelated': 'không liên quan'}


def summarize(reports: list[dict]) -> list[dict]:
    pages: dict[tuple, dict] = defaultdict(lambda: {'reasons': Counter(), 'questions': [], 'students': set()})
    for report in reports:
        entry = pages[(report['book_title'] or report['source'], report['page'], report['pdf_page'], report['lesson_title'])]
        entry['reasons'][report['reason']] += 1
        entry['students'].add(report['user_id'])
        if report['question'] and report['question'] not in entry['questions']:
            entry['questions'].append(report['question'])
    rows = [{'book': book, 'page': page, 'pdf_page': pdf_page, 'lesson': lesson, **entry}
            for (book, page, pdf_page, lesson), entry in pages.items()]
    return sorted(rows, key=lambda row: (-sum(row['reasons'].values()), -len(row['students'])))


def main(argv: list[str]) -> int:
    db.init_db()
    reports = db.list_source_reports()
    if not reports:
        print('Chưa có báo cáo trang sai nào.')
        return 0
    rows = summarize(reports)
    print(f'{len(reports)} báo cáo trên {len(rows)} trang sách.\n')
    for row in rows:
        reasons = ', '.join(f'{REASON_LABELS.get(reason, reason)} {count}' for reason, count in row['reasons'].most_common())
        print(f"{sum(row['reasons'].values())} lần · {len(row['students'])} em · {row['book']} · trang {row['page']} "
              f"(trang PDF {row['pdf_page']}){' · ' + row['lesson'] if row['lesson'] else ''}")
        print(f'    {reasons}')
        for question in row['questions'][:3]:
            print(f"    hỏi: {' '.join(question.split())[:140]}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
