// Редактор/просмотр свитка героя.
//
// Живёт отдельным компонентом, потому что нужен в двух местах: на странице «Свиток героя»
// и в модальном окне внутри игровой комнаты (чтобы смотреть свиток, не выходя из игры —
// выход рвёт WebSocket и перезагружает всю комнату).
import { useState } from "react";
import "../pages/heroes.css";
import { API_URL, api, errorMessage } from "../api/client";
import type { HeroSheet } from "../api/types";

const INV = 4;
const ABIL = 4;
const WEAK = 2;

type StatKey = "strength" | "dexterity" | "defense" | "hp" | "endurance" | "wisdom" | "intelligence" | "charisma";
const STAT_FIELDS: { key: StatKey; label: string }[] = [
  { key: "strength", label: "Сила" },
  { key: "dexterity", label: "Ловкость" },
  { key: "defense", label: "Защита" },
  { key: "hp", label: "Жизни" },
  { key: "endurance", label: "Выносливость" },
  { key: "wisdom", label: "Мудрость" },
  { key: "intelligence", label: "Интеллект" },
  { key: "charisma", label: "Харизма" },
];

const CROP_OPTIONS = [
  { value: "center", label: "Центр" },
  { value: "top", label: "Верх" },
  { value: "bottom", label: "Низ" },
  { value: "left", label: "Лево" },
  { value: "right", label: "Право" },
];

interface HeroForm {
  name: string;
  race: string;
  age: string;
  weight: string;
  height: string;
  crop_position: string;
  strength: number;
  dexterity: number;
  defense: number;
  hp: number;
  endurance: number;
  wisdom: number;
  intelligence: number;
  charisma: number;
  inventory: string[];
  abilities: string[];
  weaknesses: string[];
  innate_ability: string;
  backstory: string;
}

function pad(a: string[], n: number): string[] {
  const r = [...(a || [])];
  while (r.length < n) r.push("");
  return r.slice(0, n);
}

function blankForm(): HeroForm {
  return {
    name: "", race: "", age: "", weight: "", height: "", crop_position: "center",
    strength: 10, dexterity: 10, defense: 10, hp: 20, endurance: 10, wisdom: 10,
    intelligence: 10, charisma: 10,
    inventory: pad([], INV), abilities: pad([], ABIL), weaknesses: pad([], WEAK),
    innate_ability: "", backstory: "",
  };
}

function formFromHero(h: HeroSheet): HeroForm {
  return {
    name: h.name, race: h.race, age: h.age, weight: h.weight, height: h.height,
    crop_position: h.crop_position,
    strength: h.strength, dexterity: h.dexterity, defense: h.defense, hp: h.hp,
    endurance: h.endurance, wisdom: h.wisdom, intelligence: h.intelligence, charisma: h.charisma,
    inventory: pad(h.inventory, INV), abilities: pad(h.abilities, ABIL), weaknesses: pad(h.weaknesses, WEAK),
    innate_ability: h.innate_ability, backstory: h.backstory,
  };
}

