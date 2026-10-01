"""MOD-006 입력 검증 — 예외를 던지지 않고 발견한 오류를 모두 모아 돌려준다(EH-01)."""
import re
from datetime import date
from typing import NamedTuple

_ISBN_PATTERN = re.compile(r"[0-9-]+")


class FieldError(NamedTuple):
    field: str
    message: str


class Validator:
    REQUIRED = {
        "title": "제목을 입력하세요",
        "author": "저자를 입력하세요",
        "year": "출판연도를 입력하세요",
        "isbn": "ISBN을 입력하세요",
    }

    def validate(self, data: dict, existing_isbns: set[str] | None = None) -> list[FieldError]:
        errors: list[FieldError] = []

        # ① 필수 항목
        for name, message in self.REQUIRED.items():
            if not str(data.get(name, "")).strip():
                errors.append(FieldError(name, message))
        missing = {e.field for e in errors}

        # ② 출판연도: 정수, 1000 ~ 올해
        if "year" not in missing:
            this_year = date.today().year
            try:
                year = int(str(data["year"]).strip())
            except ValueError:
                errors.append(FieldError("year", "출판연도는 숫자로 입력하세요"))
            else:
                if not 1000 <= year <= this_year:
                    errors.append(FieldError("year", f"출판연도는 1000~{this_year} 사이로 입력하세요"))

        # ③ ISBN 형식: 숫자와 하이픈만, 숫자 1개 이상
        isbn = str(data.get("isbn", "")).strip()
        if "isbn" not in missing:
            if not _ISBN_PATTERN.fullmatch(isbn) or not any(ch.isdigit() for ch in isbn):
                errors.append(FieldError("isbn", "ISBN은 숫자와 하이픈(-)만 입력하세요"))
            # ⑤ 중복 (등록일 때만 existing_isbns가 전달됨)
            elif existing_isbns is not None and isbn in existing_isbns:
                errors.append(FieldError("isbn", "이미 등록된 도서입니다"))

        # ④ 별점: 비어 있으면 통과, 있으면 0.0~5.0 / 0.5 단위
        rating = data.get("rating")
        if rating not in (None, ""):
            try:
                value = float(rating)
            except (TypeError, ValueError):
                value = -1.0
            if not (0.0 <= value <= 5.0 and (value * 2).is_integer()):
                errors.append(FieldError("rating", "별점은 0.0~5.0 사이, 0.5 단위로 입력하세요"))

        return errors
