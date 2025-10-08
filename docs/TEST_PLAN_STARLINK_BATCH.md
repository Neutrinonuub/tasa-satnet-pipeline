# Starlink 100 衛星批次處理測試計畫

## 概要

本文件描述針對 Starlink 前 100 顆衛星批次處理功能的完整測試套件。測試遵循 **TDD (Test-Driven Development)** 原則，所有測試在實作完成前處於 **Red Phase（失敗/跳過狀態）**。

## 測試檔案

**檔案位置**: `tests/test_starlink_batch.py`

**測試框架**: pytest 7.3.1+ 搭配以下插件：
- `pytest-benchmark==4.0.0` - 效能基準測試
- `pytest-cov==4.1.0` - 程式碼覆蓋率
- `pytest-parametrize` - 參數化測試

## 測試涵蓋範圍

### 測試統計
- **總測試案例**: 34 個
- **測試類別**: 8 大類
- **目標覆蓋率**: 90%+
- **目前狀態**: Red Phase (31 skipped, 2 passed)

## 測試類別細節

### 1. TestStarlinkExtraction (4 測試)
衛星資料提取功能測試

**測試案例**:
- `test_extract_starlink_subset_count` - 驗證提取正確數量 (100 顆)
- `test_extract_starlink_subset_valid_tle` - 驗證 TLE 格式正確性與 SGP4 相容性
- `test_extract_starlink_subset_ordering` - 驗證按檔案順序提取
- `test_extract_subset_custom_count` - 驗證自訂數量提取 (10, 50 顆)

**預期行為**:
```python
satellites = extract_starlink_subset(tle_file, count=100)
assert len(satellites) == 100
assert satellites[0]["name"] == "STARLINK-1008"  # 檔案第一筆
```

---

### 2. TestSingleStationWindows (7 測試)
單一地面站可見視窗計算

**測試案例**:
- `test_calculate_windows_single_station_basic` - 基本視窗計算
- `test_calculate_windows_elevation_filtering` - 仰角閾值過濾
- `test_calculate_windows_various_elevations[5.0-30.0]` - 多組仰角參數化測試

**參數化測試**:
```python
@pytest.mark.parametrize("min_elev", [5.0, 10.0, 15.0, 20.0, 30.0])
def test_calculate_windows_various_elevations(min_elev):
    # 不同仰角閾值應產生不同數量視窗
    # 高仰角 → 視窗數量減少
```

**預期輸出格式**:
```json
{
  "type": "tle_pass",
  "start": "2025-01-15T03:45:00Z",
  "end": "2025-01-15T03:52:30Z",
  "sat": "STARLINK-1008",
  "gw": "HSINCHU",
  "max_elevation_deg": 45.3,
  "duration_sec": 450
}
```

---

### 3. TestMultiStationBatch (3 測試)
多站批次處理測試

**測試案例**:
- `test_calculate_windows_multi_station_all_six` - 6 個台灣地面站批次計算
- `test_calculate_windows_multi_station_100_satellites` - 100 顆衛星完整批次
- `test_multi_station_parallel_processing` - 並行處理效能驗證

**台灣地面站清單**:
1. HSINCHU (新竹站) - 24.7881°N, 120.9979°E
2. TAIPEI (台北站) - 25.0330°N, 121.5654°E
3. KAOHSIUNG (高雄站) - 22.6273°N, 120.3014°E
4. TAICHUNG (台中站) - 24.1477°N, 120.6736°E
5. TAINAN (台南站) - 22.9997°N, 120.2270°E
6. HUALIEN (花蓮站) - 23.9871°N, 121.6015°E

**預期輸出結構**:
```python
results = {
    "HSINCHU": [window1, window2, ...],
    "TAIPEI": [window1, window2, ...],
    ...  # 所有 6 站
}
```

---

### 4. TestWindowMerging (3 測試)
視窗合併與聚合測試

**測試案例**:
- `test_merge_windows_single_satellite` - 單衛星跨站視窗合併
- `test_merge_windows_multiple_satellites` - 多衛星視窗分組
- `test_merge_windows_coverage_timeline` - 連續覆蓋時間軸生成

**合併策略**:
```python
# Union 合併（重疊視窗合併為一）
merged = merge_windows(windows, merge_strategy="union")

# Timeline 分析（識別覆蓋期間與間隙）
timeline = merge_windows(windows, merge_strategy="timeline")
# → {
#     "covered_periods": [...],
#     "gaps": [...]
#   }
```

---

### 5. TestCoverageStatistics (3 測試)
覆蓋率統計與通聯頻率

