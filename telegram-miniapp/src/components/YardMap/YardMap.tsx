import type { FC } from 'react';

interface YardMapProps {
  targetCoordinate: string;
  containerSize?: string;
  containerNumber?: string;
}

function parseCoordinate(coord: string) {
  const match = coord.match(/^([A-E])-R(\d+)-B(\d+)-T(\d+)-([AB])$/);
  if (!match) return null;
  return {
    zone: match[1],
    row: parseInt(match[2], 10),
    bay: parseInt(match[3], 10),
    tier: parseInt(match[4], 10),
    slot: match[5],
  };
}

function getCellBackgroundColor(isTarget: boolean, isHighlighted: boolean): string {
  if (isTarget) return '#7c3aed';
  if (isHighlighted) return '#ede9fe';
  return '#f1f5f9';
}

export const YardMap: FC<YardMapProps> = ({
  targetCoordinate,
  containerSize = '40',
  containerNumber,
}) => {
  const target = parseCoordinate(targetCoordinate);

  if (!target) {
    return (
      <div className="bg-gray-100 rounded-xl p-4 text-center text-sm">
        {targetCoordinate}
      </div>
    );
  }

  const is20ft = containerSize === '20';
  const maxTier = 4;

  // Grid centered on target position
  const gridSize = { rows: 5, bays: 6 };
  const startRow = Math.max(1, target.row - 2);
  const startBay = Math.max(1, target.bay - 2);
  const rows = Array.from({ length: gridSize.rows }, (_, i) => startRow + i);
  const bays = Array.from({ length: gridSize.bays }, (_, i) => startBay + i);

  const shortNum = containerNumber?.slice(-4) || '';

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      {/* Info Bar */}
      <div className="flex items-center gap-2 px-3 py-2.5 bg-gradient-to-r from-slate-50 to-gray-50 border-b border-gray-100">
        <div
          className="text-white px-3 py-1.5 rounded-lg text-base font-bold shadow-sm"
          style={{ backgroundColor: '#3b82f6' }}
        >
          {target.zone}
        </div>
        <div className="flex items-center gap-3 text-sm">
          <div className="flex items-center gap-1">
            <span className="text-gray-400 font-medium">Ряд</span>
            <span className="font-bold text-gray-700">{target.row}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-gray-400 font-medium">Бэй</span>
            <span className="font-bold text-gray-700">{target.bay}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-gray-400 font-medium">Ярус</span>
            <span className="font-bold text-gray-700">{target.tier}/{maxTier}</span>
          </div>
        </div>
        {is20ft && (
          <div className="ml-auto bg-violet-100 text-violet-700 px-2 py-1 rounded-md text-xs font-bold">
            Слот {target.slot}
          </div>
        )}
      </div>

      {/* Two Views Side by Side */}
      <div className="flex p-4 gap-6 justify-center items-start">
        {/* Left: Top-down Grid View */}
        <div>
          <div className="text-xs text-gray-500 mb-2 font-medium">Вид сверху</div>
          <div className="inline-block">
            {/* Bay numbers header */}
            <div className="flex mb-1">
              <div className="w-6"></div>
              {bays.map((b) => (
                <div
                  key={b}
                  className="w-7 text-center text-xs font-medium"
                  style={{ color: b === target.bay ? '#7c3aed' : '#9ca3af' }}
                >
                  {b}
                </div>
              ))}
            </div>
            {/* Grid rows */}
            {rows.map((r) => (
              <div key={r} className="flex items-center">
                <div
                  className="w-6 text-xs text-right pr-1.5 font-medium"
                  style={{ color: r === target.row ? '#7c3aed' : '#9ca3af' }}
                >
                  {r}
                </div>
                {bays.map((b) => {
                  const isTarget = r === target.row && b === target.bay;
                  const isHighlighted = r === target.row || b === target.bay;
                  return (
                    <div
                      key={b}
                      className="w-7 h-7 m-0.5 rounded"
                      style={{
                        backgroundColor: getCellBackgroundColor(isTarget, isHighlighted),
                        boxShadow: isTarget ? '0 2px 4px rgba(124, 58, 237, 0.3)' : 'none',
                      }}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Tier Stack View */}
        <div className="w-28">
          <div className="text-xs text-gray-500 mb-2 font-medium">Ярусы</div>
          <div className="flex flex-col gap-1">
            {[4, 3, 2, 1].map((t) => {
              const isTarget = t === target.tier;
              return (
                <div key={t} className="flex items-center gap-1.5">
                  <span
                    className="text-xs w-4 font-medium"
                    style={{ color: isTarget ? '#7c3aed' : '#9ca3af' }}
                  >
                    {t}
                  </span>
                  <div
                    className="flex-1 h-8 rounded flex items-center justify-center"
                    style={{
                      backgroundColor: isTarget ? '#ede9fe' : '#f8fafc',
                      border: isTarget ? '2px solid #7c3aed' : '1px dashed #e2e8f0',
                      boxShadow: isTarget ? '0 2px 4px rgba(124, 58, 237, 0.15)' : 'none',
                    }}
                  >
                    {isTarget && (
                      <span className="text-xs text-violet-600 font-semibold">
                        {shortNum}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
            <div className="border-t-2 border-gray-300 mt-1 pt-1.5 text-center text-xs text-gray-400 font-medium">
              земля
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
