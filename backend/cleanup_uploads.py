"""Уборка файлов-сирот в папке uploads.

Сирота — файл, который лежит на диске, но на который не ссылается ни одна запись в базе
(ни карта, ни картинка фишки, ни портрет свитка). Такие файлы копились, пока приложение
не умело удалять их само.

Запуск (из папки backend):
    python cleanup_uploads.py          # только показать, что будет удалено
    python cleanup_uploads.py --delete # удалить

В Docker:
    docker compose exec backend python cleanup_uploads.py --delete
"""
import os
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import HeroSheet, MapImage, Token
from app.storage import UPLOAD_DIR


def used_filenames(db) -> set[str]:
    """Имена файлов, на которые ссылается база."""
    urls: list[str | None] = []
    urls += list(db.scalars(select(MapImage.file_path)))
    urls += list(db.scalars(select(Token.avatar_url)))
    urls += list(db.scalars(select(HeroSheet.portrait_url)))
    return {os.path.basename(u) for u in urls if u}


def main() -> None:
    delete = "--delete" in sys.argv

    if not os.path.isdir(UPLOAD_DIR):
        print(f"Папки {UPLOAD_DIR} нет — нечего убирать.")
        return

    db = SessionLocal()
    try:
        used = used_filenames(db)
    finally:
        db.close()

    on_disk = [f for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))]
    orphans = sorted(set(on_disk) - used)

    print(f"Файлов на диске: {len(on_disk)}")
    print(f"Используется базой: {len(used & set(on_disk))}")
    print(f"Сирот: {len(orphans)}")

    if not orphans:
        return

    freed = 0
    for name in orphans:
        path = os.path.join(UPLOAD_DIR, name)
        size = os.path.getsize(path)
        if delete:
            try:
                os.remove(path)
                freed += size
                print(f"  удалён  {name} ({size // 1024} КБ)")
            except OSError as exc:
                print(f"  ОШИБКА  {name}: {exc}")
        else:
            print(f"  сирота  {name} ({size // 1024} КБ)")

    if delete:
        print(f"Освобождено: {freed // 1024} КБ")
    else:
        print("\nЭто был предпросмотр. Чтобы удалить, запусти с флагом --delete")


if __name__ == "__main__":
    main()
