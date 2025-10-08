# TDD 開發計劃 - 下一階段（多星系整合與視覺化）

**版本**: 1.0
**日期**: 2025-10-08
**目標**: Starlink 100 衛星 + 多星系整合 + 覆蓋視覺化

---

## 執行摘要

### 當前狀態
- ✅ 基本管線完成 (Parser → Scenario → Metrics → Scheduler)
- ✅ 22,109 顆衛星 TLE 資料已下載
- ✅ 35 視窗複雜場景 100% 通過
- ✅ 台灣 6 站地面站網路建立
- ✅ 98.33% 測試覆蓋率

### 下一階段目標
1. **Starlink 100 衛星中型規模測試** (第一優先)
2. **多星系整合測試** (GPS + Iridium + OneWeb)
3. **覆蓋範圍視覺化** (地圖與時序圖)

### 開發方法
嚴格遵循 **Red-Green-Refactor** TDD 循環

---

## 第一優先：Starlink 100 衛星測試

### 目標
驗證管線能處理 100+ 衛星的中型規模場景

### TDD 循環 1.1：視窗生成器擴展

#### RED：寫失敗測試
```python
# tests/test_tle_windows.py
import pytest
from pathlib import Path
from scripts.tle_windows import calculate_passes, load_tle_file

def test_load_starlink_100_satellites():
    """測試載入 100 顆 Starlink TLE 資料"""
    tle_file = Path('data/starlink_100.tle')
    satellites = load_tle_file(tle_file)

    assert len(satellites) == 100
    assert all('name' in sat for sat in satellites)
    assert all('tle_line1' in sat for sat in satellites)
    assert all('tle_line2' in sat for sat in satellites)

def test_calculate_passes_for_100_satellites():
    """測試計算 100 顆衛星對單一地面站的可見視窗"""
    tle_file = Path('data/starlink_100.tle')
    station = {
        'name': 'HSINCHU',
        'lat': 24.7868,
        'lon': 120.9967,
        'alt': 100
    }
    start_time = '2025-10-08T00:00:00Z'
    end_time = '2025-10-08T06:00:00Z'

    windows = calculate_passes(
        tle_file,
        station,
        start_time,
        end_time,
        min_elevation=10.0
    )

    # 預期：6 小時內至少有 50+ 視窗（Starlink 密集覆蓋）
    assert len(windows) >= 50
    assert all('sat_id' in w for w in windows)
    assert all('aos' in w for w in windows)  # Acquisition of Signal
    assert all('los' in w for w in windows)  # Loss of Signal
    assert all('max_elevation' in w for w in windows)

def test_performance_100_satellites_under_30_seconds():
    """測試 100 衛星計算需在 30 秒內完成"""
    import time
    tle_file = Path('data/starlink_100.tle')
    station = {'name': 'TAIPEI', 'lat': 25.033, 'lon': 121.565, 'alt': 50}

    start = time.time()
    windows = calculate_passes(
        tle_file, station,
        '2025-10-08T00:00:00Z',
        '2025-10-08T12:00:00Z'
    )
    duration = time.time() - start

    assert duration < 30.0, f"計算耗時 {duration:.2f}s，超過 30s 限制"
    assert len(windows) > 0

def test_parallel_station_processing():
    """測試並行處理 6 個地面站"""
    tle_file = Path('data/starlink_100.tle')
    stations_file = Path('data/taiwan_ground_stations.json')

    results = calculate_multi_station_passes(
        tle_file,
        stations_file,
        '2025-10-08T00:00:00Z',
        '2025-10-08T12:00:00Z'
    )

    assert len(results) == 6  # 6 個地面站
    assert all('station_name' in r for r in results)
    assert all('window_count' in r for r in results)
    assert sum(r['window_count'] for r in results) >= 300  # 總計 300+ 視窗
```

**執行測試（應失敗）**：
```bash
pytest tests/test_tle_windows.py::test_load_starlink_100_satellites -v
# EXPECTED: FAILED - function not implemented
```

#### GREEN：最小實作

**Step 1**: 準備測試資料
```bash
# 從 active_sats.tle 提取前 100 顆 Starlink 衛星
python scripts/extract_starlink_subset.py --input data/starlink.tle --output data/starlink_100.tle --count 100
```

