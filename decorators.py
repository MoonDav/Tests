import os
from datetime import datetime
from functools import wraps


def logger(path):
	def __logger(old_function):
		@wraps(old_function)
		def new_function(*args, **kwargs):
			call_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

			args_repr = [repr(a) for a in args]
			kwargs_repr = [f'{k}={v!r}' for k, v in kwargs.items()]
			signature = ', '.join(args_repr + kwargs_repr)

			try:
				result = old_function(*args, **kwargs)
				status = f'returned {result!r}'
			except Exception as e:
				status = f'raised {type(e).__name__}: {e}'
				raise
			finally:
				with open(path, 'a', encoding='utf-8') as log_file:
					log_file.write(
						f'{call_time} - {old_function.__name__}({signature}) -> {status}\n'
					)

			return result

		return new_function

	return __logger
