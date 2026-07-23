import { useEffect, useMemo, useRef, useState } from "react";
import { Circle, Group, Image as KImage, Layer, Line, Rect, Stage, Text } from "react-konva";
import type Konva from "konva";
import type { Token } from "../api/types";
import { API_URL } from "../api/client";

// Одна клетка сетки — 5 футов. Это стандарт D&D, от него считает и линейка.
const FEET_PER_CELL = 5;
// Потолок на количество линий сетки: защита от крошечного шага, при котором
// холст пришлось бы залить тысячами линий и всё бы встало.
const MAX_GRID_LINES = 400;

// Загружает картинку по url в объект Image, который умеет рисовать Konva.
function useImg(url: string | null) {
  const [img, setImg] = useState<HTMLImageElement | null>(null);
  useEffect(() => {
    if (!url) {
      setImg(null);
      return;
    }
    const image = new window.Image();
    image.src = url.startsWith("http") ? url : API_URL + url;
    image.onload = () => setImg(image);
  }, [url]);
  return img;
}

interface Props {
  mapUrl: string | null;
  tokens: Token[];
  // Чей сейчас ход в бою — эту фишку обводим золотым, чтобы было видно с любого края карты.
  activeTokenId?: number | null;
  // Сторона клетки в пикселях карты; 0 — сетку не рисуем.
  gridSize?: number;
  // Включён режим линейки: карта не таскается, клики меряют расстояние.
  rulerActive?: boolean;
  canMove: (tk: Token) => boolean;
  onMove: (id: number, x: number, y: number) => void; // во время перетаскивания (throttle)
  onMoveEnd: (id: number, x: number, y: number) => void; // при отпускании мыши
  onSelect?: (tk: Token) => void;
}

// Базовый радиус фишки; итоговый = BASE_RADIUS * tk.size.
const BASE_RADIUS = 34;

// Как рисуется одна фишка: кружок с цветом или картинкой + имя + HP + эффекты.
function TokenShape({
  tk,
  movable,
  isActive,
  onDragMove,
  onDragEnd,
  onSelect,
}: {
  tk: Token;
  movable: boolean;
  isActive: boolean;
  onDragMove: (id: number, e: Konva.KonvaEventObject<DragEvent>) => void;
  onDragEnd: (id: number, x: number, y: number) => void;
  onSelect?: (tk: Token) => void;
}) {
  const avatar = useImg(tk.avatar_url);
  const r = BASE_RADIUS * (tk.size || 1);
  const effects = tk.effects || [];
  // Шрифты крупнее и слегка растут вместе с размером фишки (с нижним пределом).
  const nameFont = Math.max(17, r * 0.5);
  const hpFont = Math.max(16, r * 0.45);
  const effFont = Math.max(15, r * 0.42);
  const npcFont = Math.max(13, r * 0.34);
  const caption = [tk.is_npc ? "NPC" : null, tk.hidden ? "СКРЫТ" : null].filter(Boolean).join(" · ");

  return (
    <Group
      x={tk.x}
      y={tk.y}
      // Скрытую фишку видит только мастер (игрокам её не присылают вовсе).
      // Делаем полупрозрачной, чтобы он не забыл, что партия её пока не видит.
      opacity={tk.hidden ? 0.45 : 1}
      draggable={movable}
      onClick={() => onSelect?.(tk)}
      onTap={() => onSelect?.(tk)}
      onDragMove={(e) => onDragMove(tk.id, e)}
      onDragEnd={(e) => onDragEnd(tk.id, e.target.x(), e.target.y())}
    >
      {avatar ? (
        // Аватар: обрезаем картинку по кругу.
        <Group
          clipFunc={(ctx) => {
            ctx.beginPath();
            ctx.arc(0, 0, r, 0, Math.PI * 2, false);
            ctx.closePath();
          }}
        >
          <KImage image={avatar} x={-r} y={-r} width={r * 2} height={r * 2} />
        </Group>
      ) : (
        <Circle radius={r} fill={tk.color} shadowColor="black" shadowBlur={8} shadowOpacity={0.6} />
      )}

      {/* Цветное кольцо-обводка (цвет фишки заметен даже с картинкой) */}
      <Circle radius={r} stroke={tk.color} strokeWidth={4} shadowColor="black" shadowBlur={6} shadowOpacity={0.5} />
      {/* Тонкая светлая рамка сверху для контраста */}
      <Circle radius={r} stroke={movable ? "#ffffff" : "rgba(255,255,255,0.35)"} strokeWidth={1.5} />

      {/* Чей сейчас ход: широкое золотое кольцо снаружи фишки */}
      {isActive && (
        <Circle
          radius={r + 7}
          stroke="#d4af37"
          strokeWidth={5}
          shadowColor="#d4af37"
          shadowBlur={16}
          shadowOpacity={1}
          listening={false}
        />
      )}

      {/* Баффы (зелёные ▲) и дебаффы (красные ▼) стопкой над фишкой */}
      {effects.map((ef, i) => (
        <Text
          key={i}
          text={(ef.type === "buff" ? "▲ " : "▼ ") + ef.name}
          fontSize={effFont}
          fontStyle="bold"
          fill={ef.type === "buff" ? "#8ce06a" : "#ff6b6b"}
          align="center"
          width={240}
          offsetX={120}
          y={-r - effFont - 2 - i * (effFont + 4)}
          shadowColor="black"
          shadowBlur={4}
          shadowOpacity={1}
        />
      ))}

      <Text
        text={tk.name}
        fontSize={nameFont}
        fontStyle="bold"
        fill="#fff"
        align="center"
        width={240}
        offsetX={120}
        y={r + 5}
        shadowColor="black"
        shadowBlur={4}
      />

      {/* Подпись под именем: NPC мастера и/или пометка «скрыт от игроков». */}
      {caption && (
        <Text
          text={caption}
          fontSize={npcFont}
          fontStyle="bold"
          fill="#e6c98a"
          align="center"
          width={240}
          offsetX={120}
          y={r + 7 + nameFont}
          letterSpacing={1}
          shadowColor="black"
          shadowBlur={4}
        />
      )}
      <Text
        text={`${tk.hp}/${tk.max_hp}`}
        fontSize={hpFont}
        fontStyle="bold"
        fill="#fff"
        align="center"
        width={r * 2}
        offsetX={r}
        offsetY={hpFont / 2}
        shadowColor="black"
        shadowBlur={4}
      />
    </Group>
  );
}