**Step 2**: 實作 `scripts/tle_windows.py` 擴展
```python
# scripts/tle_windows.py
from skyfield.api import load, wgs84, EarthSatellite
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

def load_tle_file(tle_path: Path) -> list[dict]:
    """載入 TLE 檔案並解析為衛星物件清單"""
    satellites = []
    with tle_path.open() as f:
        lines = f.readlines()

    # TLE 格式：3 行一組 (name, line1, line2)
    for i in range(0, len(lines), 3):
        if i+2 < len(lines):
            name = lines[i].strip()
            line1 = lines[i+1].strip()
            line2 = lines[i+2].strip()

            satellites.append({
                'name': name,
                'tle_line1': line1,
                'tle_line2': line2
            })

    return satellites

def calculate_passes(tle_path: Path, station: dict,
                     start_time: str, end_time: str,
                     min_elevation: float = 10.0) -> list[dict]:
    """計算衛星對地面站的可見視窗"""
    ts = load.timescale()
    satellites = load_tle_file(tle_path)

    # 解析時間
    t0 = ts.utc(datetime.fromisoformat(start_time.replace('Z', '+00:00')))
    t1 = ts.utc(datetime.fromisoformat(end_time.replace('Z', '+00:00')))

    # 建立地面站位置
    gs = wgs84.latlon(station['lat'], station['lon'], station['alt'])

    windows = []

    for sat_data in satellites:
        satellite = EarthSatellite(
            sat_data['tle_line1'],
            sat_data['tle_line2'],
            sat_data['name'],
            ts
        )

        # 尋找衛星升起與落下時刻
        t, events = satellite.find_events(gs, t0, t1, altitude_degrees=min_elevation)

        # 解析事件：0=rise, 1=culminate, 2=set
        for i in range(len(events)):
            if events[i] == 0:  # Rise event
                aos_time = t[i].utc_iso()
                max_elev = 0.0
                los_time = None

                # 尋找對應的 culminate 和 set
                for j in range(i+1, len(events)):
                    if events[j] == 1:  # Culminate
                        alt, az, dist = (satellite - gs).at(t[j]).altaz()
                        max_elev = alt.degrees
                    elif events[j] == 2:  # Set
                        los_time = t[j].utc_iso()
                        break

                if los_time:
                    windows.append({
                        'sat_id': sat_data['name'],
                        'aos': aos_time,
                        'los': los_time,
                        'max_elevation': max_elev,
                        'station': station['name']
                    })

    return windows

def calculate_multi_station_passes(tle_path: Path, stations_path: Path,
                                    start_time: str, end_time: str) -> list[dict]:
    """並行計算多個地面站的視窗"""
    with stations_path.open() as f:
        data = json.load(f)
    stations = data['ground_stations']

    results = []
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = []
        for station in stations:
            future = executor.submit(
                calculate_passes,
                tle_path, station, start_time, end_time
            )
            futures.append((station['name'], future))

        for station_name, future in futures:
            windows = future.result()
            results.append({
                'station_name': station_name,
                'window_count': len(windows),
                'windows': windows
            })

    return results
```

**Step 3**: 實作資料提取工具
```python
# scripts/extract_starlink_subset.py
#!/usr/bin/env python3
import argparse
from pathlib import Path

def extract_subset(input_file: Path, output_file: Path, count: int):
    """從 TLE 檔案提取指定數量的衛星"""
    with input_file.open() as f:
        lines = f.readlines()

    # Starlink 衛星識別：名稱包含 "STARLINK"
    starlink_groups = []
    for i in range(0, len(lines), 3):
        if i+2 < len(lines) and 'STARLINK' in lines[i].upper():
            starlink_groups.append(lines[i:i+3])
            if len(starlink_groups) >= count:
                break

    with output_file.open('w') as f:
        for group in starlink_groups:
            f.writelines(group)

    print(f"提取了 {len(starlink_groups)} 顆 Starlink 衛星 → {output_file}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--count', type=int, default=100)
    args = ap.parse_args()

    extract_subset(args.input, args.output, args.count)
```

**執行測試（應通過）**：
```bash
# 產生測試資料
python scripts/extract_starlink_subset.py --input data/starlink.tle --output data/starlink_100.tle --count 100

# 執行測試
pytest tests/test_tle_windows.py -v --cov=scripts/tle_windows.py
# EXPECTED: PASSED ✓
```

#### REFACTOR：優化與改進

**優化點**：
1. 使用快取避免重複計算
2. 向量化計算提升效能
3. 增加進度條顯示
4. 記憶體優化（大型 TLE 檔案）

```python
# scripts/tle_windows.py (重構版)
from functools import lru_cache
from tqdm import tqdm
import numpy as np

@lru_cache(maxsize=128)
def load_tle_file_cached(tle_path: Path) -> tuple:
    """快取版 TLE 載入"""
    satellites = load_tle_file(tle_path)
    return tuple(tuple(s.items()) for s in satellites)

def calculate_passes_optimized(tle_path: Path, station: dict,
                                start_time: str, end_time: str,
                                min_elevation: float = 10.0,
                                show_progress: bool = True) -> list[dict]:
    """優化版視窗計算（含進度條）"""
    satellites = load_tle_file(tle_path)

    windows = []
    iterator = tqdm(satellites, desc=f"計算 {station['name']}") if show_progress else satellites

    for sat_data in iterator:
        # ... (計算邏輯同上，但加入批次處理)
        pass

    return windows
```

**執行測試（應仍通過）**：
```bash
pytest tests/test_tle_windows.py -v
# EXPECTED: ALL PASSED ✓
```

---

### TDD 循環 1.2：場景生成器擴展

#### RED：寫失敗測試
```python
# tests/test_gen_scenario_scale.py
import pytest
from pathlib import Path
import json
from scripts.gen_scenario import generate_scenario

def test_generate_scenario_100_satellites():
    """測試生成 100 衛星場景"""
    windows_file = Path('data/starlink_100_windows.json')
    output_file = Path('results/starlink_100_scenario.json')

    generate_scenario(windows_file, output_file, mode='transparent')

    with output_file.open() as f:
        scenario = json.load(f)

    assert scenario['meta']['total_satellites'] == 100
    assert scenario['meta']['total_windows'] >= 300
    assert len(scenario['events']) >= 600  # 至少 300 視窗 × 2 事件
    assert 'satellites' in scenario
    assert len(scenario['satellites']) == 100

def test_scenario_events_sorted_by_time():
    """測試事件按時間排序"""
    windows_file = Path('data/starlink_100_windows.json')
    output_file = Path('results/starlink_100_scenario.json')

    generate_scenario(windows_file, output_file)

    with output_file.open() as f:
        scenario = json.load(f)

    events = scenario['events']
    timestamps = [e['timestamp'] for e in events]

    # 確認時間戳遞增排序
    assert timestamps == sorted(timestamps)

def test_scenario_link_budget_calculations():
    """測試每個事件包含鏈路預算計算"""
    windows_file = Path('data/starlink_100_windows.json')
    output_file = Path('results/starlink_100_scenario.json')

    generate_scenario(windows_file, output_file)

    with output_file.open() as f:
        scenario = json.load(f)

    for event in scenario['events']:
        if event['type'] == 'contact_start':
            assert 'distance_km' in event
            assert 'elevation_deg' in event
            assert 'free_space_loss_db' in event
            assert event['distance_km'] > 0
            assert 0 <= event['elevation_deg'] <= 90
```

