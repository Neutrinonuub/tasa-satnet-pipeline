# Multi-Constellation Integration Tool

**Version**: 1.0.0
**Status**: ✅ Production Ready (34/34 tests passing)
**Coverage**: 58% (core functionality fully tested)

---

## 概覽

完整的多星系衛星整合處理工具，支援 GPS、Iridium、OneWeb、Starlink 等多種衛星星系的自動化處理。

### 主要功能

- ✅ **TLE 合併** - 智能合併多個 TLE 檔案，自動去重
- ✅ **星系識別** - 正規表達式自動識別衛星星系
- ✅ **視窗計算** - 基於 SGP4 計算混合星系通聯視窗
- ✅ **衝突檢測** - 頻段與時間重疊檢測
- ✅ **優先排程** - 基於優先級的智能排程演算法
- ✅ **CLI 介面** - 完整命令列工具支援
- ✅ **Python API** - 可程式化整合

---

## 快速開始

### 安裝需求

```bash
pip install sgp4 numpy
```

### 基本用法

```bash
# 完整管線處理
python scripts/multi_constellation.py pipeline \
  data/gps.tle data/iridium.tle data/starlink.tle \
  --stations '{"name":"TASA-1","lat":25.033,"lon":121.565,"alt":0}' \
  --start "2024-10-08T00:00:00Z" \
  --end "2024-10-09T00:00:00Z" \
  -o results.json
```

### 範例程式

```bash
# 執行完整範例
python examples/multi_constellation_example.py
```

---

## 支援的星系

| 星系 | 識別模式 | 頻段 | 優先級 | 用途 |
|------|----------|------|--------|------|
| **GPS** | GPS, NAVSTAR, PRN | L-band | 高 | 導航定位 |
| **Iridium** | IRIDIUM | Ka-band | 中 | 語音/數據 |
| **OneWeb** | ONEWEB | Ku-band | 低 | 商業寬頻 |
| **Starlink** | STARLINK | Ka-band | 低 | 商業寬頻 |
| **Globalstar** | GLOBALSTAR | L-band | 中 | 衛星電話 |
| **O3B** | O3B | Ka-band | 中 | 商業回程 |

---

## CLI 命令

### 1. merge - 合併 TLE 檔案

```bash
python scripts/multi_constellation.py merge \
  file1.tle file2.tle file3.tle \
  -o merged.tle
```

**功能**:
- 合併多個 TLE 檔案
- 基於 NORAD ID 去重
- 自動識別星系
- 保持 TLE 格式

### 2. windows - 計算通聯視窗

```bash
python scripts/multi_constellation.py windows \
  merged.tle \
  --stations '{"name":"TASA-1","lat":25.033,"lon":121.565,"alt":0}' \
  --start "2024-10-08T00:00:00Z" \
  --end "2024-10-09T00:00:00Z" \
  --min-elevation 10.0 \
  -o windows.json
```

**參數**:
- `--stations`: 地面站 JSON（可多個）
- `--start`: 開始時間（ISO 8601）
- `--end`: 結束時間（ISO 8601）
- `--min-elevation`: 最小仰角（度）

### 3. conflicts - 偵測衝突

```bash
python scripts/multi_constellation.py conflicts \
  windows.json \
  -o conflicts.json
```

**衝突條件**:
- 相同地面站
- 相同頻段
- 時間重疊

### 4. schedule - 優先排程

```bash
python scripts/multi_constellation.py schedule \
  windows.json \
  -o schedule.json
```

**排程規則**:
- 優先級排序（高 → 中 → 低）
- 衝突時保留高優先級
- 記錄拒絕原因

### 5. pipeline - 完整管線

```bash
python scripts/multi_constellation.py pipeline \
  file1.tle file2.tle \
  --stations '{"name":"TASA","lat":25.033,"lon":121.565,"alt":0}' \
  -o results.json
```

**執行步驟**:
1. 合併 TLE
2. 計算視窗
3. 偵測衝突
4. 優先排程

---

## Python API

### 基本使用

```python
from scripts.multi_constellation import (
    merge_tle_files,
    identify_constellation,
    calculate_mixed_windows,
    detect_conflicts,
    prioritize_scheduling,
    FREQUENCY_BANDS,
    PRIORITY_LEVELS
)
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 1. 合併 TLE
stats = merge_tle_files(
    [Path('gps.tle'), Path('iridium.tle')],
    Path('merged.tle')
)

# 2. 計算視窗
stations = [{"name": "TASA", "lat": 25.033, "lon": 121.565, "alt": 0}]
start = datetime(2024, 10, 8, 0, 0, 0, tzinfo=timezone.utc)
end = start + timedelta(days=1)

result = calculate_mixed_windows(
    Path('merged.tle'), stations, start, end
)

# 3. 偵測衝突
conflicts = detect_conflicts(result['windows'], FREQUENCY_BANDS)

# 4. 排程
schedule = prioritize_scheduling(result['windows'], PRIORITY_LEVELS)
```

