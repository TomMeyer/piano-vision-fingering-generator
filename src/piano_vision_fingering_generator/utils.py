from functools import wraps
import cProfile


def profile(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        try:
            result = func(*args, **kwargs)
        finally:
            profiler.disable()
            profiler.print_stats()
        return result

    return wrapper
