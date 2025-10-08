# TASA SatNet Pipeline - 重構路線圖

**版本**: 1.0
**日期**: 2025-10-08
**狀態**: 規劃中

---

## 📊 當前狀態快照

```
整體代碼品質: 8.2/10 ⭐⭐⭐⭐

測試覆蓋率:    ████████████████████ 98%
TDD 合規性:    ████████████████████ 95%
類型安全:      ████████████░░░░░░░░ 60%
效能優化:      ████████████░░░░░░░░ 65%
安全性:        ██████████░░░░░░░░░░ 50%
文檔完整性:    ████████████████████ 90%
```

### 核心指標
- ✅ 28/28 測試通過
- ✅ 98.33% 測試覆蓋率
- ✅ K8s 生產部署驗證
- ⚠️ 5 個 P0 優先級問題
- ⚠️ 12 個 P1 優先級問題
- ℹ️ 8 個 P2 優先級問題

---

## 🎯 重構目標

### 階段 1: 基礎修復 (Week 1-2)
**目標**: 修復所有 P0 問題，提升代碼品質到 9.0/10

#### Week 1: 關鍵修復
- [ ] **P0-1**: 修復 timezone 參數使用 (`parse_oasis_log.py:32`)
- [ ] **P0-2**: 添加檔案大小限制與安全檢查
- [ ] **P0-3**: 改進延遲計算公式 (`gen_scenario.py:119`)
- [ ] **P0-4**: 添加 JSON Schema 驗證
- [ ] **P0-5**: 優化 O(n²) 配對演算法

**驗收標準**:
```bash
✓ All P0 issues resolved
✓ pytest tests/ -v --cov=scripts (100% pass, ≥95% coverage)
✓ mypy scripts/ (0 errors)
✓ No security vulnerabilities in code scan
```

#### Week 2: 類型安全與文檔
- [ ] 添加完整的 type hints 到所有模組
- [ ] 設置 mypy strict mode
- [ ] 更新 docstrings 為 Google style
- [ ] 添加配置管理層

**驗收標準**:
```bash
✓ mypy scripts/ --strict (0 errors)
✓ All functions have type hints
✓ All classes have docstrings
✓ Config module implemented
```

---

### 階段 2: 功能擴展 (Week 3-5)
**目標**: 實現新功能，支援 Starlink、多星系、視覺化

#### Week 3: Starlink 批次處理器

**新檔案**:
```
scripts/starlink_batch_processor.py    (實作)
tests/test_starlink_batch.py           (測試)
data/starlink_tle/                     (測試數據)
docs/STARLINK_GUIDE.md                 (文檔)
```

**功能需求**:
1. 批次載入 TLE 檔案
2. 並行計算可見性視窗
3. 生成覆蓋率地圖
4. 導出 JSON/CSV 報告

**TDD 流程**:
```python
# Step 1: 寫測試 (紅燈)
def test_load_tle_batch():
    processor = StarlinkBatchProcessor()
    count = processor.load_tle_batch(Path("data/starlink_tle/"))
    assert count == 550  # Starlink shell 1

# Step 2: 實作功能 (綠燈)
class StarlinkBatchProcessor:
    def load_tle_batch(self, tle_dir: Path) -> int:
        # Implementation
        pass

# Step 3: 重構 (維持綠燈)
# Optimize performance, improve readability
```

**驗收標準**:
```bash
✓ pytest tests/test_starlink_batch.py -v (all pass)
✓ Coverage ≥ 90% for new module
✓ Process 500+ satellites in < 5 seconds
✓ Documentation complete
```

#### Week 4: 多星系支援

**新檔案**:
```
scripts/multi_constellation.py         (實作)
tests/test_multi_constellation.py      (測試)
config/constellations.json             (配置)
docs/MULTI_CONSTELLATION_GUIDE.md      (文檔)
```

**功能需求**:
1. 支援 Starlink、OneWeb、Kuiper
2. 跨星系切換計算
3. 多星系路由優化
4. 星系間干擾分析

