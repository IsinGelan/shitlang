
from typing import Callable, Literal

from .parser_domain import to_dicts as domain_to_dicts
from .parser_problem import to_dicts as problem_to_dicts
from .shit_objs import DomainFile, ProblemFile

# ================================
# Example of some SHIT:
EXAMPLE = """
domain minecraft

type Interactable Container < Block
const eye_of_ender : Interactable
const stronghold banana : Container

go-to-dimension : m-end(dim)
  < dim = end
  - acquire-item(eye_of_ender, a12)
  - find-structure(stronghold)
  - find-portal-room()
  - complete-end-portal
  - enter-end-portal

# Banana
sdalsdk : do-anything()
    1 banana
    2 apple
    3 orange
    4 pear
    order (1 2) < 3
    order 2 < 4 


action complete-end-portal
  < near_structure(end_portal)
  < inv_num(eye_of_ender) >= 12
  => near_structure(lit_end_portal)
"""

PATHS = {
    ("domain", False): "domain_w_macro.shit",
    ("domain", True): "error_domain_w_macro.shit",
    ("problem", False): "problem_w_macro.shit",
    ("problem", True): "error_problem_w_macro.shit"
}

# Function that modifies the source code before compilation
CodeMacro = Callable[[str], str]
FileType = Literal["domain", "problem"]

# ================================
def save_macro_code_file(code: str, ft: FileType, error: bool = False):
    path = PATHS[(ft, error)]
    with open(path, "w", encoding="utf-8") as file:
        file.write(code)


def transpile_domain_str(
        code: str, *,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False) -> DomainFile:
    
    for macro_fun in macro_funs:
        code = macro_fun(code)
    
    try:
        dicts, file_data = domain_to_dicts(code)
        file = DomainFile.from_dict(dicts, file_data)
    except Exception as e:
        if macro_funs:
            save_macro_code_file(code, ft="domain", error=True)
            print("Error with applied macros:")
        raise e
    else:
        if show_macro_result:
            save_macro_code_file(code, ft="domain", error=False)

    return file

def transpile_domain(
        filename: str,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False) -> DomainFile:
    with open(filename, "r", encoding="utf-8") as file:
        code = file.read()
    return transpile_domain_str(
        code,
        macro_funs=macro_funs,
        show_macro_result=show_macro_result)

def transpile_problem_str(
        code: str, *,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False) -> DomainFile:

    for macro_fun in macro_funs:
        code = macro_fun(code)

    try:
        dicts = problem_to_dicts(code)
        file = ProblemFile.from_dict(dicts)
    except Exception as e:
        if macro_funs:
            save_macro_code_file(code, ft="problem", error=True)
            print("Error with applied macros:")
        raise e
    else:
        if show_macro_result:
            save_macro_code_file(code, ft="problem", error=False)

    return file

def transpile_problem(
        filename: str,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False) -> DomainFile:
    with open(filename, "r", encoding="utf-8") as file:
        code = file.read()
    return transpile_problem_str(
        code,
        macro_funs=macro_funs,
        show_macro_result=show_macro_result)