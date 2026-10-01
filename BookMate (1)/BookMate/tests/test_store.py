import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bookmate.manager import BookManager
from bookmate.models import Book
from bookmate.store import CsvStore, StoreError

FIXTURE = Path(__file__).parent / "fixtures" / "sample_books.csv"


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.path = self.dir / "books.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_tc13_roundtrip(self):
        books = CsvStore(FIXTURE).load().books
        CsvStore(self.path).save(books)
        self.assertEqual(CsvStore(self.path).load().books, books)  # dataclass __eq__ 로 8개 필드 비교

    def test_tc14_missing_file(self):
        result = CsvStore(self.path).load()
        self.assertEqual((result.books, result.skipped, result.backup), ([], 0, False))

    def test_tc15_skip_bad_rows(self):
        text = FIXTURE.read_text(encoding="utf-8")
        text += "잘못된행,저자,연도아님,소설,1-1,,False,False\n"
        text += "짧은행,저자\n"
        self.path.write_text(text, encoding="utf-8")
        result = CsvStore(self.path).load()
        self.assertEqual((len(result.books), result.skipped), (12, 2))

    def test_empty_file_is_empty_list(self):
        self.path.write_bytes(b"")
        result = CsvStore(self.path).load()
        self.assertEqual((result.books, result.backup), ([], False))
        self.assertFalse((self.dir / "books.csv.bak").exists())

    def test_header_mismatch_backup(self):
        self.path.write_text("이름,값\na,b\n", encoding="utf-8")
        result = CsvStore(self.path).load()
        self.assertTrue(result.backup)
        self.assertTrue((self.dir / "books.csv.bak").exists())

    @unittest.skipUnless(sys.platform == "win32", "읽기 전용 파일 교체 실패는 Windows 동작")
    def test_tc16_readonly_file(self):
        """8.2 TC-16 그대로: 읽기 전용 books.csv에 저장."""
        store = CsvStore(self.path)
        store.save([Book("원본", "저자", 2000, "기타", "1-1")])
        original = self.path.read_bytes()
        os.chmod(self.path, stat.S_IREAD)
        try:
            with self.assertRaises(StoreError):
                store.save([Book("새것", "저자", 2001, "기타", "2-2")])
            self.assertEqual(self.path.read_bytes(), original)
            self.assertFalse(store.temp_path.exists())
        finally:
            os.chmod(self.path, stat.S_IREAD | stat.S_IWRITE)   # 임시 폴더 정리를 위해 복구

    def test_tc16_write_failure_keeps_original(self):
        """TC-16 보조: 운영체제와 관계없이 쓰기 실패를 모의로 발생시킴."""
        store = CsvStore(self.path)
        store.save([Book("원본", "저자", 2000, "기타", "1-1")])
        original = self.path.read_bytes()
        with mock.patch("bookmate.store.os.replace", side_effect=PermissionError("잠김")):
            with self.assertRaises(StoreError):
                store.save([Book("새것", "저자", 2001, "기타", "2-2")])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(store.temp_path.exists())

    def test_tc19_special_characters(self):
        tricky = Book('쉼표, "따옴표"\n줄바꿈', "저자", 2020, "기타", "9-9", 2.5, True, True)
        CsvStore(self.path).save([tricky])
        self.assertEqual(CsvStore(self.path).load().books, [tricky])

    def test_duplicate_isbn_in_file_skipped(self):
        lines = FIXTURE.read_text(encoding="utf-8").splitlines()
        self.path.write_text("\n".join(lines + [lines[1]]) + "\n", encoding="utf-8")
        manager = BookManager(CsvStore(self.path))
        result = manager.load()
        self.assertEqual((len(manager.books), result.skipped), (12, 1))


if __name__ == "__main__":
    unittest.main()
