import { useEffect, useRef } from "react";
import type { DiceRoll } from "../api/types";

interface Props {
  rolls: DiceRoll[];
}

// Журнал бросков. Новые записи снизу; автопрокрутка вниз.
export default function RollLog({ rolls }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [rolls.length]);

  return (
    <div>
      <h3>📜 Журнал бросков</h3>
      <div className="roll-log">
        {rolls.length === 0 && <p className="muted">Бросков пока нет.</p>}
        {rolls.map((r) => {
          const dice: number[] = safeParse(r.rolls_json);
          // При преимуществе и помехе сервер кидает d20 дважды и сохраняет ОБА значения,
          // хотя в итог идёт только одно. Считаем, какое именно: иначе по журналу
          // не понять, какая кость сыграла, а крит/провал подсвечивался бы по отброшенной.
          const twoDice = dice.length === 2 && (r.roll_type === "advantage" || r.roll_type === "disadvantage");
          const chosenIdx = twoDice ? chosenIndex(dice, r.roll_type) : -1;
          const counted = twoDice ? [dice[chosenIdx]] : dice;

          // Подсветка крита/провала для одиночного d20 — по кости, которая пошла в зачёт.
          const isD20 = /^d20$/i.test(r.formula.replace(/\s/g, ""));
          let cls = "roll-entry";
          if (isD20 && counted.includes(20)) cls += " crit";
          if (isD20 && counted.includes(1)) cls += " fail";
          if (r.private) cls += " private";

          return (
            <div key={r.id} className={cls}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span>
                  <b>{r.username ?? `#${r.user_id}`}</b> бросает <b>{r.formula}</b>
                  {r.roll_type === "advantage" && " (преим.)"}
                  {r.roll_type === "disadvantage" && " (помеха)"}
                  {r.private && (
                    <span className="tag private-tag" title="Виден только вам — игроки этого броска не получают">
                      🔒 скрытый
                    </span>
                  )}
                </span>
                <span className="total">{r.total}</span>
              </div>
              <div className="muted">
                кубики: [
                {dice.map((d, i) => (
                  <span key={i}>
                    {i > 0 && ", "}
                    {/* Отброшенную кость зачёркиваем: в итог она не пошла. */}
                    <span
                      className={twoDice && i !== chosenIdx ? "die-dropped" : undefined}
                      title={twoDice && i !== chosenIdx ? "Отброшена — в итог не пошла" : undefined}
                    >
                      {d}
                    </span>
                  </span>
                ))}
                ]
                {r.modifier ? (r.modifier > 0 ? ` +${r.modifier}` : ` ${r.modifier}`) : ""}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// Индекс кости, которая пошла в зачёт: при преимуществе большая, при помехе меньшая.
function chosenIndex(dice: number[], rollType: string): number {
  if (rollType === "advantage") return dice[0] >= dice[1] ? 0 : 1;
  return dice[0] <= dice[1] ? 0 : 1;
}

function safeParse(s: string): number[] {
  try {
    return JSON.parse(s);
  } catch {
    return [];
  }
}
