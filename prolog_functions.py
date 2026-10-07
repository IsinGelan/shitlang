

from itertools import chain
import subprocess
from typing import Iterator

from .shit_objs import (
    Action,
    ComparisonExpr,
    DomainFile,
    FactExpr,
    IdentifierConst,
    IdentifierParam,
    Param,
    ShitObjects,
    Task,
    TaskCall,
    ValuedExpr,
    Method)
from .helpers import dir_here, split, find

HEADER_PATH = dir_here() + "/dom_red_header.pro"

STD_PROLOG_EXPORT = "domain.pro"
STD_FACTS_FILE = "domain_facts.pro"

SUCCESS_INDICATOR = "SUCCESS"
FAILURE_INDICATOR = "FAILURE"

FAILURE_ELEMENTS = (set(), {"FAILURE"}, set())

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
def executable_code_name(ex: Action | Method | Task) -> str:
    """Name of the executable in the prolog code"""
    if isinstance(ex, Action):
        return ex.action_name.replace("-", "_")
    if isinstance(ex, Task):
        return ex.task_name.replace("-", "_")
    if isinstance(ex, Method):
        return ex.task_name.replace('-', '_')

def executable_repr_name(ex: Action | Method | Task) -> str:
    """Name representing the executable, differentiates between methods and tasks"""
    if isinstance(ex, Action):
        return ex.action_name.replace("-", "_")
    if isinstance(ex, Task):
        return ex.task_name.replace("-", "_")
    if isinstance(ex, Method):
        return ex.full_name.replace("-", "_")

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
    return f"{left} = {right}"
def prolog_executable_call(call: TaskCall) -> str:
    return call.task_name.replace("-", "_") + prolog_args(call.args)

def prolog_type_def(cons: ShitObjects) -> Iterator[str]:
    for name in cons.names:
        yield f"type{cons.type}({name})."

def necessary_consts_for_executable(ex: Action | Method) -> set[str]:
    """Returns the names of all constants in the executable."""
    res = ex.traverse(lambda node, path: isinstance(node, IdentifierConst))
    return {const.name for const, _ in res}


def action_to_prolog(action: Action, static_preds: set[str]) -> str:
    """Converts an Action object to a Prolog representation."""
    name_str = f"{executable_code_name(action)}{prolog_args(action.params)} :-\n"
    
    return executable_body_prolog(
        action, name_str, action.params,
        action.precondition, static_preds)

def method_to_prolog(method: Method, static_preds: set[str]) -> str:
    """Converts a Method object to a Prolog representation."""
    name_str = f"method_{executable_code_name(method)}{prolog_args(method._task_params)} :-\n"
    return executable_body_prolog(
        method, name_str, method.params,
        method.precondition, static_preds, method.subtasks)

def executable_body_prolog(obj, name_str, params, precondition, static_preds, subtasks=[]) -> str:
    type_checks = [
        f"{type_pred_name(param.type)}({prolog_variable(param)})"
        for param in params]
    fact_precs = [
        prec for prec in precondition
        if isinstance(prec, FactExpr) and prec.predicate_name in static_preds]
    comp_exprs = [
        prec for prec in precondition
        if isinstance(prec, ComparisonExpr)]
    # Consts need to be defined even if they appear in ignored predicates
    necessary_consts = necessary_consts_for_executable(obj)
    
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
    pos_prec_tracks = "".join(f"  tracked({prolog_fact(fact)}),\n" for fact in pos_precs)
    consts_tracks = "".join(
        f"  tracked_name({const}),\n"
        for const in necessary_consts)
    type_tracks_str = "".join(f"  tracked({check}),\n" for check in type_checks)
    executable_track = f"  tracked_executable({executable_repr_name(obj)}),\n"
    # nam = name_str.removesuffix(") :-\n")
    # pred_name, args = nam.split("(")
    # args = args.split(", ")
    # if args == [""]: args = []
    # astring = ", ".join(f"~a" for _ in args)
    # debug_name_call = f"  format(string(Debug), '{pred_name}({astring})', [{', '.join(args)}]),\n"
    body = (
        type_checks_str
        + comp_exprs_str
        + pos_prec_checks
        + neg_prec_checks
        + subtasks_str
        + consts_tracks
        + pos_prec_tracks
        + type_tracks_str
        + executable_track
        ) or "  true"
    body = body.removesuffix(",\n") + "."
    return name_str + body

def task_to_prolog(task: Task) -> str:
    sig = f"{executable_code_name(task)}{prolog_args(task.params)}"
    header = f"{sig} :-\n"
    check = f"  run_all(method_{sig}, Results),\n"
    ret = "  Results."
    return header + check + ret

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

def domain_to_prolog(domain: DomainFile, static_preds: set[str], domain_fact_filename: str, false_preds: set[str]) -> str:
    """Converts a DomainFile object to a Prolog representation."""
    fact_import = f":- ensure_loaded('{domain_fact_filename}')."
    header = prolog_header()
    top_level_signatures = {
        f"{executable_code_name(tl)}/{len(tl.params)}"
        for tl in domain.top_level_elements
        if isinstance(tl, (Action, Task))}
    tabling_methods = "\n".join(
        f":- table({signature})."
        for signature in top_level_signatures)
    obj_type_defs = "\n".join(chain.from_iterable(
        prolog_type_def(cons) for cons in domain.declared_constants))
    type_discontiguous_suppression = "\n".join(
        f":- discontiguous({type_pred_name(name)}/1)."
        for ty in domain.declared_types for name in ty.names)
    base_type_defs = "\n".join(f"type{name}(_) :- false." for ty in domain.declared_types for name in ty.names)
    false_pred_signatures = {
        (pred, decl.arity)
        for pred in false_preds
        if (decl := find(domain.declared_predicates, lambda p: p.name == pred))}
    false_preds_definitions = "\n".join(
        f"{pred}({', '.join(['_'] * arity)}) :- false."
        for pred, arity in false_pred_signatures)
    executable_str = "\n\n".join(top_level_prolog_strs(domain, static_preds))
    return (
        fact_import + "\n\n"
        + header + "\n\n"
        + tabling_methods + "\n\n"
        + type_discontiguous_suppression + "\n\n"
        + obj_type_defs + "\n\n"
        + base_type_defs + "\n\n"
        + false_preds_definitions + "\n\n"
        + executable_str)

