
from typing import NamedTuple

import pyparsing as pp

BASE_TYPE = "object"
# if we don't want surrounding brackets

# ================================
pp.ParserElement.set_default_whitespace_chars(" \t")

get_inner = lambda t: t[0] if len(t) == 1 else t

file_constants: set[str] = set()
file_types: set[str] = set()
file_preds: set[tuple[str, int]] = set()
file_called_execs: set[tuple[str, int]] = set()
file_declared_execs: set[tuple[str, int]] = set()
file_negative_facts: bool = False
current_params: set[str] = set()

def set_current_params(tokens: pp.ParseResults):
    elems = tokens[0]
    param_names = [p[0] for p in elems]
    current_params.clear()
    current_params.update(param_names)
    return tokens
def reset_file_constants():
    file_constants.clear()
def add_file_constant(name: str):
    file_constants.add(name)
def reset_file_types():
    file_types.clear()
def add_file_type(tokens: pp.ParseResults):
    if not tokens:
        return
    name = tokens[0]
    file_types.add(name)
def add_file_pred(tokens: pp.ParseResults):
    tok = tokens[0]
    if tok[0] in ("!", "~"):
        global file_negative_facts
        file_negative_facts = True
        tok = tok[1:]
    name, *args = tok
    arity = len(args)
    file_preds.add((name, arity))
def reset_file_preds():
    file_preds.clear()
def add_file_exec_call(tokens: pp.ParseResults):
    content = tokens[0][0]
    name, args = content
    file_called_execs.add((name, len(args)))
def reset_file_exec_calls():
    file_called_execs.clear()
def add_file_action_decl(tokens: pp.ParseResults):
    name, args = tokens
    file_declared_execs.add((name, len(args)))
def add_file_task_decl(tokens: pp.ParseResults):
    content = tokens[0]
    name, args = content
    file_declared_execs.add((name, len(args)))
def reset_file_exec_decls():
    file_declared_execs.clear()
def reset_negative_facts():
    global file_negative_facts
    file_negative_facts = False

def reset_file_data():
    reset_file_constants()
    reset_file_types()
    reset_file_preds()
    reset_file_exec_calls()
    reset_file_exec_decls()
    reset_negative_facts()

def identify_id_type(tokens):
    tok = tokens[0]
    if tok in current_params:
        return {"param": tok}
    else:
        file_constants.add(tok)
        return {"const": tok}
def number_dict(tokens):
    return {"number": int(tokens[0])}

# ================================
name = pp.Word(pp.alphas, pp.alphanums + "-_")
number = pp.Word(pp.nums).set_parse_action(number_dict)
# number = pp.Word(pp.nums).set_results_name("number")

identifier = pp.Word(pp.alphas, pp.alphanums + "-_").set_parse_action(identify_id_type)
param = pp.Group(
    name.set_results_name("param_name")
    + pp.Opt(pp.Suppress(":") + name)
        .add_parse_action(get_inner, add_file_type)
        .set_results_name("param_type")
    )

params = pp.Group(pp.Opt(
    pp.Suppress("(")
    + pp.Opt(pp.DelimitedList(param))
    + pp.Suppress(")"))).set_parse_action(set_current_params)
arg = identifier ^ number
args = pp.Group(pp.Opt(
        pp.Suppress("(")
        + pp.Opt(pp.DelimitedList(arg))
        + pp.Suppress(")")
    ))
true_args = (
    pp.Suppress("(")
    + pp.Opt(pp.DelimitedList(arg))
    + pp.Suppress(")"))
    

call = pp.Group(
    name.set_results_name("name")
    + args.set_results_name("args")
    ).set_results_name("call")
true_call = pp.Group(
    name.set_results_name("name")
    + true_args.set_results_name("args")
    ).set_results_name("call")
predicate_call = pp.Group(
    pp.Opt(pp.Literal("!") | pp.Literal("~")).set_results_name("negated")
    + name.set_results_name("name")
    + true_args.set_results_name("args")
    ).set_results_name("call").add_parse_action(add_file_pred)
# predicate_call = true_call.copy().add_parse_action(add_file_pred)

# ----------------------
# comparisons
comparator = pp.one_of("= != < > <= >=")
expr_value = pp.Group(
    identifier
    ^ true_call
    ^ number)
expr_comparison = pp.Group(
    expr_value.set_results_name("left")
    + comparator.set_results_name("comparator")
    + expr_value.set_results_name("right")
    ).set_results_name("comparison")
logical_expr = predicate_call ^ expr_comparison

# ----------------------
# precondtion, postcondition
precondition = pp.Group(pp.Suppress("<") + logical_expr)
postcondition = pp.Group(pp.Suppress(pp.Literal(">") ^ "=>") + logical_expr)
method_precondition = pp.ZeroOrMore(
    precondition + pp.Suppress("\n")
    ).set_results_name("precondition")
action_postcondition = pp.ZeroOrMore(
    postcondition + pp.Suppress("\n")
    ).set_results_name("postcondition")

# ----------------------
# subtasks
subtask_uo = pp.Group(number.set_results_name("id") + call).set_parse_action(add_file_exec_call)
subtasks_unordered = pp.Group(
    pp.OneOrMore(subtask_uo + pp.Suppress("\n"))
    ).set_results_name("subtasks_unordered")
