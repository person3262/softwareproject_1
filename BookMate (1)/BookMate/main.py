"""BookMate 진입점."""
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from bookmate.manager import BookManager
from bookmate.store import CsvStore
from bookmate.ui.main_window import MainWindow

# 실행 위치와 관계없이 main.py가 있는 폴더의 books.csv를 사용한다
DATA_PATH = Path(__file__).resolve().parent / "books.csv"


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow(BookManager(CsvStore(DATA_PATH)))
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
