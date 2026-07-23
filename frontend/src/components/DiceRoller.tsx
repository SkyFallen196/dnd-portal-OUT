import { useState } from "react";

const DICE = ["d4", "d6", "d8", "d10", "d12", "d20", "d100"];

interface Props {
  onRoll: (formula: string, rollType: string) => void;
}

// Панель бросков: быстрые кнопки костей + поле для формул + преимущество/помеха.
export default function DiceRoller({ onRoll }: Props) {
  const [formula, setFormula] = useState("");
  const [rollType, setRollType] = useState("normal");

  const rollFormula = () => {
    const f = formula.trim();
    if (f) onRoll(f, rollType);
  };

  return (
    <div>
      <h3>🎲 Кости</h3>

      <div className="dice-buttons" style={{ marginBottom: 10 }}>
        {DICE.map((d) => (
          <button key={d} className="secondary" onClick={() => onRoll(d, rollType)}>
            {d}
          </button>
        ))}
      </div>

      <div className="field">
        <label>Своя формула (например 2d6+3)</label>
        <div className="row">
          <input
            value={formula}
            onChange={(e) => setFormula(e.target.value)}
            placeholder="2d6+3"
            onKeyDown={(e) => e.key === "Enter" && rollFormula()}
          />
          <button onClick={rollFormula} disabled={!formula.trim()}>
            Бросить
          </button>
        </div>
      </div>

      <div className="field">
        <label>Режим для d20</label>
        <select value={rollType} onChange={(e) => setRollType(e.target.value)}>
          <option value="normal">Обычный</option>
          <option value="advantage">Преимущество (2 кубика, больший)</option>
          <option value="disadvantage">Помеха (2 кубика, меньший)</option>
        </select>
      </div>
    </div>
  );
}
