"""MOD-007 도메인 모델 — 도서 1권(Book)과 CSV 행 사이의 변환."""
from dataclasses import dataclass, fields

# 장르 선택지 (설계서 5.2)
GENRES = ("소설", "인문", "과학", "역사", "자기계발", "기타")

_TRUE = {"true", "1", "o", "y", "yes"}
_FALSE = {"false", "0", "x", "n", "no", ""}


def _to_bool(text: str) -> bool:
    value = text.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(f"True/False로 해석할 수 없는 값: {text!r}")


@dataclass
class Book:
    """도서 1권. CSV 1행과 1:1로 대응한다."""
    title: str
    author: str
    year: int
    genre: str
    isbn: str
    rating: float | None = None
    read: bool = False
    favorite: bool = False

    def to_row(self) -> list[str]:
        """CSV에 쓸 문자열 목록으로 변환한다 (헤더 순서와 동일)."""
        return [
            self.title,
            self.author,
            str(self.year),
            self.genre,
            self.isbn,
            "" if self.rating is None else f"{self.rating:.1f}",
            str(self.read),
            str(self.favorite),
        ]

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Book":
        """csv.DictReader가 읽은 한 행을 Book으로 변환한다. 실패하면 ValueError."""
        try:
            title = row["title"].strip()
            isbn = row["isbn"].strip()
            if not title or not isbn:
                raise ValueError("제목 또는 ISBN이 비어 있음")
            rating_text = (row["rating"] or "").strip()
            return cls(
                title=title,
                author=row["author"].strip(),
                year=int(row["year"]),
                genre=(row["genre"] or "").strip() or "기타",
                isbn=isbn,
                rating=float(rating_text) if rating_text else None,
                read=_to_bool(row["read"] or ""),
                favorite=_to_bool(row["favorite"] or ""),
            )
        except (KeyError, TypeError, AttributeError) as exc:
            # 열이 모자라 None이 들어온 경우 등도 모두 '형식 오류 행'으로 통일
            raise ValueError(f"형식 오류 행: {row}") from exc


# CSV 헤더 = dataclass 필드 이름 순서
FIELD_NAMES: tuple[str, ...] = tuple(f.name for f in fields(Book))