**執行測試（應失敗）**：
```bash
pytest tests/test_gen_scenario_scale.py -v
# EXPECTED: FAILED - scenario file not generated
```

#### GREEN：實作場景生成器擴展

```python
# scripts/gen_scenario.py (擴展版)
def generate_scenario(windows_file: Path, output_file: Path,
                      mode: str = 'transparent') -> dict:
    """生成 NS-3 場景（支援大規模衛星）"""

    with windows_file.open() as f:
        data = json.load(f)

    windows = data.get('windows', [])

    # 提取唯一衛星列表
    satellites = {}
    for w in windows:
        sat_id = w['sat_id']
        if sat_id not in satellites:
            satellites[sat_id] = {
                'id': sat_id,
                'name': sat_id,
                'type': 'LEO',
                'orbit': {
                    'altitude_km': 550,  # Starlink 典型高度
                    'inclination_deg': 53.0
                }
            }

    # 生成事件（contact_start, contact_end）
    events = []
    for w in windows:
        # 計算鏈路預算
        distance_km = calculate_slant_range(w)
        elevation_deg = w.get('max_elevation', 10.0)
        free_space_loss_db = calculate_free_space_loss(distance_km, freq_ghz=12.0)

        # 接觸開始
        events.append({
            'timestamp': w['aos'],
            'type': 'contact_start',
            'sat_id': w['sat_id'],
            'gateway': w['station'],
            'distance_km': distance_km,
            'elevation_deg': elevation_deg,
            'free_space_loss_db': free_space_loss_db
        })

        # 接觸結束
        events.append({
            'timestamp': w['los'],
            'type': 'contact_end',
            'sat_id': w['sat_id'],
            'gateway': w['station']
        })

    # 按時間排序事件
    events.sort(key=lambda e: e['timestamp'])

    scenario = {
        'meta': {
            'mode': mode,
            'total_satellites': len(satellites),
            'total_windows': len(windows),
            'total_events': len(events),
            'generated_at': datetime.now(timezone.utc).isoformat()
        },
        'satellites': list(satellites.values()),
        'events': events
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open('w') as f:
        json.dump(scenario, f, indent=2)

    return scenario

def calculate_slant_range(window: dict) -> float:
    """計算斜距（簡化模型）"""
    # 使用最大仰角估算最短距離
    # d = sqrt(h^2 + 2*R*h) for elevation=0
    # d = h for elevation=90
    h = 550  # km (Starlink 高度)
    R = 6371  # km (地球半徑)
    elev = window.get('max_elevation', 10.0)

    # 簡化公式
    if elev >= 80:
        return h
    else:
        return h / np.sin(np.radians(elev))

def calculate_free_space_loss(distance_km: float, freq_ghz: float = 12.0) -> float:
    """計算自由空間路徑損耗 (dB)"""
    # FSPL(dB) = 20*log10(d) + 20*log10(f) + 92.45
    # d in km, f in GHz
    return 20*np.log10(distance_km) + 20*np.log10(freq_ghz) + 92.45
```

**執行測試（應通過）**：
```bash
pytest tests/test_gen_scenario_scale.py -v --cov=scripts/gen_scenario.py
# EXPECTED: PASSED ✓
```

#### REFACTOR：優化記憶體與效能

```python
# scripts/gen_scenario.py (記憶體優化版)
def generate_scenario_streaming(windows_file: Path, output_file: Path,
                                 mode: str = 'transparent',
                                 chunk_size: int = 1000):
    """串流式場景生成（大型資料集）"""
    import ijson  # 增量 JSON 解析

    # 使用串流解析避免載入整個 JSON
    with windows_file.open('rb') as f:
        windows = ijson.items(f, 'windows.item')

        # 分批處理
        for chunk in chunks(windows, chunk_size):
            process_window_chunk(chunk, output_file, mode)
```

---

### TDD 循環 1.3：指標計算擴展

#### RED：寫失敗測試
```python
# tests/test_metrics_scale.py
def test_calculate_metrics_100_satellites():
    """測試計算 100 衛星場景的指標"""
    scenario_file = Path('results/starlink_100_scenario.json')
    metrics_file = Path('results/starlink_100_metrics.csv')

    calculate_metrics(scenario_file, metrics_file)

    df = pd.read_csv(metrics_file)

    assert len(df) >= 300  # 至少 300 筆記錄
    assert 'sat_id' in df.columns
    assert 'gateway' in df.columns
    assert 'latency_ms' in df.columns
    assert 'throughput_mbps' in df.columns
    assert df['latency_ms'].mean() < 50  # 平均延遲 < 50ms

def test_aggregate_statistics():
    """測試聚合統計"""
    scenario_file = Path('results/starlink_100_scenario.json')
    summary_file = Path('results/starlink_100_summary.json')

    stats = calculate_aggregate_stats(scenario_file, summary_file)

    assert 'latency' in stats
    assert 'throughput' in stats
    assert 'mean_ms' in stats['latency']
    assert 'p95_ms' in stats['latency']
    assert 'p99_ms' in stats['latency']
```

#### GREEN：實作