def write_domain_to_prolog_file(
        domain: DomainFile,
        filename: str = STD_PROLOG_EXPORT, *,
        domain_fact_filename: str = STD_FACTS_FILE,
        static_preds: set[str] = None,
        false_preds: set[str] = set()) -> None:
    """Writes the Prolog representation of a DomainFile to a file.\n
    `false_preds`: predicates that are assumed to be false (e.g. if not found in facts)"""
    print(f">> Writing domain {domain.domain_name!r} to Prolog file: {filename}")
    if static_preds is None:
        static_preds = domain_static_preds(domain)
    prolog_str = domain_to_prolog(domain, static_preds, domain_fact_filename, false_preds)
    with open(filename, "w") as f:
        f.write(prolog_str)

# # ================================
# # get required facts for a goal call (from computation)
# def prolog_output_elements(prolog_output: str) -> tuple[set[str], set[FactExpr], set[str]]:
#     """returns {obj_names}, {facts}, {executable_names}"""
#     result_indicator_pos = max(prolog_output.rfind(SUCCESS_INDICATOR), prolog_output.rfind(FAILURE_INDICATOR))
#     if result_indicator_pos == -1:
#         print(f"   Output of unexpected format (Expected {SUCCESS_INDICATOR} or {FAILURE_INDICATOR})")
#         return FAILURE_ELEMENTS
#     if prolog_output[result_indicator_pos:].startswith(FAILURE_INDICATOR):
#         print(f"   Prolog did not find valid domain execution. Output:\n{prolog_output}")
#         return FAILURE_ELEMENTS
#     fact_start_pos = prolog_output.find("\n", result_indicator_pos) + 1
#     fact_lines = prolog_output[fact_start_pos:].strip().splitlines()
#     facts: set[FactExpr] = set()
#     objs: set[str] = set()
#     executables: set[str] = set()
#     for line in fact_lines:
#         print("F", line)
#         fact = FactExpr.from_str(line)
#         if fact.predicate_name.startswith("type"):
#             obj: IdentifierConst = fact.args[0]
#             objs.add(obj.name)
#         elif fact.predicate_name == "atom":
#             obj: IdentifierConst = fact.args[0]
#             objs.add(obj.name)
#         elif fact.predicate_name == "executable":
#             ex_name: IdentifierConst = fact.args[0]
#             executables.add(ex_name.name)
#             if "_M_" in ex_name.name:
#                 # method executable, also add task name
#                 task_name = ex_name.name.split("_M_")[0]
#                 executables.add(task_name)
#         else:
#             facts.add(fact)
#     return objs, facts, executables

# def get_required_facts(goal_call: TaskCall, filename: str = STD_PROLOG_EXPORT)  -> tuple[set[str], set[FactExpr]]:
#     """Returns the facts needed for the given goal call."""
#     print(f">> Running Prolog file {filename!r} to get required predicates for {goal_call!r}")
#     goal_call_str = prolog_executable_call(goal_call)
#     command = f"swipl -q -g \"" \
#         f"consult('{filename}'), start_tracking," \
#         f"({goal_call_str} -> writeln('{SUCCESS_INDICATOR}'); writeln('{FAILURE_INDICATOR}'))," \
#         "print_used_facts.\" -t halt"
#     try: 
#         prolog_process = subprocess.run(
#             command,
#             capture_output=True,
#             check=True,
#             text=True,
#             shell=True
#         )
#         return prolog_output_elements(prolog_process.stdout)
#     except subprocess.CalledProcessError as e:
#         print("Error executing Prolog command:", e)
#         return FAILURE_ELEMENTS

# def optimize_domain(
#         domain: DomainFile,
#         problem: ProblemFile, *, 
#         recompile_domain: bool = True,
#         false_preds: set[str] = set()) -> None:
#     """Optimizes the domain by removing unused predicates based on the goal call."""
#     print(f">> Optimizing domain {domain.domain_name!r} based on problem {problem.problem_name!r}")

#     if recompile_domain:
#         write_domain_to_prolog_file(domain, false_preds=false_preds)
#     res = (req_objs, req_facts, req_execs) = get_required_facts(problem.goal)
#     if res == FAILURE_ELEMENTS:
#         print("  Domain optimization failed. Keeping original domain.")
#         return
    
#     print(f"   BEFORE:")
#     print(f"   dom.consts: {domain.nr_consts:>4} | dom.facts: {problem.nr_facts:>4} | "
#           f"dom.execs: {len(domain.top_level_elements):>4}")
    
#     problem.fact_declarations = [fact for fact in problem.fact_declarations if fact in req_facts]
#     domain.declared_constants = [
#         ShitObjects(
#             names=[name for name in cons.names if name in req_objs],
#             type=cons.type)
#         for cons in domain.declared_constants]
#     domain.top_level_elements = [
#         tl for tl in domain.top_level_elements
#         if (isinstance(tl, (Action, Task, Method)) and executable_repr_name(tl) in req_execs)]
    
#     print(f"   AFTER:")
#     print(f"   dom.consts: {domain.nr_consts:>4} | dom.facts: {problem.nr_facts:>4} | "
#           f"dom.execs: {len(domain.top_level_elements):>4}")
