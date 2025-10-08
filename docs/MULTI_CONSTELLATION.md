# Multi-Constellation Integration Tool

**完整的多星系整合處理工具**，支援 GPS、Iridium、OneWeb、Starlink 等多種衛星星系的合併、識別、視窗計算、衝突檢測與優先排程。

---

## 🎯 功能概覽

### 核心功能

1. **TLE 合併** - 整合多個 TLE 檔案，自動去重
2. **星系識別** - 自動辨識衛星所屬星系
3. **視窗計算** - 計算混合星系的通聯視窗
4. **衝突檢測** - 偵測頻段與時間衝突
5. **優先排程** - 基於優先級的排程演算法

### 支援的衛星星系

| 星系 | 頻段 | 優先級 | 典型用途 |
|------|------|--------|----------|
| **GPS** | L-band | 高 | 導航定位 |
| **Iridium** | Ka-band | 中 | 語音/數據通訊 |
| **OneWeb** | Ku-band | 低 | 商業寬頻 |
| **Starlink** | Ka-band | 低 | 商業寬頻 |
| **Globalstar** | L-band | 中 | 衛星電話 |
| **O3B** | Ka-band | 中 | 商業回程 |

---

## 🚀 快速開始

### 基本使用

```bash
# 1. 合併 TLE 檔案
python scripts/multi_constellation.py merge \
  data/gps.tle data/iridium.tle data/oneweb.tle \
  -o data/merged.tle

# 2. 計算通聯視窗
python scripts/multi_constellation.py windows \
  data/merged.tle \
  --stations '{"name":"TASA-1","lat":25.033,"lon":121.565,"alt":0}' \
  --stations '{"name":"TASA-2","lat":24.787,"lon":120.997,"alt":0}' \
  -o data/windows.json

# 3. 偵測衝突
python scripts/multi_constellation.py conflicts \
  data/windows.json \
  -o data/conflicts.json

# 4. 優先排程
python scripts/multi_constellation.py schedule \
  data/windows.json \
  -o data/schedule.json
```

### 完整管線

執行完整處理管線（合併 → 計算 → 衝突 → 排程）：

```bash
python scripts/multi_constellation.py pipeline \
  data/gps.tle data/iridium.tle data/starlink.tle \
  --stations '{"name":"TASA-1","lat":25.033,"lon":121.565,"alt":0}' \
  --start "2024-10-06T00:00:00Z" \
  --end "2024-10-07T00:00:00Z" \
  --min-elevation 10.0 \
  -o data/results.json
```

---

## 📋 詳細用法

### 1. TLE 合併 (merge)

合併多個 TLE 檔案，自動去除重複衛星：

```bash
python scripts/multi_constellation.py merge \
  data/constellation1.tle \
  data/constellation2.tle \
  data/constellation3.tle \
  -o data/merged.tle
```

**輸出範例**：
```
Merged 763 satellites
Constellations: GPS, Iridium, OneWeb
Duplicates removed: 12
Output: data/merged.tle
```

**功能特點**：
- 基於 NORAD ID 自動去重
- 保持 TLE 三行格式
- 自動識別星系類型
- 統計資訊輸出

---

### 2. 視窗計算 (windows)

計算混合星系的通聯視窗：

```bash
python scripts/multi_constellation.py windows \
  data/merged.tle \
  --stations '{"name":"TASA-Taipei","lat":25.033,"lon":121.565,"alt":0}' \
  --stations '{"name":"TASA-Taichung","lat":24.787,"lon":120.997,"alt":0}' \
  --start "2024-10-08T00:00:00Z" \
  --end "2024-10-09T00:00:00Z" \
  --min-elevation 10.0 \
  -o data/windows.json
```

**參數說明**：
- `--stations`: 地面站位置（JSON 格式，可多個）
- `--start`: 開始時間（ISO 8601 格式，預設為當前時間）
- `--end`: 結束時間（預設為開始時間 + 24 小時）
- `--min-elevation`: 最小仰角（度，預設 10.0）

**輸出格式**：
```json
{
  "meta": {
    "constellations": ["GPS", "Iridium", "OneWeb"],
    "total_satellites": 763,
    "ground_stations": ["TASA-Taipei", "TASA-Taichung"],
    "start": "2024-10-08T00:00:00Z",
    "end": "2024-10-09T00:00:00Z",
    "count": 1543
  },
  "windows": [
    {
      "satellite": "GPS BIIA-10 (PRN 32)",
      "constellation": "GPS",
      "frequency_band": "L-band",
      "priority": "high",
      "ground_station": "TASA-Taipei",
      "start": "2024-10-08T02:15:30Z",
      "end": "2024-10-08T02:27:45Z",
      "max_elevation": 67.8,
      "duration_sec": 735
    }
  ]
}
```

---

### 3. 衝突檢測 (conflicts)

偵測頻段與時間衝突：

