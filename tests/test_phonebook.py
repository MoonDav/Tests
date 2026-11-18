import csv
import subprocess
import sys
from pathlib import Path

import pytest


# ---------- Путь к тестируемому скрипту ----------
# test_phonebook.py лежит в tests/, phonebook.py — в корне проекта (на уровень выше)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = PROJECT_ROOT / "phonebook.py"


# ---------- Вспомогательные функции ----------
def write_csv(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter=",").writerows(rows)


def read_csv(path: Path) -> list[list[str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.reader(f, delimiter=","))


HEADER = ["lastname", "firstname", "surname", "organization",
          "position", "phone", "email"]


@pytest.fixture(scope="session", autouse=True)
def _check_script_exists():
    """Раннее падение с понятным сообщением, если путь к скрипту неверный."""
    assert SCRIPT_PATH.is_file(), (
        f"Не найден phonebook.py по пути: {SCRIPT_PATH}. "
        f"Проверьте структуру проекта: phonebook.py должен лежать "
        f"в корне, а тесты — в tests/."
    )


@pytest.fixture
def run_script(tmp_path):
    """Запускает phonebook.py в изолированной временной папке.

    Возвращает функцию run(rows) -> результат (list[list[str]]).
    """

    def run(rows: list[list[str]]) -> list[list[str]]:
        # готовим входной файл в tmp_path
        write_csv(tmp_path / "phonebook_raw.csv", rows)

        # запускаем скрипт с cwd = tmp_path, чтобы он читал/писал туда,
        # а не в рабочую директорию проекта
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Скрипт упал:\nstdout={result.stdout}\nstderr={result.stderr}"
        )
        return read_csv(tmp_path / "phonebook.csv")

    return run


# ---------- Тесты ФИО ----------
def test_fio_all_in_one_cell(run_script):
    """ФИО полностью в первой ячейке."""
    out = run_script([
        HEADER,
        ["Иванов Иван Иванович", "", "", "Орг", "должность",
         "8 (999) 123-45-67", "a@b.c"],
    ])
    assert out[1][0:3] == ["Иванов", "Иван", "Иванович"]


def test_fio_family_separate_io_together(run_script):
    """Фамилия отдельно, имя+отчество одной строкой."""
    out = run_script([
        HEADER,
        ["Петров", "Пётр Петрович", "", "Орг", "",
         "+7 999 123 45 68", ""],
    ])
    assert out[1][0:3] == ["Петров", "Пётр", "Петрович"]


def test_fio_only_family_and_name(run_script):
    """Есть только фамилия и имя — отчество пустое."""
    out = run_script([
        HEADER,
        ["Сидоров", "Сидор", "", "Орг", "", "8-800-555-35-35", ""],
    ])
    assert out[1][0:3] == ["Сидоров", "Сидор", ""]


# ---------- Тесты телефонов ----------
@pytest.mark.parametrize("raw, expected", [
    ("8 (999) 123-45-67",          "+7(999)123-45-67"),
    ("+7 999 123 45 67",           "+7(999)123-45-67"),
    ("9991234567",                "+7(999)123-45-67"),
    ("(999) 765-43-21",            "+7(999)765-43-21"),
    ("8.999.444.55.66",            "+7(999)444-55-66"),
    ("+7 (495) 913-04-78",         "+7(495)913-04-78"),
])
def test_phone_basic_formats(run_script, raw, expected):
    out = run_script([HEADER, ["Иванов", "Иван", "", "", "", raw, ""]])
    assert out[1][5] == expected


@pytest.mark.parametrize("raw, expected", [
    ("+7 (495) 983-36-99 доб. 2926",   "+7(495)983-36-99 доб.2926"),
    ("+7 (495) 913-11-11 (доб. 0792)", "+7(495)913-11-11 доб.0792"),
    ("8(999)111-22-33 доб. 99",        "+7(999)111-22-33 доб.99"),
])
def test_phone_with_extension(run_script, raw, expected):
    """Добавочный в разных формах — в т.ч. в скобках."""
    out = run_script([HEADER, ["Иванов", "Иван", "", "", "", raw, ""]])
    assert out[1][5] == expected


def test_phone_empty(run_script):
    out = run_script([HEADER, ["Иванов", "Иван", "", "", "", "", ""]])
    assert out[1][5] == ""


# ---------- Тесты слияния дублей ----------
def test_duplicates_merged_by_family_and_name(run_script):
    out = run_script([
        HEADER,
        ["Иванов", "Иван", "Иванович", "Орг", "директор",
         "8 (999) 123-45-67", "ivanov@example.com"],
        ["Иванов Иван", "Иванович", "", "Орг", "",
         "+7 999 123 45 67", ""],
    ])
    assert len(out) == 2
    assert out[1][0:2] == ["Иванов", "Иван"]


