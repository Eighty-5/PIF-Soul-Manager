import time
from functools import wraps
import logging


def func_timer(og_func):
    @wraps(og_func)
    def wrapper(*args, **kwargs):
        t0 = time.time()
        result = og_func(*args, **kwargs)
        t1 = time.time() - t0
        print(f"{og_func.__name__} ran in: {t1}s")
        return result
    return wrapper

def func_logger(og_func):
    logging.basicConfig(filename="functions.log", level=logging.INFO)
    
    @wraps(og_func)
    def wrapper(*args, **kwargs):
        logging.info(
            f"{og_func.__name__} ran with args: {args} and kwargs: {kwargs}"
        )
        return og_func(*args, **kwargs)
    return wrapper