```bash
python scripts/multi_constellation.py conflicts \
  data/windows.json \
  -o data/conflicts.json
```

**衝突條件**：
1. 相同地面站
2. 相同頻段
3. 時間重疊

**輸出格式**：
```json
{
  "conflicts": [
    {
      "type": "frequency_conflict",
      "window1": "IRIDIUM 102",
      "window2": "STARLINK-1007",
      "constellation1": "Iridium",
      "constellation2": "Starlink",
      "frequency_band": "Ka-band",
      "ground_station": "TASA-Taipei",
      "overlap_start": "2024-10-08T10:05:00Z",
      "overlap_end": "2024-10-08T10:10:00Z"
    }
  ],
  "count": 12
}
```

**衝突類型**：
- `frequency_conflict`: 相同頻段時間重疊

---

### 4. 優先排程 (schedule)

基於優先級的排程演算法：

```bash
python scripts/multi_constellation.py schedule \
  data/windows.json \
  -o data/schedule.json
```

**排程規則**：
1. 按優先級排序（高 → 中 → 低）
2. 同優先級按時間先後
3. 衝突時保留高優先級視窗
4. 記錄拒絕原因

**輸出格式**：
```json
{
  "scheduled": [
    {
      "satellite": "GPS BIIA-10 (PRN 32)",
      "constellation": "GPS",
      "frequency_band": "L-band",
      "priority": "high",
      "ground_station": "TASA-Taipei",
      "start": "2024-10-08T02:15:30Z",
      "end": "2024-10-08T02:27:45Z"
    }
  ],
  "rejected": [
    {
      "satellite": "STARLINK-1007",
      "constellation": "Starlink",
      "priority": "low",
      "reason": "Frequency conflict with higher priority window",
      "conflict_with": "IRIDIUM 102"
    }
  ]
}
```

---

### 5. 完整管線 (pipeline)

一次執行所有步驟：

```bash
python scripts/multi_constellation.py pipeline \
  data/gps.tle data/iridium.tle data/oneweb.tle data/starlink.tle \
  --stations '{"name":"TASA-1","lat":25.033,"lon":121.565,"alt":0}' \
  --stations '{"name":"TASA-2","lat":24.787,"lon":120.997,"alt":0}' \
  --start "2024-10-08T00:00:00Z" \
  --end "2024-10-09T00:00:00Z" \
  --min-elevation 10.0 \
  -o data/results.json
```

**執行步驟**：
1. 合併所有 TLE 檔案
2. 計算通聯視窗
3. 偵測衝突
4. 優先排程
5. 輸出完整結果

**輸出格式**：
```json
{
  "meta": {
    "constellations": ["GPS", "Iridium", "OneWeb", "Starlink"],
    "total_satellites": 986,
    "ground_stations": ["TASA-1", "TASA-2"],
    "conflicts": 45,
    "scheduled": 789,
    "rejected": 197
  },
  "windows": [...],
  "conflicts": [...],
  "schedule": {
    "scheduled": [...],
    "rejected": [...]
  }
}
```

---

## 🔬 技術細節

### 星系識別演算法

使用正規表達式匹配衛星名稱：

```python
CONSTELLATION_PATTERNS = {
    'GPS': [r'GPS', r'NAVSTAR', r'PRN\s+\d+'],
    'Iridium': [r'IRIDIUM'],
    'OneWeb': [r'ONEWEB'],
    'Starlink': [r'STARLINK'],
    # ...
}
```

### 頻段映射

| 頻段 | 頻率範圍 | 星系 |
|------|----------|------|
| **L-band** | 1-2 GHz | GPS, Globalstar |
| **Ku-band** | 12-18 GHz | OneWeb |
| **Ka-band** | 26.5-40 GHz | Iridium, Starlink, O3B |

### 優先級規則

```python
PRIORITY_LEVELS = {
    'GPS': 'high',        # 導航關鍵
    'Iridium': 'medium',  # 商業語音/數據
    'OneWeb': 'low',      # 商業寬頻
    'Starlink': 'low',    # 商業寬頻
}
```

### 衝突檢測邏輯

```python
def has_conflict(window1, window2):
    # 1. 檢查是否相同地面站
    if window1.station != window2.station:
        return False

    # 2. 檢查是否相同頻段
    if window1.frequency_band != window2.frequency_band:
        return False

    # 3. 檢查時間是否重疊
    if window1.end <= window2.start or window2.end <= window1.start:
        return False

    return True  # 有衝突
```

---

## 🧪 測試

### 執行測試

```bash
# 執行所有測試
pytest tests/test_multi_constellation.py -v

# 測試覆蓋率
pytest tests/test_multi_constellation.py --cov=scripts.multi_constellation

# 執行特定測試
pytest tests/test_multi_constellation.py::TestTLEMerging -v
pytest tests/test_multi_constellation.py::TestConflictDetection -v
```

