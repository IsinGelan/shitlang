
from os import path
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Literal, Optional
if TYPE_CHECKING:
    from .shit_objs import ShitObject

# ================================
def find[T](iter: Iterable[T], pred: Callable[[T], bool]) -> Optional[T]:
    for item in iter:
        if pred(item):
            return item
    return None

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

def split[T](it: Iterable[T], predicate: Callable[[T], bool]) -> tuple[list[T], list[T]]:
    """Splits an iterable into two lists based on a predicate."""
    true_list = []
    false_list = []
    for el in it:
        if predicate(el):
            true_list.append(el)
        else:
            false_list.append(el)
    return true_list, false_list

# ================================
def func_and[T: Callable[..., bool]](*funcs: T) -> T:
    def combined(*args, **kwargs) -> bool:
        return all(func(*args, **kwargs) for func in funcs)
    return combined
def func_or[T: Callable[..., bool]](*funcs: T) -> T:
    def combined(*args, **kwargs) -> bool:
        return any(func(*args, **kwargs) for func in funcs)
    return combined

# ================================
InsertionPos = Literal["before", "after"]
position_sorting = {"before": 0, "after": 1}
Insertion = tuple[InsertionPos, Any, Any] # position, reference node, node to insert

def multi_insert(l: list, *insertions: Insertion) -> None:
    """do multiple insertions into a list at once, without messing up the indices of the reference nodes"""
    insertions_with_indices = [
        (ins, l.index(ins[1]))
        for ins in insertions]
    sorted_insertions = sorted(
        insertions_with_indices,
        key=lambda ins_ind: (ins_ind[1], position_sorting[ins_ind[0][0]]))
    
    insertions_done = 0
    for (ref_node_ind, ref_node, new_node), ref_node_ind in sorted_insertions:
        insertion_index = insertions_done + ref_node_ind + (1 if ref_node_ind == "after" else 0)
        l.insert(insertion_index, new_node)
        insertions_done += 1

# ================================
def dir_here(where: str = __file__) -> str:
    return path.dirname(path.realpath(where))

# ================================
def timed[C: Callable](func: C) -> C:
    """Decorator to time a function and print its execution time."""
    import time
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Function '{func.__name__}' executed in {elapsed_time:.4f} seconds.")
        return result
    return wrapper

# ================================
class LocalNumbers:
    """to assign numbers locally and keep track of which numbers were assigned"""
    def __init__(self):
        self.highest = 0
    def __next__(self):
        res = self.highest
        self.highest += 1
        return res
    def all_numbers(self) -> list[int]:
        return list(range(self.highest))