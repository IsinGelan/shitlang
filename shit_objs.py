
from itertools import product, chain
from typing import Iterable, Iterator

from pydantic import BaseModel

from . import lisp_objs as lo
from .shit_errors import raise_const_undeclared, raise_type_undeclared
from .shit_parser import FileData

# ================================
def pairs_overlapping[T](it: Iterable[T]) -> Iterator[tuple[T, T]]:
    last = None
    for el in it:
        if last is not None:
            yield last, el
        last = el

# ================================
class ShitObject(BaseModel):
    pass

    @classmethod
    def from_dict(cls, d: dict):
        raise NotImplementedError

    def to_lisp_objs(self) -> Iterator[lo.LispObject]:
        raise NotImplementedError
    def to_lisp_obj(self) -> lo.LispObject:
        """If there is only one lisp object, return it. Otherwise, raise an error."""
        lisp_objs = list(self.to_lisp_objs())
        if len(lisp_objs) != 1:
            raise ValueError(f"Expected 1 lisp object, got {len(lisp_objs)}")
        return lisp_objs[0]

# ================================
class FunctionCall(ShitObject):
    """for state-variable like expressions, e.g. inv_num(dirt) -> int"""
    function_name: str
    args: list["ValuedExpr"]

    @classmethod
    def from_dict(cls, d):
        return cls(
            function_name=d["name"],
            args=[dict_to_valued_expr(arg) for arg in d["args"]]
        )
    
    def to_lisp_objs(self):
        # TODO: differentiate vars from consts
        yield lo.HeadArgsInline(
            self.function_name,
            [arg.to_lisp_obj() for arg in self.args]
            )

class IdentifierConst(ShitObject):
    name: str
    
    def to_lisp_objs(self):
        yield lo.Name(self.name)

class IdentifierParam(ShitObject):
    name: str
    
    def to_lisp_objs(self):
        yield lo.Name(f"?{self.name}")

class Value(ShitObject):
    value: str | int
    
    def to_lisp_objs(self):
        yield lo.Val(self.value)

ValuedExpr = IdentifierConst | IdentifierParam | Value | FunctionCall

class LogicalExpr(ShitObject):
    pass

class ComparisonExpr(LogicalExpr):
    left: ValuedExpr
    operator: str
    right: ValuedExpr

    @classmethod
    def from_dict(cls, d):
        left = d["left"]
        right = d["right"]
        return cls(
            left=dict_to_valued_expr(left),
            operator=d["comparator"],
            right=dict_to_valued_expr(right)
        )
    
    def to_lisp_objs(self):
        yield lo.HeadArgsInline(
            self.operator,
            [self.left.to_lisp_obj(), self.right.to_lisp_obj()]
            )

class FactExpr(LogicalExpr):
    predicate_name: str
    args: list[ValuedExpr]

    @classmethod
    def from_dict(cls, d):
        return cls(
            predicate_name=d["name"],
            args=[dict_to_valued_expr(arg) for arg in d["args"]]
        )
    
    def to_lisp_objs(self):
        # TODO: differentiate vars from consts
        yield lo.HeadArgsInline(
            self.predicate_name,
            [arg.to_lisp_obj() for arg in self.args]
        )


# ================================
class TaskCall(ShitObject):
    task_name: str
    args: list[ValuedExpr]

    @classmethod
    def from_dict(cls, d):
        return cls(
            task_name=d["name"],
            args=[dict_to_valued_expr(arg) for arg in d["args"]]
        )
    
    def to_lisp_objs(self):
        # TODO: differentiate vars from consts
        yield lo.HeadArgsInline(
            self.task_name,
            [arg.to_lisp_obj() for arg in self.args]
        )

class Subtasks(ShitObject):
    pass

class SubtasksWithOrdering(Subtasks):
    subtasks: dict[int, TaskCall]
    orderings: list[list[set[int]]]

    @classmethod
    def from_dict(cls, d):
        int_oderings = [
            [
                set(int(i) for i in group)
                for group in ordering]
            for ordering in d["orderings"]
        ]
        
        return cls(
            subtasks={
                t["id"]: TaskCall.from_dict(t["call"])
                for t in d["subtasks_unordered"]
            },
            orderings=int_oderings
        )
    
    def all_relationships(self) -> Iterator[tuple[int, int]]:
        for ordering_groups in self.orderings:
            group_pairs = pairs_overlapping(ordering_groups)
            for group1, group2 in group_pairs:
                orderings = product(group1, group2)
                yield from orderings

    
    def to_lisp_objs(self):
        yield lo.KeyVal(
            key=":subtasks",
            val=lo.HeadArgsIndented(
                head="and",
                children=[
                    lo.HeadArgsInline(f"t{num}", [t.to_lisp_obj()])
                    for num, t in self.subtasks.items()]
            )
        )
        if not self.orderings:
            return
        
        comp_exprs = [
            lo.HeadArgsInline("<", [lo.Name(f"t{prev}"), lo.Name(f"t{later}")])
            for prev, later in self.all_relationships()
        ]
        yield lo.KeyVal(
            key=":order",
            val=lo.HeadArgsIndented(
                head="and",
                children=comp_exprs
            )
        )