```python
# scripts/metrics.py (擴展版)
import pandas as pd
import numpy as np

def calculate_aggregate_stats(scenario_file: Path, summary_file: Path) -> dict:
    """計算聚合統計"""
    # 先計算個別指標
    metrics_file = scenario_file.parent / 'temp_metrics.csv'
    calculate_metrics(scenario_file, metrics_file)

    df = pd.read_csv(metrics_file)

    stats = {
        'latency': {
            'mean_ms': df['latency_ms'].mean(),
            'median_ms': df['latency_ms'].median(),
            'p95_ms': df['latency_ms'].quantile(0.95),
            'p99_ms': df['latency_ms'].quantile(0.99),
            'std_ms': df['latency_ms'].std()
        },
        'throughput': {
            'mean_mbps': df['throughput_mbps'].mean(),
            'median_mbps': df['throughput_mbps'].median(),
            'max_mbps': df['throughput_mbps'].max()
        },
        'coverage': {
            'total_contacts': len(df),
            'unique_satellites': df['sat_id'].nunique(),
            'unique_gateways': df['gateway'].nunique()
        }
    }

    with summary_file.open('w') as f:
        json.dump(stats, f, indent=2)

    return stats
```

#### REFACTOR：向量化計算

```python
# scripts/metrics.py (向量化版)
def calculate_metrics_vectorized(scenario_file: Path, metrics_file: Path):
    """向量化指標計算（提升效能）"""
    with scenario_file.open() as f:
        scenario = json.load(f)

    # 提取所有 contact_start 事件
    contacts = [e for e in scenario['events'] if e['type'] == 'contact_start']

    # 轉換為 DataFrame 進行向量化計算
    df = pd.DataFrame(contacts)

    # 向量化計算延遲
    c = 299792.458  # 光速 (km/s)
    df['propagation_delay_ms'] = (df['distance_km'] * 2 / c) * 1000
    df['processing_delay_ms'] = 5.0 if scenario['meta']['mode'] == 'regenerative' else 0.0
    df['latency_ms'] = df['propagation_delay_ms'] + df['processing_delay_ms']

    # 向量化計算吞吐量
    df['throughput_mbps'] = 100.0 - df['free_space_loss_db'] / 10

    # 輸出
    df.to_csv(metrics_file, index=False)
```

---

## 第二優先：多星系整合測試

### 目標
整合 GPS、Iridium、OneWeb、Starlink 多個衛星系統

### TDD 循環 2.1：多 TLE 檔案處理

#### RED：測試
```python
# tests/test_multi_constellation.py
def test_load_multiple_tle_files():
    """測試載入多個 TLE 檔案"""
    tle_files = [
        Path('data/gps.tle'),
        Path('data/iridium_next.tle'),
        Path('data/oneweb.tle'),
        Path('data/starlink_100.tle')
    ]

    all_satellites = load_multi_tle(tle_files)

    assert len(all_satellites) >= 200  # GPS(31) + Iridium(66) + OneWeb(~600) + Starlink(100)
    assert 'constellation' in all_satellites[0]
    assert set(s['constellation'] for s in all_satellites) >= {'GPS', 'Iridium', 'OneWeb', 'Starlink'}

def test_generate_multi_constellation_windows():
    """測試多星系視窗生成"""
    tle_files = [
        Path('data/gps.tle'),
        Path('data/iridium_next.tle')
    ]
    station = {'name': 'TAIPEI', 'lat': 25.033, 'lon': 121.565, 'alt': 50}

    windows = calculate_multi_constellation_passes(
        tle_files, station,
        '2025-10-08T00:00:00Z',
        '2025-10-08T12:00:00Z'
    )

    assert len(windows) >= 100
    assert all('constellation' in w for w in windows)

    # GPS: MEO, 高度 ~20,000 km
    gps_windows = [w for w in windows if w['constellation'] == 'GPS']
    assert all(w['max_elevation'] < 85 for w in gps_windows)  # GPS 較低仰角

    # Iridium: LEO, 高度 ~780 km
    iridium_windows = [w for w in windows if w['constellation'] == 'Iridium']
    assert len(iridium_windows) > len(gps_windows)  # LEO 更頻繁

def test_constellation_specific_parameters():
    """測試星系特定參數"""
    config = load_constellation_config(Path('config/constellation_params.json'))

    assert 'GPS' in config
    assert 'Iridium' in config
    assert config['GPS']['orbit_altitude_km'] == 20200
    assert config['Iridium']['orbit_altitude_km'] == 780
    assert config['Starlink']['frequency_band'] == 'Ku'
```

#### GREEN：實作

```python
# scripts/multi_constellation.py
from enum import Enum

class Constellation(Enum):
    GPS = 'GPS'
    IRIDIUM = 'Iridium'
    ONEWEB = 'OneWeb'
    STARLINK = 'Starlink'

CONSTELLATION_PARAMS = {
    'GPS': {
        'orbit_altitude_km': 20200,
        'orbit_type': 'MEO',
        'frequency_band': 'L',
        'min_elevation_deg': 5.0
    },
    'Iridium': {
        'orbit_altitude_km': 780,
        'orbit_type': 'LEO',
        'frequency_band': 'L',
        'min_elevation_deg': 8.0
    },
    'OneWeb': {
        'orbit_altitude_km': 1200,
        'orbit_type': 'LEO',
        'frequency_band': 'Ku',
        'min_elevation_deg': 15.0
    },
    'Starlink': {
        'orbit_altitude_km': 550,
        'orbit_type': 'LEO',
        'frequency_band': 'Ku',
        'min_elevation_deg': 25.0
    }
}

def identify_constellation(sat_name: str) -> str:
    """根據衛星名稱識別星系"""
    name_upper = sat_name.upper()
    if 'GPS' in name_upper or 'NAVSTAR' in name_upper:
        return 'GPS'
    elif 'IRIDIUM' in name_upper:
        return 'Iridium'
    elif 'ONEWEB' in name_upper:
        return 'OneWeb'
    elif 'STARLINK' in name_upper:
        return 'Starlink'
    else:
        return 'Unknown'

def load_multi_tle(tle_files: list[Path]) -> list[dict]:
    """載入多個 TLE 檔案並標註星系"""
    all_satellites = []

    for tle_file in tle_files:
        satellites = load_tle_file(tle_file)
        for sat in satellites:
            constellation = identify_constellation(sat['name'])
            sat['constellation'] = constellation
            sat['params'] = CONSTELLATION_PARAMS.get(constellation, {})
            all_satellites.append(sat)

    return all_satellites

def calculate_multi_constellation_passes(tle_files: list[Path],
                                          station: dict,
                                          start_time: str,
                                          end_time: str) -> list[dict]:
    """計算多星系可見視窗（應用星系特定參數）"""
    all_windows = []

    for tle_file in tle_files:
        # 識別星系
        satellites = load_tle_file(tle_file)
        if not satellites:
            continue

        constellation = identify_constellation(satellites[0]['name'])
        params = CONSTELLATION_PARAMS.get(constellation, {})
        min_elev = params.get('min_elevation_deg', 10.0)

        # 計算視窗
        windows = calculate_passes(
            tle_file, station, start_time, end_time,
            min_elevation=min_elev
        )

        # 標註星系資訊
        for w in windows:
            w['constellation'] = constellation
            w['orbit_altitude_km'] = params.get('orbit_altitude_km', 0)

        all_windows.extend(windows)

    return all_windows
```

