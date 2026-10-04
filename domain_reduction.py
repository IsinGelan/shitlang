
from itertools import chain
import subprocess
from typing import Iterator

from pydantic import BaseModel

from .helpers import LocalNumbers, dir_here, find, split, timed
from .shit_objs import (
    Action,
    ComparisonExpr,
    DomainFile,
    FactExpr,
    Identifier,
    IdentifierConst,
    IdentifierParam,
    LogicalExpr,
    Param,
    ProblemFile,
    ShitObjects,
    Task,
    TaskCall,
    Method)
from .prolog_functions import (
    domain_static_preds,
    executable_code_name,
    executable_repr_name,
    necessary_consts_for_executable,
    prolog_args,
    prolog_comp_expr,
    prolog_executable_call,
    prolog_fact,
    prolog_header,
    prolog_type_def,
    prolog_variable,
    type_pred_name
)


HEADER_PATH = dir_here() + "/dom_red_header.pro"

STD_PROLOG_EXPORT = "domain.pro"
STD_FACTS_FILE = "domain_facts.pro"

SUCCESS_INDICATOR = "SUCCESS"
FAILURE_INDICATOR = "FAILURE"

FAILURE_ELEMENTS = (set(), {"FAILURE"}, set())

# ================================
def executable_to_prolog(obj: Action | Method, static_preds: set[str]) -> str:
    type_checks = [
        f"{type_pred_name(param.type)}({prolog_variable(param)})"
        for param in obj.params]
    fact_precs = [
        prec for prec in obj.precondition
        if isinstance(prec, FactExpr) and prec.predicate_name in static_preds]
    comp_exprs = [
        prec for prec in obj.precondition
        if isinstance(prec, ComparisonExpr)]
    subtasks = [] if isinstance(obj, Action) else obj.subtasks.subtasks

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
        for fact in neg_precs)

    pos_prec_tracks = "".join(f"  tracked({prolog_fact(fact)}),\n" for fact in pos_precs)
    consts_tracks = "".join(
        f"  tracked_name({const}),\n"
        for const in necessary_consts)
    type_tracks_str = "".join(f"  tracked({check}),\n" for check in type_checks)
    executable_track = f"  tracked_executable({executable_repr_name(obj)}),\n"

    name_str = (f"method_{executable_code_name(obj)}{prolog_args(obj._task_params)} :-\n"
                if isinstance(obj, Method) else
                f"{executable_code_name(obj)}{prolog_args(obj.params)} :-\n")

    body = (
        pos_prec_checks
        + neg_prec_checks # fact checks before type checks to allow early failing
        + type_checks_str # to keep the number of checked instantiations small
        + comp_exprs_str
        + subtasks_str
        + consts_tracks
        + pos_prec_tracks
        + type_tracks_str
        + executable_track
        ) or "  true"
    body = body.removesuffix(",\n") + "."
    return name_str + body

def task_to_prolog(task: Task, methods: list[Method]) -> str:
    sig = f"{executable_code_name(task)}{prolog_args(task.params)}"
    header = f"{sig} :-\n"
    body = (
        f"  method_{sig}."
        if len(methods) == 1 else
        f"  run_all(method_{sig}, Results),\n  Results.")
    return header + body

# ================================
class ArgMapping(BaseModel):
    mapping: dict[Identifier, Identifier]
    @classmethod
    def from_params_n_args(cls, params: list[Param], call_args: list[Identifier]):
        return cls(mapping={
            IdentifierParam(name=param.name): arg
            for param, arg in zip(params, call_args)})
    def map_to_call_context(self, expr: LogicalExpr) -> LogicalExpr:
        """Map the fact from executable A to how it would look in the context of B (a caller of A)"""
        if isinstance(expr, FactExpr):
            return FactExpr(
                predicate_name=expr.predicate_name,
                args=[self.mapping.get(arg, arg) for arg in expr.args],
                negated=expr.negated)
        elif isinstance(expr, ComparisonExpr):
            return ComparisonExpr(
                left=self.mapping.get(expr.left, expr.left),
                operator=expr.operator,
                right=self.mapping.get(expr.right, expr.right),
            )
        raise ValueError(f"Cannot map expression of type {expr.__class__.__name__!r}!")