def test_duplicates_fill_empty_fields(run_script):
    """Дубли дополняют друг друга по пустым полям."""
    out = run_script([
        HEADER,
        ["Иванов", "Иван", "", "", "", "", "ivanov@example.com"],
        ["Иванов", "Иван", "Иванович", "Орг", "директор",
         "+7(999)123-45-67", ""],
    ])
    assert len(out) == 2
    row = out[1]
    assert row[0:3] == ["Иванов", "Иван", "Иванович"]
    assert row[3] == "Орг"
    assert row[4] == "директор"
    assert row[5] == "+7(999)123-45-67"
    assert row[6] == "ivanov@example.com"


def test_phone_with_extension_wins_over_plain(run_script):
    """Телефон с добавочным имеет приоритет над телефоном без него."""
    out = run_script([
        HEADER,
        ["Лагунцов", "Иван", "Алексеевич", "Минфин", "",
         "+7 (495) 913-11-11 (доб. 0792)", ""],
        ["Лагунцов", "Иван", "", "", "", "", "Ivan.Laguntcov@minfin.ru"],
    ])
    assert len(out) == 2
    row = out[1]
    assert row[5] == "+7(495)913-11-11 доб.0792"
    assert row[6] == "Ivan.Laguntcov@minfin.ru"


def test_phone_plain_kept_when_duplicate_has_none(run_script):
    """Если у дубля телефона нет — исходный телефон сохраняется."""
    out = run_script([
        HEADER,
        ["Иванов", "Иван", "", "", "", "+7(999)123-45-67", ""],
        ["Иванов", "Иван", "", "", "", "", "ivanov@example.com"],
    ])
    assert out[1][5] == "+7(999)123-45-67"
    assert out[1][6] == "ivanov@example.com"


def test_different_people_not_merged(run_script):
    out = run_script([
        HEADER,
        ["Иванов", "Иван", "", "", "", "", ""],
        ["Петров", "Пётр", "", "", "", "", ""],
    ])
    assert len(out) == 3


def test_same_family_different_name_not_merged(run_script):
    out = run_script([
        HEADER,
        ["Иванов", "Иван", "", "", "", "", ""],
        ["Иванов", "Пётр", "", "", "", "", ""],
    ])
    assert len(out) == 3


def test_case_insensitive_key(run_script):
    """Регистр фамилии/имени не должен мешать слиянию."""
    out = run_script([
        HEADER,
        ["Иванов", "Иван", "", "", "", "+7(999)123-45-67", ""],
        ["иванов", "иван", "", "Орг", "", "", ""],
    ])
    assert len(out) == 2
    assert out[1][3] == "Орг"


# ---------- Полный сценарий из задания ----------
def test_full_scenario_from_task(run_script):
    """Прогон реального набора из ДЗ (сокращённый, но с ключевыми кейсами)."""
    rows = [
        HEADER,
        ["Усольцев Олег Валентинович", "", "", "ФНС",
         "главный специалист", "+7 (495) 913-04-78", "opendata@nalog.ru"],
        ["Мартиняхин Виталий Геннадьевич", "", "", "ФНС", "",
         "+74959130037", ""],
        ["Наркаев", "Вячеслав Рифхатович", "", "ФНС", "",
         "8 495-913-0168", ""],
        ["Мартиняхин", "Виталий", "Геннадьевич", "ФНС", "советник", "", ""],
        ["Лукина Ольга", "", "Владимировна", "Минфин", "",
         "+7 (495) 983-36-99 доб. 2926", "Olga.Lukina@minfin.ru"],
        ["Паньшин Алексей Владимирович", "", "", "Минфин", "",
         "8(495)748-49-73", "1248@minfin.ru"],
        ["Лагунцов Иван Алексеевич", "", "", "Минфин", "",
         "+7 (495) 913-11-11 (доб. 0792)", ""],
        ["Лагунцов Иван", "", "", "", "", "", "Ivan.Laguntcov@minfin.ru"],
        ["Лукина", "Оксана", "Владимировна", "Минфин", "",
         "+7 (495) 983-36-99 доб. 2929", "OLukina@minfin.ru"],
    ]
    out = run_script(rows)

    # 7 уникальных людей + header
    assert len(out) == 1 + 7

    by_key = {(r[0], r[1]): r for r in out[1:]}

    # Лагунцов: ФИО + добавочный + email из дубля
    lag = by_key[("Лагунцов", "Иван")]
    assert lag[2] == "Алексеевич"
    assert lag[5] == "+7(495)913-11-11 доб.0792"
    assert lag[6] == "Ivan.Laguntcov@minfin.ru"

    # Мартиняхин: должность из второй записи + телефон из первой
    mart = by_key[("Мартиняхин", "Виталий")]
    assert mart[2] == "Геннадьевич"
    assert mart[4] == "советник"
    assert mart[5] == "+7(495)913-00-37"

    # Лукина Ольга и Лукина Оксана — два разных человека
    assert ("Лукина", "Ольга") in by_key
    assert ("Лукина", "Оксана") in by_key
    assert by_key[("Лукина", "Ольга")][5] == "+7(495)983-36-99 доб.2926"
    assert by_key[("Лукина", "Оксана")][5] == "+7(495)983-36-99 доб.2929"
