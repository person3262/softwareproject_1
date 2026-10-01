"""UI-002 도서 등록·수정 대화상자."""
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from ..manager import BookManager, Result
from ..models import GENRES, Book

RATING_CHOICES = ["없음"] + [f"{i / 2:.1f}" for i in range(11)]  # 0.0 ~ 5.0
ERROR_STYLE = "border: 1px solid #d33;"


class BookDialog(QDialog):
    def __init__(self, manager: BookManager, book: Book | None = None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.book = book                  # None이면 등록 모드
        self.result_message = ""
        self.setWindowTitle("도서 수정" if book else "도서 등록")
        self.setMinimumWidth(420)

        self.title_edit = QLineEdit()
        self.author_edit = QLineEdit()
        self.year_edit = QLineEdit()
        self.year_edit.setPlaceholderText("예: 2006")
        self.isbn_edit = QLineEdit()
        self.isbn_edit.setPlaceholderText("숫자와 하이픈(-)")
        self.genre_combo = QComboBox()
        self.genre_combo.addItems(GENRES)
        self.rating_combo = QComboBox()
        self.rating_combo.addItems(RATING_CHOICES)
        self.read_check = QCheckBox("읽음")
        self.favorite_check = QCheckBox("즐겨찾기")

        # 필드 이름 → (입력 위젯, 오류 라벨)
        self.inputs = {
            "title": self.title_edit, "author": self.author_edit,
            "year": self.year_edit, "isbn": self.isbn_edit,
            "rating": self.rating_combo,
        }
        self.error_labels: dict[str, QLabel] = {}

        form = QFormLayout()
        form.addRow("제목 *", self._with_error("title", self.title_edit))
        form.addRow("저자 *", self._with_error("author", self.author_edit))
        form.addRow("출판연도 *", self._with_error("year", self.year_edit))
        form.addRow("ISBN *", self._with_error("isbn", self.isbn_edit))
        form.addRow("장르", self.genre_combo)
        form.addRow("별점", self._with_error("rating", self.rating_combo))
        checks = QHBoxLayout()
        checks.addWidget(self.read_check)
        checks.addWidget(self.favorite_check)
        checks.addStretch()
        form.addRow("", checks)

        save_btn = QPushButton("저장")
        save_btn.setDefault(True)          # Enter = 저장
        save_btn.clicked.connect(self.on_save)
        cancel_btn = QPushButton("취소")   # Esc = 취소 (QDialog 기본 동작)
        cancel_btn.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)

        if book:
            self._fill(book)

    def _with_error(self, name: str, widget: QWidget) -> QWidget:
        """입력 위젯 아래에 빨간 오류 라벨을 붙인 묶음을 만든다."""
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        label = QLabel()
        label.setStyleSheet("color: #d33; font-size: 11px;")
        label.hide()
        v.addWidget(widget)
        v.addWidget(label)
        self.error_labels[name] = label
        return box

    def _fill(self, book: Book) -> None:
        self.title_edit.setText(book.title)
        self.author_edit.setText(book.author)
        self.year_edit.setText(str(book.year))
        self.isbn_edit.setText(book.isbn)
        self.isbn_edit.setReadOnly(True)   # ISBN은 키이므로 수정 불가
        self.isbn_edit.setStyleSheet("background: #eee;")
        idx = self.genre_combo.findText(book.genre)
        self.genre_combo.setCurrentIndex(idx if idx >= 0 else len(GENRES) - 1)
        self.rating_combo.setCurrentText("없음" if book.rating is None else f"{book.rating:.1f}")
        self.read_check.setChecked(book.read)
        self.favorite_check.setChecked(book.favorite)

    def form_data(self) -> dict:
        rating = self.rating_combo.currentText()
        return {
            "title": self.title_edit.text(),
            "author": self.author_edit.text(),
            "year": self.year_edit.text(),
            "isbn": self.isbn_edit.text(),
            "genre": self.genre_combo.currentText(),
            "rating": "" if rating == "없음" else rating,
            "read": self.read_check.isChecked(),
            "favorite": self.favorite_check.isChecked(),
        }

    def on_save(self) -> None:
        data = self.form_data()
        if self.book is None:
            result = self.manager.add_book(data)
        else:
            result = self.manager.update_book(self.book.isbn, data)
        self._show_errors(result)
        if result.ok:
            self.result_message = result.message
            self.accept()

    def _show_errors(self, result: Result) -> None:
        for name, label in self.error_labels.items():
            label.hide()
            self.inputs[name].setStyleSheet("background: #eee;" if name == "isbn" and self.book else "")
        for err in result.errors:           # 실패해도 입력값은 그대로 유지 (EH-01)
            label = self.error_labels.get(err.field)
            if label and label.isHidden():
                label.setText(err.message)
                label.show()
                self.inputs[err.field].setStyleSheet(
                    ERROR_STYLE if not isinstance(self.inputs[err.field], QComboBox) else "")
        if result.errors:
            first = self.inputs.get(result.errors[0].field)
            if first:
                first.setFocus()