**測試案例**:
- `test_coverage_statistics_basic` - 基本統計指標
- `test_coverage_statistics_100_satellites` - 100 衛星 7 天統計
- `test_coverage_statistics_gap_analysis` - 覆蓋間隙分析

**統計輸出範例**:
```python
stats = {
    "total_windows": 145,
    "total_coverage_seconds": 86400,
    "coverage_percentage": 14.3,
    "contacts_per_satellite": {
        "STARLINK-1008": 12,
        "STARLINK-1010": 10,
        ...
    },
    "contacts_per_station": {
        "HSINCHU": 28,
        "TAIPEI": 24,
        ...
    },
    "average_contacts_per_day": 20.7,
    "max_gap_duration_seconds": 3600,
    "gaps": [...]
}
```

---

### 6. TestPerformance (3 測試)
效能基準測試

**測試案例**:
- `test_performance_100_satellites_single_station` - 100 顆衛星 × 1 站
- `test_performance_10_satellites_six_stations` - 10 顆衛星 × 6 站
- `test_memory_usage_100_satellites` - 記憶體使用分析

**效能目標**:
| 測試案例 | 衛星數 | 地面站數 | 時間範圍 | 目標時間 | 記憶體上限 |
|---------|-------|---------|---------|---------|-----------|
| 單站批次 | 100 | 1 | 24h | <60s | - |
| 多站批次 | 10 | 6 | 24h | <30s | - |
| 記憶體測試 | 20 | 6 | 24h | - | <500MB |

**Benchmark 使用**:
```python
@pytest.mark.benchmark
def test_performance(benchmark):
    result = benchmark(process_function)
    assert len(result) > 0
```

---

### 7. TestEdgeCases (6 測試)
邊界條件與錯誤處理

**測試案例**:
- `test_empty_tle_file` - 空 TLE 檔案
- `test_malformed_tle_handling` - 格式錯誤 TLE
- `test_invalid_time_range` - 結束時間早於開始時間
- `test_zero_duration_time_range` - 零時長時間範圍
- `test_invalid_elevation_threshold` - 無效仰角閾值 (<0 或 >90)
- `test_missing_station_coordinates` - 缺少地面站座標

**錯誤處理範例**:
```python
# 時間範圍錯誤
with pytest.raises(ValueError, match="end.*before.*start"):
    calculate_windows(start=later, end=earlier, ...)

# 仰角範圍錯誤
with pytest.raises(ValueError, match="elevation"):
    calculate_windows(min_elevation_deg=-10.0, ...)
```

---

### 8. TestStarlinkBatchProcessor (3 測試)
整合處理器類別測試

**測試案例**:
- `test_processor_initialization` - 處理器初始化
- `test_processor_process_all` - 完整處理流程
- `test_processor_incremental_processing` - 增量批次處理

**處理器使用範例**:
```python
processor = StarlinkBatchProcessor(
    tle_file="data/starlink.tle",
    stations_file="data/taiwan_ground_stations.json",
    satellite_count=100
)

results = processor.process_all(
    start_time=datetime(2025, 1, 15, 0, 0, 0),
    end_time=datetime(2025, 1, 16, 0, 0, 0),
    min_elevation_deg=10.0,
    output_file="results/windows.json"
)

# 輸出結構
{
    "satellites": [...],
    "stations": [...],
    "windows": [...],
    "statistics": {...}
}
```

---

## 測試資料依賴

### 必需檔案
1. **TLE 資料**: `data/starlink.tle` (8,451 顆衛星)
2. **地面站資料**: `data/taiwan_ground_stations.json` (6 站)

### Fixtures
所有 fixtures 定義於 `tests/conftest.py` 和測試檔案中：

```python
@pytest.fixture
def starlink_tle_file() -> Path
    """Starlink TLE 檔案路徑"""

@pytest.fixture
def taiwan_stations() -> list[dict]
    """台灣地面站清單"""

@pytest.fixture
def test_time_range() -> tuple[datetime, datetime]
    """標準測試時間範圍 (24 小時)"""

@pytest.fixture
def extended_time_range() -> tuple[datetime, datetime]
    """延長測試時間範圍 (7 天)"""
```

---

## 執行測試

### 完整測試套件
```bash
pytest tests/test_starlink_batch.py -v
```

### 排除慢速測試
```bash
pytest tests/test_starlink_batch.py -v -m "not slow"
```

### 執行特定測試類別
```bash
pytest tests/test_starlink_batch.py::TestStarlinkExtraction -v
```

### 執行效能基準測試
```bash
pytest tests/test_starlink_batch.py -v -m benchmark --benchmark-only
```

### 測試覆蓋率報告
```bash
pytest tests/test_starlink_batch.py --cov=scripts --cov-report=html
```

---

## TDD 開發流程

