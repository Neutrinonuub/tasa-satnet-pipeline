# Starlink 批次處理測試套件

## 快速啟動

### 執行所有測試
```bash
pytest tests/test_starlink_batch.py -v
```

### 當前狀態
```
✅ TDD Red Phase Complete
📊 34 測試案例已編寫
⏳ 31 測試等待實作 (SKIPPED)
✔️  2 配置測試通過 (PASSED)
🎯 目標覆蓋率: 90%+
```

---

## 測試組織結構

```
tests/test_starlink_batch.py
├── TestStarlinkExtraction (4 測試)
│   ├── test_extract_starlink_subset_count
│   ├── test_extract_starlink_subset_valid_tle
│   ├── test_extract_starlink_subset_ordering
│   └── test_extract_subset_custom_count
│
├── TestSingleStationWindows (7 測試)
│   ├── test_calculate_windows_single_station_basic
│   ├── test_calculate_windows_elevation_filtering
│   └── test_calculate_windows_various_elevations[5.0-30.0] (參數化)
│
├── TestMultiStationBatch (3 測試)
│   ├── test_calculate_windows_multi_station_all_six
│   ├── test_calculate_windows_multi_station_100_satellites
│   └── test_multi_station_parallel_processing
│
├── TestWindowMerging (3 測試)
│   ├── test_merge_windows_single_satellite
│   ├── test_merge_windows_multiple_satellites
│   └── test_merge_windows_coverage_timeline
│
├── TestCoverageStatistics (3 測試)
│   ├── test_coverage_statistics_basic
│   ├── test_coverage_statistics_100_satellites
│   └── test_coverage_statistics_gap_analysis
│
├── TestPerformance (3 測試) [benchmark]
│   ├── test_performance_100_satellites_single_station
│   ├── test_performance_10_satellites_six_stations
│   └── test_memory_usage_100_satellites [slow]
│
├── TestEdgeCases (6 測試)
│   ├── test_empty_tle_file
│   ├── test_malformed_tle_handling
│   ├── test_invalid_time_range
│   ├── test_zero_duration_time_range
│   ├── test_invalid_elevation_threshold
│   └── test_missing_station_coordinates
│
├── TestStarlinkBatchProcessor (3 測試)
│   ├── test_processor_initialization
│   ├── test_processor_process_all
│   └── test_processor_incremental_processing
│
└── 配置測試 (2 測試)
    ├── test_pytest_configuration ✅
    └── test_fixtures_available ✅
```

---

## 執行選項

### 基本執行
```bash
# 完整測試套件
pytest tests/test_starlink_batch.py -v

# 短格式輸出
pytest tests/test_starlink_batch.py -q

# 顯示測試名稱（不執行）
pytest tests/test_starlink_batch.py --collect-only
```

### 選擇性執行
```bash
# 執行特定測試類別
pytest tests/test_starlink_batch.py::TestStarlinkExtraction -v

# 執行特定測試
pytest tests/test_starlink_batch.py::TestStarlinkExtraction::test_extract_starlink_subset_count -v

# 跳過慢速測試
pytest tests/test_starlink_batch.py -v -m "not slow"

# 僅執行 benchmark 測試
pytest tests/test_starlink_batch.py -v -m benchmark --benchmark-only
```

### 覆蓋率報告
```bash
# HTML 報告
pytest tests/test_starlink_batch.py --cov=scripts --cov-report=html

# 終端輸出
pytest tests/test_starlink_batch.py --cov=scripts --cov-report=term-missing

# 僅覆蓋率數據
pytest tests/test_starlink_batch.py --cov=scripts.starlink_batch --cov-report=term
```

### 詳細輸出
```bash
# 顯示所有輸出
pytest tests/test_starlink_batch.py -v -s

# 失敗時顯示完整 traceback
pytest tests/test_starlink_batch.py -v --tb=long

# 僅顯示失敗詳情
pytest tests/test_starlink_batch.py -v --tb=short
```

---

## 測試資料需求

### 必需檔案
- ✅ `data/starlink.tle` - Starlink TLE 資料 (8,451 顆衛星)
- ✅ `data/taiwan_ground_stations.json` - 台灣地面站資料 (6 站)

### 測試時間範圍
```python
# 標準範圍 (test_time_range)
start = 2025-01-15T00:00:00Z
end   = 2025-01-16T00:00:00Z  # 24 小時

# 延長範圍 (extended_time_range)
start = 2025-01-15T00:00:00Z
end   = 2025-01-22T00:00:00Z  # 7 天
```

---

## 待實作模組

### 目標檔案
`scripts/starlink_batch.py`

### 必要函數簽名

