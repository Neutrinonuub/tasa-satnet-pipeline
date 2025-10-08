# 資料集與測試場景完整清單

**更新日期**: 2025-10-08

---

## 🛰️ TLE 資料集 (真實衛星軌道資料)

### 已下載資料集

| 資料集 | 衛星數量 | 檔案大小 | 軌道類型 | 用途 |
|--------|----------|----------|----------|------|
| **Starlink** | 8,451 | 1.4 MB | LEO (550km) | 低軌通訊星系 |
| **OneWeb** | 651 | 107 KB | LEO (1,200km) | 低軌通訊星系 |
| **Iridium NEXT** | 80 | 14 KB | LEO (780km) | 低軌通訊星系 |
| **GPS** | 32 | 5.3 KB | MEO (20,180km) | 中軌導航星系 |
| **ISS** | 1 | 152 B | LEO (400km) | 國際太空站 |
| **Active Satellites** | 12,894 | 2.1 MB | Various | 所有活躍衛星 |
| **總計** | **22,109** | **3.6 MB** | - | - |

### 資料來源
- **CelesTrak**: https://celestrak.org/
- **更新頻率**: 每日
- **格式**: TLE (Two-Line Element)
- **精度**: 預測誤差 < 1km (24小時內)

---

## 🌍 地面站配置

### 台灣地面站網路

| 站點 | 位置 | 座標 | 海拔 | 類型 | 波束容量 | 頻段 |
|------|------|------|------|------|----------|------|
| **HSINCHU** | 新竹 | 24.79°N, 120.99°E | 52m | 指揮控制 | 8 beams | S/X/Ka |
| **TAIPEI** | 台北 | 25.03°N, 121.57°E | 10m | 資料下傳 | 6 beams | X/Ka |
| **KAOHSIUNG** | 高雄 | 22.63°N, 120.30°E | 15m | 指揮控制 | 8 beams | S/X |
| **TAICHUNG** | 台中 | 24.15°N, 120.67°E | 84m | 遙測 | 4 beams | S/UHF |
| **TAINAN** | 台南 | 23.00°N, 120.23°E | 12m | 資料下傳 | 6 beams | X/Ka |
| **HUALIEN** | 花蓮 | 23.99°N, 121.60°E | 16m | 備援 | 4 beams | S/X |

**總波束容量**: 36 beams
**覆蓋範圍**: 台灣及周邊海域

---

## 📋 測試場景

### 1. 基本場景 (sample_oasis.log)

**規模**: 小型
**衛星**: 1 (SAT-1)
**地面站**: 2 (HSINCHU, TAIPEI)
**時段**: 2 windows
**用途**: 單元測試、快速驗證

**內容**:
```
enter command window @ 2025-10-08T01:23:45Z sat=SAT-1 gw=HSINCHU
exit command window @ 2025-10-08T01:33:45Z sat=SAT-1 gw=HSINCHU
X-band data link window: 2025-10-08T02:00:00Z..2025-10-08T02:08:00Z sat=SAT-1 gw=TAIPEI
```

### 2. 複雜場景 (complex_oasis.log)

**規模**: 中型
**衛星**: 6 (Starlink x2, OneWeb x2, Iridium x1, GPS x1)
**地面站**: 6 (全台網路)
**時段**: 35 windows
**期間**: 24小時
**用途**: 壓力測試、並發處理、模式比較

**特點**:
- 多衛星並發通聯 (12:00-12:21 三衛星同時)
- 全天候覆蓋 (凌晨、上午、中午、傍晚、夜間)
- 不同軌道高度 (LEO + MEO)
- 多種通聯類型 (指令視窗 + 資料下傳)

### 3. TLE 計算視窗 (generate_tle_windows.py)

**規模**: 可擴展至大型
**功能**: 從 TLE 資料計算真實衛星可見視窗
**輸入**: TLE 檔案 + 地面站配置
**輸出**: 可見視窗 JSON

**使用範例**:
```bash
# 計算 Starlink 衛星對台灣站點的可見視窗
python scripts/generate_tle_windows.py \
  --tle data/starlink.tle \
  --stations data/taiwan_ground_stations.json \
  --start 2025-10-08T00:00:00Z \
  --end 2025-10-09T00:00:00Z \
  --output-dir data/windows \
  --merged data/starlink_windows_24h.json
```

---

## 🧪 測試案例

### 已驗證場景

