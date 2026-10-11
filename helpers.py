
import hashlib
from os import path
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Iterator, Literal, Optional

from pydantic import BaseModel, ValidatorFunctionWrapHandler, model_validator
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

def static_file_hash(code: str) -> str:
    m = hashlib.sha256(code.encode("utf-8"))
    return m.hexdigest()

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

# ================================
def deserializable_poly_superclass(distinctor_attr_name: str):
    """Decorator to make a polymorphic pydantic superclass deserializable.\n
    Adds subclass registry. Use together with `@deserializer(distinctor_attr_name)`, like this:\n
        @deserializable_poly_superclass("discriminator")
        class Superclass(BaseModel):
            discriminator: str | None = None
            @deserializer("discriminator")
            def deserialize(...):
                pass
    """
    def decorator[C: type[BaseModel]](supercls: C) -> C:
        reg: dict[str, type[C]] = {}
        supercls._registry = reg

        def __init_subclass__(cls, **kwargs) -> None:
            super(cls).__init_subclass__(**kwargs)
            name = cls.__name__
            if name is supercls.__name__:
                return
            # print("Registering subclass:", name)
            supercls._registry[name] = cls
            setattr(cls, distinctor_attr_name, name)
        
        supercls.__init_subclass__ = classmethod(__init_subclass__)
        supercls.model_rebuild()
        return supercls

    return decorator

def deserializer(distinctor_attr_name: str):
    """Mysterious decorator wrapping the deserializer method for a polymorphic class.\n
    Fragile stuff! Do not touch!\n
    The decorator fills in an empty method. Use like this:\n
        @deserializer(<discriminator>)
        def deserialize(<any arguments>) -> Any:
            pass
    """
    def decorator(fun: Callable):
        @model_validator(mode="wrap")
        @classmethod
        def _deserialize_polymorphic(cls: type[BaseModel], value: Any, handler: ValidatorFunctionWrapHandler) -> Any:
            if not isinstance(value, dict):
                return handler(value)
            subclass = cls._registry.get(value.get(distinctor_attr_name))
            if subclass == cls:
                return handler(value)
            if subclass is not None:
                return subclass.model_validate(value)
            return handler(value)
        return _deserialize_polymorphic
    return decorator

# Generated class looks something like this:
# class TopLevel(ShitObject):
#     _registry: ClassVar[dict[str, type[Self]]] = {}
#     
#     def __init_subclass__(cls, **kwargs) -> None:
#         super().__init_subclass__(**kwargs)
#         name = cls.__name__
#         if name is not TopLevel.__name__:
#             print("Registering subclass:", name)
#             TopLevel._registry[name] = cls
#             setattr(cls, "poly_id", name)
# 
#     @model_validator(mode="wrap")
#     @classmethod
#     def _deserialize_polymorphic(cls, value: Any, handler: ValidatorFunctionWrapHandler) -> Any:
#         if cls is TopLevel and isinstance(value, dict):
#             subclass = cls._registry.get(value.get("poly_id"))
#             if subclass is not None:
#                 return subclass.model_validate(value)
#         return handler(value)