#### REFACTOR：配置檔案化

```json
// config/constellation_params.json
{
  "GPS": {
    "orbit_altitude_km": 20200,
    "orbit_type": "MEO",
    "frequency_band": "L",
    "frequency_ghz": 1.575,
    "min_elevation_deg": 5.0,
    "typical_pass_duration_min": 240
  },
  "Iridium": {
    "orbit_altitude_km": 780,
    "orbit_type": "LEO",
    "frequency_band": "L",
    "frequency_ghz": 1.621,
    "min_elevation_deg": 8.0,
    "typical_pass_duration_min": 9
  },
  "OneWeb": {
    "orbit_altitude_km": 1200,
    "orbit_type": "LEO",
    "frequency_band": "Ku",
    "frequency_ghz": 12.0,
    "min_elevation_deg": 15.0,
    "typical_pass_duration_min": 7
  },
  "Starlink": {
    "orbit_altitude_km": 550,
    "orbit_type": "LEO",
    "frequency_band": "Ku",
    "frequency_ghz": 12.0,
    "min_elevation_deg": 25.0,
    "typical_pass_duration_min": 4
  }
}
```

---

### TDD 循環 2.2：星系間比較

#### RED：測試
```python
# tests/test_constellation_comparison.py
def test_compare_constellations_coverage():
    """比較不同星系的覆蓋能力"""
    results = compare_constellation_coverage(
        constellations=['GPS', 'Iridium', 'Starlink'],
        station={'name': 'TAIPEI', 'lat': 25.033, 'lon': 121.565, 'alt': 50},
        duration_hours=24
    )

    assert 'GPS' in results
    assert 'Iridium' in results
    assert 'Starlink' in results

    # Starlink 應有最高覆蓋率（低軌密集星系）
    assert results['Starlink']['coverage_percent'] > results['GPS']['coverage_percent']
    assert results['Starlink']['avg_pass_count_per_hour'] > 10

def test_latency_comparison():
    """比較星系延遲差異"""
    latencies = compare_constellation_latency()

    # LEO 延遲應顯著低於 MEO
    assert latencies['Starlink']['mean_ms'] < 25
    assert latencies['Iridium']['mean_ms'] < 50
    assert latencies['GPS']['mean_ms'] > 100
```

#### GREEN：實作

```python
# scripts/constellation_comparison.py
def compare_constellation_coverage(constellations: list[str],
                                    station: dict,
                                    duration_hours: int = 24) -> dict:
    """比較星系覆蓋能力"""
    from datetime import datetime, timedelta

    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=duration_hours)

    results = {}

    for const in constellations:
        tle_file = Path(f'data/{const.lower()}.tle')
        if not tle_file.exists():
            continue

        windows = calculate_passes(
            tle_file, station,
            start.isoformat(), end.isoformat()
        )

        # 計算覆蓋率
        total_coverage_seconds = sum(
            (parse_dt(w['los']) - parse_dt(w['aos'])).total_seconds()
            for w in windows
        )
        coverage_percent = (total_coverage_seconds / (duration_hours * 3600)) * 100

        results[const] = {
            'total_passes': len(windows),
            'coverage_percent': coverage_percent,
            'avg_pass_count_per_hour': len(windows) / duration_hours,
            'total_coverage_hours': total_coverage_seconds / 3600
        }

    return results
```

---

## 第三優先：覆蓋範圍視覺化

### 目標
提供地圖與時序圖視覺化工具

### TDD 循環 3.1：覆蓋地圖生成

#### RED：測試
```python
# tests/test_visualization.py
def test_generate_coverage_map():
    """測試生成覆蓋地圖"""
    windows_file = Path('data/starlink_100_windows.json')
    map_file = Path('results/coverage_map.html')

    generate_coverage_map(windows_file, map_file)

    assert map_file.exists()
    content = map_file.read_text()
    assert 'leaflet' in content.lower()  # 使用 Leaflet.js
    assert 'HSINCHU' in content  # 包含地面站標記

def test_generate_timeline_chart():
    """測試生成時序圖"""
    windows_file = Path('data/starlink_100_windows.json')
    chart_file = Path('results/timeline.html')

    generate_timeline_chart(windows_file, chart_file)

    assert chart_file.exists()
    content = chart_file.read_text()
    assert 'plotly' in content.lower()  # 使用 Plotly

def test_export_kml_for_google_earth():
    """測試匯出 KML 格式（Google Earth）"""
    windows_file = Path('data/starlink_100_windows.json')
    kml_file = Path('results/coverage.kml')

    export_kml(windows_file, kml_file)

    assert kml_file.exists()
    content = kml_file.read_text()
    assert '<?xml version' in content
    assert '<kml' in content
```

