// Типы данных, приходящих с бэкенда.

// Платформенная роль. Игровая роль мастера — отдельный флаг is_dm,
// поэтому можно быть одновременно и админом, и мастером.
export type Role = "player" | "admin";

export interface User {
  id: number;
  username: string;
  email: string;
  role: Role;
  is_dm: boolean;
  subscription_expires_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AccessCode {
  id: number;
  code: string;
  duration_days: number;
  is_activated: boolean;
  assigned_user_id: number | null;
  activated_at: string | null;
  created_at: string;
}

export interface Member {
  user_id: number;
  username: string;
  role: string;
}

export interface MapImage {
  id: number;
  filename: string;
  file_path: string;
  width: number;
  height: number;
}

export interface Room {
  id: number;
  name: string;
  dm_id: number;
  invite_code: string;
  active_map_id: number | null;
  // Сторона клетки сетки в пикселях карты. 0 — сетки нет. Одна клетка = 5 футов.
  grid_size: number;
  created_at: string;
}

export interface RoomDetail extends Room {
  members: Member[];
  active_map: MapImage | null;
}

export interface StatusEffect {
  name: string;
  type: "buff" | "debuff";
}

// Фишка на карте. Лист персонажа со всеми характеристиками — это HeroSheet («свиток»).
export interface Token {
  id: number;
  room_id: number;
  owner_user_id: number | null;
  hero_sheet_id: number | null;
  name: string;
  color: string;
  avatar_url: string | null;
  x: number;
  y: number;
  hp: number;
  max_hp: number;
  is_npc: boolean;
  size: number;
  effects: StatusEffect[];
  initiative: number | null; // null — фишка не в бою
  hidden: boolean; // скрыта от игроков; им такие фишки сервер вообще не отдаёт
  z: number; // порядок отрисовки: больше — лежит выше
}

// Состояние боя в комнате. round === 0 — боя нет.
export interface Combatant {
  token_id: number;
  name: string;
  color: string;
  initiative: number;
  is_npc: boolean;
  hp: number;
  max_hp: number;
  owner_user_id: number | null;
}

export interface CombatState {
  round: number;
  current_token_id: number | null;
  order: Combatant[];
}

export interface HeroSheet {
  id: number;
  owner_user_id: number;
  name: string;
  race: string;
  age: string;
  weight: string;
  height: string;
  portrait_url: string | null;
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
  created_at: string;
}

export interface HeroSummary {
  id: number;
  owner_user_id: number;
  owner_username: string;
  name: string;
  race: string;
  portrait_url: string | null;
}

export interface DiceRoll {
  id: number;
  room_id: number;
  user_id: number;
  username: string;
  formula: string;
  rolls_json: string;
  modifier: number;
  total: number;
  roll_type: string;
  // Скрытый бросок мастера: игрокам сервер такие записи не отдаёт вовсе.
  private: boolean;
  created_at: string;
}

// Заметка или раздаточный материал комнаты. Пока is_public выключен,
// материал видит только мастер (сервер его игрокам не присылает).
export interface Handout {
  id: number;
  room_id: number;
  title: string;
  body: string;
  image_url: string | null;
  is_public: boolean;
  created_at: string;
}
