
import json
from os import path
from typing import Callable, Literal


from .helpers import static_file_hash, timed
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
DUMP_DOMAIN_PATH = "temp/domain.json"
DUMP_PROBLEM_PATH = "temp/problem.json"


# Function that modifies the source code before compilation
CodeMacro = Callable[[str], str]
FileType = Literal["domain", "problem"]

# ================================
def save_macro_code_file(code: str, ft: FileType, error: bool = False):
    path = PATHS[(ft, error)]
    with open(path, "w", encoding="utf-8") as file:
        file.write(code)

# ================================
def preprocessed_str(
        code: str,
        macro_funs: list[CodeMacro] = []) -> str:
    for macro_fun in macro_funs:
        code = macro_fun(code)
    return code

def needs_recompilation(
        filename: str, *,
        macro_funs: list[CodeMacro] = [],
        dump_json_filepath: str = DUMP_DOMAIN_PATH
    ) -> bool:
    if not path.exists(dump_json_filepath):
        return True
    with open(dump_json_filepath, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    json_hash: str = json_data.get("file_hash")

    if json_hash is None:
        return True

    with open(filename, "r", encoding="utf-8") as file:
        code = file.read()
    preprocessed_code = preprocessed_str(code, macro_funs=macro_funs)
    file_hash = static_file_hash(preprocessed_code)

    return file_hash != json_hash

# ================================
def parse_domain_str(
        code: str, *,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False) -> DomainFile:
    
    code = preprocessed_str(code, macro_funs=macro_funs)
    
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

@timed
def parse_domain(
        filename: str, *,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False) -> DomainFile:
    with open(filename, "r", encoding="utf-8") as file:
        code = file.read()
    return parse_domain_str(
        code,
        macro_funs=macro_funs,
        show_macro_result=show_macro_result)

def get_domain(
        filename: str, *,
        recompile: bool = False,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False,
        dump_json_filepath: str = DUMP_DOMAIN_PATH) -> tuple[DomainFile, bool]:
    """Get Python representation of the domain. and return whether it was recompiled.\n
    If `recompile`, recompute the domain even if a JSON dump with same hash exists"""
    recompiling = recompile or needs_recompilation(
        filename, macro_funs=macro_funs, dump_json_filepath=dump_json_filepath)
    if recompiling:
        print(f">> Recompiling domain from {filename}...")
        domain = parse_domain(
            filename,
            macro_funs=macro_funs,
            show_macro_result=show_macro_result)
    else:
        print(f">> Restoring domain from {dump_json_filepath}...")
        domain = DomainFile.load_json(dump_json_filepath)

    return domain, recompiling


# ================================
def parse_problem_str(
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

@timed
def parse_problem(
        filename: str,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False) -> ProblemFile:
    with open(filename, "r", encoding="utf-8") as file:
        code = file.read()
    return parse_problem_str(
        code,
        macro_funs=macro_funs,
        show_macro_result=show_macro_result)

def get_problem(
        filename: str, *,
        recompile: bool = False,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False,
        dump_json_filepath: str = DUMP_PROBLEM_PATH) -> ProblemFile:
    """Get Python representation of the problem.\n
    If `recompile`, recompute the problem even if a JSON dump with same hash exists"""
    recompiling = recompile or needs_recompilation(
        filename, macro_funs=macro_funs, dump_json_filepath=dump_json_filepath)
    if recompiling:
        print(f">> Recompiling problem from {filename}...")
        problem = parse_problem(
            filename,
            macro_funs=macro_funs,
            show_macro_result=show_macro_result)
    else:
        print(f">> Restoring problem from {dump_json_filepath}...")
        problem = ProblemFile.load_json(dump_json_filepath)

    return problem