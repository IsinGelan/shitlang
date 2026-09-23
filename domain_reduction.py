

from itertools import chain
from typing import Iterator

from .shit_objs import Action, ComparisonExpr, DomainFile, FactExpr, IdentifierConst, IdentifierParam, Param, ShitObjects, Task, TaskCall, ValuedExpr, Method
from .helpers import dir_here, split

HEADER_PATH = dir_here() + "/dom_red_header.pro"

# ================================
def fact_in_effect(fact: FactExpr) -> bool:
    parent, field = fact._origin
    if parent is None or field is None:
        return False
    if isinstance(parent, Action):
        return fact in parent.postcondition
    return False 

def domain_static_preds(domain: DomainFile) -> set[str]:
    """Returns a names for all predicates that are static in the domain,
    i.e., do not appear in the effect of any method or action."""
    facts = domain.traverse(lambda node, path: isinstance(node, FactExpr))
    effect_facts: list[FactExpr] = (fact for fact, _ in facts if fact_in_effect(fact))
    all_preds = {pred.name for pred in domain.declared_predicates}    
    return all_preds - {fact.predicate_name for fact in effect_facts}

# ================================
def executable_name(ex: Action | Method) -> str:
    if isinstance(ex, Action):
        return ex.action_name.replace("-", "_")
    if isinstance(ex, (Method, Task)):
        return ex.task_name.replace("-", "_")

def type_pred_name(type_name: str) -> str:
    return "type" + type_name

def prolog_variable(p: Param | ValuedExpr) -> str:
    if isinstance(p, Param):
        return p.name.capitalize()
    if isinstance(p, IdentifierConst):
        return p.name
    if isinstance(p, IdentifierParam):
        return p.name.capitalize()
    raise ValueError("Expected Param or Identifier Argument. Other argument "
                     "types are not implemented for domain reduction")
def prolog_args(args: list[Param | ValuedExpr]) -> str:
    return "(" + ", ".join(prolog_variable(arg) for arg in args) + ")"

def prolog_fact(fact: FactExpr) -> str:
    """gives capital names to the variables"""
    return fact.predicate_name + prolog_args(fact.args)
def prolog_comp_expr(comp: ComparisonExpr) -> str:
    left = prolog_variable(comp.left)
    right = prolog_variable(comp.right)
    assert comp.operator == "="
    return f"{left} == {right}"
def prolog_executable_call(call: TaskCall) -> str:
    return call.task_name.replace("-", "_") + prolog_args(call.args)

def prolog_type_def(cons: ShitObjects) -> Iterator[str]:
    for name in cons.names:
        yield f"type{cons.type}({name})."


def action_to_prolog(action: Action, static_preds: set[str]) -> str:
    """Converts an Action object to a Prolog representation."""
    name_str = f"{executable_name(action)}{prolog_args(action.params)} :-\n"
    
    return executable_body_prolog(
        name_str, action.params,
        action.precondition, static_preds)

def method_to_prolog(method: Method, static_preds: set[str]) -> str:
    """Converts a Method object to a Prolog representation."""
    name_str = f"method_{executable_name(method)}{prolog_args(method._task_params)} :-\n"
    return executable_body_prolog(
        name_str, method.params,
        method.precondition, static_preds, method.subtasks)