### 測試覆蓋

- ✅ TLE 合併功能（4 tests）
- ✅ 星系識別（6 tests）
- ✅ 頻段映射（5 tests）
- ✅ 優先級設定（4 tests）
- ✅ 視窗計算（4 tests）
- ✅ 衝突檢測（4 tests）
- ✅ 優先排程（4 tests）
- ✅ 輸出格式（3 tests）

**總計**: 34 tests, 100% passing

---

## 📊 效能指標

### 處理速度

| 資料規模 | 衛星數 | 視窗數 | 處理時間 |
|---------|--------|--------|----------|
| 小型 | 10 | 100 | ~1 秒 |
| 中型 | 100 | 1,000 | ~10 秒 |
| 大型 | 1,000 | 10,000 | ~90 秒 |

### 記憶體使用

- TLE 合併: ~10 MB / 1000 satellites
- 視窗計算: ~50 MB / 10000 windows
- 衝突檢測: ~20 MB / 10000 windows

---

## 🔧 進階用法

### Python API

```python
from scripts.multi_constellation import (
    merge_tle_files,
    identify_constellation,
    calculate_mixed_windows,
    detect_conflicts,
    prioritize_scheduling
)
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 1. 合併 TLE
stats = merge_tle_files(
    [Path('gps.tle'), Path('iridium.tle')],
    Path('merged.tle')
)
print(f"Merged {stats['total_satellites']} satellites")

# 2. 計算視窗
stations = [
    {"name": "TASA-1", "lat": 25.033, "lon": 121.565, "alt": 0}
]
start = datetime(2024, 10, 8, 0, 0, 0, tzinfo=timezone.utc)
end = start + timedelta(days=1)

result = calculate_mixed_windows(
    Path('merged.tle'), stations, start, end, min_elevation=10.0
)
print(f"Calculated {result['meta']['count']} windows")

# 3. 偵測衝突
from scripts.multi_constellation import FREQUENCY_BANDS
conflicts = detect_conflicts(result['windows'], FREQUENCY_BANDS)
print(f"Found {len(conflicts)} conflicts")

# 4. 優先排程
from scripts.multi_constellation import PRIORITY_LEVELS
schedule = prioritize_scheduling(result['windows'], PRIORITY_LEVELS)
print(f"Scheduled: {len(schedule['scheduled'])}")
print(f"Rejected: {len(schedule['rejected'])}")
```

### 自訂星系

```python
# 新增自訂星系
from scripts.multi_constellation import (
    CONSTELLATION_PATTERNS,
    FREQUENCY_BANDS,
    PRIORITY_LEVELS
)

# 定義新星系
CONSTELLATION_PATTERNS['MyConstellation'] = [r'MYSAT']
FREQUENCY_BANDS['MyConstellation'] = 'X-band'
PRIORITY_LEVELS['MyConstellation'] = 'high'
```

### 地面站配置

```python
# 多個地面站
stations = [
    {
        "name": "TASA-Taipei",
        "lat": 25.0330,
        "lon": 121.5654,
        "alt": 0  # meters
    },
    {
        "name": "TASA-Kaohsiung",
        "lat": 22.6273,
        "lon": 120.3014,
        "alt": 10
    },
    {
        "name": "TASA-Hualien",
        "lat": 23.9871,
        "lon": 121.6015,
        "alt": 0
    }
]
```

---

## 🐛 常見問題

### Q1: 為什麼計算不到視窗？

**可能原因**：
1. TLE 時期太舊或太新
2. 地面站位置不正確
3. 最小仰角設定太高
4. 時間範圍太短

**解決方法**：
```bash
# 降低最小仰角
--min-elevation 5.0

# 延長計算時間
--end "2024-10-10T00:00:00Z"

# 使用 TLE 時期附近的時間
--start "2024-10-06T00:00:00Z"
```

### Q2: 衝突太多怎麼辦？

**解決策略**：
1. 增加地面站數量
2. 使用不同頻段的衛星
3. 調整優先級設定
4. 分時段處理

### Q3: 如何處理大型 TLE 檔案？

**優化建議**：
```python
# 增加計算步長
step_seconds=120  # 從 60 秒增加到 120 秒

# 減少計算範圍
end_time = start_time + timedelta(hours=12)  # 從 24 小時減少到 12 小時
```

---

## 📚 相關文檔

- [TLE 處理器](../scripts/tle_processor.py)
- [OASIS Log 解析](../scripts/parse_oasis_log.py)
- [排程器](../scripts/scheduler.py)
- [測試套件](../tests/test_multi_constellation.py)

---

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

### 開發流程

1. Fork 本專案
2. 創建功能分支
3. 撰寫測試
4. 實作功能
5. 通過所有測試
6. 提交 PR

---

## 📄 授權

本專案採用 MIT 授權條款。

---

**Made with ❤️ for multi-constellation satellite operations**
