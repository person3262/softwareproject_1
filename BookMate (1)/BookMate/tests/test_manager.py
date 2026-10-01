import os
import tempfile
import time
import unittest
from pathlib import Path

from bookmate.manager import BookManager, eul_reul
from bookmate.models import Book
from bookmate.store import CsvStore

FIXTURE = Path(__file__).parent / "fixtures" / "sample_books.csv"


def data(**kw):
    base = {"title": "새 책", "author": "저자", "year": "2020", "isbn": "111-222",
            "genre": "기타", "rating": "", "read": False, "favorite": False}
    base.update(kw)
    return base


class ManagerTest(unittest.TestCase):
    def setUp(self):
        self.manager = BookManager(CsvStore(FIXTURE))
        self.manager.load()

    def test_tc01_add(self):
        before = len(self.manager.books)
        result = self.manager.add_book(data())
        self.assertTrue(result.ok)
        self.assertEqual(result.message, "'새 책'을 등록했습니다")   # 6.3 문구
        self.assertEqual(len(self.manager.books), before + 1)
        # books와 isbn_map이 '같은 객체'를 가리키는지 확인
        self.assertIs(self.manager.books[-1], self.manager.isbn_map["111-222"])

    def test_add_invalid_keeps_list(self):
        before = len(self.manager.books)
        result = self.manager.add_book(data(title=""))
        self.assertFalse(result.ok)
        self.assertEqual(len(self.manager.books), before)

    def test_tc04_duplicate(self):
        result = self.manager.add_book(data(isbn="978-89-8371-154-1"))
        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].message, "이미 등록된 도서입니다")

    def test_tc05_update(self):
        isbn = "978-89-364-3413-0"  # 채식주의자
        result = self.manager.update_book(isbn, data(title="채식주의자", author="한강",
                                                     year="2007", rating="4.5", read=True))
        self.assertTrue(result.ok)
        book = self.manager.isbn_map[isbn]
        self.assertEqual((book.read, book.rating, book.isbn), (True, 4.5, isbn))
        self.assertIn(book, self.manager.books)

    def test_tc07_delete(self):
        isbn = "978-89-8371-154-1"
        self.assertTrue(self.manager.delete_book(isbn).ok)
        self.assertNotIn(isbn, self.manager.isbn_map)
        self.assertFalse(any(b.isbn == isbn for b in self.manager.books))
        before = len(self.manager.books)
        self.assertFalse(self.manager.delete_book("없는-ISBN").ok)
        self.assertEqual(len(self.manager.books), before)

    def test_tc08_search(self):
        found = self.manager.search("title", "사피")
        self.assertEqual([b.title for b in found], ["사피엔스"])

    def test_search_case_insensitive(self):
        self.assertEqual(len(self.manager.search("title", "clean code")), 1)

    def test_tc09_search_none(self):
        self.assertEqual(self.manager.search("author", "없는이름"), [])

    def test_search_empty_keyword_returns_all(self):
        self.assertEqual(len(self.manager.search("title", "  ")), len(self.manager.books))

    def test_search_bad_field(self):
        with self.assertRaises(ValueError):
            self.manager.search("isbn", "978")

    def test_tc10_stats(self):
        s = self.manager.get_stats(goal=20)
        self.assertEqual((s.total, s.read_count, s.favorite_count, s.achieved), (12, 8, 3, False))
        self.assertEqual(s.avg_rating, round((4.5 + 4.0 + 5.0 + 3.5 + 4.0 + 3.0 + 3.5) / 7, 1))

    def test_tc11_stats_no_ratings(self):
        with tempfile.TemporaryDirectory() as d:
            manager = BookManager(CsvStore(Path(d) / "books.csv"))
            manager.load()
            manager.add_book(data())              # 도서는 있지만 별점 없음
            self.assertIsNone(manager.get_stats().avg_rating)

    def test_tc11_stats_empty(self):
        empty = BookManager(CsvStore(Path(tempfile.gettempdir()) / "no_such_bookmate.csv"))
        empty.load()
        s = empty.get_stats(goal=0)
        self.assertIsNone(s.avg_rating)
        self.assertEqual(s.goal, 1)

    def test_tc12_toggle_twice(self):
        isbn = "978-89-8371-154-1"
        original = self.manager.isbn_map[isbn].favorite
        self.manager.toggle_favorite(isbn)
        self.assertEqual(self.manager.toggle_favorite(isbn), original)

    def test_toggle_missing(self):
        with self.assertRaises(KeyError):
            self.manager.toggle_favorite("없는-ISBN")

    def test_eul_reul(self):
        self.assertEqual(eul_reul("데미안"), "을")
        self.assertEqual(eul_reul("코스모스"), "를")
        self.assertEqual(eul_reul("Clean Code"), "을(를)")


def elapsed(func, repeat=5):
    """5회 측정 평균(초) — 8.1 성능 테스트 완료 기준."""
    start = time.perf_counter()
    for _ in range(repeat):
        func()
    return (time.perf_counter() - start) / repeat


class PerformanceTest(unittest.TestCase):
    """TC-18: 도서 1,000건 기준 성능 (NFR-02, 8.1)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        store = CsvStore(Path(self.tmp.name) / "books.csv")
        store.save([Book(f"책{i}", f"저자{i % 50}", 2000 + i % 20, "기타", f"{i:05d}", 3.0, i % 2 == 0)
                    for i in range(1000)])
        self.store = store
        self.manager = BookManager(store)
        self.manager.load()

    def tearDown(self):
        self.tmp.cleanup()

    def test_tc18_load_save(self):                      # 기준 1초
        self.assertLess(elapsed(self.manager.load), 1.0)
        self.assertLess(elapsed(self.manager.save), 1.0)

    def test_tc18_add_search_stats(self):               # 기준 0.1초
        counter = iter(range(100000, 100010))
        self.assertLess(elapsed(lambda: self.manager.add_book(data(isbn=str(next(counter))))), 0.1)
        self.assertLess(elapsed(lambda: self.manager.search("author", "저자7")), 0.1)
        self.assertLess(elapsed(self.manager.get_stats), 0.1)

    def test_tc18_favorite(self):                       # 기준 0.05초
        self.assertLess(elapsed(lambda: self.manager.toggle_favorite("00500")), 0.05)

    def test_tc18_table_refresh(self):                  # 기준 0.5초 (MOD-008)
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")   # 창을 띄우지 않고 측정
        from PyQt5.QtWidgets import QApplication
        from bookmate.ui.main_window import MainWindow
        app = QApplication.instance() or QApplication([])
        window = MainWindow(BookManager(self.store))
        self.assertEqual(window.table.rowCount(), 1000)
        self.assertLess(elapsed(window.refresh_table), 0.5)
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