class SequencedSubtasks(Subtasks):
    subtasks: list[TaskCall]

    @classmethod
    def from_dict(cls, d):
        return cls(
            subtasks=[
                TaskCall.from_dict(t["call"])
                for t in d["subtasks_sequence"]
            ]
        )
    
    def to_lisp_objs(self):
        val_lisp = lo.HeadArgsIndented("and", [t.to_lisp_obj() for t in self.subtasks]
        ) if self.subtasks else lo.HeadArgsInline("and", [])
        
        yield lo.KeyVal(":ordered-subtasks", val_lisp)


# ================================
class Param(ShitObject):
    name: str
    type: str | None = None

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            name=d["param_name"],
            type=d.get("param_type")
        )

    def __str__(self):
        if self.type:
            return f"?{self.name} - {self.type}"
        return f"?{self.name}"

    def __repr__(self):
        if self.type:
            return f"{self.name}: {self.type}"
        return f"{self.name}"
    
    def to_lisp_objs(self):
        yield lo.Name(str(self))

class TopLevel(ShitObject):
    ...

class Task(TopLevel):
    task_name: str
    params: list[Param]

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            task_name=d["task_name"],
            params=[Param.from_dict(p) for p in d["task_params"]]
        )
    
    def to_lisp_objs(self):
        params = lo.ListInline([p.to_lisp_obj() for p in self.params])
        yield lo.HeadArgsFirstChildInline(
            ":task",
            [
                lo.Name(self.task_name),
                lo.KeyVal(":parameters", params)
            ]
        )

class Method(TopLevel):
    task_name: str
    method_name: str
    params: list[Param]
    precondition: list[LogicalExpr]
    subtasks: Subtasks

    @classmethod
    def from_dict(cls, d: dict):
        params = [Param.from_dict(p) for p in d["method_params"]]
        return cls(
            task_name=d["task_name"],
            method_name=d["method_name"],
            params=params,
            precondition=[dict_to_logical_expr(p) for p in d["precondition"]],
            subtasks=dict_to_subtasks(d)
        )

    def _set_task_params(self, task_params: list[Param]):
        """Set params of this method's task"""
        self._task_params = task_params
    
    def to_lisp_objs(self):
        m_params = lo.ListInline([p.to_lisp_obj() for p in self.params])
        t_params = lo.ListInline([lo.Name(f"?{p.name}") for p in self._task_params])
        prec = [] if not self.precondition else [
            lo.KeyVal(
                ":precondition",
                lo.HeadArgsIndented("and", [prec.to_lisp_obj() for prec in self.precondition])
                )
        ]

        children = [
            lo.Name(self.full_name()),
            lo.KeyVal(":parameters", m_params),
            lo.KeyVal(":task", [lo.Name(self.task_name)] + t_params),
            *prec,
            *self.subtasks.to_lisp_objs()
        ]
        yield lo.HeadArgsFirstChildInline(":method", children)

    def is_only_task_method(self) -> bool:
        """Returns True if this method is the only method for its task.\n
        Does not validate whether it really is the only method or just has the name"""
        return self.method_name == ""

    def full_name(self) -> str:
        if self.is_only_task_method():
            return f"{self.task_name}-M"
        return f"{self.task_name}-M-{self.method_name}"

class Action(TopLevel):
    action_name: str
    params: list[Param]
    precondition: list[LogicalExpr]
    postcondition: list[FactExpr]

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            action_name=d["action_name"],
            params=[Param.from_dict(p) for p in d["action_params"]],
            precondition=[dict_to_logical_expr(p) for p in d["precondition"]],
            postcondition=[dict_to_logical_expr(p) for p in d["postcondition"]]
        )
    
    def to_lisp_objs(self):
        params = lo.ListInline([p.to_lisp_obj() for p in self.params])
        prec = [] if not self.precondition else [
            lo.KeyVal(
                ":precondition",
                lo.HeadArgsIndented("and", [prec.to_lisp_obj() for prec in self.precondition])
                )
        ]
        postc = [] if not self.postcondition else [
            lo.KeyVal(
                ":effect",
                lo.HeadArgsIndented("and", [postc.to_lisp_obj() for postc in self.postcondition])
                )
        ]
        children = [
            lo.Name(self.action_name),
            lo.KeyVal(":parameters", params),
            *prec,
            *postc
        ]
        yield lo.HeadArgsFirstChildInline(":action", children)

