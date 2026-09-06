// Shared by the map annotations and the numerical browser-data checks.
export function geography([u, v]) {
  const latitude = 2 * Math.atan(Math.exp((.5 - v) * 2 * Math.PI)) - Math.PI / 2;
  return [u, .28 - latitude / Math.PI * .5];
}

export function sampleWarp([u, v], data, n) {
  const x = Math.max(0, Math.min(n - 1e-6, u * n));
  const y = Math.max(0, Math.min(n - 1e-6, v * n));
  const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j;
  const k = 2 * (j * (n + 1) + i), stride = 2 * (n + 1);
  return [0, 1].map(c => fx >= fy ?
    data[k+c]*(1-fx)+data[k+2+c]*(fx-fy)+data[k+stride+2+c]*fy :
    data[k+c]*(1-fy)+data[k+stride+2+c]*fx+data[k+stride+c]*(fy-fx));
}

export function endpoints(uv, data, n) {
  const a = geography(uv), b = sampleWarp(uv, data, n);
  return [a[0], a[1], b[0], b[1] * .56];
}

export function interpolate(p, t) {
  return [p[0] * (1 - t) + p[2] * t, p[1] * (1 - t) + p[3] * t];
}

export function ease(t) { return t * t * (3 - 2 * t); }