```python
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Any

def extract_starlink_subset(
    tle_file: Path,
    count: int
) -> list[dict[str, str]]:
    """提取前 N 顆 Starlink 衛星。

    Returns:
        [{"name": str, "tle_line1": str, "tle_line2": str}, ...]
    """
    pass


def calculate_windows_single_station(
    satellite_name: str,
    tle_line1: str,
    tle_line2: str,
    station: dict[str, Any],
    start_time: datetime,
    end_time: datetime,
    min_elevation_deg: float = 10.0,
    step_seconds: int = 30
) -> list[dict[str, Any]]:
    """計算單一衛星對單一站的可見視窗。

    Returns:
        [{
            "type": "tle_pass",
            "start": "2025-01-15T03:45:00Z",
            "end": "2025-01-15T03:52:30Z",
            "sat": str,
            "gw": str,
            "max_elevation_deg": float,
            "duration_sec": int
        }, ...]
    """
    pass


def calculate_windows_multi_station(
    satellite_name: str,
    tle_line1: str,
    tle_line2: str,
    stations: list[dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
    min_elevation_deg: float = 10.0
) -> dict[str, list[dict[str, Any]]]:
    """計算單一衛星對多個站的可見視窗。

    Returns:
        {
            "HSINCHU": [window1, window2, ...],
            "TAIPEI": [...],
            ...
        }
    """
    pass


def merge_windows(
    windows: list[dict[str, Any]],
    merge_strategy: str = "union",
    group_by: str | None = None
) -> dict | list:
    """合併視窗資料。

    Args:
        merge_strategy: "union" | "timeline"
        group_by: "station" | "satellite" | None

    Returns:
        根據策略返回合併後的視窗
    """
    pass


def calculate_coverage_statistics(
    windows: list[dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
    analyze_gaps: bool = False
) -> dict[str, Any]:
    """計算覆蓋率統計。

    Returns:
        {
            "total_windows": int,
            "total_coverage_seconds": int,
            "coverage_percentage": float,
            "contacts_per_satellite": dict,
            "contacts_per_station": dict,
            "average_contacts_per_day": float,
            "max_gap_duration_seconds": int,
            "gaps": list  # if analyze_gaps=True
        }
    """
    pass


class StarlinkBatchProcessor:
    """Starlink 批次處理器。"""

    def __init__(
        self,
        tle_file: Path,
        stations_file: Path,
        satellite_count: int
    ):
        """初始化處理器。"""
        self.tle_file = tle_file
        self.stations_file = stations_file
        self.satellite_count = satellite_count
        self.satellites = []
        self.stations = []

    def process_all(
        self,
        start_time: datetime,
        end_time: datetime,
        min_elevation_deg: float = 10.0,
        output_file: Path | None = None
    ) -> dict[str, Any]:
        """執行完整批次處理。

        Returns:
            {
                "satellites": list,
                "stations": list,
                "windows": list,
                "statistics": dict
            }
        """
        pass

    def process_batch(
        self,
        satellite_indices: range,
        start_time: datetime,
        end_time: datetime,
        min_elevation_deg: float = 10.0
    ) -> list[dict[str, Any]]:
        """處理指定批次的衛星。"""
        pass
```

---

## 效能基準目標

| 測試案例 | 衛星數 | 地面站數 | 時間範圍 | 目標時間 | 記憶體上限 |
|---------|-------|---------|---------|---------|-----------|
| 單站批次 | 100   | 1       | 24h     | <60s    | -         |
| 多站批次 | 10    | 6       | 24h     | <30s    | -         |
| 記憶體   | 20    | 6       | 24h     | -       | <500MB    |

---

## 測試標記

```python
@pytest.mark.benchmark  # 效能基準測試
@pytest.mark.slow       # 慢速測試（>10s）
@pytest.mark.parametrize  # 參數化測試
```

---

## TDD 工作流程

### ✅ Phase 1: Red (當前)
所有測試已編寫，處於 SKIPPED 狀態

```bash
$ pytest tests/test_starlink_batch.py -v
=================== 2 passed, 31 skipped in 1.05s ===================
```

### ⏳ Phase 2: Green (下一步)
實作 `scripts/starlink_batch.py`，使測試通過

**目標**:
```bash
$ pytest tests/test_starlink_batch.py -v
=================== 34 passed in 45.2s ===================
```

### 🔄 Phase 3: Refactor (最終)
優化效能、品質、文件

**檢查清單**:
- [ ] mypy 類型檢查通過
- [ ] 測試覆蓋率 >90%
- [ ] 效能基準達標
- [ ] 文件字串完整
- [ ] 程式碼複雜度 <10

---

## 相關文件

- **詳細測試計畫**: `docs/TEST_PLAN_STARLINK_BATCH.md`
- **專案 README**: `README.md`
- **專案指南**: `CLAUDE.md`

---

## 錯誤排除

### pytest-benchmark not found
```bash
pip install pytest-benchmark==4.0.0
```

### 資料檔案遺失
```bash
# 確認檔案存在
ls data/starlink.tle
ls data/taiwan_ground_stations.json
```

### 測試收集錯誤
```bash
# 清除快取
pytest --cache-clear

# 檢查語法
python -m py_compile tests/test_starlink_batch.py
```

---

**版本**: 1.0
**狀態**: TDD Red Phase ✅
**下一步**: 實作 `scripts/starlink_batch.py` (Green Phase)
