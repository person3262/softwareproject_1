"""MOD-005 CSV 입출력 — books.csv 전량 적재·저장과 파일 오류 처리(EH-03)."""
import csv
import os
import shutil
from pathlib import Path
from typing import NamedTuple

from .models import FIELD_NAMES, Book

ENCODING = "utf-8-sig"  # BOM 포함: 엑셀에서 열어도 한글이 깨지지 않음


class StoreError(Exception):
    """저장 실패. 원본 파일은 그대로 남아 있다."""


class LoadResult(NamedTuple):
    books: list[Book]
    skipped: int = 0      # 형식 오류로 건너뛴 행 수
    backup: bool = False  # 헤더 불일치로 .bak 백업을 만들었는지


class CsvStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    @property
    def backup_path(self) -> Path:
        return self.path.with_name(self.path.name + ".bak")

    @property
    def temp_path(self) -> Path:
        return self.path.with_name(self.path.name + ".tmp")

    def load(self) -> LoadResult:
        # ① 파일이 없으면 빈 목록으로 시작
        if not self.path.exists():
            return LoadResult([])

        try:
            with open(self.path, encoding=ENCODING, newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:        # 내용이 없는 빈 파일 → 빈 목록
                    return LoadResult([])
                # ② 헤더 확인
                if tuple(reader.fieldnames) != FIELD_NAMES:
                    return self._backup_and_reset()
                # ③ 행 변환, 실패한 행은 건너뛰며 센다
                books: list[Book] = []
                skipped = 0
                for row in reader:
                    try:
                        books.append(Book.from_row(row))
                    except ValueError:
                        skipped += 1
        except UnicodeDecodeError:
            # 인코딩이 다른 파일도 '헤더 불일치'와 같은 방식으로 원본을 보호한다
            return self._backup_and_reset()

        return LoadResult(books, skipped)

    def _backup_and_reset(self) -> LoadResult:
        shutil.copy2(self.path, self.backup_path)
        return LoadResult([], 0, backup=True)

    def save(self, books: list[Book]) -> None:
        tmp = self.temp_path
        try:
            with open(tmp, "w", encoding=ENCODING, newline="") as f:
                writer = csv.writer(f)
                writer.writerow(FIELD_NAMES)
                writer.writerows(book.to_row() for book in books)
            os.replace(tmp, self.path) 
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise StoreError(str(exc)) from exc