### 星系識別

```python
from scripts.multi_constellation import identify_constellation

# 識別衛星星系
constellation = identify_constellation("GPS BIIA-10 (PRN 32)")
# 返回: "GPS"

constellation = identify_constellation("STARLINK-1007")
# 返回: "Starlink"
```

---

## 輸出格式

### 視窗計算輸出

```json
{
  "meta": {
    "constellations": ["GPS", "Iridium"],
    "total_satellites": 763,
    "ground_stations": ["TASA-1"],
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
      "ground_station": "TASA-1",
      "start": "2024-10-08T02:15:30Z",
      "end": "2024-10-08T02:27:45Z",
      "max_elevation": 67.8,
      "duration_sec": 735
    }
  ]
}
```

### 衝突輸出

```json
{
  "conflicts": [
    {
      "type": "frequency_conflict",
      "window1": "IRIDIUM 102",
      "window2": "STARLINK-1007",
      "frequency_band": "Ka-band",
      "ground_station": "TASA-1",
      "overlap_start": "2024-10-08T10:05:00Z",
      "overlap_end": "2024-10-08T10:10:00Z"
    }
  ],
  "count": 12
}
```

### 排程輸出

```json
{
  "scheduled": [...],
  "rejected": [
    {
      "satellite": "STARLINK-1007",
      "reason": "Frequency conflict with higher priority window",
      "conflict_with": "IRIDIUM 102"
    }
  ]
}
```

---

## 測試

### 執行測試

```bash
# 所有測試
pytest tests/test_multi_constellation.py -v

# 特定測試類別
pytest tests/test_multi_constellation.py::TestTLEMerging -v
pytest tests/test_multi_constellation.py::TestConflictDetection -v
```

### 測試覆蓋

```
TestTLEMerging                    ✅ 4/4 tests
TestConstellationIdentification   ✅ 6/6 tests
TestFrequencyBandMapping          ✅ 5/5 tests
TestPriorityLevels                ✅ 4/4 tests
TestMixedWindowsCalculation       ✅ 4/4 tests
TestConflictDetection             ✅ 4/4 tests
TestPriorityScheduling            ✅ 4/4 tests
TestOutputFormat                  ✅ 3/3 tests
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total                             ✅ 34/34 tests
```

---

## 進階功能

### 自訂星系

```python
from scripts.multi_constellation import (
    CONSTELLATION_PATTERNS,
    FREQUENCY_BANDS,
    PRIORITY_LEVELS
)

# 新增自訂星系
CONSTELLATION_PATTERNS['MyConstellation'] = [r'MYSAT']
FREQUENCY_BANDS['MyConstellation'] = 'X-band'
PRIORITY_LEVELS['MyConstellation'] = 'high'
```

### 批次處理

```bash
# 處理多個地面站
for station in TASA-1 TASA-2 TASA-3; do
  python scripts/multi_constellation.py windows \
    merged.tle \
    --stations "{\"name\":\"$station\",\"lat\":25.033,\"lon\":121.565,\"alt\":0}" \
    -o "${station}_windows.json"
done
```

---

## 效能指標

| 資料規模 | 衛星數 | 視窗數 | 處理時間 | 記憶體 |
|---------|--------|--------|----------|--------|
| 小型 | 10 | 100 | ~1 秒 | ~10 MB |
| 中型 | 100 | 1,000 | ~10 秒 | ~50 MB |
| 大型 | 1,000 | 10,000 | ~90 秒 | ~200 MB |

---

## 常見問題

### Q: 為什麼沒有計算到視窗？

**可能原因**:
1. TLE 時期太舊或太新
2. 衛星不經過地面站
3. 最小仰角設定太高

**解決方法**:
```bash
# 降低最小仰角
--min-elevation 5.0

# 延長時間範圍
--end "2024-10-10T00:00:00Z"

# 使用 TLE 時期附近的時間
--start "2024-10-06T00:00:00Z"
```

### Q: 如何處理大量 TLE 檔案？

使用萬用字元合併:
```bash
python scripts/multi_constellation.py merge data/*.tle -o merged.tle
```

### Q: 如何匯出成其他格式？

使用 `jq` 轉換:
```bash
# 轉 CSV
cat results.json | jq -r '.windows[] | [.satellite,.start,.end] | @csv' > windows.csv

# 提取特定星系
cat results.json | jq '.windows[] | select(.constellation=="GPS")' > gps_windows.json
```

---

## 相關文檔

- **詳細文檔**: [docs/MULTI_CONSTELLATION.md](../docs/MULTI_CONSTELLATION.md)
- **測試**: [tests/test_multi_constellation.py](../tests/test_multi_constellation.py)
- **範例**: [examples/multi_constellation_example.py](../examples/multi_constellation_example.py)
- **TLE 處理**: [scripts/tle_processor.py](tle_processor.py)

---

## 授權

MIT License

---

**開發者**: TASA SatNet Pipeline Team
**最後更新**: 2025-10-08
**版本**: 1.0.0