// ---------- Редактор / просмотр одного свитка ----------
export default function HeroSheetEditor({
  hero,
  canEdit,
  onDone,
  onCancel,
}: {
  hero: HeroSheet | null; // null = создание нового
  canEdit: boolean;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [f, setF] = useState<HeroForm>(hero ? formFromHero(hero) : blankForm());
  const [portraitFile, setPortraitFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(hero?.portrait_url ? API_URL + hero.portrait_url : null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const set = <K extends keyof HeroForm>(k: K, v: HeroForm[K]) => setF((p) => ({ ...p, [k]: v }));
  const setList = (k: "inventory" | "abilities" | "weaknesses", i: number, v: string) =>
    setF((p) => {
      const a = [...p[k]];
      a[i] = v;
      return { ...p, [k]: a };
    });

  const onPickPortrait = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPortraitFile(file);
    setPreview(URL.createObjectURL(file));
  };

  const save = async () => {
    if (!f.name.trim()) {
      setError("Впиши имя героя");
      return;
    }
    setError("");
    setSaving(true);
    try {
      const payload = {
        ...f,
        inventory: f.inventory.map((s) => s.trim()).filter(Boolean),
        abilities: f.abilities.map((s) => s.trim()).filter(Boolean),
        weaknesses: f.weaknesses.map((s) => s.trim()).filter(Boolean),
      };
      let id = hero?.id;
      if (hero) {
        await api.put(`/heroes/${hero.id}`, payload);
      } else {
        const { data } = await api.post<HeroSheet>("/heroes", payload);
        id = data.id;
      }
      if (portraitFile && id) {
        const fd = new FormData();
        fd.append("file", portraitFile);
        await api.post(`/heroes/${id}/portrait`, fd);
      }
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const dis = !canEdit;

  return (
    <div className="hero-scroll">
      <div className="hs-title">
        <h1>Свиток Героя</h1>
        <p>✧ {canEdit ? "Впиши свою судьбу" : "Летопись героя"} ✧</p>
      </div>
      {error && <div className="hs-error">{error}</div>}

      <div className="hs-form">
        {/* Портрет */}
        <div className="hs-section">
          <h3>✧ Портрет ✧</h3>
          <div className="hs-portrait-row">
            <div className={`hs-portrait-preview hs-crop-${f.crop_position}`}>
              {preview ? <img src={preview} alt="Портрет" /> : <span>Портрет не выбран</span>}
            </div>
            <div className="hs-portrait-controls">
              {canEdit && (
                <>
                  <label className="hs-btn small" style={{ cursor: "pointer" }}>
                    Выбрать файл
                    <input type="file" accept="image/*" style={{ display: "none" }} onChange={onPickPortrait} />
                  </label>
                  {!hero && <p className="hs-muted" style={{ marginTop: 8 }}>Портрет сохранится вместе со свитком.</p>}
                </>
              )}
              <div className="hs-field" style={{ marginTop: 12 }}>
                <label>Область отображения</label>
                <select value={f.crop_position} disabled={dis} onChange={(e) => set("crop_position", e.target.value)}>
                  {CROP_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Основное */}
        <div className="hs-section">
          <h3>✧ Основное ✧</h3>
          <div className="hs-grid-2">
            <div className="hs-field">
              <label>Имя героя</label>
              <input value={f.name} disabled={dis} placeholder="например: Арагорн" onChange={(e) => set("name", e.target.value)} />
            </div>
            <div className="hs-field">
              <label>Раса</label>
              <input value={f.race} disabled={dis} placeholder="Человек, Эльф…" onChange={(e) => set("race", e.target.value)} />
            </div>
            <div className="hs-field">
              <label>Возраст</label>
              <input value={f.age} disabled={dis} placeholder="лет" onChange={(e) => set("age", e.target.value)} />
            </div>
            <div className="hs-field">
              <label>Вес</label>
              <input value={f.weight} disabled={dis} placeholder="кг" onChange={(e) => set("weight", e.target.value)} />
            </div>
            <div className="hs-field">
              <label>Рост</label>
              <input value={f.height} disabled={dis} placeholder="см" onChange={(e) => set("height", e.target.value)} />
            </div>
          </div>
        </div>

        {/* Характеристики */}
        <div className="hs-section full">
          <h3>✧ Характеристики ✧</h3>
          <div className="hs-grid-4">
            {STAT_FIELDS.map((s) => (
              <div className="hs-field" key={s.key}>
                <label>{s.label}</label>
                <input
                  type="number"
                  min={1}
                  max={s.key === "hp" ? 100 : 30}
                  disabled={dis}
                  value={f[s.key]}
                  onChange={(e) => set(s.key, Number(e.target.value))}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Инвентарь */}
        <div className="hs-section full">
          <h3>✧ Инвентарь ✧</h3>
          <div className="hs-grid-4">
            {f.inventory.map((v, i) => (
              <div className="hs-field" key={i}>
                <label>Предмет {i + 1}</label>
                <input value={v} disabled={dis} placeholder="Меч, зелье…" onChange={(e) => setList("inventory", i, e.target.value)} />
              </div>
            ))}
          </div>
        </div>

        {/* Способности */}
        <div className="hs-section full">
          <h3>✧ Способности ✧</h3>
          <div className="hs-grid-4">
            {f.abilities.map((v, i) => (
              <div className="hs-field" key={i}>
                <label>Способность {i + 1}</label>
                <input value={v} disabled={dis} placeholder="Огненный шар…" onChange={(e) => setList("abilities", i, e.target.value)} />
              </div>
            ))}
          </div>
        </div>

        {/* Слабости + врождённая */}
        <div className="hs-section">
          <h3>✧ Слабости ✧</h3>
          {f.weaknesses.map((v, i) => (
            <div className="hs-field" key={i} style={{ marginBottom: 10 }}>
              <label>Слабость {i + 1}</label>
              <input value={v} disabled={dis} placeholder="Страх высоты…" onChange={(e) => setList("weaknesses", i, e.target.value)} />
            </div>
          ))}
        </div>
        <div className="hs-section">
          <h3>✧ Врождённая способность ✧</h3>
          <div className="hs-field">
            <label>Особая сила</label>
            <input value={f.innate_ability} disabled={dis} placeholder="Драконья кровь…" onChange={(e) => set("innate_ability", e.target.value)} />
          </div>
        </div>

        {/* История */}
        <div className="hs-section full">
          <h3>✧ История героя ✧</h3>
          <textarea
            value={f.backstory}
            disabled={dis}
            placeholder="Откуда он родом, какие испытания прошёл, как стал искателем приключений…"
            onChange={(e) => set("backstory", e.target.value)}
          />
        </div>

        {canEdit && (
          <p className="hs-muted hs-sync-note">
            ✧ Имя, портрет и «Жизни» подхватятся фишками этого героя на картах. Текущее HP в бою
            остаётся у фишки.
          </p>
        )}

        {/* Кнопки */}
        <div className="hs-actions">
          <button className="hs-btn ghost" onClick={onCancel}>
            {canEdit ? "Отмена" : "Назад"}
          </button>
          {canEdit && (
            <button className="hs-btn" onClick={save} disabled={saving}>
              {saving ? "Записываем…" : hero ? "Сохранить свиток" : "Создать свиток"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
