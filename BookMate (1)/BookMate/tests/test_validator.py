import unittest

from bookmate.validator import Validator


def data(**kw):
    base = {"title": "코스모스", "author": "칼 세이건", "year": "2006",
            "isbn": "978-89-01", "genre": "과학", "rating": "", "read": False, "favorite": False}
    base.update(kw)
    return base


class ValidatorTest(unittest.TestCase):
    def setUp(self):
        self.v = Validator()

    def fields(self, errors):
        return [e.field for e in errors]

    def test_valid(self):
        self.assertEqual(self.v.validate(data()), [])

    def test_tc02_title_missing(self):
        errors = self.v.validate(data(title="  "))
        self.assertEqual(self.fields(errors), ["title"])

    def test_tc03_year_not_number(self):
        errors = self.v.validate(data(year="이천육"))
        self.assertEqual(errors[0].message, "출판연도는 숫자로 입력하세요")

    def test_year_range(self):
        self.assertEqual(self.fields(self.v.validate(data(year="999"))), ["year"])
        self.assertEqual(self.fields(self.v.validate(data(year="9999"))), ["year"])

    def test_tc04_duplicate_isbn(self):
        errors = self.v.validate(data(), existing_isbns={"978-89-01"})
        self.assertEqual(errors[0].message, "이미 등록된 도서입니다")

    def test_isbn_format(self):
        for bad in ("ABC", "---", "978 89"):
            self.assertEqual(self.fields(self.v.validate(data(isbn=bad))), ["isbn"], bad)

    def test_tc06_rating_range(self):
        for bad in ("5.5", "-1.0", "3.3", "별"):
            self.assertEqual(self.fields(self.v.validate(data(rating=bad))), ["rating"], bad)
        for ok in ("0.0", "2.5", "5.0", ""):
            self.assertEqual(self.v.validate(data(rating=ok)), [], ok)

    def test_collects_all_errors(self):
        errors = self.v.validate(data(title="", author="", year="", isbn=""))
        self.assertEqual(len(errors), 4)


if __name__ == "__main__":
    unittest.main()
