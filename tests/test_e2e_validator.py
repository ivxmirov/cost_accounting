import ast
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def extract_string_from_node(node) -> Optional[str]:
    """Извлекает строковый литерал из узла AST, обрабатывая f-строки и обычные строки."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
    elif isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
        if parts:
            base = "".join(parts)
            if "?" in base:
                base = base.split("?")[0]
            return base
    return None


def extract_endpoint_from_call(node: ast.Call) -> Optional[str]:
    """Извлекает URL эндпоинта из вызова client.post/get."""
    if not isinstance(node.func, ast.Attribute):
        return None

    if node.func.attr not in ("post", "get", "put", "patch", "delete"):
        return None

    if not isinstance(node.func.value, ast.Name):
        return None

    if node.func.value.id != "client":
        return None

    if not node.args:
        return None

    endpoint = extract_string_from_node(node.args[0])
    if endpoint:
        if "?" in endpoint:
            endpoint = endpoint.split("?")[0]
        return endpoint

    return None


def extract_api_calls_from_function(func_node) -> List[Tuple[str, str]]:
    """Извлекает все вызовы API (метод, эндпоинт) из тестовой функции."""
    calls = []

    class ApiCallVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            if isinstance(node.func, ast.Attribute):
                method = node.func.attr.upper()
                endpoint = extract_endpoint_from_call(node)
                if endpoint:
                    calls.append((method, endpoint))
            self.generic_visit(node)

    visitor = ApiCallVisitor()
    visitor.visit(func_node)
    return calls


def extract_api_calls_from_test(file_path: str, test_name: str) -> List[Tuple[str, str]]:
    """Извлекает вызовы API из тестовой функции в Python файле."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Test file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        raise SyntaxError(f"Failed to parse {file_path}: {e}")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == test_name:
            return extract_api_calls_from_function(node)

    raise ValueError(f"Test function '{test_name}' not found in {file_path}")


def normalize_endpoint(endpoint: str) -> str:
    """Нормализует эндпоинт: убирает query параметры и trailing слэши."""
    if "?" in endpoint:
        endpoint = endpoint.split("?")[0]
    return endpoint.rstrip("/")


def validate_test_structure(
    test_name: str,
    actual_calls: List[Tuple[str, str]],
    expected_pattern: List[Tuple[str, str]],
    allow_extra: bool = True,
) -> Tuple[bool, str]:
    """Проверяет что фактические вызовы соответствуют ожидаемому паттерну.

    Args:
        test_name: Имя проверяемого теста
        actual_calls: Список (метод, эндпоинт) из теста
        expected_pattern: Список (метод, эндпоинт) ожидаемых вызовов
        allow_extra: Если True, разрешает дополнительные вызовы между ожидаемыми

    Returns:
        Кортеж (валиден ли тест, сообщение об ошибке)
    """
    if not actual_calls:
        return False, f"Test '{test_name}' has no API calls"

    actual_normalized = [
        (method, normalize_endpoint(endpoint)) for method, endpoint in actual_calls
    ]
    expected_normalized = [
        (method, normalize_endpoint(endpoint)) for method, endpoint in expected_pattern
    ]

    if allow_extra:
        expected_idx = 0
        matched_positions = []

        for i, (actual_method, actual_endpoint) in enumerate(actual_normalized):
            if expected_idx < len(expected_normalized):
                expected_method, expected_endpoint = expected_normalized[expected_idx]
                if actual_method == expected_method and actual_endpoint == expected_endpoint:
                    matched_positions.append(i)
                    expected_idx += 1

        if expected_idx < len(expected_normalized):
            missing = expected_normalized[expected_idx:]
            missing_str = ", ".join([f"{method} {endpoint}" for method, endpoint in missing])
            return (
                False,
                f"Test '{test_name}' is missing required calls: {missing_str}. "
                f"Expected sequence: {expected_pattern}. "
                f"Actual sequence: {actual_calls}",
            )

        return True, ""
    else:
        if len(actual_normalized) != len(expected_normalized):
            return (
                False,
                f"Test '{test_name}' has wrong number of calls. "
                f"Expected {len(expected_normalized)}, got {len(actual_normalized)}. "
                f"Expected: {expected_pattern}. Actual: {actual_calls}",
            )

        for i, (actual, expected) in enumerate(zip(actual_normalized, expected_normalized)):
            if actual != expected:
                return (
                    False,
                    f"Test '{test_name}' call {i + 1} mismatch: expected {expected}, got {actual}. "
                    f"Expected sequence: {expected_pattern}. "
                    f"Actual sequence: {actual_calls}",
                )

        return True, ""


def get_test_file_path() -> str:
    """Получает путь к файлу test_e2e.py."""
    current_dir = Path(__file__).parent
    test_file = current_dir / "test_e2e.py"
    return str(test_file)


