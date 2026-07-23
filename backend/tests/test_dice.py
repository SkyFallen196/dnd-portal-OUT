"""Тесты парсера костей. Запуск: pytest  (из папки backend)."""
import sys
from pathlib import Path

import pytest

# Чтобы импортировать пакет app при запуске из папки backend.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.dice_engine import parse_and_roll  # noqa: E402


def test_single_d20_range():
    for _ in range(100):
        r = parse_and_roll("d20")
        assert 1 <= r.total <= 20
        assert len(r.rolls) == 1


def test_2d6_plus_3():
    for _ in range(100):
        r = parse_and_roll("2d6+3")
        assert len(r.rolls) == 2
        assert r.modifier == 3
        assert 5 <= r.total <= 15  # (1+1+3) .. (6+6+3)


def test_negative_modifier():
    r = parse_and_roll("4d8-1")
    assert r.modifier == -1
    assert len(r.rolls) == 4


def test_multiple_groups():
    r = parse_and_roll("2d6+1d4+2")
    assert len(r.rolls) == 3  # 2 шестигранника + 1 четырёхгранник
    assert r.modifier == 2


def test_advantage_takes_two_dice():
    r = parse_and_roll("d20", "advantage")
    assert len(r.rolls) == 2
    assert r.total == max(r.rolls)


def test_disadvantage_takes_lower():
    r = parse_and_roll("d20", "disadvantage")
    assert len(r.rolls) == 2
    assert r.total == min(r.rolls)


def test_invalid_die_rejected():
    with pytest.raises(ValueError):
        parse_and_roll("d7")


def test_garbage_rejected():
    with pytest.raises(ValueError):
        parse_and_roll("hello")


def test_empty_rejected():
    with pytest.raises(ValueError):
        parse_and_roll("")