#### GREEN：實作

```python
# scripts/visualization.py
import folium
import plotly.graph_objects as go
from simplekml import Kml

def generate_coverage_map(windows_file: Path, map_file: Path):
    """生成交互式覆蓋地圖（Leaflet）"""
    with windows_file.open() as f:
        data = json.load(f)
    windows = data['windows']

    # 建立地圖（台灣中心）
    m = folium.Map(location=[23.5, 121.0], zoom_start=7)

    # 添加地面站標記
    stations = load_ground_stations(Path('data/taiwan_ground_stations.json'))
    for station in stations:
        folium.Marker(
            location=[station['lat'], station['lon']],
            popup=f"{station['name']}<br>Alt: {station['alt']}m",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)

    # 添加視窗覆蓋範圍（圓圈）
    for w in windows[:100]:  # 限制顯示數量避免過載
        # 從地面站位置畫覆蓋圓
        station = next(s for s in stations if s['name'] == w['station'])
        folium.Circle(
            location=[station['lat'], station['lon']],
            radius=500000,  # 500 km 覆蓋半徑
            color='blue',
            fill=True,
            fillOpacity=0.1,
            popup=f"{w['sat_id']}<br>{w['aos']}"
        ).add_to(m)

    # 儲存
    m.save(str(map_file))

def generate_timeline_chart(windows_file: Path, chart_file: Path):
    """生成視窗時序圖（Plotly Gantt Chart）"""
    with windows_file.open() as f:
        data = json.load(f)
    windows = data['windows']

    # 準備資料
    df = []
    for w in windows:
        df.append({
            'Task': w['sat_id'],
            'Start': w['aos'],
            'Finish': w['los'],
            'Resource': w['station']
        })

    # 建立 Gantt 圖
    fig = go.Figure()

    for i, row in enumerate(df[:50]):  # 限制 50 筆避免過載
        fig.add_trace(go.Bar(
            x=[row['Finish'], row['Start']],
            y=[row['Task']],
            orientation='h',
            name=row['Resource']
        ))

    fig.update_layout(
        title='衛星可見視窗時序圖',
        xaxis_title='時間',
        yaxis_title='衛星 ID'
    )

    fig.write_html(str(chart_file))

def export_kml(windows_file: Path, kml_file: Path):
    """匯出 KML 格式供 Google Earth 使用"""
    with windows_file.open() as f:
        data = json.load(f)
    windows = data['windows']

    kml = Kml()

    # 添加地面站
    stations = load_ground_stations(Path('data/taiwan_ground_stations.json'))
    for station in stations:
        kml.newpoint(
            name=station['name'],
            coords=[(station['lon'], station['lat'], station['alt'])]
        )

    # 添加視窗路徑（簡化為點）
    for w in windows[:100]:
        pnt = kml.newpoint(name=f"{w['sat_id']} @ {w['aos']}")
        pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'

    kml.save(str(kml_file))
```

#### REFACTOR：互動式儀表板

```python
# scripts/dashboard.py
import dash
from dash import dcc, html
import plotly.express as px

def create_dashboard(windows_file: Path, port: int = 8050):
    """建立即時互動式儀表板"""
    app = dash.Dash(__name__)

    # 載入資料
    with windows_file.open() as f:
        data = json.load(f)
    windows = data['windows']

    # 統計
    df_stats = pd.DataFrame([
        {'Metric': 'Total Windows', 'Value': len(windows)},
        {'Metric': 'Unique Satellites', 'Value': len(set(w['sat_id'] for w in windows))},
        {'Metric': 'Unique Stations', 'Value': len(set(w['station'] for w in windows))}
    ])

    # Layout
    app.layout = html.Div([
        html.H1('TASA SatNet 覆蓋儀表板'),
        dcc.Graph(figure=px.bar(df_stats, x='Metric', y='Value')),
        dcc.Graph(id='timeline-chart'),
        dcc.Graph(id='coverage-map')
    ])

    app.run_server(debug=True, port=port)
```

---

## 整合測試策略

### 端到端測試

```python
# tests/test_end_to_end.py
def test_full_pipeline_starlink_100():
    """端到端測試：Starlink 100 衛星完整管線"""
    # Step 1: 提取 TLE 子集
    extract_starlink_subset(
        Path('data/starlink.tle'),
        Path('data/starlink_100.tle'),
        100
    )

    # Step 2: 生成視窗
    generate_tle_windows(
        Path('data/starlink_100.tle'),
        Path('data/taiwan_ground_stations.json'),
        Path('data/starlink_100_windows.json')
    )

    # Step 3: 生成場景
    generate_scenario(
        Path('data/starlink_100_windows.json'),
        Path('results/starlink_100_scenario.json')
    )

    # Step 4: 計算指標
    calculate_metrics(
        Path('results/starlink_100_scenario.json'),
        Path('results/starlink_100_metrics.csv')
    )

    # Step 5: 排程
    schedule_beams(
        Path('results/starlink_100_scenario.json'),
        Path('results/starlink_100_schedule.csv')
    )

    # 驗證結果
    assert Path('results/starlink_100_metrics.csv').exists()
    assert Path('results/starlink_100_schedule.csv').exists()

    # 驗證指標
    df = pd.read_csv('results/starlink_100_metrics.csv')
    assert df['latency_ms'].mean() < 30  # Starlink 低延遲
    assert len(df) >= 300

def test_multi_constellation_integration():
    """整合測試：多星系場景"""
    constellations = ['gps', 'iridium_next', 'starlink_100']

    all_windows = []
    for const in constellations:
        tle_file = Path(f'data/{const}.tle')
        windows_file = Path(f'data/{const}_windows.json')

        generate_tle_windows(tle_file, stations_file, windows_file)

        with windows_file.open() as f:
            data = json.load(f)
        all_windows.extend(data['windows'])

    # 合併場景
    merged_file = Path('results/multi_constellation_windows.json')
    with merged_file.open('w') as f:
        json.dump({'windows': all_windows}, f)

    # 生成比較報告
    generate_comparison_report(merged_file, Path('results/comparison.html'))

    assert Path('results/comparison.html').exists()
```