# ================================
class PrologDomain(BaseModel):
    domain: DomainFile
    tasks: dict[str, Task] = {}
    methods: dict[str, Method] = {}
    actions: dict[str, Action] = {}

    @classmethod
    def from_domain(cls, domain: DomainFile):
        return cls(
            domain=domain,
            tasks={
                task.task_name: task.model_copy()
                for task in domain.top_level_elements if isinstance(task, Task)},
            methods={
                method.full_name: method.model_copy()
                for method in domain.top_level_elements if isinstance(method, Method)},
            actions={
                action.action_name: action.model_copy()
                for action in domain.top_level_elements if isinstance(action, Action)}
        )

    def _task_methods(self, task_name: str) -> list[Method]:
        methods = [m for m in self.methods.values() if m.task_name == task_name]
        return methods

    def _is_only_task_method(self, method: Method) -> bool:
        return len(self._task_methods(method.task_name)) == 1

    def _called_at(self, executable: Action | Method) -> dict[Action|Method, ArgMapping]:
        """Return all calls to tasks in the executable's subtasks"""
        call_name = executable.call_name
        if isinstance(executable, Method) and not self._is_only_task_method(executable):
            # we could check here if all methods have at least one unifiable precondition,
            # but we'll just ignore this case and leave the preconditions where they are
            return dict()
        calls: Iterator[tuple[TaskCall, str]] = self.domain.traverse(
            lambda x, p: isinstance(x, TaskCall) and x.task_name == call_name)
        return {
            (call._origin.parent or print("Call", call))._origin.parent : ArgMapping.from_params_n_args(executable.params, call.args)
            for call, _p in calls}

    @property
    def executables(self) -> list[Action | Method]:
        return list(self.actions.values()) + list(self.methods.values())

    def move_preconditions_up(self, move_preds: set[str] = None):
        """Move preconditions as far up the tree as possible to reduce unsuccessful calls"""
        print(">> Prolog Domain: Moving preconditions up in the task hierarchy...")
        if move_preds is None:
            move_preds = domain_static_preds(self.domain)

        # queue of executables to check for movements
        check_movements: list[Action | Method] = list(self.actions.values())

        movable_prec = lambda prec: prec.predicate_name in move_preds if isinstance(prec, FactExpr) else True
        # TODO: replace by bottom up multi-source BFS
        while check_movements:
            ex = check_movements.pop(0); #print(f"Checking {ex.impl_name}")
            precs_to_move = [prec for prec in ex.precondition if movable_prec(prec)]
            # print(f"  # found {len(precs_to_move)} calls to move")
            if not precs_to_move:
                continue
            callers = self._called_at(ex); #print(f"  # found {len(callers)} call contexts")
            for caller, arg_mapping in callers.items():
                # print(f"  Moving precs to {caller.impl_name}")
                mapped_precs = [arg_mapping.map_to_call_context(prec) for prec in precs_to_move]
                caller.precondition.extend(mapped_precs)
                check_movements.append(caller)

    def _header(self, domain_fact_filename: str, false_preds: set[str] = set()) -> str:
        fact_import = f":- ensure_loaded('{domain_fact_filename}')."
        header = prolog_header()
        top_level_signatures = {
            f"{executable_code_name(tl)}/{len(tl.params)}"
            for tl in self.domain.top_level_elements
            if isinstance(tl, (Action, Task))}
        tabling_methods = "\n".join(
            f":- table({signature})."
            for signature in top_level_signatures)
        obj_type_defs = "\n".join(chain.from_iterable(
            prolog_type_def(cons) for cons in self.domain.declared_constants))
        type_discontiguous_suppression = "\n".join(
            f":- discontiguous({type_pred_name(name)}/1)."
            for ty in self.domain.declared_types for name in ty.names)
        base_type_defs = "\n".join(f"type{name}(_) :- false." for ty in self.domain.declared_types for name in ty.names)
        false_pred_signatures = {
            (pred, decl.arity)
            for pred in false_preds
            if (decl := find(self.domain.declared_predicates, lambda p: p.name == pred))}
        false_preds_definitions = "\n".join(
            f"{pred}({', '.join(['_'] * arity)}) :- false."
            for pred, arity in false_pred_signatures)
        return (
            fact_import + "\n\n"
            + header + "\n\n"
            + tabling_methods + "\n\n"
            + type_discontiguous_suppression + "\n\n"
            + obj_type_defs + "\n\n"
            + base_type_defs + "\n\n"
            + false_preds_definitions)

    def to_str(self, domain_fact_filename: str, static_preds: set[str], false_preds: set[str] = set()) -> str:
        task_blocks = [
            task_to_prolog(task, self._task_methods(task.task_name)) + "\n" + "\n".join(
                executable_to_prolog(method, static_preds) for method in self._task_methods(task_name)
            )
            for task_name, task in self.tasks.items()
        ]
        task_str = "\n\n".join(task_blocks)
        action_str = "\n\n".join(executable_to_prolog(action, static_preds) for action in self.actions.values())
        return (
            self._header(domain_fact_filename, false_preds) + "\n\n"
            + task_str + "\n\n"
            + action_str)
    
    def export_to_prolog(
            self,
            filename: str = STD_PROLOG_EXPORT, *,
            domain_fact_filename: str = STD_FACTS_FILE,
            static_preds: set[str] = None,
            false_preds: set[str] = set()):
        """Writes the Prolog representation of a DomainFile to a file.\n
        `false_preds`: predicates that are assumed to be false (e.g. if not found in facts)"""
        print(f">> Writing domain {self.domain.domain_name!r} to Prolog file: {filename}")
        if static_preds is None:
            static_preds = domain_static_preds(self.domain)
        prolog_str = self.to_str(domain_fact_filename, static_preds, false_preds)
        with open(filename, "w") as f:
            f.write(prolog_str)


