# -*- coding: utf-8 -*-
"""FBRAH Advanced Calculator: safe scientific calculator with per-user history and reports."""
from __future__ import annotations

import ast
import math
import cmath
import operator
import os
import sqlite3
import statistics
import re
import time
from decimal import Decimal, InvalidOperation, DivisionByZero, getcontext
from io import BytesIO
getcontext().prec = 40

_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CONSTANTS = {"pi": Decimal(str(math.pi)), "e": Decimal(str(math.e)), "tau": Decimal(str(math.tau))}
_MAX_EXPR = 4000
_MAX_NODES = 250
_MAX_ABS = Decimal("1e1000")


def _num(value):
    if isinstance(value, bool):
        raise ValueError("Boolean values are not numeric.")
    if isinstance(value, complex):
        if not (math.isfinite(value.real) and math.isfinite(value.imag)) or abs(value) > float(_MAX_ABS):
            raise ValueError("Result is outside the supported numeric range.")
        return value
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, float):
        result = Decimal(str(value))
    elif isinstance(value, str):
        raw = value.strip().lower().replace("i", "j")
        try:
            result = Decimal(raw)
        except Exception:
            try:
                result = complex(raw)
            except Exception as exc:
                raise ValueError("Unsupported numeric value.") from exc
            return _num(result)
    else:
        raise ValueError("Unsupported numeric value.")
    if not result.is_finite() or abs(result) > _MAX_ABS:
        raise ValueError("Result is outside the supported numeric range.")
    return result