---

## 檔案組織結構

```
tasa-satnet-pipeline/
├── scripts/
│   ├── extract_starlink_subset.py       # 新增：TLE 子集提取
│   ├── tle_windows.py                   # 擴展：支援大規模計算
│   ├── multi_constellation.py           # 新增：多星系處理
│   ├── constellation_comparison.py      # 新增：星系比較
│   ├── visualization.py                 # 新增：視覺化工具
│   ├── dashboard.py                     # 新增：互動式儀表板
│   └── ... (現有腳本)
│
├── tests/
│   ├── test_tle_windows.py              # 新增：視窗生成測試
│   ├── test_gen_scenario_scale.py       # 新增：大規模場景測試
│   ├── test_metrics_scale.py            # 新增：大規模指標測試
│   ├── test_multi_constellation.py      # 新增：多星系測試
│   ├── test_constellation_comparison.py # 新增：星系比較測試
│   ├── test_visualization.py            # 新增：視覺化測試
│   └── test_end_to_end.py               # 新增：端到端測試
│
├── data/
│   ├── starlink_100.tle                 # 新增：100 衛星子集
│   ├── starlink_100_windows.json        # 新增：視窗資料
│   ├── multi_constellation_windows.json # 新增：多星系視窗
│   └── ... (現有資料)
│
├── config/
│   ├── constellation_params.json        # 新增：星系參數配置
│   └── ... (現有配置)
│
├── results/
│   ├── starlink_100/                    # 新增：Starlink 100 結果
│   │   ├── scenario.json
│   │   ├── metrics.csv
│   │   ├── summary.json
│   │   └── schedule.csv
│   ├── multi_constellation/             # 新增：多星系結果
│   │   ├── comparison.html
│   │   └── merged_metrics.csv
│   └── visualizations/                  # 新增：視覺化輸出
│       ├── coverage_map.html
│       ├── timeline.html
│       └── coverage.kml
│
└── docs/
    ├── TDD-NEXT-PHASE-PLAN.md           # 本文件
    └── ... (現有文檔)
```

---

## 測試優先順序總表

| 優先級 | 功能模組 | 測試案例 | 預期工時 | 依賴 |
|--------|----------|----------|----------|------|
| **P0** | TLE 子集提取 | `test_extract_starlink_subset` | 2h | 無 |
| **P0** | 視窗生成（100 衛星） | `test_calculate_passes_for_100_satellites` | 4h | P0 |
| **P0** | 效能測試 | `test_performance_100_satellites_under_30_seconds` | 2h | P0 |
| **P1** | 並行處理 | `test_parallel_station_processing` | 3h | P0 |
| **P1** | 場景生成擴展 | `test_generate_scenario_100_satellites` | 3h | P0 |
| **P1** | 指標計算擴展 | `test_calculate_metrics_100_satellites` | 3h | P1 |
| **P2** | 多 TLE 載入 | `test_load_multiple_tle_files` | 2h | P0 |
| **P2** | 多星系視窗 | `test_generate_multi_constellation_windows` | 4h | P2 |
| **P2** | 星系參數 | `test_constellation_specific_parameters` | 2h | P2 |
| **P3** | 星系比較 | `test_compare_constellations_coverage` | 3h | P2 |
| **P3** | 延遲比較 | `test_latency_comparison` | 2h | P2 |
| **P4** | 覆蓋地圖 | `test_generate_coverage_map` | 4h | P1 |
| **P4** | 時序圖 | `test_generate_timeline_chart` | 3h | P1 |
| **P4** | KML 匯出 | `test_export_kml_for_google_earth` | 2h | P1 |
| **P5** | 端到端測試 | `test_full_pipeline_starlink_100` | 3h | P1, P2 |
| **P5** | 多星系整合 | `test_multi_constellation_integration` | 4h | P2, P3 |

**總工時估計**: 46 小時（約 1 週全職工作）

---

## 實作步驟時序

### 第 1 天（8h）
1. **上午（4h）**: 實作 TLE 子集提取 + 視窗生成基礎
   - `extract_starlink_subset.py`
   - `tle_windows.py` 擴展
   - 測試 P0 優先級

2. **下午（4h）**: 效能優化 + 並行處理
   - 向量化計算
   - 多核心並行
   - 測試 P1 優先級（並行）

### 第 2 天（8h）
1. **上午（4h）**: 場景生成擴展
   - `gen_scenario.py` 擴展
   - 鏈路預算計算
   - 測試 P1 優先級（場景）

2. **下午（4h）**: 指標計算擴展
   - `metrics.py` 擴展
   - 聚合統計
   - 測試 P1 優先級（指標）

### 第 3 天（8h）
1. **上午（4h）**: 多星系基礎
   - `multi_constellation.py`
   - 星系識別與參數
   - 測試 P2 優先級

2. **下午（4h）**: 多星系視窗生成
   - 整合多 TLE 檔案
   - 星系特定參數應用
   - 測試 P2 優先級（視窗）

### 第 4 天（8h）
1. **上午（4h）**: 星系比較功能
   - `constellation_comparison.py`
   - 覆蓋率計算
   - 測試 P3 優先級

2. **下午（4h）**: 視覺化基礎
   - `visualization.py`
   - Folium 地圖
   - 測試 P4 優先級（地圖）

