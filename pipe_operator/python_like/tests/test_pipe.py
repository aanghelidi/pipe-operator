from unittest import TestCase
from unittest.mock import Mock, patch

from pipe_operator.python_like.pipe import Pipe, PipeValue, Tap, Then


def double(x: int) -> int:
    return x * 2


def duplicate_string(x: str) -> str:
    return f"{x}{x}"


def compute(x: int, y: int, z: int = 0) -> int:
    return x + y + z


def _sum(*args: int) -> int:
    return sum(args)


class BasicClass:
    def __init__(self, value: int) -> None:
        self.value = value

    def increment(self) -> None:
        self.value += 1

    @property
    def get_value_property(self) -> int:
        return self.value

    def get_value_method(self) -> int:
        return self.value

    def get_value_plus_arg(self, value: int) -> int:
        return self.value + value

    @classmethod
    def get_double(cls, instance: "BasicClass") -> "BasicClass":
        return BasicClass(instance.value * 2)


class PipeTestCase(TestCase):
    # ------------------------------
    # Settings
    # ------------------------------
    def test_pipe_does_not_support_lambdas(self) -> None:
        with self.assertRaises(TypeError):
            _ = PipeValue(3) >> Pipe(lambda x: x + 1)

    def test_then_only_supports_lambdas(self) -> None:
        with self.assertRaises(TypeError):
            _ = PipeValue(3) >> Then(double)

    # ------------------------------
    # Workflows
    # ------------------------------
    def test_with_functions(self) -> None:
        op = (
            PipeValue("3")
            >> Pipe(duplicate_string)
            >> Pipe(int)
            >> Pipe(compute, 30, z=10)
            # >> Pipe(_sum, 4, 5)
        )
        self.assertEqual(op.value, 73)

    def test_with_then(self) -> None:
        op = (
            PipeValue("3")
            >> Then[str, int](lambda x: int(x) + 1)
            >> Then[int, int](lambda x: double(x))
        )
        self.assertEqual(op.value, 8)

    def test_with_classes(self) -> None:
        op = (
            PipeValue(3)
            >> Pipe(double)
            >> Pipe(BasicClass)
            >> Pipe(BasicClass.get_double)
        )
        self.assertEqual(op.value.value, 12)

    def test_with_tap(self) -> None:
        mock = Mock()
        op = (
            PipeValue(3)
            >> Tap(lambda x: [x])
            >> Pipe(double)
            >> Tap(str)
            >> Pipe(double)
            >> Tap(compute, 2000, z=10)
            >> Tap(lambda x: mock(x))
            >> Pipe(double)
        )
        self.assertEqual(op.value, 24)
        mock.assert_called_once_with(12)

    def test_debug(self) -> None:
        with patch("builtins.print") as mock_print:
            op = (
                PipeValue(3, debug=True)
                >> Pipe(double)
                >> Tap(lambda x: mock_print(x))
                >> Pipe(double)
            )
            self.assertEqual(op.value, 12)
        self.assertEqual(mock_print.call_count, 5)

    def test_complex(self) -> None:
        op = (
            PipeValue("3")
            >> Pipe(duplicate_string)
            >> Pipe(int)
            >> Tap(compute, 2000, z=10)
            >> Then(lambda x: x + 1)
            >> Pipe(BasicClass)
            >> Pipe(BasicClass.get_double)
            >> Then[BasicClass, int](lambda x: x.value * 2)
            # >> Pipe(_sum, 4, 5, 6)
        )
        self.assertEqual(op.value, 136)