**關鍵介面**:
```python
class IConstellation(ABC):
    @abstractmethod
    def get_satellites(self) -> List[Satellite]:
        pass

    @abstractmethod
    def compute_coverage(self, location: GeoLocation) -> CoverageData:
        pass

class ConstellationManager:
    def add_constellation(self, name: str, constellation: IConstellation):
        pass

    def compute_handover_opportunities(self) -> List[HandoverWindow]:
        pass
```

**驗收標準**:
```bash
✓ Support 3+ constellations
✓ Handover computation < 1s for 100 satellites
✓ Test coverage ≥ 90%
✓ Integration test with Starlink module
```

#### Week 5: 視覺化模組

**新檔案**:
```
scripts/visualizer.py                  (實作)
tests/test_visualization.py            (測試)
examples/visualization_examples.ipynb  (範例)
docs/VISUALIZATION_GUIDE.md            (文檔)
```

**功能需求**:
1. 覆蓋率地圖 (地理投影)
2. 延遲熱力圖 (時間序列)
3. 波束排程甘特圖
4. 衛星軌跡動畫

**實作計劃**:
```python
class SatelliteVisualizer:
    def __init__(self, style: str = "seaborn"):
        self.style = style
        plt.style.use(style)

    def plot_coverage_map(
        self,
        coverage_data: Dict,
        projection: str = "mercator",
        output: Path = None
    ) -> plt.Figure:
        """Plot geographic coverage map."""
        pass

    def plot_latency_heatmap(
        self,
        metrics: List[Dict],
        time_window_min: int = 60,
        output: Path = None
    ) -> plt.Figure:
        """Plot latency heatmap over time."""
        pass

    def animate_satellite_passes(
        self,
        satellite_positions: List[Position],
        ground_stations: List[GeoLocation],
        fps: int = 30,
        output: Path = None
    ) -> Animation:
        """Create animation of satellite passes."""
        pass
```

**驗收標準**:
```bash
✓ Generate all 4 visualization types
✓ Plots saved to PNG/SVG/HTML
✓ Animation renders at 30 FPS
✓ Test coverage ≥ 85% (visual tests challenging)
✓ Jupyter notebook examples
```

---

### 階段 3: 效能與架構優化 (Week 6-8)

#### Week 6: 效能優化

**目標**: 支援 10,000+ 衛星、100,000+ 視窗

**優化任務**:

1. **流式處理**
```python
def parse_large_log_streaming(log_path: Path):
    """Parse large files without loading entire content."""
    chunk_size = 10000  # lines
    buffer = []

    with log_path.open('r') as f:
        for line in f:
            buffer.append(line)
            if len(buffer) >= chunk_size:
                yield process_chunk(buffer)
                buffer = []

        if buffer:
            yield process_chunk(buffer)
```

2. **並行處理**
```python
from multiprocessing import Pool

def process_batch_parallel(files: List[Path], workers: int = 4):
    """Process multiple files in parallel."""
    with Pool(processes=workers) as pool:
        results = pool.map(process_single_file, files)
    return merge_results(results)
```

3. **快取機制**
```python
from functools import lru_cache

@lru_cache(maxsize=10000)
def compute_propagation_delay(altitude_km: float) -> float:
    """Cached delay computation."""
    return (2 * altitude_km) / SPEED_OF_LIGHT
```

**基準測試**:
```python
# tests/test_performance.py
def test_parse_10k_satellites_benchmark(benchmark):
    """Benchmark parsing 10,000 satellites."""
    result = benchmark(lambda: parse_batch(large_dataset))
    assert result.stats['mean'] < 5.0  # < 5 seconds
    assert result.stats['max_memory_mb'] < 500  # < 500 MB
```

**驗收標準**:
```bash
✓ Parse 10,000 satellites in < 5s
✓ Memory usage < 500 MB for large datasets
✓ Parallel speedup ≥ 2.5x with 4 workers
✓ All benchmarks pass
```

