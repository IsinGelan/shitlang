
from typing import Iterable, Iterator

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

