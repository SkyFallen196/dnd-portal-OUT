import type { User } from "../api/types";

// Показывает роли пользователя. Их может быть две сразу: админ и мастер.
export default function RoleTags({ user }: { user: User | null }) {
  if (!user) return null;
  const tags: { label: string; cls: string; title?: string }[] = [];
  if (user.role === "admin") tags.push({ label: "admin", cls: "admin", title: "администратор портала" });
  if (user.is_dm) tags.push({ label: "dm", cls: "dm", title: "мастер подземелий (Dungeon Master) — ведёт игру" });
  if (tags.length === 0) tags.push({ label: "player", cls: "player", title: "игрок" });

  return (
    <>
      {tags.map((t) => (
        <span key={t.label} className={`tag ${t.cls}`} style={{ marginLeft: 4 }} title={t.title}>
          {t.label}
        </span>
      ))}
    </>
  );
}
