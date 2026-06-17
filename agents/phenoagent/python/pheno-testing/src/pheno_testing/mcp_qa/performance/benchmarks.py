"""
Benchmarking and profiling decorators.
"""

import functools
import time
from typing import Callable


def benchmark(func: Callable):
    """
    Decorator to benchmark function execution time.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.4f}s")
        return result

    return wrapper


def profile(func: Callable):
    """
    Decorator to profile function execution.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Would use cProfile or memory_profiler here
        return await func(*args, **kwargs)

    return wrapper
