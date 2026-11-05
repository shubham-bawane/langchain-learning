"""Defence-in-depth runner for LLM-written code. NOT a real security boundary: use containers or
gVisor/Firecracker for genuinely untrusted code."""
import ast
import json
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ALLOWED_IMPORTS = {
    "math", "itertools", "collections", "re", "functools", "heapq", "bisect", "string",
    "operator", "statistics", "decimal", "fractions", "typing", "dataclasses",
}
BANNED_NAMES = {
    "eval", "exec", "compile", "open", "input", "breakpoint", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "memoryview", "help", "exit", "quit",
}
ALLOWED_DUNDER_ATTRS = {"__init__"}
ALLOWED_DUNDER_NAMES = {"__name__"}
TIMEOUT_S = 5.0


def check_source(code: str) -> list[str]:
    """Static allowlist check run before any execution."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"syntax error: {exc.msg} (line {exc.lineno})"]
    problems: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    problems.add(f"import of '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                problems.add(f"import from '{node.module}' is not allowed")
        elif isinstance(node, ast.Name):
            bad_dunder = node.id.startswith("__") and node.id not in ALLOWED_DUNDER_NAMES
            if node.id in BANNED_NAMES or bad_dunder:
                problems.add(f"use of '{node.id}' is not allowed")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr not in ALLOWED_DUNDER_ATTRS:
                problems.add(f"attribute '{node.attr}' is not allowed")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Blocks format-string tricks such as '{0.__class__}'.format(x)
            if "__" in node.value and node.value != "__main__":
                problems.add("string literals containing '__' are not allowed")
    return sorted(problems)


def validate_assert(src: str) -> list[str]:
    """A test must be exactly one assert statement that passes the same static check."""
    try:
        body = ast.parse(src).body
    except SyntaxError as exc:
        return [f"syntax error: {exc.msg}"]
    if len(body) != 1 or not isinstance(body[0], ast.Assert):
        return ["must be a single assert statement"]
    return check_source(src)


RUNNER = r'''
import ast, builtins, contextlib, io, json, resource

with open("payload.json") as f:
    payload = json.load(f)
for lim, val in ((resource.RLIMIT_CPU, 6), (resource.RLIMIT_AS, 768 * 1024 * 1024),
                 (resource.RLIMIT_FSIZE, 1024 * 1024), (resource.RLIMIT_NOFILE, 16)):
    try:
        resource.setrlimit(lim, (val, val))
    except (ValueError, OSError):
        pass

SAFE = ("abs all any bool bytes bytearray callable chr complex dict divmod enumerate filter float format "
        "frozenset hasattr hash hex int isinstance issubclass iter len list map max min next object oct ord "
        "pow print property range repr reversed round set slice sorted staticmethod classmethod str sum super "
        "tuple type zip bin id").split()
EXC = ("ArithmeticError AssertionError AttributeError Exception IndexError KeyError LookupError "
       "NotImplementedError OverflowError RuntimeError StopIteration TypeError ValueError ZeroDivisionError "
       "RecursionError").split()
safe = {n: getattr(builtins, n) for n in SAFE + EXC}
safe["__build_class__"] = builtins.__build_class__
allowed = set(payload["allowed"])
real_import = builtins.__import__


def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name.split(".")[0] not in allowed:
        raise ImportError("import of %r is not allowed" % name)
    return real_import(name, globals, locals, fromlist, level)


safe["__import__"] = guarded_import
ns = {"__builtins__": safe, "__name__": "solution"}
buf = io.StringIO()
error = ""
results = []
try:
    with contextlib.redirect_stdout(buf):
        exec(compile(payload["code"], "<solution>", "exec"), ns)
except BaseException as exc:
    error = type(exc).__name__ + ": " + str(exc)[:300]

if not error:
    for src in payload["asserts"]:
        res = {"test": src, "passed": False, "error": ""}
        try:
            node = ast.parse(src).body[0]
            with contextlib.redirect_stdout(buf):
                try:
                    exec(compile(src, "<test>", "exec"), ns)
                    res["passed"] = True
                except AssertionError:
                    t = node.test
                    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
                        got = eval(compile(ast.fix_missing_locations(ast.Expression(t.left)), "<t>", "eval"), ns)
                        exp = eval(compile(ast.fix_missing_locations(ast.Expression(t.comparators[0])), "<t>", "eval"), ns)
                        res["error"] = "got %r, expected %r" % (got, exp)
                    else:
                        res["error"] = "assertion failed"
        except BaseException as exc:
            res["error"] = type(exc).__name__ + ": " + str(exc)[:200]
        res["error"] = res["error"][:300]
        results.append(res)

print(json.dumps({"nonce": payload["nonce"], "error": error, "results": results, "stdout": buf.getvalue()[:1000]}))
'''


def _failed(asserts: list[str], reason: str) -> dict[str, Any]:
    return {
        "error": reason,
        "results": [{"test": a, "passed": False, "error": reason} for a in asserts],
        "stdout": "",
    }


def run_tests(code: str, asserts: list[str], timeout: float = TIMEOUT_S) -> dict[str, Any]:
    """Run each assert against the solution in a throwaway interpreter with no env and a restricted namespace."""
    nonce = secrets.token_hex(8)
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "payload.json").write_text(
            json.dumps({"code": code, "asserts": asserts, "allowed": sorted(ALLOWED_IMPORTS), "nonce": nonce})
        )
        Path(tmp, "runner.py").write_text(RUNNER)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-S", "runner.py"],
                cwd=tmp, env={}, capture_output=True, text=True, timeout=timeout, start_new_session=True,
            )
        except subprocess.TimeoutExpired:
            return _failed(asserts, f"timed out after {timeout:.0f}s (infinite loop?)")
    lines = (proc.stdout or "").strip().splitlines()
    try:
        data = json.loads(lines[-1])
        if data.get("nonce") != nonce:
            raise ValueError("nonce mismatch")
    except (IndexError, ValueError):
        return _failed(asserts, "runner crashed: " + (proc.stderr or "no output")[-200:])
    data.pop("nonce", None)
    if data["error"] and not data["results"]:
        data["results"] = [{"test": a, "passed": False, "error": data["error"]} for a in asserts]
    return data
