# BookMate — 개인 도서 관리 시스템

## 설치·실행 (Windows)
1. Python 3.14.7 설치 ("Add python.exe to PATH" 선택)
2. 이 폴더에서 명령 프롬프트 실행
3. `python -m venv .venv`
4. `.venv\Scripts\activate`
5. `pip install -r requirements.txt`
6. `python main.py`

샘플 데이터로 시작하려면 `tests\fixtures\sample_books.csv`를 이 폴더에 `books.csv`로 복사하세요.

## 테스트
`python -m unittest -v`

- TC-16(읽기 전용 파일 저장)은 Windows에서만 실행되고, 다른 운영체제에서는 건너뜁니다.
- TC-18의 목록 갱신 성능은 창을 띄우지 않는 offscreen 모드로 측정합니다.

## 구조
| 파일 | 모듈 |
|---|---|
| bookmate/models.py | MOD-007 Book |
| bookmate/validator.py | MOD-006 Validator |
| bookmate/manager.py | MOD-001~004 BookManager |
| bookmate/store.py | MOD-005 CsvStore |
| bookmate/ui/ | MOD-008 MainWindow · BookDialog · StatsDialog |
