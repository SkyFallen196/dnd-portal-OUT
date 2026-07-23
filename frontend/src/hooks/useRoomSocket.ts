import { useEffect, useRef } from "react";
import { WS_URL, getToken } from "../api/client";
import { useAdminEdit } from "../store/adminEdit";

type MessageHandler = (msg: any) => void;

// Подключается к WebSocket комнаты и вызывает onMessage на каждое событие сервера.
// Возвращает ref с функцией sendMove для отправки перемещений.
export function useRoomSocket(roomId: number, onMessage: MessageHandler) {
  const socketRef = useRef<WebSocket | null>(null);
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;
  // Права на сокете выдаются один раз при подключении, поэтому переключение
  // «Режима редактирования» обязано пересоздать соединение — иначе сервер продолжит
  // считать админа наблюдателем и молча игнорировать перетаскивание чужих фишек.
  const adminEdit = useAdminEdit((s) => s.enabled);

  useEffect(() => {
    let closedByUs = false;
    let reconnectTimer: number | undefined;

    const connect = () => {
      const token = getToken();
      if (!token) return;
      // Админу права мастера в чужой комнате даются только с включённым режимом.
      const editParam = adminEdit ? "&admin_edit=1" : "";
      const ws = new WebSocket(`${WS_URL}/ws/rooms/${roomId}?token=${token}${editParam}`);
      socketRef.current = ws;

      ws.onmessage = (event) => {
        try {
          handlerRef.current(JSON.parse(event.data));
        } catch {
          /* игнорируем битые сообщения */
        }
      };

      ws.onclose = () => {
        if (!closedByUs) {
          // Переподключаемся через 2 секунды, если соединение оборвалось.
          reconnectTimer = window.setTimeout(connect, 2000);
        }
      };
    };

    connect();

    return () => {
      closedByUs = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      socketRef.current?.close();
    };
  }, [roomId, adminEdit]);

  // Отправка перемещения фишки (throttle делаем на стороне вызывающего).
  const sendMove = (tokenId: number, x: number, y: number) => {
    const ws = socketRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "move", token_id: tokenId, x, y }));
    }
  };

  return { sendMove };
}