// Две точки линейки в координатах карты.
interface Measure {
  from: { x: number; y: number };
  to: { x: number; y: number };
  done: boolean; // false — вторую точку ещё водят мышью
}

export default function MapCanvas({
  mapUrl,
  tokens,
  activeTokenId,
  gridSize = 0,
  rulerActive = false,
  canMove,
  onMove,
  onMoveEnd,
  onSelect,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [scale, setScale] = useState(1);
  const image = useImg(mapUrl);
  const lastSent = useRef(0);
  const [measure, setMeasure] = useState<Measure | null>(null);

  // Порядок отрисовки: снизу вверх по z, при равном z — по id. Konva рисует
  // в порядке массива, поэтому последняя фишка окажется поверх остальных.
  const ordered = useMemo(
    () => [...tokens].sort((a, b) => (a.z || 0) - (b.z || 0) || a.id - b.id),
    [tokens]
  );

  // Размер поля под сетку: по карте, а если её нет — по заглушке.
  const mapW = image?.width || 1000;
  const mapH = image?.height || 700;

  // Линии сетки пересчитываем только при смене шага или карты, а не на каждый кадр зума.
  const gridLines = useMemo(() => {
    if (!gridSize || gridSize <= 0) return [];
    if (mapW / gridSize > MAX_GRID_LINES || mapH / gridSize > MAX_GRID_LINES) return [];
    const lines: number[][] = [];
    for (let x = 0; x <= mapW; x += gridSize) lines.push([x, 0, x, mapH]);
    for (let y = 0; y <= mapH; y += gridSize) lines.push([0, y, mapW, y]);
    return lines;
  }, [gridSize, mapW, mapH]);

  // Выход из режима линейки стирает недомеренное — иначе замер повиснет на карте.
  useEffect(() => {
    if (!rulerActive) setMeasure(null);
  }, [rulerActive]);

  // Подгоняем размер холста под размер контейнера.
  useEffect(() => {
    const update = () => {
      if (containerRef.current) {
        setSize({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  // Зум колёсиком мыши.
  const onWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    const factor = e.evt.deltaY > 0 ? 0.92 : 1.08;
    setScale((s) => Math.min(4, Math.max(0.2, s * factor)));
  };

  const handleDragMove = (id: number, e: Konva.KonvaEventObject<DragEvent>) => {
    const now = Date.now();
    // Не чаще ~20 раз в секунду, чтобы не залить сеть.
    if (now - lastSent.current > 50) {
      lastSent.current = now;
      onMove(id, e.target.x(), e.target.y());
    }
  };

  // Координаты указателя в системе самой карты: getRelativePointerPosition
  // уже учитывает и зум, и сдвиг холста.
  const pointer = (e: Konva.KonvaEventObject<MouseEvent>) =>
    e.target.getStage()?.getRelativePointerPosition() ?? null;

  // Линейка: первый клик ставит начало, второй фиксирует замер, третий начинает заново.
  const handleClick = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (!rulerActive) return;
    const p = pointer(e);
    if (!p) return;
    setMeasure((prev) =>
      prev && !prev.done ? { ...prev, to: p, done: true } : { from: p, to: p, done: false }
    );
  };

  const handleMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (!rulerActive) return;
    setMeasure((prev) => {
      if (!prev || prev.done) return prev;
      const p = pointer(e);
      return p ? { ...prev, to: p } : prev;
    });
  };

  return (
    <div ref={containerRef} style={{ width: "100%", height: "100%" }}>
      <Stage
        width={size.width}
        height={size.height}
        scaleX={scale}
        scaleY={scale}
        // В режиме линейки холст не таскаем: иначе клик по карте её панорамирует,
        // а не ставит точку замера.
        draggable={!rulerActive}
        onWheel={onWheel}
        onClick={handleClick}
        onMouseMove={handleMouseMove}
        style={{ cursor: rulerActive ? "crosshair" : "grab" }}
      >
        <Layer>
          {image ? (
            <KImage image={image} />
          ) : (
            <>
              <Rect width={1000} height={700} fill="#0d0b0a" />
              <Text
                text="Карта не загружена. Мастер может загрузить её в панели справа."
                x={40}
                y={40}
                fontSize={18}
                fill="#a99a86"
              />
            </>
          )}

          {/* Сетка поверх карты, но под фишками. listening=false — линии не должны
              перехватывать клики по карте и по фишкам. */}
          {gridLines.map((points, i) => (
            <Line key={i} points={points} stroke="rgba(255,255,255,0.18)" strokeWidth={1} listening={false} />
          ))}

          {ordered.map((tk) => (
            <TokenShape
              key={tk.id}
              tk={tk}
              // В режиме линейки фишки не двигаются: замер важнее случайного сдвига.
              movable={canMove(tk) && !rulerActive}
              isActive={tk.id === activeTokenId}
              onDragMove={handleDragMove}
              onDragEnd={onMoveEnd}
              // При включённой линейке клик по фишке ставит точку замера, а не
              // открывает свиток — иначе окно свитка перекрыло бы карту посреди измерения.
              onSelect={rulerActive ? undefined : onSelect}
            />
          ))}

          {measure && <Ruler measure={measure} gridSize={gridSize} scale={scale} />}
        </Layer>
      </Stage>
    </div>
  );
}

// Линейка: пунктирная линия между двумя точками и подпись с расстоянием.
function Ruler({ measure, gridSize, scale }: { measure: Measure; gridSize: number; scale: number }) {
  const { from, to } = measure;
  const dist = Math.hypot(to.x - from.x, to.y - from.y);
  // Клетки округляем — на столе меряют клетками, а не пикселями.
  const cells = gridSize > 0 ? Math.round(dist / gridSize) : 0;
  const label = gridSize > 0 ? `${cells * FEET_PER_CELL} фт · ${cells} кл.` : `${Math.round(dist)} px`;

  // Подпись не должна расти и уменьшаться вместе с зумом — держим её читаемой.
  const font = 16 / scale;
  const pad = 5 / scale;
  const boxW = label.length * font * 0.58 + pad * 2;
  const boxH = font + pad * 2;

  return (
    <Group listening={false}>
      <Line
        points={[from.x, from.y, to.x, to.y]}
        stroke="#d4af37"
        strokeWidth={3 / scale}
        dash={[10 / scale, 6 / scale]}
        shadowColor="black"
        shadowBlur={4}
      />
      <Circle x={from.x} y={from.y} radius={5 / scale} fill="#d4af37" />
      <Circle x={to.x} y={to.y} radius={5 / scale} fill="#d4af37" />
      <Group x={to.x + 12 / scale} y={to.y - boxH - 6 / scale}>
        <Rect width={boxW} height={boxH} fill="rgba(20,17,15,0.85)" stroke="#d4af37" strokeWidth={1 / scale} cornerRadius={4 / scale} />
        <Text text={label} x={pad} y={pad} fontSize={font} fontStyle="bold" fill="#d4af37" />
      </Group>
    </Group>
  );
}
