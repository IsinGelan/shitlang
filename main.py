
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

PARTIAL = """action complete-end-portal
  < near_structure(end_portal)
  < inv_num(eye_of_ender) >= 12
  => near_structure(lit_end_portal)"""


# ================================
def export_dicts_to_json(dicts: dict, filename: str):
    import json
    with open(filename, "w") as f:
        json.dump(dicts, f, indent=4)

def transpile_str_to_str(code: str) -> list[str]:
    dicts, file_data = shit_to_dicts(code)
    #export_dicts_to_json(dicts, "example_dump.json")
    file = dicts_to_shit_objects(dicts, file_data)
    return file.to_lisp_obj().to_hddl_str()

def transpile_str_to_file(code: str, filename: str):
    res = transpile_str_to_str(code)
    with open(filename, "w") as f:
        f.write(res)

def transpile_file_to_file(input_filename: str, output_filename: str):
    with open(input_filename, "r") as f:
        code = f.read()
    transpile_str_to_file(code, output_filename)


# code = EXAMPLE
# transpile_str_to_file(code, "test_output.hddl")
if __name__ == "__main__":
    transpile_file_to_file("example.shit", "example.hddl")