| 場景 | 模式 | 時段數 | 延遲 | 吞吐量 | 成功率 | 狀態 |
|------|------|--------|------|--------|--------|------|
| Basic | Transparent | 2 | 8.91ms | 40 Mbps | 100% | ✅ |
| Basic | Regenerative | 2 | 13.91ms | 40 Mbps | 100% | ✅ |
| Complex | Transparent | 35 | 8.91ms | 40 Mbps | 100% | ✅ |
| Complex | Regenerative | 35 | 13.91ms | 40 Mbps | 100% | ✅ |

### 效能指標

| 場景 | 解析時間 | 場景生成 | 指標計算 | 排程時間 | 總計 |
|------|----------|----------|----------|----------|------|
| Basic (2 windows) | < 0.1s | < 0.1s | < 0.1s | < 0.1s | ~0.3s |
| Complex (35 windows) | < 0.2s | < 0.2s | < 0.2s | < 0.2s | ~0.7s |

---

## 📊 可用工具腳本

### 核心管線

1. **parse_oasis_log.py** - OASIS 日誌解析器
   - 輸入: `.log`
   - 輸出: `.json` (windows)
   - 支援過濾: `--sat`, `--gw`, `--min-duration`

2. **gen_scenario.py** - NS-3 場景生成器
   - 輸入: `windows.json`
   - 輸出: `scenario.json`
   - 模式: `--mode transparent|regenerative`

3. **metrics.py** - KPI 指標計算器
   - 輸入: `scenario.json`
   - 輸出: `metrics.csv`, `summary.json`
   - 計算: 延遲、吞吐量、RTT

4. **scheduler.py** - 波束排程器
   - 輸入: `scenario.json`
   - 輸出: `schedule.csv`, `stats.json`
   - 參數: `--capacity` (beams per gateway)

### TLE 處理

5. **tle_processor.py** - TLE 軌道計算器
   - 功能: SGP4 傳播、位置計算
   - 輸入: TLE 資料
   - 輸出: 衛星位置與速度

6. **tle_windows.py** - 可見視窗計算器
   - 功能: 計算衛星對地面站的可見視窗
   - 輸入: TLE + 觀測站座標
   - 輸出: 視窗 JSON

7. **generate_tle_windows.py** - 批次視窗生成器
   - 功能: 多地面站批次計算
   - 輸入: TLE + 站點配置
   - 輸出: 合併視窗資料

### 整合測試

8. **run_complex_scenario.py** - 複雜場景測試執行器
   - 功能: 端到端管線自動化
   - 輸入: 複雜 OASIS 日誌
   - 輸出: 完整測試報告

---

## 🚀 快速開始範例

### 範例 1: 基本測試

```bash
# 1. 解析日誌
python scripts/parse_oasis_log.py data/sample_oasis.log -o data/windows.json

# 2. 生成場景
python scripts/gen_scenario.py data/windows.json -o config/scenario.json --mode transparent

# 3. 計算指標
python scripts/metrics.py config/scenario.json -o reports/metrics.csv

# 4. 排程波束
python scripts/scheduler.py config/scenario.json -o reports/schedule.csv
```

### 範例 2: 複雜場景測試

```bash
# 一鍵執行完整測試
python scripts/run_complex_scenario.py \
  --log data/complex_oasis.log \
  --mode transparent \
  --output-dir results/complex
```

### 範例 3: TLE 視窗計算

```bash
# 計算 ISS 對新竹站的可見視窗
python scripts/tle_windows.py \
  --tle data/sample_iss.tle \
  --lat 24.7881 --lon 120.9979 --alt 0.052 \
  --start 2025-10-08T00:00:00Z \
  --end 2025-10-09T00:00:00Z \
  --min-elev 10.0 \
  --out data/iss_hsinchu_windows.json
```

### 範例 4: Starlink 全台覆蓋分析

```bash
# 計算 Starlink 衛星群對全台站點的覆蓋
python scripts/generate_tle_windows.py \
  --tle data/starlink.tle \
  --stations data/taiwan_ground_stations.json \
  --start 2025-10-08T00:00:00Z \
  --end 2025-10-09T00:00:00Z \
  --merged data/starlink_taiwan_24h.json

# 注意: 8,451 顆衛星 × 6 站點 = 50,706 組計算，需要較長時間
```

---

## 📈 擴展測試建議

### 1. 大規模 TLE 測試

**目標**: 驗證系統處理數千顆衛星的能力

```bash
# 選取 Starlink 前 100 顆衛星測試
head -n 300 data/starlink.tle > data/starlink_100.tle

python scripts/generate_tle_windows.py \
  --tle data/starlink_100.tle \
  --stations data/taiwan_ground_stations.json \
  --start 2025-10-08T00:00:00Z \
  --end 2025-10-08T06:00:00Z \
  --merged data/starlink100_6h.json
```

