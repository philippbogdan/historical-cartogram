"""D3: HYDE 3.3 population grids (5 arcmin, 4320 x 2160, 10,000 BCE to 2023 CE) from population.nc."""
import numpy as np
import netCDF4


class Hyde:
    def __init__(self, path):
        self.ds = netCDF4.Dataset(path)
        names = list(self.ds.variables)
        self.var = next(v for v in names if v.lower().startswith("pop") or v == "population")
        self.time_name = next(v for v in names if v.lower() in ("time", "year", "years"))
        self.lat_name = next(v for v in names if v.lower().startswith("lat"))
        self.lon_name = next(v for v in names if v.lower().startswith("lon"))
        t = self.ds.variables[self.time_name]
        self.years = self._years(t)
        lat = self.ds.variables[self.lat_name][:]
        lon = self.ds.variables[self.lon_name][:]
        self.north_up = lat[0] > lat[-1]
        dlat = abs(float(lat[1] - lat[0])); dlon = abs(float(lon[1] - lon[0]))
        self.bounds = (float(lon.min()) - dlon / 2, float(lat.min()) - dlat / 2, float(lon.max()) + dlon / 2, float(lat.max()) + dlat / 2)

    @staticmethod
    def _years(t):
        units = getattr(t, "units", "")
        vals = np.array(t[:], dtype=np.float64)
        if "since" in units:  # e.g. "years since 0000-01-01" or "days since ..."
            import re
            m = re.search(r"since\s*(-?\d+)", units)
            base = int(m.group(1)) if m else 0
            if units.startswith("days"):
                vals = vals / 365.25
            return (vals + base).astype(int)
        return vals.astype(int)

    def counts(self, i):
        """People per cell for epoch index i, north row first, as float64 (nodata -> 0)."""
        a = np.array(self.ds.variables[self.var][i], dtype=np.float64)
        a = np.nan_to_num(a); a[a < 0] = 0
        if not self.north_up:
            a = a[::-1]
        return a

    def total(self, i):
        return float(self.counts(i).sum())