class TopLevelComment(TopLevel):
    comment: str

    @classmethod
    def from_dict(cls, d: dict):
        return cls(comment=d["content"])
    
    def to_lisp_objs(self):
        yield lo.Comment(self.comment)


# ================================ 
class ShitTypes(ShitObject):
    """one type declaration statement. May be split into multiple types,\n
    e.g. `type1 type2 < supertype` becomes two statements"""
    names: list[str]
    supertype: str

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            names=d["subtypes"],
            supertype=d["supertype"]
        )
    
    def to_lisp_objs(self):
        # Strategy: each subtype gets its own line
        for typ in self.names: 
            yield lo.Name(f"{typ} - {self.supertype}")

class ShitConstants(ShitObject):
    names: list[str]
    type: str

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            names=d["ids"],
            type=d["type"]
        )

    @classmethod
    def from_undeclared(cls, undeclared_constants: set[str]):
        return cls(
            names=list(undeclared_constants),
            type="<undeclared>"
        )

    def to_lisp_objs(self):
        for name in self.names:
            yield lo.Name(f"{name} - {self.type}")

class ShitPredicate(ShitObject):
    name: str
    params: list[Param]

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            name=d["pred_name"],
            params=[Param.from_dict(p) for p in d["pred_params"]]
        )
    
    def to_lisp_objs(self):
        yield lo.HeadArgsInline(
            self.name,
            [param.to_lisp_obj() for param in self.params])

# ================================ 
class ShitFile(ShitObject):
    domain_name: str
    # types: list[tuple[str, str]]
    declared_types: list[ShitTypes] # types declared with a type statement
    declared_constants: list[ShitConstants] # constants declared with a const statement
    declared_predicates: list[ShitPredicate] # predicates declared with a pred statement
    found_constants: set[str] = set() # constants found in the code
    found_types: set[str] = set() # types found in the code
    
    top_level_elements: list[TopLevel]

    @classmethod
    def from_dict(cls, d: dict, file_data: FileData):
        type_decls = d["file_header"]["type_declarations"]
        const_decls = d["file_header"]["const_declarations"]
        pred_decls = d["file_header"]["pred_declarations"]

        declared_types = [ShitTypes.from_dict(ty) for ty in type_decls]
        declared_constants = [ShitConstants.from_dict(const) for const in const_decls]
        declared_predicates = [ShitPredicate.from_dict(pred) for pred in pred_decls]

        undeclared_constants = file_data.found_constants - {c for const in declared_constants for c in const.names}
        if undeclared_constants:
            declared_constants.append(ShitConstants.from_undeclared(undeclared_constants))
            raise_const_undeclared(list(undeclared_constants))
        undeclared_types = file_data.found_types - {t for typ in declared_types for t in typ.names}
        if undeclared_types:
            raise_type_undeclared(list(undeclared_types))
        declared_pred_signatures = {(p.name, len(p.params)) for p in declared_predicates}
        undeclared_predicates = file_data.found_predicates - declared_pred_signatures
        if undeclared_predicates:
            raise ValueError(f"Undeclared predicates found: {undeclared_predicates}")

        top_level_elems = [dict_to_top_level(e) for e in d.get("file_elements", [])]

        return cls(
            domain_name=d["file_header"].get("domain_name", "???"),
            declared_types=declared_types,
            declared_constants=declared_constants,
            declared_predicates=declared_predicates,
            top_level_elements=top_level_elems,
            found_constants=file_data.found_constants,
            found_types=file_data.found_types
        )

    def model_post_init(self, context):
        # - TODO: Find all types
        # - Find all requirements
        self._tasks_signatures = self.tasks_signatures()
        self._requirements = self.analyze_requirements()
        self.validate_methods()
        self.validate_task_methods()
        self.set_method_task_params()

    def analyze_requirements(self) -> list[str]:
        # TODO: analyze the structure to find the actual requirements
        return [":hierarchy", ":typing"]
    
    def tasks_signatures(self) -> dict[str, list[Param]]:
        signatures = {}
        for elem in self.top_level_elements:
            if isinstance(elem, Task):
                signatures[elem.task_name] = elem.params
            elif isinstance(elem, Method) and elem.is_only_task_method():
                signatures[elem.task_name] = elem.params
        return signatures

    def validate_methods(self):
        for elem in self.top_level_elements:
            if not isinstance(elem, Method):
                continue
            if elem.task_name not in self._tasks_signatures:
                print(self._tasks_signatures)
                raise ValueError(f"Must define task '{elem.task_name}'! "
                                 f"(For method '{elem.full_name()}')")

            task_params = self._tasks_signatures[elem.task_name]
            m_params = {p.name for p in elem.params}
            t_params = {p.name for p in task_params}
            if not t_params.issubset(m_params):
                raise ValueError(f"Parameters of method '{elem.full_name()}' {elem.params} "
                                 "must be a superset of "
                                 f"its task's parameters {task_params}!")

    def validate_task_methods(self):
        """Validate that methods annotated like the only method
        of a task are indeed the only method of that task"""
        tasks = {t: "unseen" for t in self._tasks_signatures}
        for elem in self.top_level_elements:
            if not isinstance(elem, Method):
                continue
            if elem.is_only_task_method() and tasks[elem.task_name] == "one_m_found":
                raise ValueError(f"Task '{elem.task_name}' has multiple methods, "
                                 "although one is annotated as the only method!")
            if elem.is_only_task_method():
                tasks[elem.task_name] = "only_m_found"
                continue
            if tasks[elem.task_name] == "only_m_found":
                raise ValueError(f"Task '{elem.task_name}' has multiple methods, "
                                 "although one is annotated as the only method!")
            tasks[elem.task_name] = "one_m_found"

    def set_method_task_params(self):
        """Set the task parameters of each method to the parameters of its task"""
        for elem in self.top_level_elements:
            if not isinstance(elem, Method):
                continue
            task_params = self._tasks_signatures[elem.task_name]
            elem._set_task_params(task_params)
    
    def to_lisp_objs(self):
        yield lo.HeadArgsFirstChildInline(
            "define",
            [
                lo.HeadArgsInline("domain", [lo.Name(self.domain_name)]),
                lo.HeadArgsIndented(
                    ":requirements",
                    [lo.Name(req) for req in self._requirements],
                ),
                lo.HeadArgsIndented(
                    ":types",
                    chain.from_iterable(t.to_lisp_objs() for t in self.declared_types)
                ),
                lo.HeadArgsIndented(
                    ":constants",
                    chain.from_iterable(c.to_lisp_objs() for c in self.declared_constants)
                ),
                lo.HeadArgsIndented(
                    ":predicates",
                    [p.to_lisp_obj() for p in self.declared_predicates]
                ),
                *[elem.to_lisp_obj() for elem in self.top_level_elements]
            ])

