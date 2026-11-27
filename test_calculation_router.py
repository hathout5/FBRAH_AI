# -*- coding: utf-8 -*-
import tempfile
from pathlib import Path
from fbrah_calculation_router import extract_expression, calculate_question


def test_natural_arabic_percent_routes_to_calculator():
    assert extract_expression("احسب ١٥٪ من ٢٤٠") == "٢٤٠*١٥%"
    assert extract_expression("احسب ١٥٫٥٪ من ٢٤٠") == "٢٤٠*١٥٫٥%"
    with tempfile.TemporaryDirectory() as td:
        result=calculate_question("احسب ١٥٪ من ٢٤٠", "alice", str(Path(td)/"calc.db"))
        assert result["result"] == "36"


def test_pure_arithmetic_and_english_calculation_route():
    assert extract_expression("١٢ + ٣") == "١٢ + ٣"
    assert extract_expression("calculate 5 * 6") == "5 * 6"
    assert extract_expression("القانون رقم 15/2000") is None
    assert extract_expression("اشرح لي معنى النسبة المئوية") is None


def test_ans_uses_each_users_own_history():
    with tempfile.TemporaryDirectory() as td:
        db=str(Path(td)/"calc.db")
        first=calculate_question("7*8", "alice", db)
        second=calculate_question("ans+4", "alice", db)
        other=calculate_question("ans+4", "bob", db)
        assert first["result"]=="56"
        assert second["result"]=="60"
        assert other["result"]=="4"
