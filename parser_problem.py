
import pyparsing as pp

from .parser_domain import BASE_TYPE

# ================================
def as_const(tokens: pp.ParseResults):
    tok = tokens[0]
    return {"const": tok}
def number_dict(tokens: pp.ParseResults):
    return {"number": int(tokens[0])}

# ================================
name = pp.Word(pp.alphas, pp.alphanums + "-_").set_name("name")
identifier = pp.Word(pp.alphas, pp.alphanums + "-_").set_parse_action(as_const).set_name("identifier")
number = pp.Word(pp.nums).set_parse_action(number_dict).set_name("number")

arg = identifier ^ number
args = pp.Group(pp.Opt(
        pp.Suppress("(")
        + pp.Opt(pp.DelimitedList(arg))
        + pp.Suppress(")")
    )).set_name("arguments")
true_args = (
    pp.Suppress("(")
    + pp.Opt(pp.DelimitedList(arg))
    + pp.Suppress(")")).set_name("true_arguments")
    
call = pp.Group(
    name("name")
    + args("args")
    ).set_name("call")
true_call = pp.Group(
    name("name")
    + true_args("args")
    ).set_name("true_call")

# ================================
pp.ParserElement.set_default_whitespace_chars(" \t\n")
EOL = pp.LineEnd().suppress()

problem = (
    pp.Suppress("problem")
    + name("domain_name")
    + pp.Suppress(":")
    + name("problem_name")
    + EOL
).set_name("file_header")

goal = (
    pp.Suppress("goal")
    + call("goal")
    + EOL
).set_name("goal")

obj_decl = pp.Group(
    pp.Suppress("obj")
    + pp.Group(pp.OneOrMore(name))("ids")
    + pp.Opt(
        pp.Suppress(":") + name,
        default=BASE_TYPE)("type"))
obj_declarations = pp.Group(
    pp.ZeroOrMore(obj_decl + EOL)
    ).set_name("object_declarations")

fact_declarations = pp.Group(
    pp.ZeroOrMore(true_call + EOL)
    ).set_name("fact_declarations")

comment_ignore = pp.Literal("#") + pp.SkipTo(pp.LineEnd())

file = pp.Group(
    problem
    + goal
    + obj_declarations("obj_declarations")
    + fact_declarations("fact_declarations")
).ignore(comment_ignore).set_name("file").set_results_name("file")

def to_dicts(inp: str):
    return file.parse_string(inp, parse_all=True).as_dict().get("file", {})

