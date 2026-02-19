/**
 * colorConvert.js — CIELAB → sRGB conversion for 3D shader materials.
 *
 * Replicates the same conversion the Python backend uses (color.py)
 * so we can colour the tea-bed mesh directly from L*, a*, b* telemetry.
 */

// D65 white-point
const Xn = 0.95047;
const Yn = 1.0;
const Zn = 1.08883;

/**
 * Convert CIELAB (L*, a*, b*) to sRGB hex string "#rrggbb".
 */
export function labToHex(L, a, b) {
  const [r, g, bl] = labToRgb(L, a, b);
  const toHex = (v) => {
    const h = Math.round(v).toString(16);
    return h.length === 1 ? '0' + h : h;
  };
  return `#${toHex(r)}${toHex(g)}${toHex(bl)}`;
}

/**
 * Convert CIELAB (L*, a*, b*) to [R, G, B] in 0–255.
 */
export function labToRgb(L, a, b) {
  // CIELAB → XYZ
  const fy = (L + 16) / 116;
  const fx = a / 500 + fy;
  const fz = fy - b / 200;

  const delta = 6 / 29;
  const inv = (t) =>
    t > delta ? t * t * t : 3 * delta * delta * (t - 4 / 29);

  const X = Xn * inv(fx);
  const Y = Yn * inv(fy);
  const Z = Zn * inv(fz);

  // XYZ → linear RGB (sRGB matrix)
  let rLin = 3.2406 * X - 1.5372 * Y - 0.4986 * Z;
  let gLin = -0.9689 * X + 1.8758 * Y + 0.0415 * Z;
  let bLin = 0.0557 * X - 0.2040 * Y + 1.0570 * Z;

  // Gamma correction
  const gamma = (c) => {
    c = Math.max(0, Math.min(1, c));
    return c <= 0.0031308
      ? 12.92 * c
      : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
  };

  return [
    Math.round(gamma(rLin) * 255),
    Math.round(gamma(gLin) * 255),
    Math.round(gamma(bLin) * 255),
  ];
}

/**
 * Get a colour description for a temperature value.
 * cold = blue, warm = orange, hot = red
 */
export function tempToColor(temp) {
  if (temp < 60) return '#60a5fa';   // blue
  if (temp < 90) return '#fbbf24';   // amber
  if (temp < 110) return '#f97316';  // orange
  return '#ef4444';                   // red
}

/**
 * Compute a simple quality score 0–100 from final state.
 */
export function qualityScore(state) {
  if (!state) return 0;
  const m = state.moisture ?? 0.7;
  const enz = state.enzyme_activity ?? 1;
  const pyr = state.pyrazine ?? 0;

  // Moisture component: target 3-4%, penalise deviation
  const mPct = m * 100;
  const mScore = Math.max(0, 100 - Math.abs(mPct - 3.5) * 15);

  // Enzyme: should be fully denatured (near 0)
  const eScore = (1 - enz) * 100;

  // Pyrazine: more is better, cap at 5
  const pScore = Math.min(100, (pyr / 5) * 100);

  return Math.round(mScore * 0.4 + eScore * 0.3 + pScore * 0.3);
}