#### Week 7: 架構重構

**目標**: 清晰的抽象層、可擴展架構

**重構任務**:

1. **定義介面抽象**
```python
# interfaces/parser.py
class ILogParser(ABC):
    @abstractmethod
    def parse(self, input_path: Path) -> ParsedData:
        pass

# interfaces/scenario_generator.py
class IScenarioGenerator(ABC):
    @abstractmethod
    def generate(self, data: ParsedData) -> Scenario:
        pass

# interfaces/metrics_calculator.py
class IMetricsCalculator(ABC):
    @abstractmethod
    def compute(self, scenario: Scenario) -> Metrics:
        pass
```

2. **實現管線編排**
```python
# pipeline/orchestrator.py
class PipelineOrchestrator:
    def __init__(self):
        self.steps = []

    def add_step(self, name: str, function: Callable):
        self.steps.append(PipelineStep(name, function))

    def execute(self, input_data: Any) -> PipelineResult:
        context = {"input": input_data}

        for step in self.steps:
            try:
                result = step.execute(context)
                context.update(result)
            except Exception as e:
                return PipelineResult(
                    success=False,
                    failed_step=step.name,
                    error=str(e)
                )

        return PipelineResult(success=True, data=context)
```

3. **集中化配置**
```python
# config/settings.py
@dataclass
class PhysicsConfig:
    speed_of_light_km_s: float = 299792.458
    earth_radius_km: float = 6371.0

@dataclass
class SatelliteConfig:
    leo_altitude_km: float = 550
    meo_altitude_km: float = 8000
    geo_altitude_km: float = 35786

class Config:
    physics = PhysicsConfig()
    satellite = SatelliteConfig()

    @classmethod
    def load_from_file(cls, path: Path):
        """Load config from YAML/JSON."""
        pass
```

**驗收標準**:
```bash
✓ All core modules use interfaces
✓ Pipeline orchestrator functional
✓ Config loaded from external file
✓ Dependency injection implemented
✓ All tests still pass
```

#### Week 8: 整合與文檔

**任務**:
1. 端到端整合測試
2. 效能基準測試套件
3. 完整的 API 文檔
4. 使用指南與範例

**整合測試**:
```python
def test_full_pipeline_with_starlink():
    """Test complete pipeline with Starlink data."""
    # 1. Load Starlink TLE
    processor = StarlinkBatchProcessor()
    satellites = processor.load_tle_batch(tle_dir)

    # 2. Generate windows
    windows = processor.compute_visibility_windows(ground_stations)

    # 3. Create scenario
    scenario = generate_scenario(windows, mode="regenerative")

    # 4. Compute metrics
    metrics = compute_metrics(scenario)

    # 5. Schedule beams
    schedule = schedule_beams(scenario)

    # 6. Visualize
    viz = SatelliteVisualizer()
    viz.plot_coverage_map(windows)

    # Assertions
    assert len(satellites) > 500
    assert metrics['latency']['mean_ms'] < 50
    assert schedule['success_rate'] > 95
```

**文檔需求**:
- [ ] API 文檔 (Sphinx)
- [ ] 使用者指南
- [ ] 開發者指南
- [ ] 架構設計文檔
- [ ] 部署指南
- [ ] 故障排除指南

**驗收標準**:
```bash
✓ All integration tests pass
✓ Performance benchmarks meet targets
✓ Documentation 100% complete
✓ Code review approval
✓ Ready for production deployment
```

---

## 📋 詳細任務分解

### Phase 1: Week 1 任務清單

#### Day 1-2: P0 修復
```
[ ] Task 1.1: 修復 timezone 參數
    - Edit parse_oasis_log.py
    - Add pytz dependency
    - Update tests
    - Verify with pytest

[ ] Task 1.2: 添加檔案大小限制
    - Create safe_read_file() function
    - Add max_size parameter
    - Add error handling
    - Write unit tests

[ ] Task 1.3: 改進延遲計算
    - Update _compute_base_latency()
    - Use physics constants
    - Add tests with known values
```

