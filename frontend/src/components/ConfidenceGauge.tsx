interface ConfidenceGaugeProps {
  value: number; // 0–1
}

export default function ConfidenceGauge({ value }: ConfidenceGaugeProps) {
  const pct = Math.max(0, Math.min(1, value));
  const percentage = Math.round(pct * 100);

  // SVG arc parameters
  const cx = 100, cy = 100, r = 72;
  const startAngle = -180;
  const endAngle = 0;
  const totalArc = endAngle - startAngle; // 180 degrees

  const toRad = (deg: number) => (deg * Math.PI) / 180;

  const arcPath = (fromDeg: number, toDeg: number) => {
    const x1 = cx + r * Math.cos(toRad(fromDeg));
    const y1 = cy + r * Math.sin(toRad(fromDeg));
    const x2 = cx + r * Math.cos(toRad(toDeg));
    const y2 = cy + r * Math.sin(toRad(toDeg));
    const largeArc = Math.abs(toDeg - fromDeg) > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
  };

  const fillEndDeg = startAngle + totalArc * pct;

  // Needle angle
  const needleDeg = startAngle + totalArc * pct;
  const needleRad = toRad(needleDeg);
  const needleLength = 58;
  const nx = cx + needleLength * Math.cos(needleRad);
  const ny = cy + needleLength * Math.sin(needleRad);

  // Color stops for the arc
  const getColor = (p: number) => {
    if (p < 0.33) return '#EF4444';
    if (p < 0.66) return '#F59E0B';
    return '#10B981';
  };
  const fillColor = getColor(pct);

  return (
    <svg viewBox="0 0 200 110" className="w-full" style={{ maxHeight: 160 }}>
      {/* Background arc */}
      <path
        d={arcPath(startAngle, endAngle)}
        fill="none"
        stroke="#E2E8F0"
        strokeWidth="14"
        strokeLinecap="round"
      />

      {/* Filled arc – red segment */}
      {pct > 0 && (
        <path
          d={arcPath(startAngle, fillEndDeg)}
          fill="none"
          stroke={fillColor}
          strokeWidth="14"
          strokeLinecap="round"
        />
      )}

      {/* Center dot */}
      <circle cx={cx} cy={cy} r="5" fill="#334155" />

      {/* Needle */}
      <line
        x1={cx} y1={cy}
        x2={nx} y2={ny}
        stroke="#334155"
        strokeWidth="2.5"
        strokeLinecap="round"
      />

      {/* Percentage label */}
      <text
        x={cx} y={cy - 18}
        textAnchor="middle"
        fontSize="22"
        fontWeight="700"
        fill="#111827"
      >
        {percentage}%
      </text>

      {/* Min / Max labels */}
      <text x="16" y="108" fontSize="11" fill="#94A3B8" fontWeight="600">0</text>
      <text x="178" y="108" fontSize="11" fill="#94A3B8" fontWeight="600" textAnchor="end">100</text>
    </svg>
  );
}
