"""Разбор и бросок формул костей D&D.

Поддерживается:
  - одиночная кость: d20, d6, d100
  - количество: 2d6, 4d8
  - модификатор: 2d6+3, d20-1, 3d4 + 2
  - несколько групп: 2d6+1d4+3
  - преимущество/помеха (advantage/disadvantage) — только для одиночного d20:
    кидаем дважды и берём больший/меньший результат.
"""
import random
import re
from dataclasses import dataclass, field

# Разрешённые «грани» костей.
ALLOWED_DICE = {4, 6, 8, 10, 12, 20, 100}

# Одна группа вида (количество)d(грани), например "2d6".
_DICE_RE = re.compile(r"(\d*)d(\d+)", re.IGNORECASE)
# Плоский модификатор — просто число, например "+3".
_MOD_RE = re.compile(r"^[+-]?\d+$")


@dataclass
class RollResult:
    formula: str
    rolls: list[int] = field(default_factory=list)  # все выпавшие значения
    modifier: int = 0
    total: int = 0
    roll_type: str = "normal"


def _roll_die(sides: int) -> int:
    return random.randint(1, sides)


def parse_and_roll(formula: str, roll_type: str = "normal") -> RollResult:
    """Разбирает формулу, кидает кости и возвращает результат.

    Кидает ValueError, если формула некорректна.
    """
    raw = formula.replace(" ", "").lower()
    if not raw:
        raise ValueError("Пустая формула")

    # Разбиваем на слагаемые по знакам + и -, сохраняя знак.
    tokens = re.findall(r"[+-]?[^+-]+", raw)
    if not tokens:
        raise ValueError("Не удалось разобрать формулу")

    rolls: list[int] = []
    modifier = 0
    dice_groups: list[tuple[int, int]] = []  # (count, sides)

    for token in tokens:
        sign = -1 if token.startswith("-") else 1
        body = token.lstrip("+-")

        dice_match = _DICE_RE.fullmatch(body)
        if dice_match:
            count = int(dice_match.group(1)) if dice_match.group(1) else 1
            sides = int(dice_match.group(2))
            if sides not in ALLOWED_DICE:
                raise ValueError(f"Недопустимая кость d{sides}. Разрешены: {sorted(ALLOWED_DICE)}")
            if not (1 <= count <= 100):
                raise ValueError("Количество костей должно быть от 1 до 100")
            dice_groups.append((count, sides))
            continue

        if _MOD_RE.fullmatch(token):
            modifier += sign * int(body)
            continue

        raise ValueError(f"Непонятная часть формулы: '{token}'")

    if not dice_groups and modifier == 0:
        raise ValueError("В формуле нет костей")

    # Преимущество/помеха работают только для одиночного d20.
    is_single_d20 = len(dice_groups) == 1 and dice_groups[0] == (1, 20)
    if roll_type in ("advantage", "disadvantage") and is_single_d20:
        a, b = _roll_die(20), _roll_die(20)
        chosen = max(a, b) if roll_type == "advantage" else min(a, b)
        rolls = [a, b]
        total = chosen + modifier
        return RollResult(formula=formula, rolls=rolls, modifier=modifier, total=total, roll_type=roll_type)

    # Обычный бросок.
    for count, sides in dice_groups:
        for _ in range(count):
            rolls.append(_roll_die(sides))

    total = sum(rolls) + modifier
    return RollResult(formula=formula, rolls=rolls, modifier=modifier, total=total, roll_type="normal")