#### Day 3-4: 類型安全
```
[ ] Task 1.4: 添加 type hints
    - parse_oasis_log.py: 100% coverage
    - gen_scenario.py: 100% coverage
    - metrics.py: 100% coverage
    - scheduler.py: 100% coverage

[ ] Task 1.5: 設置 mypy
    - Add mypy.ini configuration
    - Run mypy on all modules
    - Fix all type errors
    - Add to CI pipeline
```

#### Day 5: 驗證與優化
```
[ ] Task 1.6: 優化配對演算法
    - Implement O(n) algorithm
    - Benchmark old vs new
    - Update tests
    - Verify correctness

[ ] Task 1.7: JSON Schema 驗證
    - Define schemas for all JSON formats
    - Implement validation functions
    - Add validation tests
    - Update documentation
```

### Phase 2: Week 3 任務清單 (Starlink)

#### Day 1: TDD Setup
```
[ ] Task 2.1: 創建測試結構
    - Create tests/test_starlink_batch.py
    - Define test fixtures
    - Write failing tests
    - Commit (red state)

[ ] Task 2.2: 實現基礎類
    - Create scripts/starlink_batch_processor.py
    - Implement StarlinkBatchProcessor class
    - Basic TLE loading
    - Tests pass (green state)
```

#### Day 2-3: 核心功能
```
[ ] Task 2.3: TLE 批次載入
    - Implement load_tle_batch()
    - Support multiple file formats
    - Error handling
    - Progress reporting

[ ] Task 2.4: 可見性視窗計算
    - Implement compute_visibility_windows()
    - Use SGP4 for propagation
    - Parallel processing
    - Optimize performance
```

#### Day 4: 報告生成
```
[ ] Task 2.5: 覆蓋率地圖
    - Implement compute_coverage_map()
    - Geographic binning
    - Statistics computation
    - Export to JSON

[ ] Task 2.6: 批次報告
    - Generate comprehensive reports
    - CSV export
    - JSON summary
    - HTML dashboard (bonus)
```

#### Day 5: 測試與文檔
```
[ ] Task 2.7: 完整測試覆蓋
    - Unit tests for all functions
    - Integration tests
    - Performance benchmarks
    - Coverage ≥ 90%

[ ] Task 2.8: 文檔
    - Write STARLINK_GUIDE.md
    - Add docstrings
    - Create examples
    - Update README
```

---

## 🔄 持續改進流程

### 每週檢查點
```bash
# Week 1 Checkpoint
✓ All P0 issues resolved
✓ Type hints: 100%
✓ Test coverage: ≥ 95%
✓ Mypy: 0 errors

# Week 3 Checkpoint
✓ Starlink module: Complete
✓ Test coverage: ≥ 90%
✓ Performance: < 5s for 500 satellites
✓ Documentation: Complete

# Week 5 Checkpoint
✓ Visualization module: Complete
✓ All plots working
✓ Animation rendering
✓ Examples complete

# Week 8 Checkpoint
✓ All modules integrated
✓ Performance targets met
✓ Documentation 100%
✓ Production ready
```

### 程式碼品質閘門
```bash
# Pre-commit hooks
1. pytest tests/ -v --cov=scripts
2. mypy scripts/ --strict
3. black scripts/ tests/ --check
4. flake8 scripts/ tests/
5. isort scripts/ tests/ --check

# CI/CD pipeline
1. Run all tests (Linux, Windows, macOS)
2. Generate coverage report
3. Run security scan (bandit)
4. Build Docker image
5. Deploy to staging (K8s)
6. Run integration tests
7. Deploy to production (manual approval)
```

---

## 📈 成功指標