# ================================
# get required facts for a goal call (from computation)
def prolog_output_elements(prolog_output: str) -> tuple[set[str], set[FactExpr], set[str]]:
    """returns {obj_names}, {facts}, {executable_names}"""
    result_indicator_pos = max(prolog_output.rfind(SUCCESS_INDICATOR), prolog_output.rfind(FAILURE_INDICATOR))
    if result_indicator_pos == -1:
        print(f"   Output of unexpected format (Expected {SUCCESS_INDICATOR} or {FAILURE_INDICATOR})")
        return FAILURE_ELEMENTS
    if prolog_output[result_indicator_pos:].startswith(FAILURE_INDICATOR):
        print(f"   Prolog did not find valid domain execution. Output:\n{prolog_output}")
        return FAILURE_ELEMENTS
    fact_start_pos = prolog_output.find("\n", result_indicator_pos) + 1
    fact_lines = prolog_output[fact_start_pos:].strip().splitlines()
    facts: set[FactExpr] = set()
    objs: set[str] = set()
    executables: set[str] = set()
    for line in fact_lines:
        # print("F", line)
        fact = FactExpr.from_str(line)
        if fact.predicate_name.startswith("type"):
            obj: IdentifierConst = fact.args[0]
            objs.add(obj.name)
        elif fact.predicate_name == "atom":
            obj: IdentifierConst = fact.args[0]
            objs.add(obj.name)
        elif fact.predicate_name == "executable":
            ex_name: IdentifierConst = fact.args[0]
            executables.add(ex_name.name)
            if "_M_" in ex_name.name:
                # method executable, also add task name
                task_name = ex_name.name.split("_M_")[0]
                executables.add(task_name)
        else:
            facts.add(fact)
    return objs, facts, executables

def get_required_facts(goal_call: TaskCall, filename: str = STD_PROLOG_EXPORT)  -> tuple[set[str], set[FactExpr]]:
    """Returns the facts needed for the given goal call."""
    print(f">> Running Prolog file {filename!r} to get required predicates for {str(goal_call)!r}")
    goal_call_str = prolog_executable_call(goal_call)
    command = f"swipl -q -g \"" \
        f"consult('{filename}'), start_tracking," \
        f"({goal_call_str} -> writeln('{SUCCESS_INDICATOR}'); writeln('{FAILURE_INDICATOR}'))," \
        "print_used_facts.\" -t halt"
    try: 
        prolog_process = subprocess.run(
            command,
            capture_output=True,
            check=True,
            text=True,
            shell=True
        )
        return prolog_output_elements(prolog_process.stdout)
    except subprocess.CalledProcessError as e:
        print("Error executing Prolog command:", e)
        return FAILURE_ELEMENTS

@timed
def optimize_domain(
        domain: DomainFile,
        problem: ProblemFile, *, 
        recompile_domain: bool = True,
        static_preds: set[str] = None,
        false_preds: set[str] = set()) -> bool:
    """Optimizes the domain by removing unused predicates based on the goal call.\n
    returns True if optimization was successful, False otherwise."""
    print(f">> Optimizing domain {domain.domain_name!r} based on problem {problem.problem_name!r}")

    if static_preds is None:
        static_preds = domain_static_preds(domain)
    if recompile_domain:
        # write_domain_to_prolog_file(domain, false_preds=false_preds)
        prolog_domain = PrologDomain.from_domain(domain)
        prolog_domain.move_preconditions_up(move_preds=static_preds)
        prolog_domain.export_to_prolog(static_preds=static_preds, false_preds=false_preds)
    
    res = (req_objs, req_facts, req_execs) = get_required_facts(problem.goal)
    if res == FAILURE_ELEMENTS:
        print("  Domain optimization failed. Keeping original domain.")
        return False
    
    print(f"   BEFORE:")
    print(f"   dom.consts: {domain.nr_consts:>4} | dom.facts: {problem.nr_facts:>4} | "
          f"dom.execs: {len(domain.top_level_elements):>4}")

    # keep only needed static facts, keep all non-static facts
    problem.fact_declarations = [
        fact for fact in problem.fact_declarations
        if fact in req_facts or fact.predicate_name not in static_preds]
    # keep only needed constants and executables
    domain.declared_constants = [
        ShitObjects(
            names=[name for name in cons.names if name in req_objs],
            type=cons.type)
        for cons in domain.declared_constants]
    domain.top_level_elements = [
        tl for tl in domain.top_level_elements
        if (isinstance(tl, (Action, Task, Method)) and executable_repr_name(tl) in req_execs)]
    
    print(f"   AFTER:")
    print(f"   dom.consts: {domain.nr_consts:>4} | dom.facts: {problem.nr_facts:>4} | "
          f"dom.execs: {len(domain.top_level_elements):>4}")
    return True