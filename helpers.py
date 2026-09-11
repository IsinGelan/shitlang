
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Literal
if TYPE_CHECKING:
    from .shit_objs import ShitObject

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
