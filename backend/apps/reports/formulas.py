import ast
from datetime import date

ALLOWED_FUNCTIONS = {'today', 'days_between', 'months_between', 'coalesce'}
ALLOWED_NODES = {
    ast.Expression,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.UnaryOp,
    ast.USub,
}


class FormulaValidationError(ValueError):
    pass


def validate_formula(expression):
    tree = ast.parse(expression, mode='eval')
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            raise FormulaValidationError(f'Unsupported formula syntax: {type(node).__name__}')
        if isinstance(node, ast.Call) and getattr(node.func, 'id', '') not in ALLOWED_FUNCTIONS:
            raise FormulaValidationError(f"Unsupported formula function: {getattr(node.func, 'id', '')}")
    return tree


def today():
    return date.today()


def days_between(a, b):
    return abs((a - b).days)


def months_between(a, b):
    return abs((a.year - b.year) * 12 + (a.month - b.month))


def coalesce(*values):
    for value in values:
        if value not in (None, ''):
            return value
    return None