# ================================
def dict_to_valued_expr(d: dict) -> ValuedExpr:
    match d:
        case [{"number": num}]:
            # TODO: remove the possibility to generate the surrounding brackets
            return Value(value=int(num))
        case {"number": num}:
            return Value(value=int(num))
        case [{"const": name}]:
            # TODO: remove the possibility to generate the surrounding brackets
            return IdentifierConst(name=name)
        case [{"param": name}]:
            return IdentifierParam(name=name)
        case {"const": name}:
            return IdentifierConst(name=name)
        case {"param": name}:
            return IdentifierParam(name=name)
        case {"call": call}:
            return FunctionCall.from_dict(call)
        case _:
            raise ValueError(f"Invalid valued expression: {d}")

def dict_to_logical_expr(d: dict) -> LogicalExpr:
    if "comparison" in d:
        return ComparisonExpr.from_dict(d["comparison"])
    elif "call" in d:
        return FactExpr.from_dict(d["call"])
    raise ValueError(f"Invalid logical expression: {d}")

def dict_to_subtasks(d: dict) -> Subtasks:
    if "subtasks_sequence" in d:
        return SequencedSubtasks.from_dict(d)

    if "subtasks_unordered" not in d:
        raise ValueError(f"No subtasks were specified in {d['task_names']}:{d['method_name']}")
    if "orderings" not in d:
        raise ValueError(f"No orderings for 'subtasks_unordered' were specified in {d['task_names']}:{d['method_name']}")
    return SubtasksWithOrdering.from_dict(d)

def dict_to_top_level(d: dict) -> TopLevel:
    if "task" in d:
        return Task.from_dict(d["task"])
    if "method" in d:
        return Method.from_dict(d["method"])
    if "action" in d:
        return Action.from_dict(d["action"])
    if "comment" in d:
        return TopLevelComment.from_dict(d["comment"])
    raise ValueError(f"Invalid top-level element: {d}")

# ================================
def dicts_to_shit_objects(dicts: list[dict], file_data: FileData) -> ShitFile:
    return ShitFile.from_dict(dicts, file_data)
