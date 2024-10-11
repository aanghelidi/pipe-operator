import ast

PLACEHOLDER = "_"
LAMBDA_VAR = "_pipe_x"


class PipeTransformer(ast.NodeTransformer):
    def __init__(self) -> None:
        self.lambda_transformer = LambdaTransformer(self, PLACEHOLDER, LAMBDA_VAR)
        super().__init__()

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        # Exit early if not `>>` operator
        if not isinstance(node.op, ast.RShift):
            return node

        # Property call `_.attribute`
        if (
            isinstance(node.right, ast.Attribute)
            and isinstance(node.right.value, ast.Name)
            and node.right.value.id == PLACEHOLDER
        ):
            return self._transform_attribute(node)

        # Method call `_.method(...)`
        if (
            isinstance(node.right, ast.Call)
            and isinstance(node.right.func, ast.Attribute)
            and isinstance(node.right.func.value, ast.Name)
            and node.right.func.value.id == PLACEHOLDER
        ):
            return self._transform_method_call(node)

        # Binary operator instruction other than `>>`
        if (
            isinstance(node.right, ast.BinOp)
            and not isinstance(node.right.op, ast.RShift)
            and self._contains_underscore(node.right)
        ):
            return self._transform_operation_to_lambda(node)

        # Lambda or function without parenthesis
        if not isinstance(node.right, ast.Call):
            return self._transform_name_to_call(node)

        # Basic function call `a >> b(...)`
        return self._transform_pipe_operation(node)

    def _transform_attribute(self, node: ast.expr) -> ast.expr:
        """Rewrite `a >> _.property` as `a.property`"""
        attr = ast.Attribute(
            value=node.left,
            attr=node.right.attr,
            ctx=ast.Load(),
            lineno=node.right.lineno,
            col_offset=node.right.col_offset,
        )
        return self.visit(attr)

    def _transform_method_call(self, node: ast.expr) -> ast.Call:
        """Rewrite `a >> _.method(...)` as `a.method(...)`"""
        call = ast.Call(
            func=ast.Attribute(
                value=node.left,
                attr=node.right.func.attr,
                ctx=ast.Load(),
                lineno=node.right.func.lineno,
                col_offset=node.right.func.col_offset,
            ),
            args=node.right.args,
            keywords=node.right.keywords,
            lineno=node.right.lineno,
            col_offset=node.right.col_offset,
        )
        return self.visit(call)

    def _transform_operation_to_lambda(self, node: ast.expr) -> ast.AST:
        """Rewrites `_ + a + b - _` as `lambda pipe_x: pipe_x + a + b - pipe_x`"""
        return self.lambda_transformer.visit(node)

    def _transform_name_to_call(self, node: ast.expr) -> ast.Call:
        """Convert function name / lambda etc without braces into call"""
        call = ast.Call(
            func=node.right,
            args=[node.left],
            keywords=[],
            lineno=node.right.lineno,
            col_offset=node.right.col_offset,
        )
        return self.visit(call)

    def _transform_pipe_operation(self, node: ast.expr) -> ast.Call:
        """Rewrite `a >> b(...)` as `b(a, ...)`"""
        args = 0 if isinstance(node.op, ast.RShift) else len(node.right.args)
        node.right.args.insert(args, node.left)
        return self.visit(node.right)

    @staticmethod
    def _contains_underscore(node: ast.expr) -> bool:
        """Checks if a node contains an underscore Name node"""
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Name) and subnode.id == "_":
                return True
        return False


class LambdaTransformer(ast.NodeTransformer):
    """
    Changes a not-right-shift BinOp node
    into a 1-arg lambda function node that performs the same operation
    but also replaces the `placeholder` variable with `var_name`

    Usage:
        LambdaTransformer()
        1_000 >> _ + 3 >> double >> _ - _
        1000 >> (lambda _pipe_x: _pipe_x + 3) >> double >> (lambda _pipe_x: _pipe_x - _pipe_x)
    """

    def __init__(
        self, fallback_transformer: ast.NodeTransformer, placeholder: str, var_name: str
    ) -> None:
        self.fallback_transformer = fallback_transformer
        self.placeholder = placeholder
        self.var_name = var_name
        self.name_transformer = NameReplacer(placeholder, var_name)
        super().__init__()

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        # Maybe change the operation
        if not isinstance(node.op, ast.RShift) and self._contains_placeholder(node):
            return self._create_lambda(node)
        # Recursively visit all BinOp nodes in the AST
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        return self.fallback_transformer.visit(node)

    def _contains_placeholder(self, node: ast.BinOp) -> bool:
        """Checks if a node contains an `placeholder` Name node."""
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Name) and subnode.id == self.placeholder:
                return True
        return False

    def _create_lambda(self, node: ast.BinOp) -> ast.Lambda:
        """Transforms the binary operation into a lambda function."""
        new_node = self.name_transformer.visit(node)
        return ast.Lambda(
            args=ast.arguments(
                args=[
                    ast.arg(
                        arg=self.var_name,
                        annotation=None,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                    )
                ],
                posonlyargs=[],
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=new_node,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )


class NameReplacer(ast.NodeTransformer):
    """
    In a Name node, replaces the id from `target` to `replacement`

    Usage:
        NameReplacer("_", "x")
        In:     "1000 + _ + func(_)"
        Out:    "1000 + x + func(x)"
    """

    def __init__(self, target: str, replacement: str) -> None:
        if target == replacement:
            raise ValueError("`target` and `replacement` must be different")
        self.target = target
        self.replacement = replacement
        super().__init__()

    def visit_Name(self, subnode: ast.expr) -> ast.expr:
        # Exit if not our target
        if subnode.id != self.target:
            return subnode
        # Replace `target` with `replacement`
        return ast.Name(
            id=self.replacement,
            ctx=ast.Load(),
            lineno=subnode.lineno,
            col_offset=subnode.col_offset,
        )
