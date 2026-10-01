"""UI-001 메인 화면 (MOD-008 화면 제어)."""
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..manager import BookManager, eul_reul
from ..models import Book
from ..store import StoreError
from .book_dialog import BookDialog
from .stats_dialog import StatsDialog

COLUMNS = ["★", "제목", "저자", "출판연도", "장르", "별점", "읽음"]
STAR_COL = 0
SEARCH_CHOICES = [("제목", "title"), ("저자", "author"), ("장르", "genre")]
MESSAGE_MS = 3000


class MainWindow(QMainWindow):
    def __init__(self, manager: BookManager):
        super().__init__()
        self.manager = manager
        self.goal = 20                    # 실행 중에만 유지되는 연간 목표
        self.search_state: tuple[str, str] | None = None  # 현재 검색 조건
        self.setWindowTitle("BookMate")
        self.setMinimumSize(900, 600)
        self._build_ui()

        load_result = self.manager.load()   # ① 기동 시 적재
        self.refresh_table()
        # 창이 뜬 다음에 안내 상자를 띄우기 위해 이벤트 루프로 미룬다
        QTimer.singleShot(0, lambda: self._notify_load(load_result))

    # ---------- 화면 구성 ----------
    def _build_ui(self) -> None:
        buttons = QHBoxLayout()
        for text, slot in [("+ 등록", self.on_add), ("수정", self.on_edit),
                           ("삭제", self.on_delete), ("통계", self.on_stats)]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            buttons.addWidget(btn)
        buttons.addStretch()

        self.field_combo = QComboBox()
        for label, field in SEARCH_CHOICES:
            self.field_combo.addItem(label, field)
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("검색어를 입력하고 Enter")
        self.keyword_edit.returnPressed.connect(self.on_search)
        search_btn = QPushButton("검색")
        search_btn.clicked.connect(self.on_search)
        all_btn = QPushButton("전체 보기")
        all_btn.clicked.connect(self.on_show_all)
        search = QHBoxLayout()
        search.addWidget(self.field_combo)
        search.addWidget(self.keyword_edit, 1)
        search.addWidget(search_btn)
        search.addWidget(all_btn)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.cellDoubleClicked.connect(lambda row, col: self.on_edit())

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(buttons)
        layout.addLayout(search)
        layout.addWidget(self.table)
        self.setCentralWidget(central)

        self.summary_label = QLabel()
        self.statusBar().addPermanentWidget(self.summary_label)

    # ---------- 목록 표시 ----------
    def refresh_table(self) -> None:
        if self.search_state:
            books = self.manager.search(*self.search_state)
        else:
            books = self.manager.list_all()
        self.table.setRowCount(len(books))
        for row, book in enumerate(books):
            self._fill_row(row, book)
        self._update_summary()

    def _fill_row(self, row: int, book: Book) -> None:
        values = [
            "★" if book.favorite else "☆",
            book.title, book.author, str(book.year), book.genre,
            "—" if book.rating is None else f"{book.rating:.1f}",
            "O" if book.read else "X",
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col != 1 and col != 2:
                item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, book.isbn)   # 어느 칸을 눌러도 ISBN을 알 수 있게
            self.table.setItem(row, col, item)

    def _update_summary(self) -> None:
        s = self.manager.get_stats(self.goal)
        self.summary_label.setText(
            f"총 {s.total}권 · 읽은 책 {s.read_count}권 · 즐겨찾기 {s.favorite_count}권")

    def _selected_isbn(self) -> str | None:
        row = self.table.currentRow()
        if row < 0 or not self.table.selectionModel().hasSelection():
            return None
        return self.table.item(row, 1).data(Qt.UserRole)

    def _find_book(self, isbn: str) -> Book | None:
        """BookManager의 공개 메서드(list_all)만으로 도서를 찾는다."""
        return next((b for b in self.manager.list_all() if b.isbn == isbn), None)

    def _show_all_after_change(self, message: str) -> None:
        """등록·수정·삭제 후에는 전체 목록으로 돌아간다(그림 4-3)."""
        self.keyword_edit.clear()
        self.search_state = None
        self.refresh_table()
        self.statusBar().showMessage(message, MESSAGE_MS)

    def _need_selection(self) -> str | None:
        isbn = self._selected_isbn()
        if isbn is None:
            QMessageBox.information(self, "BookMate", "도서를 먼저 선택하세요")  # EH-04
        return isbn

    # ---------- 슬롯 ----------
    def on_add(self) -> None:
        dialog = BookDialog(self.manager, parent=self)
        if dialog.exec_():
            self._show_all_after_change(dialog.result_message)

    def on_edit(self) -> None:
        isbn = self._need_selection()
        if isbn is None:
            return
        book = self._find_book(isbn)
        if book is None:
            QMessageBox.information(self, "BookMate", "대상 도서를 찾을 수 없습니다")
            return
        dialog = BookDialog(self.manager, book, parent=self)
        if dialog.exec_():
            self._show_all_after_change(dialog.result_message)

    def on_delete(self) -> None:
        isbn = self._need_selection()
        if isbn is None:
            return
        book = self._find_book(isbn)
        title = book.title if book else isbn
        box = QMessageBox(QMessageBox.Question, "삭제 확인",
                          f"'{title}'{eul_reul(title)} 삭제하시겠습니까?",
                          QMessageBox.Yes | QMessageBox.No, self)
        box.button(QMessageBox.Yes).setText("예")       # 버튼 글자를 한국어로
        box.button(QMessageBox.No).setText("아니오")
        box.setDefaultButton(QMessageBox.No)            # 실수로 Enter를 눌러도 안전
        if box.exec_() != QMessageBox.Yes:
            return
        result = self.manager.delete_book(isbn)
        if not result.ok:
            QMessageBox.information(self, "BookMate", result.message)
            return
        self._show_all_after_change(result.message)

    def on_search(self) -> None:
        keyword = self.keyword_edit.text().strip()
        if not keyword:
            self.on_show_all()
            return
        self.search_state = (self.field_combo.currentData(), keyword)
        self.refresh_table()
        if self.table.rowCount() == 0:
            self.statusBar().showMessage("검색 결과가 없습니다", MESSAGE_MS)  # EH-02
        else:
            self.statusBar().showMessage(f"{self.table.rowCount()}건 검색됨", MESSAGE_MS)

    def on_show_all(self) -> None:
        self.keyword_edit.clear()
        self.search_state = None
        self.refresh_table()

    def on_cell_clicked(self, row: int, col: int) -> None:
        if col != STAR_COL:
            return
        isbn = self.table.item(row, col).data(Qt.UserRole)
        try:
            favorite = self.manager.toggle_favorite(isbn)
        except KeyError:
            QMessageBox.information(self, "BookMate", "대상 도서를 찾을 수 없습니다")  # EH-04
            return
        self.table.item(row, STAR_COL).setText("★" if favorite else "☆")  # 해당 칸만 갱신
        self._update_summary()

    def on_stats(self) -> None:
        stats = self.manager.get_stats(self.goal)            # 그림 4-5: 먼저 계산해서
        dialog = StatsDialog(self.manager, stats, parent=self)  # 통계 창에 전달
        dialog.exec_()
        self.goal = dialog.goal

    # ---------- 기동 안내 / 종료 저장 ----------
    def _notify_load(self, result) -> None:
        if result.backup:
            QMessageBox.warning(
                self, "BookMate",
                "books.csv의 형식이 올바르지 않아 books.csv.bak으로 백업하고 빈 목록으로 시작합니다.")
        elif result.skipped:
            QMessageBox.warning(
                self, "BookMate", f"형식이 잘못된 {result.skipped}개 행을 건너뛰었습니다.")

    def closeEvent(self, event) -> None:
        try:
            self.manager.save()                      # ⑦ 종료 시 자동 저장
        except StoreError:
            QMessageBox.warning(                     # EH-03
                self, "BookMate",
                "저장에 실패했습니다. 원본 파일은 그대로 유지됩니다.\n"
                "books.csv가 다른 프로그램(엑셀 등)에서 열려 있는지 확인하세요.")
        event.accept()
