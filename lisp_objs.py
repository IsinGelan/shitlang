
from typing import Iterable, Self

from pydantic import BaseModel

INDENT = "    "

def first_line(indent_level: int, *words: str, start_indent: bool = False) -> str:
    """first_line might be attached to the end previous section, instead of indented"""
    return INDENT * (indent_level * start_indent) + " ".join(words)
def line(indent_level: int, *words: str) -> str:
    return INDENT * indent_level + " ".join(words)

def indent_lines(first_line_strs: list[str], children: list["LispObject"], indent: int = 0, start_indent: bool = False) -> str:
    return (
        first_line(indent, *first_line_strs, start_indent=start_indent)
        + "\n"
        + "".join(
            child.to_hddl_str(indent+1, start_indent=True) + "\n"
            for child in children)
        + line(indent,")")
    )


# ================================
class LispObject:
    def to_hddl_str(self, indent: int = 0, start_indent: bool = False) -> str:
        """first_line might be attached to the end previous section, instead of indented.\n
        start_indent: if False, no indent will come before the first line of the result"""
        ...

class Comment(LispObject):
    # comment: str

    def __init__(self, comment: str):
        self.comment = comment

    def to_hddl_str(self, indent = 0, start_indent = False):
        return first_line(indent, ";", self.comment, start_indent=start_indent)#+"\n"

class Name(LispObject):
    # name: str
    def __init__(self, name: str):
        self.name = name
    
    def to_hddl_str(self, indent = 0, start_indent = False):
        return first_line(indent, self.name, start_indent=start_indent)

class Val(LispObject):
    # value: str | int
    def __init__(self, value: str | int):
        self.value = value
        if isinstance(value, str):
            raise ValueError(f"Are strings ever used?: {value}")
    
    def to_hddl_str(self, indent = 0, start_indent = False):
        return first_line(indent, repr(self.value), start_indent=start_indent)

class KeyVal(LispObject):
    """e.g. for :precondition (). It does not have surrounding parentheses"""
    # key: str
    # val: LispObject

    def __init__(self, key: str, val: LispObject):
        self.key = key
        self.val = val
    
    def to_hddl_str(self, indent = 0, start_indent = False):
        valstr = self.val.to_hddl_str(indent)
        return first_line(indent, self.key, valstr, start_indent=start_indent)

# ----------------------
class Multi(LispObject):
    # children: list[LispObject]
    pass

class HeadArgs(Multi):
    head: str
    def __init__(self, head: str, children: list[LispObject]):
        self.head = head
        self.children = list(children)

class HeadArgsInline(HeadArgs):
    def to_hddl_str(self, indent = 0, start_indent = False):
        children_strs = [child.to_hddl_str(indent+1) for child in self.children]
        return first_line(indent, "(", self.head, *children_strs, ")", start_indent=start_indent)

class HeadArgsFirstChildInline(HeadArgs):
    def to_hddl_str(self, indent = 0, start_indent = False):
        assert len(self.children)
        first_child, *remaining_children = self.children
        first_child_str = first_child.to_hddl_str()
        first_line_strs = ["(", self.head, first_child_str]
        return indent_lines(first_line_strs, remaining_children, indent=indent, start_indent=start_indent)

class HeadArgsIndented(HeadArgs):
    def to_hddl_str(self, indent = 0, start_indent = False):
        first_line_strs = ["(", self.head]
        return indent_lines(first_line_strs, self.children, indent=indent, start_indent=start_indent)

class List(Multi):
    def __init__(self, children: Iterable[LispObject]):
        self.children = list(children)

    def __add__(self, other: Self | list[LispObject]) -> Self:
        if isinstance(other, List):
            return self.__class__(self.children + other.children)
        if isinstance(other, list):
            return self.__class__(self.children + other)
        raise TypeError(f"Cannot concatenate {type(other)} to List")
    
    def __radd__(self, other: list[LispObject]) -> Self:
        if isinstance(other, List):
            return self.__class__(other.children + self.children)
        if isinstance(other, list):
            return self.__class__(other + self.children) 
        raise TypeError(f"Cannot concatenate {type(other)} to List")

class ListInline(List):
    def to_hddl_str(self, indent = 0, start_indent = False):
        children_strs = [child.to_hddl_str(indent+1) for child in self.children]
        return first_line(indent, "(", *children_strs, ")", start_indent=start_indent)

class ListIndented(List):
    def to_hddl_str(self, indent = 0, start_indent = False):
        first_line_strs = ["("]
        return indent_lines(first_line_strs, self.children, indent=indent, start_indent=start_indent)

