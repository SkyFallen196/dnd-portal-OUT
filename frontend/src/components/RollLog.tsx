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
          // Подсветка крита/провала для одиночного d20.
          const isD20 = /^d20$/i.test(r.formula.replace(/\s/g, ""));
          let cls = "roll-entry";
          if (isD20 && dice.includes(20)) cls += " crit";
          if (isD20 && dice.includes(1) && r.roll_type === "normal") cls += " fail";

          return (
            <div key={r.id} className={cls}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span>
                  <b>{r.username ?? `#${r.user_id}`}</b> бросает <b>{r.formula}</b>
                  {r.roll_type === "advantage" && " (преим.)"}
                  {r.roll_type === "disadvantage" && " (помеха)"}
                </span>
                <span className="total">{r.total}</span>
              </div>
              <div className="muted">
                кубики: [{dice.join(", ")}]
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

function safeParse(s: string): number[] {
  try {
    return JSON.parse(s);
  } catch {
    return [];
  }
}
