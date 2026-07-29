
class ShitError(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class TypeUndeclaredError(ShitError):
    def __init__(self, type_names: list[str]):
        self.message = f"Types are not declared: {', '.join(type_names)}."
        super().__init__(self.message)

class ConstUndeclaredError(ShitError):
    """Exception raised for using a constant that is not declared.

    Attributes:
        name -- name of the constant
        message -- explanation of the error
    """

    def __init__(self, const_names: list[str]):
        self.message = f"Constants are not declared: {', '.join(const_names)}."
        super().__init__(self.message)


def raise_const_undeclared(const_names: list[str]):
    raise ConstUndeclaredError(const_names)

def raise_type_undeclared(types_names: list[str]):
    raise TypeUndeclaredError(types_names)