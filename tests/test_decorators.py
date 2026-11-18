import os
from datetime import datetime

import pytest

from decorators import logger


# ----------------------------------------------------------------------
# Фикстуры
# ----------------------------------------------------------------------
@pytest.fixture
def log_path(tmp_path):
    """Уникальный путь к лог-файлу на каждый тест."""
    return tmp_path / 'test.log'


def read_log(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# ----------------------------------------------------------------------
# 1. Базовое поведение
# ----------------------------------------------------------------------
def test_returns_original_result(log_path):
    @logger(log_path)
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_creates_log_file_if_missing(log_path):
    assert not os.path.exists(log_path)

    @logger(log_path)
    def func():
        return 42

    func()
    assert os.path.exists(log_path)


def test_logs_one_line_per_call(log_path):
    @logger(log_path)
    def func():
        return 'ok'

    func()
    func()
    func()

    lines = read_log(log_path).strip().split('\n')
    assert len(lines) == 3


def test_log_entry_format(log_path):
    @logger(log_path)
    def greet(name, greeting='Hello'):
        return f'{greeting}, {name}!'

    greet('World', greeting='Hi')

    line = read_log(log_path).strip()
    assert " - greet('World', greeting='Hi') -> returned 'Hi, World!'" in line


def test_logs_positional_and_keyword_args(log_path):
    @logger(log_path)
    def func(a, b, c=0):
        return a + b + c

    func(1, 2, c=3)
    line = read_log(log_path).strip()

    assert "func(1, 2, c=3)" in line
    assert "returned 6" in line


def test_logs_return_none(log_path):
    @logger(log_path)
    def func():
        pass

    func()
    assert "func() -> returned None" in read_log(log_path)


# ----------------------------------------------------------------------
# 2. Обработка исключений
# ----------------------------------------------------------------------
def test_exception_is_propagated(log_path):
    @logger(log_path)
    def boom():
        raise ValueError('kaboom')

    with pytest.raises(ValueError, match='kaboom'):
        boom()


def test_exception_is_logged(log_path):
    @logger(log_path)
    def boom(x):
        raise ValueError(f'bad {x}')

    with pytest.raises(ValueError):
        boom(7)

    assert "boom(7) -> raised ValueError: bad 7" in read_log(log_path)


def test_log_written_when_exception_raised(log_path):
    @logger(log_path)
    def boom():
        raise RuntimeError('x')

    with pytest.raises(RuntimeError):
        boom()

    assert os.path.exists(log_path)
    assert 'raised RuntimeError: x' in read_log(log_path)


# ----------------------------------------------------------------------
# 3. Сохранение метаданных (functools.wraps)
# ----------------------------------------------------------------------
def test_preserves_function_name(log_path):
    @logger(log_path)
    def my_func():
        """Docstring."""
        return 1

    assert my_func.__name__ == 'my_func'
    assert my_func.__doc__ == 'Docstring.'


# ----------------------------------------------------------------------
# 4. Формат времени
# ----------------------------------------------------------------------
def test_timestamp_format(log_path, mocker):
    mock_datetime = mocker.patch('decorators.datetime')
    mock_datetime.now.return_value = datetime(2024, 5, 17, 13, 45, 30)

    @logger(log_path)
    def func():
        return 1

    func()
    line = read_log(log_path).strip()
    assert line.startswith('2024-05-17 13:45:30 - ')


# ----------------------------------------------------------------------
# 5. Разные типы аргументов (repr)
# ----------------------------------------------------------------------
def test_logs_various_argument_types(log_path):
    @logger(log_path)
    def func(items, mapping, text, number):
        return 'done'

    func([1, 2], {'a': 1}, 'hi', None)

    line = read_log(log_path).strip()
    assert "func([1, 2], {'a': 1}, 'hi', None)" in line


# ----------------------------------------------------------------------
# 6. Дозапись в существующий файл
# ----------------------------------------------------------------------
def test_appends_to_existing_file(log_path):
    log_path.write_text('previous line\n', encoding='utf-8')

    @logger(log_path)
    def func():
        return 1

    func()
    log = read_log(log_path)
    assert log.startswith('previous line\n')
    assert 'func()' in log


# ----------------------------------------------------------------------
# 7. Разные функции используют общий лог
# ----------------------------------------------------------------------
def test_multiple_functions_share_log(log_path):
    @logger(log_path)
    def one():
        return 1

    @logger(log_path)
    def two():
        return 2

    one()
    two()

    log = read_log(log_path)
    assert 'one()' in log
    assert 'two()' in log


# ----------------------------------------------------------------------
# 8. Возвращаемое значение не искажается
# ----------------------------------------------------------------------
def test_complex_return_value(log_path):
    @logger(log_path)
    def func():
        return {'a': [1, 2], 'b': None}

    result = func()
    assert result == {'a': [1, 2], 'b': None}
    assert "returned {'a': [1, 2], 'b': None}" in read_log(log_path)


# ----------------------------------------------------------------------
# 9. Параметризация (бонус — то, чего нет в unittest-варианте)
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    'args, kwargs, expected',
    [
        ((), {}, 'func()'),
        ((1, 2), {}, 'func(1, 2)'),
        ((), {'x': 1, 'y': 'z'}, "func(x=1, y='z')"),
        ((1,), {'x': 'a'}, "func(1, x='a')"),
        ((None, True, [1]), {}, 'func(None, True, [1])'),
    ],
)
def test_signature_formatting(log_path, args, kwargs, expected):
    @logger(log_path)
    def func(*a, **kw):
        return None

    func(*args, **kwargs)
    assert expected in read_log(log_path)