### Phase 1: Red (當前狀態)
✅ **完成** - 所有測試已編寫，處於 SKIPPED 狀態

**狀態**: 31 skipped, 2 passed
- 2 個配置測試通過 (test_pytest_configuration, test_fixtures_available)
- 31 個功能測試跳過 (等待實作)

### Phase 2: Green (下一步)
📝 **待完成** - 實作最小可運行程式碼

**實作檔案**: `scripts/starlink_batch.py`

**必要函數**:
```python
def extract_starlink_subset(tle_file: Path, count: int) -> list[dict]:
    """從 TLE 檔案提取前 N 顆衛星"""
    pass

def calculate_windows_single_station(
    satellite_name: str,
    tle_line1: str,
    tle_line2: str,
    station: dict,
    start_time: datetime,
    end_time: datetime,
    min_elevation_deg: float = 10.0,
    step_seconds: int = 30
) -> list[dict]:
    """計算單一衛星對單一地面站的可見視窗"""
    pass

def calculate_windows_multi_station(
    satellite_name: str,
    tle_line1: str,
    tle_line2: str,
    stations: list[dict],
    start_time: datetime,
    end_time: datetime,
    min_elevation_deg: float = 10.0
) -> dict[str, list[dict]]:
    """計算單一衛星對多個地面站的可見視窗"""
    pass

def merge_windows(
    windows: list[dict],
    merge_strategy: str = "union",
    group_by: str = None
) -> dict | list:
    """合併視窗資料"""
    pass

def calculate_coverage_statistics(
    windows: list[dict],
    start_time: datetime,
    end_time: datetime,
    analyze_gaps: bool = False
) -> dict:
    """計算覆蓋率統計"""
    pass

class StarlinkBatchProcessor:
    """Starlink 批次處理器"""
    def __init__(self, tle_file: Path, stations_file: Path, satellite_count: int):
        pass

    def process_all(self, start_time, end_time, min_elevation_deg, output_file):
        pass

    def process_batch(self, satellite_indices, start_time, end_time):
        pass
```

### Phase 3: Refactor
🔄 **最終步驟** - 優化與重構

**重構目標**:
- 效能優化 (並行處理、快取)
- 程式碼品質 (mypy 類型檢查、文件字串)
- 測試覆蓋率達標 (>90%)

---

## 品質指標

### 測試覆蓋率目標
- **Statements**: >80%
- **Branches**: >75%
- **Functions**: >80%
- **Lines**: >80%

### 測試特性 (FIRST 原則)
- **Fast**: 單元測試 <100ms
- **Isolated**: 測試間無依賴
- **Repeatable**: 相同結果
- **Self-validating**: 明確的通過/失敗
- **Timely**: 與程式碼同步編寫

---

## 待實作功能清單

### 高優先級
1. ✅ 測試套件編寫 (已完成)
2. ⏳ `extract_starlink_subset()` - TLE 提取
3. ⏳ `calculate_windows_single_station()` - 單站視窗
4. ⏳ `calculate_windows_multi_station()` - 多站批次

### 中優先級
5. ⏳ `merge_windows()` - 視窗合併
6. ⏳ `calculate_coverage_statistics()` - 統計分析
7. ⏳ `StarlinkBatchProcessor` - 整合處理器

### 低優先級
8. ⏳ 並行處理優化
9. ⏳ 記憶體效率優化
10. ⏳ CLI 介面開發

---

## 相關文件

- **專案主文件**: `README.md`
- **CLAUDE.md**: AI 協作指南
- **Makefile**: 測試自動化命令
- **pytest.ini**: 測試配置

---

## 附錄：範例測試輸出

### 成功的測試執行 (Green Phase)
```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-7.4.4
collected 34 items

tests/test_starlink_batch.py::TestStarlinkExtraction::test_extract_starlink_subset_count PASSED
tests/test_starlink_batch.py::TestStarlinkExtraction::test_extract_starlink_subset_valid_tle PASSED
tests/test_starlink_batch.py::TestStarlinkExtraction::test_extract_starlink_subset_ordering PASSED
...
tests/test_starlink_batch.py::TestPerformance::test_performance_100_satellites_single_station PASSED

=================== 34 passed in 45.2s (benchmark: 3 tests) ===================

---------- coverage: platform win32, python 3.13.5-final-0 -----------
Name                             Stmts   Miss  Cover
--------------------------------------------------------
scripts/starlink_batch.py          245      8    97%
--------------------------------------------------------
TOTAL                              245      8    97%
```

---

**文件版本**: 1.0
**建立日期**: 2025-10-08
**作者**: TASA SatNet Pipeline Testing Agent (Claude Code)
**狀態**: TDD Red Phase Complete ✅
