
from typing import Callable, Iterable, Iterator

# ================================
def pairs_overlapping[T](it: Iterable[T]) -> Iterator[tuple[T, T]]:
    last = None
    for el in it:
        if last is not None:
            yield last, el
        last = el

def last[T](it: Iterable[T]) -> T | None:
    last_el = None
    for el in it:
        last_el = el
    return last_el

def func_and[T: Callable[..., bool]](*funcs: T) -> T:
    def combined(*args, **kwargs) -> bool:
        return all(func(*args, **kwargs) for func in funcs)
    return combined
def func_or[T: Callable[..., bool]](*funcs: T) -> T:
    def combined(*args, **kwargs) -> bool:
        return any(func(*args, **kwargs) for func in funcs)
    return combined