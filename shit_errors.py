
class ShitError(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class UndeclaredTypesError(ShitError):
    def __init__(self, type_names: list[str]):
        self.message = f"Types are not declared: {', '.join(type_names)}."
        super().__init__(self.message)

class UndeclaredConstsError(ShitError):
    """Exception raised for using a constant that is not declared.

    Attributes:
        name -- name of the constant
        message -- explanation of the error
    """

    def __init__(self, const_names: list[str]):
        self.message = f"Constants are not declared: {', '.join(const_names)}."
        super().__init__(self.message)

CallSignature = tuple[str, int]  # (predicate_name, arity)

class UndeclaredPredicatesError(ShitError):
    """Exception raised for using a predicate that is not declared.

    Attributes:
        name -- name of the predicate
        message -- explanation of the error
    """

    def __init__(self, predicates: list[CallSignature]):
        pred_strings = [f"{name}/{arity}" for name, arity in predicates]
        self.message = f"Predicates are not declared:\n  {',\n  '.join(pred_strings)}."
        super().__init__(self.message)

class UndeclaredExecutablesError(ShitError):
    """Exception raised for using a predicate that is not declared.

    Attributes:
        name -- name of the predicate
        message -- explanation of the error
    """

    def __init__(self, predicates: list[CallSignature]):
        exec_strings = [f"{name}/{arity}" for name, arity in predicates]
        self.message = f"Actions / Tasks are not declared:\n  {',\n  '.join(exec_strings)}."
        super().__init__(self.message)


def raise_const_undeclared(const_names: list[str]):
    raise UndeclaredConstsError(const_names)

def raise_type_undeclared(types_names: list[str]):
    raise UndeclaredTypesError(types_names)

def raise_predicate_undeclared(predicates: list[CallSignature]):
    raise UndeclaredPredicatesError(predicates)