### 代碼品質目標
```
當前狀態 → 目標狀態

測試覆蓋率:   98%  → 99%
類型覆蓋率:   60%  → 100%
代碼複雜度:   4.2  → < 5.0
文檔覆蓋率:   90%  → 100%
安全評分:    7.0  → 9.0
整體評分:    8.2  → 9.5
```

### 效能目標
```
操作                  當前     目標
─────────────────────────────────
解析 1K 視窗          0.5s  → 0.3s
解析 10K 視窗         5s    → 3s
生成場景 (1K)         1s    → 0.5s
計算指標 (1K)         2s    → 1s
排程 (1K)             3s    → 1.5s
完整管線 (1K)         12s   → 6s
```

### 功能目標
```
模組                  狀態    目標
──────────────────────────────────
OASIS Parser         ✅     ✅ (優化)
Scenario Generator   ✅     ✅ (擴展)
Metrics Calculator   ✅     ✅ (改進)
Beam Scheduler       ✅     ✅ (優化)
Starlink Processor   ❌     ✅ (新增)
Multi-Constellation  ❌     ✅ (新增)
Visualizer           ❌     ✅ (新增)
Pipeline Orchestrator ❌     ✅ (新增)
```

---

## 🎯 決策記錄

### ADR-001: 使用 OR-Tools 進行排程優化
**日期**: 2025-10-08
**狀態**: 建議
**背景**: 當前貪婪演算法無法保證最優排程
**決策**: 採用 Google OR-Tools 的 CP-SAT solver
**後果**:
- ✅ 可獲得最優解
- ✅ 支援複雜約束
- ⚠️ 增加依賴項
- ⚠️ 學習曲線

### ADR-002: 使用 Matplotlib + Folium 進行視覺化
**日期**: 2025-10-08
**狀態**: 建議
**背景**: 需要地理投影與互動式地圖
**決策**: Matplotlib (靜態圖) + Folium (互動地圖)
**後果**:
- ✅ 廣泛使用，文檔豐富
- ✅ 支援多種輸出格式
- ⚠️ 動畫效能可能受限

### ADR-003: 使用 Pydantic 進行數據驗證
**日期**: 2025-10-08
**狀態**: 考慮中
**替代方案**: JSON Schema, attrs, dataclasses
**建議**: Pydantic v2 (效能更好，類型安全)

---

## 📞 溝通計劃

### 週報格式
```markdown
# Week N Progress Report

## 完成項目
- [x] Task 1: Description
- [x] Task 2: Description

## 進行中
- [ ] Task 3: Description (50% complete)

## 阻礙
- Issue 1: Description
  - Impact: High
  - Plan: ...

## 下週計劃
- [ ] Task 4
- [ ] Task 5

## 指標
- Test Coverage: 98.5%
- Code Quality: 8.5/10
- Open Issues: 3
```

### 程式碼審查
- **頻率**: 每個 PR
- **審查者**: Senior Developer + 1 Peer
- **標準**:
  - ✅ 所有測試通過
  - ✅ 覆蓋率不降低
  - ✅ 文檔更新
  - ✅ 無安全問題

---

## 🏁 完成標準

### Phase 1 完成定義
```bash
✓ All P0 and P1 issues resolved
✓ Test coverage ≥ 95%
✓ Mypy strict mode: 0 errors
✓ All security scans pass
✓ Code review approved
✓ Documentation updated
```

### Phase 2 完成定義
```bash
✓ Starlink module: Fully functional
✓ Multi-constellation: 3+ constellations supported
✓ Visualizer: All 4 plot types working
✓ Test coverage ≥ 90% for all new modules
✓ Integration tests pass
✓ Documentation complete
```

### Phase 3 完成定義
```bash
✓ Performance targets met
✓ Architecture refactoring complete
✓ Pipeline orchestrator functional
✓ All benchmarks pass
✓ Production deployment successful
✓ User acceptance testing passed
```

---

**文件版本**: 1.0
**最後更新**: 2025-10-08
**下次審查**: 2025-10-22 (2 週後)

**負責人**: Development Team
**審批**: Project Manager
