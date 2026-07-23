"""Менеджер WebSocket-соединений, сгруппированных по комнатам.

Для каждой комнаты храним активные сокеты и признак «это мастер». Признак нужен
из-за скрытых фишек: их нельзя просто прятать на клиенте — данные не должны уходить
игрокам вообще, иначе засаду видно в инструментах разработчика.
"""
import asyncio

from fastapi import WebSocket


class RoomConnectionManager:
    def __init__(self) -> None:
        # room_id -> {сокет: является ли мастером}
        self._rooms: dict[int, dict[WebSocket, bool]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, room_id: int, websocket: WebSocket, is_dm: bool = False) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms.setdefault(room_id, {})[websocket] = is_dm

    async def disconnect(self, room_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self._rooms.get(room_id)
            if conns and websocket in conns:
                conns.pop(websocket, None)
                if not conns:
                    self._rooms.pop(room_id, None)

    async def _send(self, room_id: int, targets: list[WebSocket], message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(room_id, ws)

    async def broadcast(self, room_id: int, message: dict, dm_only: bool = False) -> None:
        """Отправить сообщение всем в комнате (или только мастерам)."""
        conns = dict(self._rooms.get(room_id, {}))
        targets = [ws for ws, is_dm in conns.items() if is_dm or not dm_only]
        await self._send(room_id, targets, message)

    async def broadcast_split(
        self, room_id: int, dm_message: dict, player_message: dict | None
    ) -> None:
        """Разные сообщения мастерам и игрокам.

        Нужно, когда фишку прячут или показывают: мастер видит обновление, а у игроков
        она должна появиться или исчезнуть. `player_message=None` — игрокам не слать ничего.
        """
        conns = dict(self._rooms.get(room_id, {}))
        dms = [ws for ws, is_dm in conns.items() if is_dm]
        players = [ws for ws, is_dm in conns.items() if not is_dm]
        await self._send(room_id, dms, dm_message)
        if player_message is not None and players:
            await self._send(room_id, players, player_message)


# Один общий менеджер на всё приложение.
manager = RoomConnectionManager()