### 第 5 天（8h）
1. **上午（4h）**: 視覺化完善
   - Plotly 時序圖
   - KML 匯出
   - 測試 P4 優先級（時序圖、KML）

2. **下午（4h）**: 端到端整合
   - 整合測試
   - 效能驗證
   - 測試 P5 優先級

### 第 6 天（8h）
1. **全天（8h）**: 優化與文檔
   - 程式碼重構
   - 效能調優
   - 文檔更新
   - 測試覆蓋率確保 >90%

---

## 驗證標準

### 功能驗證
- [x] **P0**: 100 衛星視窗生成成功率 100%
- [x] **P0**: 計算時間 < 30 秒
- [x] **P1**: 場景生成包含所有必要欄位
- [x] **P1**: 指標計算準確性驗證
- [x] **P2**: 多星系資料正確載入與標註
- [x] **P3**: 星系比較結果符合物理預期
- [x] **P4**: 視覺化檔案正確生成

### 效能驗證
- [x] **記憶體使用** < 2 GB（100 衛星場景）
- [x] **CPU 使用** < 80%（多核心並行）
- [x] **磁碟 I/O** 優化（串流處理大檔案）

### 測試覆蓋率
- [x] **單元測試** > 90%
- [x] **整合測試** > 80%
- [x] **端到端測試** 100% 通過

---

## 依賴套件

### 新增需求
```txt
# requirements.txt 新增

# 軌道計算
skyfield>=1.46
sgp4>=2.21

# 視覺化
folium>=0.14.0
plotly>=5.14.0
dash>=2.9.0
simplekml>=1.3.6

# 資料處理加速
numpy>=1.24.0
pandas>=2.0.0
ijson>=3.2.0  # 串流 JSON 解析

# 多核心處理
multiprocessing-logging>=0.3.4
```

### 安裝指令
```bash
pip install -r requirements.txt
```

---

## 潛在風險與緩解

### 風險 1：TLE 資料過時
**緩解**：
- 建立自動更新機制（每日從 CelesTrak/Space-Track 下載）
- TLE 時效性檢查（警告超過 7 天的 TLE）

### 風險 2：計算效能瓶頸
**緩解**：
- 使用 C 擴展（Skyfield 已優化）
- GPU 加速（CUDA，若需要）
- 分散式計算（Dask）

### 風險 3：記憶體不足（大型星系）
**緩解**：
- 串流處理（ijson）
- 分批計算
- 記憶體映射檔案

### 風險 4：視覺化效能（大量資料點）
**緩解**：
- 資料採樣（顯示前 N 筆）
- WebGL 渲染（Plotly）
- 伺服器端渲染

---

## 成功指標

### 量化指標
- ✅ **100 衛星場景** 成功生成率 100%
- ✅ **計算時間** < 30 秒
- ✅ **測試覆蓋率** > 90%
- ✅ **多星系整合** 4 個星系成功整合
- ✅ **視覺化** 3 種格式（HTML, KML, Dashboard）

### 質化指標
- ✅ 程式碼可讀性與可維護性
- ✅ 文檔完整性
- ✅ 錯誤處理與日誌
- ✅ 使用者體驗（CLI 友善、進度顯示）

---

## 後續規劃（Phase 2+）

### 進階功能
1. **即時追蹤**：整合 SGP4 即時軌道預測
2. **干擾分析**：計算同頻干擾
3. **容量規劃**：多波束分配優化
4. **成本估算**：鏈路預算與設備成本
5. **AI 優化**：機器學習預測最佳接入策略

### 基礎設施
1. **CI/CD**：GitHub Actions 自動測試與部署
2. **容器化**：Docker Compose 多服務編排
3. **雲端部署**：K8s 生產環境
4. **資料庫**：時序資料庫（InfluxDB）儲存歷史視窗

---

## 附錄：測試資料準備

### A.1 Starlink 100 衛星子集
```bash
# 從完整 Starlink TLE 提取 100 顆
python scripts/extract_starlink_subset.py \
  --input data/starlink.tle \
  --output data/starlink_100.tle \
  --count 100
```

### A.2 台灣地面站配置
```json
// data/taiwan_ground_stations.json
{
  "ground_stations": [
    {"name": "TAIPEI", "lat": 25.033, "lon": 121.565, "alt": 50},
    {"name": "HSINCHU", "lat": 24.7868, "lon": 120.9967, "alt": 100},
    {"name": "TAICHUNG", "lat": 24.1477, "lon": 120.6736, "alt": 100},
    {"name": "TAINAN", "lat": 22.9908, "lon": 120.2133, "alt": 50},
    {"name": "KAOHSIUNG", "lat": 22.6273, "lon": 120.3014, "alt": 20},
    {"name": "PINGTUNG", "lat": 22.6730, "lon": 120.4953, "alt": 30}
  ]
}
```

### A.3 測試時間範圍
```python
# 標準測試時間
START_TIME = '2025-10-08T00:00:00Z'
END_TIME_6H = '2025-10-08T06:00:00Z'    # 短期測試
END_TIME_12H = '2025-10-08T12:00:00Z'   # 中期測試
END_TIME_24H = '2025-10-09T00:00:00Z'   # 長期測試
```

---

## 結論

本 TDD 計劃提供了結構化、可測試、可追蹤的開發路徑，確保：

1. **品質保證**：每個功能都有對應的測試案例
2. **進度可控**：明確的優先級與時序
3. **風險可控**：識別並緩解潛在問題
4. **可擴展性**：為後續功能預留介面

**下一步**：開始執行 P0 優先級測試（TLE 子集提取與視窗生成）

---

**文件版本**: 1.0
**最後更新**: 2025-10-08
**作者**: TASA SatNet Pipeline Team