def _fmt(value):
    if isinstance(value, str):
        return value
    if isinstance(value, complex):
        def part(x):
            txt = format(Decimal(str(x)), ".14g")
            if txt.endswith(".0"): txt = txt[:-2]
            return "0" if txt in ("-0", "0") else txt
        real, imag = value.real, value.imag
        if abs(imag) < 1e-14:
            return part(real)
        if abs(real) < 1e-14:
            return part(imag) + "i" if abs(imag - 1) > 1e-14 and abs(imag + 1) > 1e-14 else ("i" if imag > 0 else "-i")
        sign = "+" if imag >= 0 else "-"
        imag_abs = abs(imag)
        imag_txt = "" if abs(imag_abs - 1) < 1e-14 else part(imag_abs)
        return part(real) + sign + imag_txt + "i"
    result = format(value, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return result


def _functions():
    def unary_math(fn, cfn=None):
        def run(x):
            value = _num(x)
            if isinstance(value, complex):
                return _num((cfn or fn)(value))
            try:
                return Decimal(str(fn(float(value))))
            except ValueError:
                if cfn:
                    return _num(cfn(complex(float(value), 0)))
                raise
        return run
    def round_fn(x, n=0):
        value = _num(x)
        if isinstance(value, complex):
            raise ValueError("round does not accept complex values.")
        n = int(n)
        if abs(n) > 100:
            raise ValueError("round precision must be between -100 and 100.")
        return value.quantize(Decimal(1).scaleb(-n))
    def factorial(x):
        d = _num(x)
        if isinstance(d, complex) or d != d.to_integral_value() or d < 0 or d > 10000:
            raise ValueError("factorial requires an integer from 0 to 10000.")
        return Decimal(math.factorial(int(d)))
    def integer(x, label="n"):
        v = _num(x)
        if isinstance(v, complex) or v != v.to_integral_value() or v < 0 or v > 10000:
            raise ValueError(label + " must be a non-negative integer up to 10000.")
        return int(v)
    def ncr(n, r):
        n, r = integer(n, "n"), integer(r, "r")
        if r > n: return Decimal(0)
        return Decimal(math.comb(n, r))
    def npr(n, r):
        n, r = integer(n, "n"), integer(r, "r")
        if r > n: return Decimal(0)
        return Decimal(math.perm(n, r))
    def fib(n):
        n = integer(n)
        if n > 5000: raise ValueError("Fibonacci index is too large.")
        a, b = 0, 1
        for _ in range(n): a, b = b, a+b
        return Decimal(a)
    def seq_arith(a, d, n):
        a, d, n = _num(a), _num(d), integer(n)
        if n > 200: raise ValueError("Sequence length must be 1–200.")
        return ", ".join(_fmt(a + d*i) for i in range(n))
    def seq_geom(a, r, n):
        a, r, n = _num(a), _num(r), integer(n)
        if n > 200: raise ValueError("Sequence length must be 1–200.")
        return ", ".join(_fmt(a * (r**i)) for i in range(n))
    def prime_n(n):
        n = integer(n)
        if n < 1 or n > 10000: raise ValueError("Prime index must be between 1 and 10000.")
        found, candidate = 0, 1
        while found < n:
            candidate += 1
            if all(candidate % d for d in range(2, int(math.sqrt(candidate))+1)): found += 1
        return Decimal(candidate)
    return {
        "sqrt": unary_math(math.sqrt, cmath.sqrt), "sin": unary_math(math.sin, cmath.sin),
        "cos": unary_math(math.cos, cmath.cos), "tan": unary_math(math.tan, cmath.tan),
        "asin": unary_math(math.asin, cmath.asin), "acos": unary_math(math.acos, cmath.acos),
        "atan": unary_math(math.atan, cmath.atan), "sinh": unary_math(math.sinh, cmath.sinh),
        "cosh": unary_math(math.cosh, cmath.cosh), "tanh": unary_math(math.tanh, cmath.tanh),
        "log": lambda x, base=Decimal(10): _num(cmath.log(complex(_num(x))) / cmath.log(complex(_num(base)))) if isinstance(_num(x), complex) or isinstance(_num(base), complex) else Decimal(str(math.log(float(_num(x)), float(_num(base))))),
        "ln": unary_math(math.log, cmath.log), "log10": lambda x: _num(cmath.log10(complex(_num(x)))) if isinstance(_num(x), complex) else Decimal(str(math.log10(float(_num(x))))),
        "exp": unary_math(math.exp, cmath.exp), "abs": lambda x: Decimal(str(abs(_num(x)))),
        "round": round_fn, "floor": lambda x: Decimal(math.floor(_num(x))),
        "ceil": lambda x: Decimal(math.ceil(_num(x))), "factorial": factorial,
        "degrees": unary_math(math.degrees), "radians": unary_math(math.radians),
        "pow": lambda x, y: _num(x) ** _num(y),
        "min": lambda *xs: min(_num(x) for x in xs), "max": lambda *xs: max(_num(x) for x in xs),
        "mean": lambda *xs: _num(statistics.mean([float(_num(x)) for x in xs])),
        "median": lambda *xs: _num(statistics.median([float(_num(x)) for x in xs])),
        "stdev": lambda *xs: _num(statistics.stdev([float(_num(x)) for x in xs])),
        "variance": lambda *xs: _num(statistics.variance([float(_num(x)) for x in xs])),
        "percent": lambda x, p: _num(x) * _num(p) / Decimal(100),
        "compound": lambda p, r, n: _num(p) * ((Decimal(1) + _num(r)) ** _num(n)),
        "simple_interest": lambda p, r, t: _num(p) * (Decimal(1) + _num(r) * _num(t)),
        "sind": unary_math(lambda x: math.sin(math.radians(x))),
        "cosd": unary_math(lambda x: math.cos(math.radians(x))),
        "tand": unary_math(lambda x: math.tan(math.radians(x))),
        "complex": lambda a, b=0: complex(float(_num(a)), float(_num(b))),
        "real": lambda z: Decimal(str(_num(z).real if isinstance(_num(z), complex) else _num(z))),
        "imag": lambda z: Decimal(str(_num(z).imag if isinstance(_num(z), complex) else 0)),
        "conj": lambda z: _num(z).conjugate() if isinstance(_num(z), complex) else _num(z),
        "phase": lambda z: Decimal(str(cmath.phase(complex(_num(z))))),
        "ncr": ncr, "npr": npr, "gcd": lambda a,b: Decimal(math.gcd(integer(a),integer(b))),
        "lcm": lambda a,b: Decimal(math.lcm(integer(a),integer(b))), "fibonacci": fib,
        "arith_term": lambda a,d,n: _num(a)+_num(d)*(integer(n)-1),
        "arith_sum": lambda a,d,n: ((integer(n)*(2*_num(a)+(integer(n)-1)*_num(d))/2) if isinstance(_num(a), complex) or isinstance(_num(d), complex) else Decimal(integer(n))*(Decimal(2)*_num(a)+Decimal(integer(n)-1)*_num(d))/Decimal(2)),
        "geom_term": lambda a,r,n: _num(a)*(_num(r)**(integer(n)-1)),
        "geom_sum": lambda a,r,n: (_num(a)*(_num(r)**integer(n)-1)/(_num(r)-1)) if _num(r)!=1 else _num(a)*integer(n),
        "arithmetic_sequence": seq_arith, "geometric_sequence": seq_geom, "prime": prime_n,
    }


def normalize_expression(expression: str) -> str:
    """Normalize Arabic-Indic numerals and common Arabic calculator labels."""
    source = str(expression or "").strip()
    digits = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
    source = source.translate(digits).replace("٫", ".").replace("٬", "")
    aliases = {
        "الجذر": "sqrt", "باي": "pi", "جذر": "sqrt",
        "جا": "sin", "جيب": "sin", "جتا": "cos", "جيب_تمام": "cos",
        "ظا": "tan", "لو": "log10", "لن": "ln", "القيمة_المطلقة": "abs",
    }
    for arabic, english in aliases.items():
        source = source.replace(arabic, english)
    source = source.replace("×", "*").replace("÷", "/").replace("−", "-").replace("٪", "%")
    # Percent postfix: 15% -> (15/100), including values in parentheses.
    source = re.sub(r"(\d+(?:\.\d+)?|\([^()]*\))\s*%", r"(\1/100)", source)
    return source


def evaluate_expression(expression: str, ans=None):
    source = normalize_expression(expression).replace("^", "**")
    if not source or len(source) > _MAX_EXPR:
        raise ValueError("Expression is empty or too long.")
    if any(token in source for token in ("__", "[", "]", "{", "}", ";", "=", "`")):
        raise ValueError("Unsupported syntax.")
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid mathematical expression.") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > _MAX_NODES:
        raise ValueError("Expression is too complex.")
    env = dict(_CONSTANTS)
    env["i"] = complex(0, 1)
    env["j"] = complex(0, 1)
    env["ans"] = _num(ans or 0)
    funcs = _functions()

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return _num(node.value)
        if isinstance(node, ast.Name):
            key = node.id.lower()
            if key in env:
                return env[key]
            raise ValueError("Unknown constant: " + node.id)
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left, right = _num(visit(node.left)), _num(visit(node.right))
            if isinstance(left, complex) or isinstance(right, complex):
                left, right = complex(left), complex(right)
            if isinstance(node.op, ast.Pow) and ((not isinstance(right, complex) and abs(right) > 10000) or (isinstance(right, complex) and abs(right) > 10000)):
                raise ValueError("Exponent is too large.")
            try:
                return _num(_BINOPS[type(node.op)](left, right))
            except (DivisionByZero, ZeroDivisionError, InvalidOperation, OverflowError) as exc:
                raise ValueError("Mathematical domain or division error.") from exc
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _num(_UNARY[type(node.op)](_num(visit(node.operand))))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            fn = funcs.get(node.func.id.lower())
            if not fn:
                raise ValueError("Function is not allowed: " + node.func.id)
            args = [visit(a) for a in node.args]
            try:
                result = fn(*args)
                return result if isinstance(result, str) else _num(result)
            except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
                raise ValueError(str(exc) or "Invalid function arguments.") from exc
        raise ValueError("Unsupported mathematical operation.")

    value = visit(tree)
    return source, value


def _db(db_path):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = sqlite3.connect(db_path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS calculator_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        expression TEXT NOT NULL,
        result TEXT NOT NULL,
        created_at REAL NOT NULL
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_calc_user_id ON calculator_history(username,id DESC)")
    return con


def register_calculator(app, db_path):
    from flask import Blueprint, jsonify, request, session, send_file
    calculator_bp = Blueprint("fbrah_calculator", __name__)

    def current_user():
        return (session.get("user") or session.get("username") or "").strip()

    @calculator_bp.post("/api/calculator/preview")
    def calculator_preview():
        user = current_user()
        if not user:
            return jsonify(ok=False, error="Authentication required."), 401
        payload = request.get_json(silent=True) or {}
        expression = str(payload.get("expression") or "").strip()
        if len(expression) > _MAX_EXPR:
            return jsonify(ok=False, error="Expression is too long."), 413
        con = _db(db_path)
        try:
            row = con.execute(
                "SELECT result FROM calculator_history WHERE username=? ORDER BY id DESC LIMIT 1",
                (user,),
            ).fetchone()
            ans = row["result"] if row else "0"
            source, value = evaluate_expression(expression, ans)
            result = _fmt(value)
            return jsonify(ok=True, expression=source, result=result, preview=True)
        except Exception as exc:
            return jsonify(ok=False, error=str(exc)), 400
        finally:
            con.close()

    @calculator_bp.post("/api/calculator/evaluate")
    def calculator_evaluate():
        user = current_user()
        if not user:
            return jsonify(ok=False, error="Authentication required."), 401
        payload = request.get_json(silent=True) or {}
        expression = str(payload.get("expression") or "").strip()
        if len(expression) > _MAX_EXPR:
            return jsonify(ok=False, error="Expression is too long."), 413
        con = None
        try:
            con = _db(db_path)
            row = con.execute(
                "SELECT result FROM calculator_history WHERE username=? ORDER BY id DESC LIMIT 1",
                (user,),
            ).fetchone()
            ans = row["result"] if row else "0"
            source, value = evaluate_expression(expression, ans)
            result = _fmt(value)
            con.execute(
                "INSERT INTO calculator_history(username,expression,result,created_at) VALUES(?,?,?,?)",
                (user, source, result, time.time()),
            )
            con.commit()
            record_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            con.close()
            return jsonify(ok=True, id=record_id, expression=source, result=result)
        except Exception as exc:
            try:
                con.close()
            except Exception:
                pass
            return jsonify(ok=False, error=str(exc)), 400

    @calculator_bp.get("/api/calculator/history")
    def calculator_history():
        user = current_user()
        if not user:
            return jsonify(ok=False, error="Authentication required."), 401
        con = _db(db_path)
        rows = con.execute(
            "SELECT id,expression,result,created_at FROM calculator_history WHERE username=? ORDER BY id DESC LIMIT 200",
            (user,),
        ).fetchall()
        con.close()
        return jsonify(ok=True, items=[dict(r) for r in rows])

    @calculator_bp.delete("/api/calculator/history")
    def calculator_clear_history():
        user = current_user()
        if not user:
            return jsonify(ok=False, error="Authentication required."), 401
        con = _db(db_path)
        con.execute("DELETE FROM calculator_history WHERE username=?", (user,))
        con.commit()
        con.close()
        return jsonify(ok=True, cleared=True)

    @calculator_bp.post("/api/calculator/report")
    def calculator_report():
        user = current_user()
        if not user:
            return jsonify(ok=False, error="Authentication required."), 401
        payload = request.get_json(silent=True) or {}
        limit = max(1, min(int(payload.get("limit") or 200), 200))
        con = _db(db_path)
        rows = con.execute(
            "SELECT expression,result,created_at FROM (SELECT expression,result,created_at,id FROM calculator_history WHERE username=? ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
            (user, limit),
        ).fetchall()
        con.close()
        if not rows:
            return jsonify(ok=False, error="No calculations are available for a report."), 404
        from datetime import datetime
        lines = [
            "FBRAH — CALCULATION REPORT",
            "User: " + user,
            "Generated: " + datetime.now().astimezone().isoformat(timespec="seconds"),
            "Operations: " + str(len(rows)),
            "-" * 72,
        ]
        for idx, row in enumerate(rows, 1):
            stamp = datetime.fromtimestamp(row["created_at"]).astimezone().isoformat(timespec="seconds")
            lines.extend([f"{idx}. {row['expression']}", f"   Result: {row['result']}", f"   Time: {stamp}", ""])
        data = ("\n".join(lines)).encode("utf-8-sig")
        return send_file(BytesIO(data), mimetype="text/plain; charset=utf-8",
                         as_attachment=True, download_name="FBRAH_Calculation_Report.txt")
    app.register_blueprint(calculator_bp)
