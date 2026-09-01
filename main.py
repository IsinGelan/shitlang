
from typing import Callable

from .shit_parser import shit_to_dicts
from .shit_objs import dicts_to_shit_objects

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

MACRO_ERROR_PATH = "error_code_w_macro.shit"
MACRO_RESULT_PATH = "code_w_macro.shit"

# Function that modifies the source code before compilation
CodeMacro = Callable[[str], str]

# ================================
def save_macro_code_file(code: str, error: bool = False):
    path = MACRO_ERROR_PATH if error else MACRO_RESULT_PATH
    with open(path, "w", encoding="utf-8") as file:
        file.write(code)

# ================================
def export_dicts_to_json(dicts: dict, filename: str):
    import json
    with open(filename, "w") as f:
        json.dump(dicts, f, indent=4)

def transpile_str_to_str(
        code: str, *,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False) -> list[str]:
    for macro_fun in macro_funs:
        code = macro_fun(code)
    
    try:
        dicts, file_data = shit_to_dicts(code)
        file = dicts_to_shit_objects(dicts, file_data)
    except Exception as e:
        if macro_funs:
            save_macro_code_file(code, error=True)
            print("Error with applied macros:")
        raise e
    else:
        if show_macro_result:
            save_macro_code_file(code)

    #export_dicts_to_json(dicts, "example_dump.json")
    return file.to_lisp_obj().to_hddl_str()

def transpile_str_to_file(
        code: str, filename: str, *,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False):
    res = transpile_str_to_str(
        code,
        macro_funs=macro_funs,
        show_macro_result=show_macro_result)
    with open(filename, "w") as f:
        f.write(res)

def transpile_file_to_file(
        input_filename: str,
        output_filename: str, *,
        macro_funs: list[CodeMacro] = [],
        show_macro_result: bool = False):
    with open(input_filename, "r") as f:
        code = f.read()
    transpile_str_to_file(
        code,
        output_filename,
        macro_funs=macro_funs,
        show_macro_result=show_macro_result)