### 2. 多星系整合測試

**目標**: 混合不同軌道衛星系統

```bash
# 合併 GPS + Iridium + OneWeb
cat data/gps.tle data/iridium_next.tle data/oneweb.tle > data/multi_constellation.tle

python scripts/generate_tle_windows.py \
  --tle data/multi_constellation.tle \
  --stations data/taiwan_ground_stations.json \
  --merged data/multi_const_windows.json
```

### 3. 長期預測測試

**目標**: 驗證 7 天預測精度

```bash
# 計算一週視窗
python scripts/generate_tle_windows.py \
  --tle data/sample_iss.tle \
  --stations data/taiwan_ground_stations.json \
  --start 2025-10-08T00:00:00Z \
  --end 2025-10-15T00:00:00Z \
  --merged data/iss_week_windows.json
```

---

## 📚 資料檔案結構

```
data/
├── TLE 資料集
│   ├── starlink.tle           (8,451 sats, 1.4MB)
│   ├── oneweb.tle             (651 sats, 107KB)
│   ├── iridium_next.tle       (80 sats, 14KB)
│   ├── gps.tle                (32 sats, 5.3KB)
│   ├── sample_iss.tle         (1 sat, 152B)
│   └── active_sats.tle        (12,894 sats, 2.1MB)
│
├── 測試日誌
│   ├── sample_oasis.log       (基本場景, 2 windows)
│   └── complex_oasis.log      (複雜場景, 35 windows)
│
├── 配置檔案
│   └── taiwan_ground_stations.json  (6 stations)
│
└── 生成資料
    ├── windows/               (TLE 計算視窗, 按站點分類)
    └── merged_tle_windows.json (合併視窗資料)

results/
└── complex/                   (複雜場景測試結果)
    ├── windows.json
    ├── scenario_transparent.json
    ├── scenario_regenerative.json
    ├── metrics_transparent.csv
    ├── metrics_regenerative.csv
    ├── summary_transparent.json
    ├── summary_regenerative.json
    ├── schedule_transparent.csv
    ├── schedule_regenerative.csv
    ├── schedule_stats_transparent.json
    └── schedule_stats_regenerative.json
```

---

## 🔬 進階應用

### 1. 與 NS-3 整合

已生成的 `scenario.json` 可轉換為 NS-3 Python 腳本：

```bash
python scripts/gen_scenario.py \
  data/windows.json \
  -o output/scenario.py \
  --format ns3
```

### 2. 自訂地面站網路

修改 `taiwan_ground_stations.json` 加入新站點：

```json
{
  "name": "PENGHU",
  "location": "澎湖站",
  "lat": 23.5711,
  "lon": 119.5792,
  "alt": 25,
  "type": "relay",
  "capacity_beams": 4,
  "frequency_bands": ["S-band", "X-band"]
}
```

### 3. OASIS 日誌驗證

將 TLE 計算視窗與 OASIS 日誌比對：

```python
from scripts.tle_processor import TLEProcessor

# 載入 OASIS 視窗
with open('data/windows.json') as f:
    oasis_windows = json.load(f)

# 載入 TLE 視窗
with open('data/tle_windows.json') as f:
    tle_windows = json.load(f)

# 交叉驗證
for ow in oasis_windows['windows']:
    # 比對 TLE 計算是否吻合
    ...
```

---

## 📊 統計摘要

### 資料集統計

- **TLE 衛星總數**: 22,109 顆
- **測試場景**: 2 個 (基本 + 複雜)
- **地面站網路**: 6 站 (台灣)
- **測試視窗**: 37 個 (2 + 35)
- **驗證通過率**: 100%

### 覆蓋能力

- **LEO 衛星**: 9,182 顆 (Starlink + OneWeb + Iridium + ISS)
- **MEO 衛星**: 32 顆 (GPS)
- **活躍衛星**: 12,894 顆
- **軌道高度範圍**: 400km ~ 20,180km

---

## ✅ 下一步建議

1. **執行 Starlink 100 衛星測試** - 驗證中等規模處理能力
2. **TLE 與 OASIS 交叉驗證** - 確認視窗準確性
3. **建立視覺化介面** - 地圖顯示覆蓋範圍與衛星軌跡
4. **優化大規模計算** - 平行處理 8,451 顆 Starlink 衛星
5. **整合即時 TLE 更新** - 自動下載最新軌道資料

---

**文件版本**: 1.0
**最後更新**: 2025-10-08
**維護者**: TASA SatNet Pipeline Team
