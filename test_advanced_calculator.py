# -*- coding: utf-8 -*-
import unittest
import sys
import types
from decimal import Decimal
from fbrah_advanced_calculator import evaluate_expression, register_calculator

class AdvancedCalculatorTests(unittest.TestCase):
    def test_arithmetic_and_precedence(self):
        _, result = evaluate_expression("2 + 3 * 4")
        self.assertEqual(result, Decimal("14"))

    def test_scientific_functions(self):
        _, result = evaluate_expression("sqrt(81) + log10(100)")
        self.assertEqual(result, Decimal("11.0"))

    def test_previous_answer(self):
        _, first = evaluate_expression("12 * 3")
        _, second = evaluate_expression("ans + 4", first)
        self.assertEqual(second, Decimal("40"))

    def test_arabic_digits_and_percent(self):
        _, result = evaluate_expression("٢٤٠ * ١٥٪")
        self.assertEqual(result, Decimal("36.00"))

    def test_arabic_sqrt_alias(self):
        _, result = evaluate_expression("جذر(٨١)")
        self.assertEqual(result, Decimal("9.0"))

    def test_power_alias(self):
        _, result = evaluate_expression("2^8")
        self.assertEqual(result, Decimal("256"))

    def test_financial_and_statistical_functions(self):
        _, interest = evaluate_expression("compound(1000, 0.05, 2)")
        self.assertEqual(interest, Decimal("1102.5"))
        _, avg = evaluate_expression("mean(10, 20, 30)")
        self.assertEqual(avg, Decimal("20.0"))
        _, percent = evaluate_expression("percent(240, 15)")
        self.assertEqual(percent, Decimal("36"))

    def test_degree_trigonometry(self):
        _, result = evaluate_expression("sind(30)")
        self.assertAlmostEqual(float(result), 0.5, places=10)

    def test_arithmetic_and_geometric_sequences(self):
        _, total = evaluate_expression("arith_sum(2, 3, 5)")
        self.assertEqual(total, Decimal("40"))
        _, terms = evaluate_expression("arithmetic_sequence(2, 3, 5)")
        self.assertEqual(terms, "2, 5, 8, 11, 14")
        _, geometric = evaluate_expression("geometric_sequence(2, 3, 4)")
        self.assertEqual(geometric, "2, 6, 18, 54")
        _, fib = evaluate_expression("fibonacci(10)")
        self.assertEqual(fib, Decimal("55"))

    def test_complex_numbers(self):
        _, result = evaluate_expression("(3+4*i)*(2-i)")
        self.assertEqual(result, complex(10, 5))
        _, magnitude = evaluate_expression("abs(3+4*i)")
        self.assertEqual(magnitude, Decimal("5.0"))
        _, root = evaluate_expression("sqrt(-1)")
        self.assertEqual(root, complex(0, 1))
        _, chained = evaluate_expression("ans*(1+i)", root)
        self.assertEqual(chained, complex(-1, 1))
        _, cseq = evaluate_expression("arithmetic_sequence(complex(1,1), i, 3)")
        self.assertEqual(cseq, "1+i, 1+2i, 1+3i")

    def test_combinatorics_and_statistics(self):
        _, c = evaluate_expression("ncr(5,2)")
        _, p = evaluate_expression("npr(5,2)")
        self.assertEqual(c, Decimal("10"))
        self.assertEqual(p, Decimal("20"))

    def test_blueprint_registers_all_routes_after_definition(self):
        class FakeBlueprint:
            def __init__(self, name, import_name):
                self.name=name
                self.routes=[]
            def post(self, path):
                return self._route(path, "POST")
            def get(self, path):
                return self._route(path, "GET")
            def delete(self, path):
                return self._route(path, "DELETE")
            def _route(self, path, method):
                def deco(fn):
                    self.routes.append((method,path,fn.__name__))
                    return fn
                return deco
        fake=types.ModuleType("flask")
        fake.Blueprint=FakeBlueprint
        fake.jsonify=lambda *a,**k: None
        fake.request=object()
        fake.session={}
        fake.send_file=lambda *a,**k: None
        class FakeApp:
            def register_blueprint(self,bp):
                self.registered=list(bp.routes)
        old=sys.modules.get("flask")
        sys.modules["flask"]=fake
        try:
            app=FakeApp()
            register_calculator(app,":memory:")
            self.assertEqual(len(app.registered),5)
            self.assertEqual({x[1] for x in app.registered},{
                "/api/calculator/evaluate","/api/calculator/history","/api/calculator/report","/api/calculator/preview"
            })
            self.assertIn(("DELETE", "/api/calculator/history", "calculator_clear_history"), app.registered)
            self.assertIn(("POST", "/api/calculator/preview", "calculator_preview"), app.registered)
        finally:
            if old is None:
                sys.modules.pop("flask",None)
            else:
                sys.modules["flask"]=old

    def test_blocks_unsafe_syntax(self):
        for expr in ("__import__('os').system('whoami')", "open('x')", "1;2", "x[0]"):
            with self.assertRaises(ValueError):
                evaluate_expression(expr)

if __name__ == "__main__":
    unittest.main()
