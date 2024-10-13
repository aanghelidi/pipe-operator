import ast
from typing import Literal, Type

OperatorString = Literal[
    "+", "-", "*", "/", "%", "**", "<<", ">>", "|", "^", "&", "//", "@"
]

AST_STRING_MAP: dict[OperatorString, Type[ast.operator]] = {
    "+": ast.Add,
    "-": ast.Sub,
    "*": ast.Mult,
    "/": ast.Div,
    "%": ast.Mod,
    "**": ast.Pow,
    "<<": ast.LShift,
    ">>": ast.RShift,
    "|": ast.BitOr,
    "^": ast.BitXor,
    "&": ast.BitAnd,
    "//": ast.FloorDiv,
    "@": ast.MatMult,
}

SUPPORTED_DIRECT_OPERATIONS = (
    ast.Dict,
    ast.DictComp,
    ast.GeneratorExp,
    ast.JoinedStr,
    ast.List,
    ast.ListComp,
    ast.Set,
    ast.SetComp,
    ast.Tuple,
)


def string_to_ast_BinOp(value: OperatorString) -> Type[ast.operator]:
    """Converts a string to a BinOp"""
    if value not in AST_STRING_MAP:
        raise ValueError(f"Invalid operator: {value}")
    return AST_STRING_MAP[value]


def node_contains_name(node: ast.expr, name: str) -> bool:
    """Checks if a node contains a Name(id=`name`) node"""
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Name) and subnode.id == name:
            return True
    return False


def node_is_regular_BinOp(
    node: ast.expr, forbidden_operator: Type[ast.operator]
) -> bool:
    """Checks if a node is a BinOp but not the pipe operator"""
    return isinstance(node, ast.BinOp) and not isinstance(node.op, forbidden_operator)


def node_is_supported_operation(
    node: ast.expr, forbidden_operator: Type[ast.operator]
) -> bool:
    """Checks if a node is a direct operation or a regular BinOp"""
    is_supported_operation = isinstance(node, SUPPORTED_DIRECT_OPERATIONS)
    is_supported_BinOp = node_is_regular_BinOp(node, forbidden_operator)
    return is_supported_operation or is_supported_BinOp