EXPECTED_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
    "test_e2e_basic_user_flow_registration_to_expense": [
        ("POST", "/api/v1/users"),
        ("POST", "/api/v1/wallets"),
        ("PUT", "/api/v1/operations/income"),
        ("GET", "/api/v1/wallets"),
        ("PUT", "/api/v1/operations/expense"),
        ("GET", "/api/v1/wallets"),
    ],
    "test_e2e_multi_wallet_flow_with_transfer": [
        ("POST", "/api/v1/users"),
        ("POST", "/api/v1/wallets"),
        ("POST", "/api/v1/wallets"),
        ("GET", "/api/v1/wallets"),
        ("PUT", "/api/v1/operations/income"),
        ("PUT", "/api/v1/operations/transfer"),
        ("GET", "/api/v1/balance"),
        ("GET", "/api/v1/wallets"),
    ],
    "test_e2e_operations_history_and_report": [
        ("POST", "/api/v1/users"),
        ("POST", "/api/v1/wallets"),
        ("PUT", "/api/v1/operations/income"),
        ("PUT", "/api/v1/operations/income"),
        ("PUT", "/api/v1/operations/expense"),
        ("PUT", "/api/v1/operations/expense"),
        ("GET", "/api/v1/operations"),
        ("GET", "/api/v1/operations"),
        ("GET", "/api/v1/wallets"),
    ],
    "test_e2e_insufficient_funds_after_income": [
        ("POST", "/api/v1/users"),
        ("POST", "/api/v1/wallets"),
        ("PUT", "/api/v1/operations/income"),
        ("GET", "/api/v1/wallets"),
        ("PUT", "/api/v1/operations/expense"),
        ("GET", "/api/v1/wallets"),
    ],
    "test_e2e_expense_without_income": [
        ("POST", "/api/v1/users"),
        ("POST", "/api/v1/wallets"),
        ("GET", "/api/v1/wallets"),
        ("PUT", "/api/v1/operations/expense"),
        ("GET", "/api/v1/wallets"),
        ("GET", "/api/v1/operations"),
    ],
    "test_e2e_transfer_insufficient_funds": [
        ("POST", "/api/v1/users"),
        ("POST", "/api/v1/wallets"),
        ("POST", "/api/v1/wallets"),
        ("PUT", "/api/v1/operations/income"),
        ("PUT", "/api/v1/operations/transfer"),
        ("GET", "/api/v1/wallets"),
    ],
}


def test_e2e_basic_user_flow_structure():
    """Проверяет структуру теста test_e2e_basic_user_flow_registration_to_expense."""
    test_file = get_test_file_path()
    test_name = "test_e2e_basic_user_flow_registration_to_expense"

    actual_calls = extract_api_calls_from_test(test_file, test_name)
    expected_pattern = EXPECTED_PATTERNS[test_name]

    is_valid, error_msg = validate_test_structure(test_name, actual_calls, expected_pattern)
    assert is_valid, error_msg


def test_e2e_multi_wallet_flow_structure():
    """Проверяет структуру теста test_e2e_multi_wallet_flow_with_transfer."""
    test_file = get_test_file_path()
    test_name = "test_e2e_multi_wallet_flow_with_transfer"

    actual_calls = extract_api_calls_from_test(test_file, test_name)
    expected_pattern = EXPECTED_PATTERNS[test_name]

    is_valid, error_msg = validate_test_structure(test_name, actual_calls, expected_pattern)
    assert is_valid, error_msg


def test_e2e_operations_history_structure():
    """Проверяет структуру теста test_e2e_operations_history_and_report."""
    test_file = get_test_file_path()
    test_name = "test_e2e_operations_history_and_report"

    actual_calls = extract_api_calls_from_test(test_file, test_name)
    expected_pattern = EXPECTED_PATTERNS[test_name]

    is_valid, error_msg = validate_test_structure(test_name, actual_calls, expected_pattern)
    assert is_valid, error_msg


def test_e2e_insufficient_funds_structure():
    """Проверяет структуру теста test_e2e_insufficient_funds_after_income."""
    test_file = get_test_file_path()
    test_name = "test_e2e_insufficient_funds_after_income"

    actual_calls = extract_api_calls_from_test(test_file, test_name)
    expected_pattern = EXPECTED_PATTERNS[test_name]

    is_valid, error_msg = validate_test_structure(test_name, actual_calls, expected_pattern)
    assert is_valid, error_msg


def test_e2e_expense_without_income_structure():
    """Проверяет структуру теста test_e2e_expense_without_income."""
    test_file = get_test_file_path()
    test_name = "test_e2e_expense_without_income"

    actual_calls = extract_api_calls_from_test(test_file, test_name)
    expected_pattern = EXPECTED_PATTERNS[test_name]

    is_valid, error_msg = validate_test_structure(test_name, actual_calls, expected_pattern)
    assert is_valid, error_msg


def test_e2e_transfer_insufficient_funds_structure():
    """Проверяет структуру теста test_e2e_transfer_insufficient_funds."""
    test_file = get_test_file_path()
    test_name = "test_e2e_transfer_insufficient_funds"

    actual_calls = extract_api_calls_from_test(test_file, test_name)
    expected_pattern = EXPECTED_PATTERNS[test_name]

    is_valid, error_msg = validate_test_structure(test_name, actual_calls, expected_pattern)
    assert is_valid, error_msg


def test_e2e_file_exists():
    """Проверяет что файл test_e2e.py существует."""
    test_file = get_test_file_path()
    assert os.path.exists(test_file), f"test_e2e.py file not found at {test_file}"


def test_all_required_tests_present():
    """Проверяет что все необходимые E2E тестовые функции присутствуют в test_e2e.py."""
    test_file = get_test_file_path()

    if not os.path.exists(test_file):
        assert False, f"test_e2e.py file not found at {test_file}"

    with open(test_file, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=test_file)
    except SyntaxError as e:
        assert False, f"Failed to parse test_e2e.py: {e}"

    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    required_tests = set(EXPECTED_PATTERNS.keys())
    missing_tests = required_tests - function_names

    assert not missing_tests, (
        f"Missing required test functions in test_e2e.py: {', '.join(missing_tests)}. "
        f"Found functions: {', '.join(sorted(function_names))}"
    )
