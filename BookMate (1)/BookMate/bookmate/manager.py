"""서비스 계층 BookManager — MOD-001(등록·수정·삭제), MOD-002(검색·조회),
MOD-003(통계), MOD-004(즐겨찾기). 화면 계층은 이 클래스만 호출한다."""
import unicodedata
from dataclasses import dataclass, field
from typing import NamedTuple

from .models import Book
from .store import CsvStore, LoadResult
from .validator import FieldError, Validator

SEARCH_FIELDS = ("title", "author", "genre")


@dataclass
class Result:
    ok: bool
    message: str = ""
    errors: list[FieldError] = field(default_factory=list)


class Stats(NamedTuple):
    total: int
    read_count: int
    avg_rating: float | None
    favorite_count: int
    goal: int
    achieved: bool


def eul_reul(word: str) -> str:
    """목적격 조사: 마지막 글자에 받침이 있으면 '을', 없으면 '를'.
    마지막 글자가 한글이 아니면 '을(를)'로 둔다."""
    if word and "가" <= word[-1] <= "힣":
        return "을" if (ord(word[-1]) - ord("가")) % 28 else "를"
    return "을(를)"


def _normalize(text: str) -> str:
    """검색 비교용: 유니코드 정규화(NFC) + 대소문자 무시."""
    return unicodedata.normalize("NFC", text).casefold()


class BookManager:
    def __init__(self, store: CsvStore, validator: Validator | None = None):
        self.store = store
        self.validator = validator or Validator()
        self.books: list[Book] = []           # 등록 순서 유지
        self.isbn_map: dict[str, Book] = {}   # isbn → books 안의 '같은' 객체

    # ---------- 적재·저장 (MOD-005 호출 창구) ----------
    def load(self) -> LoadResult:
        result = self.store.load()
        self.books, self.isbn_map = [], {}
        skipped = result.skipped
        for book in result.books:
            if book.isbn in self.isbn_map:   # 파일 안의 ISBN 중복 행도 형식 오류로 취급
                skipped += 1
                continue
            self.books.append(book)
            self.isbn_map[book.isbn] = book
        return result._replace(books=self.list_all(), skipped=skipped)

    def save(self) -> None:
        self.store.save(self.books)  # 실패 시 StoreError가 그대로 올라감

    # ---------- MOD-001 ----------
    def add_book(self, data: dict) -> Result:
        errors = self.validator.validate(data, existing_isbns=set(self.isbn_map))
        if errors:
            return Result(False, "입력값을 확인하세요", errors)
        book = self._make_book(data)
        self.books.append(book)
        self.isbn_map[book.isbn] = book
        return Result(True, f"'{book.title}'{eul_reul(book.title)} 등록했습니다")

    def update_book(self, isbn: str, data: dict) -> Result:
        book = self.isbn_map.get(isbn)
        if book is None:
            return Result(False, "대상 도서를 찾을 수 없습니다")
        errors = self.validator.validate({**data, "isbn": isbn})
        if errors:
            return Result(False, "입력값을 확인하세요", errors)
        new = self._make_book({**data, "isbn": isbn})
        # 같은 객체의 필드만 바꾼다 → books와 isbn_map이 자동으로 함께 갱신됨
        book.title, book.author, book.year = new.title, new.author, new.year
        book.genre, book.rating = new.genre, new.rating
        book.read, book.favorite = new.read, new.favorite
        return Result(True, f"'{book.title}'{eul_reul(book.title)} 수정했습니다")

    def delete_book(self, isbn: str) -> Result:
        book = self.isbn_map.pop(isbn, None)
        if book is None:
            return Result(False, "대상 도서를 찾을 수 없습니다")
        self.books.remove(book)
        return Result(True, f"'{book.title}'{eul_reul(book.title)} 삭제했습니다")

    @staticmethod
    def _make_book(data: dict) -> Book:
        rating = data.get("rating")
        return Book(
            title=str(data["title"]).strip(),
            author=str(data["author"]).strip(),
            year=int(str(data["year"]).strip()),
            genre=str(data.get("genre") or "기타"),
            isbn=str(data["isbn"]).strip(),
            rating=None if rating in (None, "") else float(rating),
            read=bool(data.get("read", False)),
            favorite=bool(data.get("favorite", False)),
        )

    # ---------- MOD-002 ----------
    def list_all(self) -> list[Book]:
        return list(self.books)  # 리스트는 복사, 안의 Book은 같은 객체

    def search(self, field: str, keyword: str) -> list[Book]:
        if field not in SEARCH_FIELDS:
            raise ValueError(f"검색할 수 없는 필드: {field}")
        key = _normalize(keyword.strip())
        if not key:
            return self.list_all()
        return [b for b in self.books if key in _normalize(getattr(b, field))]

    # ---------- MOD-003 ----------
    def get_stats(self, goal: int = 20) -> Stats:
        goal = max(goal, 1)
        books = self.list_all()
        read_count = sum(1 for b in books if b.read)
        ratings = [b.rating for b in books if b.rating is not None]
        avg = round(sum(ratings) / len(ratings), 1) if ratings else None
        return Stats(
            total=len(books),
            read_count=read_count,
            avg_rating=avg,
            favorite_count=sum(1 for b in books if b.favorite),
            goal=goal,
            achieved=read_count >= goal,
        )

    # ---------- MOD-004 ----------
    def toggle_favorite(self, isbn: str) -> bool:
        book = self.isbn_map[isbn]  # 없으면 KeyError → 화면 계층이 EH-04 안내
        book.favorite = not book.favorite
        return book.favorite
