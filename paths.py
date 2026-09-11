
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Literal, NamedTuple, Union

if TYPE_CHECKING:
    from .shit_objs import ShitObject

# ================================
ChildField = Union[Iterable["ShitObject"], "ShitObject"]
class NodeOrigin(NamedTuple):
    parent: Union["ShitObject", None]
    field: ChildField | None

# ================================
NodePredicate = Callable[["ShitObject", str], bool]
PathData = tuple[str, int] # path, index in parent
PathType = Literal["numbered", "xpath"]

def path_descriptor(path: PathData, path_type: PathType) -> str:
    if path_type == "numbered":
        return f"{path[0]}/{path[1]}"
    elif path_type == "xpath":
        return f"{path[0]}[{path[1]}]"
    else:
        raise ValueError(f"Unknown path type: {path_type}")

def subpath(
        path_type: PathType,
        here_descriptor: str,
        child: "ShitObject",
        child_index: int,
        subtype_highest_index: dict[str, int]) -> PathData:
    if path_type == "numbered":
        return (here_descriptor, child_index)
    elif path_type == "xpath":
        child_type = type(child).__name__
        subtype_highest_index[child_type] = subtype_highest_index.get(child_type, -1) + 1
        child_index = subtype_highest_index[child_type]
        return (here_descriptor + f"/{child_type}", child_index)
    else:
        raise ValueError(f"Unknown path type: {path_type}")

def regard_max_depth(depth: int) -> NodePredicate:
    """Returns a node filter that only regards nodes until depth n"""
    def regard(node: "ShitObject", descriptor: str) -> bool:
        return descriptor.strip("/").count("/") <= depth
    return regard

def path_type(path: str) -> PathType:
    """Returns the type of a path, e.g. /Block[0]/Item[1] -> XPATH, /0/1/2 -> NUMBERED"""
    if "[" in path:
        return "xpath"
    else:
        return "numbered"

def path_parent(path: str) -> str:
    """Returns the parent path of a given path (in the same format)"""
    # print(f"parent of {path} is {path.rsplit('/', 1)[0]}")
    return path.rsplit("/", 1)[0]

def filter_parent_is(
        parent_condition: NodePredicate,
        child_relation: Callable[["ShitObject", "ShitObject"], bool] = lambda parent, child: True
        ) -> NodePredicate:
    """Returns a node filter that only yields nodes whose parent matches the given condition.\n
    Can specify a necessary relation between parent and child."""
    valid_parents: dict[str, "ShitObject"] = {} # path -> parent
    def filter(node: "ShitObject", descriptor: str) -> bool:
        if parent_condition(node, descriptor):
            valid_parents[descriptor] = node
        parent = valid_parents.get(path_parent(descriptor))
        if parent:
            return child_relation(parent, node)
        return False
    return filter

def find_of_type(
        root: "ShitObject",
        typ: type["ShitObject"], *,
        extra_filter: NodePredicate = lambda node, descriptor: True,
        max_depth: int | None = None
        ) -> Iterator[tuple["ShitObject", str]]:
    """Find all descendant nodes of a given type, optionally below a given depth"""
    node_filter = lambda node, descriptor: isinstance(node, typ) and extra_filter(node, descriptor)
    regard_children = regard_max_depth(max_depth) if max_depth is not None else lambda node, descriptor: True
    yield from root.traverse(node_filter, regard_children, path_type="xpath")

# ================================
def replace(root: "ShitObject", path: str, new_node: "ShitObject"):
    """Replaces the node at the given path with a new node"""
    old_node = root.resolve_path(path)
    origin = old_node._origin
    if origin == (None, None):
        raise ValueError(f"Cannot replace root node")
    parent, field = origin
    if isinstance(field, "ShitObject"):
        # TEST!
        field = new_node
    elif isinstance(field, list):
        index = field.index(old_node)
        field[index] = new_node
    elif isinstance(field, tuple):
        index = field.index(old_node)
        field = list(field)
        field[index] = new_node
        field = tuple(field)
    else:
        raise ValueError(f"Cannot replace node at path {path}: "
                         "unsupported field type {type(field)}")
    new_node._assign_origin(NodeOrigin(parent, field))