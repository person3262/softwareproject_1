"""UI-003 독서 통계 대화상자."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QSpinBox, QVBoxLayout,
)

from ..manager import BookManager, Stats


class StatsDialog(QDialog):
    def __init__(self, manager: BookManager, stats: Stats, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("독서 통계")
        self.setMinimumWidth(460)

        grid = QGridLayout()
        self.cards: dict[str, QLabel] = {}
        for i, (key, caption) in enumerate(
            [("total", "등록 도서"), ("read_count", "읽은 책"),
             ("avg_rating", "평균 별점"), ("favorite_count", "즐겨찾기")]
        ):
            grid.addWidget(self._card(key, caption), i // 2, i % 2)

        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(1, 999)
        self.goal_spin.setValue(stats.goal)     # 연결 전에 값을 넣어 불필요한 재계산을 막음
        self.goal_spin.setSuffix(" 권")
        self.goal_spin.valueChanged.connect(self.refresh)
        goal_row = QHBoxLayout()
        goal_row.addWidget(QLabel("연간 목표 권수"))
        goal_row.addWidget(self.goal_spin)
        goal_row.addStretch()

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.count_label = QLabel()
        self.rate_label = QLabel()

        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addSpacing(8)
        layout.addLayout(goal_row)
        layout.addWidget(self.progress)
        layout.addWidget(self.count_label)
        layout.addWidget(self.rate_label)
        layout.addLayout(bottom)

        self.show_stats(stats)                  # MainWindow가 계산해 넘겨준 Stats 표시

    def _card(self, key: str, caption: str) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        v = QVBoxLayout(frame)
        cap = QLabel(caption)
        cap.setStyleSheet("color: #666;")
        value = QLabel("-")
        value.setStyleSheet("font-size: 22px; font-weight: bold;")
        value.setAlignment(Qt.AlignRight)
        v.addWidget(cap)
        v.addWidget(value)
        self.cards[key] = value
        return frame

    @property
    def goal(self) -> int:
        return self.goal_spin.value()

    def refresh(self) -> None:
        """목표 권수를 바꿨을 때만 다시 계산을 요청한다."""
        self.show_stats(self.manager.get_stats(self.goal))

    def show_stats(self, s: Stats) -> None:
        self.cards["total"].setText(f"{s.total}권")
        self.cards["read_count"].setText(f"{s.read_count}권")
        self.cards["avg_rating"].setText("-" if s.avg_rating is None else f"{s.avg_rating:.1f}")
        self.cards["favorite_count"].setText(f"{s.favorite_count}권")
        percent = min(100, round(s.read_count / s.goal * 100))
        self.progress.setValue(percent)
        self.count_label.setText(f"{s.read_count} / {s.goal}권")
        self.rate_label.setText(
            f"달성률 {percent}% · {'목표 달성' if s.achieved else '목표 미달성'}")
