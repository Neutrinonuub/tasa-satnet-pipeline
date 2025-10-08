#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
from sgp4.api import Satrec, jday

@dataclass
class Site:
    lat: float
    lon: float
    alt: float

def gmst(dt: datetime) -> float:
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond*1e-6)
    T = ((jd - 2451545.0) + fr) / 36525.0
    gmst_sec = 67310.54841 + (876600.0*3600 + 8640184.812866)*T + 0.093104*(T**2) - 6.2e-6*(T**3)
    return math.radians((gmst_sec/240.0) % 360.0)

def teme_to_ecef(r_teme: np.ndarray, dt: datetime) -> np.ndarray:
    th = gmst(dt)
    c, s = math.cos(th), math.sin(th)
    R = np.array([[ c, s, 0],[-s, c, 0],[0,0,1]], float)
    return R @ r_teme

def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_km: float) -> np.ndarray:
    a = 6378.137; f = 1/298.257223563; e2 = f*(2-f)
    lat = math.radians(lat_deg); lon = math.radians(lon_deg)
    N = a / math.sqrt(1 - e2 * (math.sin(lat)**2))
    x = (N + alt_km) * math.cos(lat) * math.cos(lon)
    y = (N + alt_km) * math.cos(lat) * math.sin(lon)
    z = (N*(1 - e2) + alt_km) * math.sin(lat)
    return np.array([x,y,z], float)

def ecef_to_enu(vec_ecef: np.ndarray, lat_deg: float, lon_deg: float) -> np.ndarray:
    lat = math.radians(lat_deg); lon = math.radians(lon_deg)
    sl, cl = math.sin(lat), math.cos(lat)
    so, co = math.sin(lon), math.cos(lon)
    R = np.array([[-so, co, 0],[-sl*co, -sl*so, cl],[cl*co, cl*so, sl]], float)
    return R @ vec_ecef

def elevation_deg(sat_ecef: np.ndarray, site_ecef: np.ndarray, lat: float, lon: float) -> float:
    rho = sat_ecef - site_ecef
    enu = ecef_to_enu(rho, lat, lon)
    e = enu[2] / np.linalg.norm(enu)
    return math.degrees(math.asin(max(-1.0, min(1.0, e))))

def parse_tle_file(path: Path):
    lines = path.read_text(encoding='utf-8', errors='ignore').strip().splitlines()
    if len(lines) >= 3 and not lines[0].startswith('1 ') and not lines[0].startswith('2 '):
        name = lines[0].strip(); l1, l2 = lines[1].strip(), lines[2].strip()
    else:
        name = "SAT-UNK"; l1, l2 = lines[0].strip(), lines[1].strip()
    sat = Satrec.twoline2rv(l1, l2); return name, sat

def dt_range(start: datetime, end: datetime, step_s: int):
    t = start
    while t <= end:
        yield t; t += timedelta(seconds=step_s)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tle', type=Path, required=True)
    ap.add_argument('--lat', type=float, required=True)
    ap.add_argument('--lon', type=float, required=True)
    ap.add_argument('--alt', type=float, default=0.0)
    ap.add_argument('--start', type=str, required=True)
    ap.add_argument('--end', type=str, required=True)
    ap.add_argument('--step', type=int, default=30)
    ap.add_argument('--min-elev', type=float, default=10.0)
    ap.add_argument('--out', type=Path, default=Path('data/tle_windows.json'))
    args = ap.parse_args()

    site = Site(args.lat, args.lon, args.alt)
    site_ecef = geodetic_to_ecef(site.lat, site.lon, site.alt)
    name, sat = parse_tle_file(args.tle)

    t0 = datetime.fromisoformat(args.start.replace('Z','+00:00')).astimezone(timezone.utc).replace(tzinfo=timezone.utc)
    t1 = datetime.fromisoformat(args.end.replace('Z','+00:00')).astimezone(timezone.utc).replace(tzinfo=timezone.utc)

    in_contact, current, windows = False, None, []
    for t in dt_range(t0, t1, args.step):
        jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond*1e-6)
        e, r, v = sat.sgp4(jd, fr)
        if e != 0: continue
        r_ecef = teme_to_ecef(np.array(r, float), t)
        elev = elevation_deg(r_ecef, site_ecef, site.lat, site.lon)
        if elev >= args.min_elev and not in_contact:
            in_contact = True
            current = {'type':'tle_pass','start':t.isoformat().replace('+00:00','Z'),
                       'end':None,'sat':name,'gw':f'{site.lat:.3f},{site.lon:.3f}'}
        elif elev < args.min_elev and in_contact:
            in_contact = False
            current['end'] = t.isoformat().replace('+00:00','Z')
            windows.append(current); current=None
    if in_contact and current:
        current['end'] = t1.isoformat().replace('+00:00','Z'); windows.append(current)

    out = {'meta': {'tle': str(args.tle), 'min_elev_deg': args.min_elev, 'step_s': args.step, 'count': len(windows)},
           'windows': windows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps({'kept': len(windows), 'outfile': str(args.out)}, indent=2))

if __name__ == '__main__': main()