def executable_body_prolog(name_str, params, precondition, static_preds, subtasks=[]) -> str:
    type_checks = [
        f"{type_pred_name(param.type)}({prolog_variable(param)})"
        for param in params]
    fact_precs = [
        prec for prec in precondition
        if isinstance(prec, FactExpr) and prec.predicate_name in static_preds]
    comp_exprs = [
        prec for prec in precondition
        if isinstance(prec, ComparisonExpr)]
    
    subtasks_str = "".join(f"  {prolog_executable_call(subtask)},\n" for subtask in subtasks)

    neg_precs, pos_precs = split(fact_precs, lambda prec: prec.negated)
    # type checks to instantiate and check all parameters
    type_checks_str = "".join(f"  {check},\n" for check in type_checks)
    # comparison expressions
    comp_exprs_str = "".join(f"  {prolog_comp_expr(expr)},\n" for expr in comp_exprs)
    # check pos preconditions. If unsuccessful, action couldnt execute
    pos_prec_checks = "".join(f"  {prolog_fact(fact)},\n" for fact in pos_precs)
    # check neg preconditions. If true (prohibits execution), record it
    neg_prec_checks = "".join(
        f"  (\n  {prolog_fact(fact)},\n"
        "  no_track,\n"
        f"{subtasks_str}"
        "  track\n"
        f"  -> tracked({prolog_fact(fact)}), fail\n"
        "  ;  true),\n"
        for fact in neg_precs) # TODO: do not track subtasks

    # EXECUTABLE
    # EXECUTABLE WITH SUBTASKS
    # If action is executable record positive precondition facts
    pos_prec_tracks = "".join(f"  tracked({prolog_fact(fact)}),\n" for fact in pos_precs)
    type_tracks_str = "".join(f"  tracked({check}),\n" for check in type_checks)
    nam = name_str.removesuffix(") :-\n")
    pred_name, args = nam.split("(")
    args = args.split(", ")
    if args == [""]: args = []
    astring = ", ".join(f"~a" for _ in args)
    debug_name_call = f"  format(string(Debug), '{pred_name}({astring})', [{', '.join(args)}]),\n"
    body = (
        debug_name_call
        + f"  format('Calling ~a~n', [Debug]),\n"
        + type_checks_str
        + comp_exprs_str
        + pos_prec_checks
        + neg_prec_checks
        + f"  format('Subtasks for ~a~n', [Debug]),\n"
        + subtasks_str
        + f"  format('APPLICABLE   ~a~n', [Debug]),\n"
        + pos_prec_tracks
        + type_tracks_str
        ) or "  true"
    body = body.removesuffix(",\n") + "."
    return name_str + body

def task_to_prolog(task: Task) -> str:
    sig = f"{executable_name(task)}{prolog_args(task.params)}"
    header = f"{sig} :-\n"
    # check all method implementations to get all paths explored
    check = f"  findall(true, method_{sig}, Results),\n"
    # succeed if at least one method implementation is applicable
    ret = "  Results \\= []."
    return header + check + ret

# - type checks for objects
# - subcalls for methods

def top_level_prolog_strs(domain: DomainFile, static_preds: set[str]) -> Iterator[str]:
    """Yields Prolog strings for top-level elements of the domain."""
    for tl in domain.top_level_elements:
        if isinstance(tl, Method):
            yield method_to_prolog(tl, static_preds)
        elif isinstance(tl, Action):
            yield action_to_prolog(tl, static_preds)
        elif isinstance(tl, Task):
            yield task_to_prolog(tl)

def prolog_header() -> str:
    with open(HEADER_PATH) as f:
        return f.read()

def domain_to_prolog(domain: DomainFile, static_preds: set[str], domain_fact_filename: str) -> str:
    """Converts a DomainFile object to a Prolog representation."""
    fact_import = f":- ensure_loaded('{domain_fact_filename}')."
    header = prolog_header()
    top_level_signatures = {
        f"{executable_name(tl)}/{len(tl.params)}"
        for tl in domain.top_level_elements
        if isinstance(tl, (Action, Method))}
    tabling_methods = "\n".join(
        f":- table({signature})."
        for signature in top_level_signatures)
    obj_type_defs = "\n".join(chain.from_iterable(
        prolog_type_def(cons) for cons in domain.declared_constants))
    base_type_defs = "\n".join(f"type{name}(_) :- false." for ty in domain.declared_types for name in ty.names)
    executable_str = "\n\n".join(top_level_prolog_strs(domain, static_preds))
    return (
        fact_import + "\n\n"
        + header + "\n\n"
        + tabling_methods + "\n\n"
        + obj_type_defs + "\n\n"
        + base_type_defs + "\n\n"
        + executable_str)

def write_domain_to_prolog_file(
        domain: DomainFile,
        filename: str, *,
        domain_fact_filename: str = "domain_facts.pro",
        static_preds: set[str] = None,
        ignore_preds: set[str] = set()) -> None:
    """Writes the Prolog representation of a DomainFile to a file."""
    if static_preds is None:
        static_preds = domain_static_preds(domain)
    static_preds -= ignore_preds
    prolog_str = domain_to_prolog(domain, static_preds, domain_fact_filename)
    with open(filename, "w") as f:
        f.write(prolog_str)