subtask_seq = pp.Group(pp.Suppress("-") + call).set_parse_action(add_file_exec_call)
subtasks_sequence = pp.Group(
    pp.OneOrMore(subtask_seq + pp.Suppress("\n"))
    ).set_results_name("subtasks_sequence")#.add_parse_action(lambda t: print("SEQ", t))

# ----------------------
# orderings
order_group = pp.Group(pp.Suppress("(") + pp.OneOrMore(number) + pp.Suppress(")"))
order_num = pp.Group(number)
order_seq = pp.Group(pp.Suppress("order") + pp.DelimitedList(order_group ^ order_num, delim="<", min=2))
orderings = pp.Group(
    pp.OneOrMore(order_seq + pp.Suppress("\n"))
    ).set_results_name("orderings")
subtasks_with_orderings = subtasks_unordered + orderings

# ----------------------
# method
task = pp.Group(
    pp.Suppress("task")
    + name.set_results_name("task_name")
    + params.set_results_name("task_params")
).set_results_name("task").set_parse_action(add_file_task_decl)

method_identifier = (
    name.set_results_name("task_name")
    + pp.Opt(
        pp.Suppress(":")
        + name,
        default=""
        ).set_parse_action(get_inner).set_results_name("method_name")
    )
method_head = (
    method_identifier
    + params.set_results_name("method_params")
    + pp.Suppress("\n"))

method = pp.Group(
    method_head
    + method_precondition
    + (subtasks_with_orderings ^ subtasks_sequence)
).set_results_name("method")

# ----------------------
# action
action_head = (
    pp.Suppress("action")
    + name.set_results_name("action_name")
    + params.set_results_name("action_params")
    + pp.Suppress("\n")
    ).set_parse_action(add_file_action_decl)

incomplete_ellipsis = pp.Group(pp.Suppress("...\n")).set_results_name("incomplete_ellipsis")

action = pp.Group(
    action_head
    + method_precondition
    + action_postcondition
    + pp.Opt(incomplete_ellipsis)
).set_results_name("action")

# ----------------------
# file header
domain_name = pp.Suppress("domain") + name.set_results_name("domain_name") + pp.Suppress("\n")
type_decl = pp.Group(
    pp.Suppress("type")
    + pp.Group(pp.OneOrMore(name)).set_results_name("subtypes")
    + pp.Opt(
        pp.Suppress("<") + name,
        default=BASE_TYPE
        ).set_parse_action(get_inner).set_results_name("supertype"))

type_declarations = pp.Group(
    pp.ZeroOrMore(type_decl + pp.Suppress("\n"))
    ).set_results_name("type_declarations")

const_decl = pp.Group(
    pp.Suppress("const")
    + pp.Group(pp.OneOrMore(name)).set_results_name("ids")
    + pp.Opt(
        pp.Suppress(":") + name,
        default=BASE_TYPE).set_parse_action(get_inner).set_results_name("type"))
const_declarations = pp.Group(
    pp.ZeroOrMore(const_decl + pp.Suppress("\n"))
    ).set_results_name("const_declarations")

pred_decl = pp.Group(
    pp.Suppress("pred")
    + name.set_results_name("pred_name")
    + params.set_results_name("pred_params"))
pred_declarations = pp.Group(
    pp.ZeroOrMore(pred_decl + pp.Suppress("\n"))
    ).set_results_name("pred_declarations")


# ----------------------
# top level
comment = pp.Group(pp.Suppress("#") + pp.rest_of_line.set_results_name("content")).set_results_name("comment")

element_delim = pp.Suppress(pp.Regex(r"[ \t\n]*"))
file_header = pp.Group(
    domain_name + element_delim
    + type_declarations + pp.Opt(element_delim)
    + const_declarations + pp.Opt(element_delim)
    + pred_declarations
).set_fail_action(lambda *_: print("File header expected: domain, types, constants"))

shit_element = pp.Group(task) ^ pp.Group(method) ^ pp.Group(action) ^ pp.Group(comment)

file = pp.Group(
    pp.Opt(element_delim)
    + file_header.set_results_name("file_header")
    + pp.Opt(element_delim)
    + pp.Group(
        pp.ZeroOrMore(shit_element + element_delim)
    ).set_results_name("file_elements")
    ).set_results_name("file")


# ================================
class FileData(NamedTuple):
    found_constants: set[str]
    found_types: set[str]
    found_predicates: set[tuple[str, int]]
    found_exec_calls: set[tuple[str, int]]
    found_exec_decls: set[tuple[str, int]]
    found_negative_facts: bool


# ================================
def shit_to_dicts(code: str) -> tuple[dict, FileData]:
    """returns dict, constants from file"""
    reset_file_data()
    res = file.parse_string(code+"\n", parse_all=True).as_dict().get("file", {})
    file_data = FileData(
        found_constants=file_constants,
        found_types=file_types,
        found_predicates=file_preds,
        found_exec_calls=file_called_execs,
        found_exec_decls=file_declared_execs,
        found_negative_facts=file_negative_facts)
    return (
        res,
        file_data)

def make_parsing_graph(nonterminal: pp.ParserElement = file):
    with open("parsing_graph.html", "w") as f:
        nonterminal.create_diagram(f)

# ================================
def main():
    test = "type Container Interactable < Block"
    print(type_decl.parse_string(test).as_dict())
    test = "type Block"
    print(type_decl.parse_string(test).as_dict())

if __name__ == "__main__":
    main()
