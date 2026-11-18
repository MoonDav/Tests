import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from decorators import logger


class TestLoggerDecorator(unittest.TestCase):
    """Тесты для декоратора @logger."""

    def setUp(self):
        # Временный файл для каждого теста
        self.tmp_fd, self.log_path = tempfile.mkstemp(suffix='.log')
        os.close(self.tmp_fd)

    def tearDown(self):
        if os.path.exists(self.log_path):
            os.remove(self.log_path)

    def _read_log(self):
        with open(self.log_path, 'r', encoding='utf-8') as f:
            return f.read()

    # ------------------------------------------------------------------
    # 1. Базовое поведение: результат и запись в лог
    # ------------------------------------------------------------------
    def test_returns_original_result(self):
        @logger(self.log_path)
        def add(a, b):
            return a + b

        self.assertEqual(add(2, 3), 5)

    def test_creates_log_file_if_missing(self):
        os.remove(self.log_path)
        self.assertFalse(os.path.exists(self.log_path))

        @logger(self.log_path)
        def func():
            return 42

        func()
        self.assertTrue(os.path.exists(self.log_path))

    def test_logs_one_line_per_call(self):
        @logger(self.log_path)
        def func():
            return 'ok'

        func()
        func()
        func()

        lines = self._read_log().strip().split('\n')
        self.assertEqual(len(lines), 3)

    def test_log_entry_format(self):
        @logger(self.log_path)
        def greet(name, greeting='Hello'):
            return f'{greeting}, {name}!'

        greet('World', greeting='Hi')

        line = self._read_log().strip()
        # Пример: 2024-01-01 12:00:00 - greet('World', greeting='Hi') -> returned 'Hi, World!'
        self.assertIn(" - greet('World', greeting='Hi') -> returned 'Hi, World!'", line)

    def test_logs_positional_and_keyword_args(self):
        @logger(self.log_path)
        def func(a, b, c=0):
            return a + b + c

        func(1, 2, c=3)
        line = self._read_log().strip()

        self.assertIn("func(1, 2, c=3)", line)
        self.assertIn("returned 6", line)

    def test_logs_return_none(self):
        @logger(self.log_path)
        def func():
            pass

        func()
        self.assertIn("func() -> returned None", self._read_log())

    # ------------------------------------------------------------------
    # 2. Обработка исключений
    # ------------------------------------------------------------------
    def test_exception_is_propagated(self):
        @logger(self.log_path)
        def boom():
            raise ValueError('kaboom')

        with self.assertRaises(ValueError) as ctx:
            boom()
        self.assertEqual(str(ctx.exception), 'kaboom')

    def test_exception_is_logged(self):
        @logger(self.log_path)
        def boom(x):
            raise ValueError(f'bad {x}')

        with self.assertRaises(ValueError):
            boom(7)

        log = self._read_log()
        self.assertIn("boom(7) -> raised ValueError: bad 7", log)

    def test_log_written_when_exception_raised(self):
        @logger(self.log_path)
        def boom():
            raise RuntimeError('x')

        with self.assertRaises(RuntimeError):
            boom()

        self.assertTrue(os.path.exists(self.log_path))
        self.assertIn('raised RuntimeError: x', self._read_log())

    # ------------------------------------------------------------------
    # 3. Сохранение метаданных (functools.wraps)
    # ------------------------------------------------------------------
    def test_preserves_function_name(self):
        @logger(self.log_path)
        def my_func():
            """Docstring."""
            return 1

        self.assertEqual(my_func.__name__, 'my_func')
        self.assertEqual(my_func.__doc__, 'Docstring.')

    # ------------------------------------------------------------------
    # 4. Формат времени
    # ------------------------------------------------------------------
    @patch('decorators.datetime')
    def test_timestamp_format(self, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 5, 17, 13, 45, 30)

        @logger(self.log_path)
        def func():
            return 1

        func()
        line = self._read_log().strip()
        self.assertTrue(line.startswith('2024-05-17 13:45:30 - '))

    # ------------------------------------------------------------------
    # 5. Разные типы аргументов (repr)
    # ------------------------------------------------------------------
    def test_logs_various_argument_types(self):
        @logger(self.log_path)
        def func(items, mapping, text, number):
            return 'done'

        func([1, 2], {'a': 1}, 'hi', None)

        line = self._read_log().strip()
        self.assertIn("func([1, 2], {'a': 1}, 'hi', None)", line)

    # ------------------------------------------------------------------
    # 6. Дозапись в существующий файл
    # ------------------------------------------------------------------
    def test_appends_to_existing_file(self):
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write('previous line\n')

        @logger(self.log_path)
        def func():
            return 1

        func()
        log = self._read_log()
        self.assertTrue(log.startswith('previous line\n'))
        self.assertIn('func()', log)

    # ------------------------------------------------------------------
    # 7. Разные декорируемые функции используют общий лог
    # ------------------------------------------------------------------
    def test_multiple_functions_share_log(self):
        @logger(self.log_path)
        def one():
            return 1

        @logger(self.log_path)
        def two():
            return 2

        one()
        two()

        log = self._read_log()
        self.assertIn('one()', log)
        self.assertIn('two()', log)

    # ------------------------------------------------------------------
    # 8. Возвращаемое значение не искажается
    # ------------------------------------------------------------------
    def test_complex_return_value(self):
        @logger(self.log_path)
        def func():
            return {'a': [1, 2], 'b': None}

        result = func()
        self.assertEqual(result, {'a': [1, 2], 'b': None})
        self.assertIn("returned {'a': [1, 2], 'b': None}", self._read_log())


if __name__ == '__main__':
    unittest.main()
