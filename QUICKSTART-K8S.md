# 🚀 TASA SatNet Pipeline - Kubernetes 快速開始

**狀態**: ✅ 生產就緒  
**測試時間**: 2025-10-08  
**驗證方式**: 真實 K8s 部署

---

## 📋 前置需求

- ✅ Docker Desktop (含 Kubernetes)
- ✅ kubectl 命令列工具
- ✅ 管理員權限 (建置 Docker 映像)

---

## ⚡ 快速部署 (3 步驟)

### 步驟 1: 建置 Docker 映像
```bash
cd tasa-satnet-pipeline
docker build -t tasa-satnet-pipeline:latest .
```

### 步驟 2: 部署到 K8s
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
```

### 步驟 3: 執行管線
```bash
kubectl apply -f k8s/job-test-real.yaml
```

### 檢查結果
```bash
# 查看 Job 狀態
kubectl get jobs -n tasa-satnet

# 查看 Pod 狀態
kubectl get pods -n tasa-satnet

# 查看完整 Log
kubectl logs -n tasa-satnet job/tasa-test-pipeline
```

---

## 📊 預期輸出

### 成功執行
```
=== Testing Full Pipeline ===
Step 1: Parse
{"kept": 2, "outfile": "/tmp/windows.json"}

Step 2: Scenario
{"satellites": 1, "gateways": 2, "links": 2, "events": 4}

Step 3: Metrics
{"mean_latency_ms": 8.91, "mean_throughput_mbps": 40.0}

Step 4: Scheduler
{"scheduled": 2, "conflicts": 0, "success_rate": 100.0}

=== Pipeline Complete ===
All tests passed!
```

### Job 狀態
```
NAME                 STATUS     COMPLETIONS   DURATION
tasa-test-pipeline   Complete   1/1           4s
```

---

## 🔧 PowerShell 自動化腳本 (Windows)

```powershell
# 一鍵部署
.\k8s\deploy-local.ps1
```

這個腳本會自動：
1. ✅ 檢查前置需求
2. ✅ 建置 Docker 映像
3. ✅ 部署到 K8s
4. ✅ 顯示狀態

---

## 🐧 Bash 自動化腳本 (Linux/Mac)

```bash
# 一鍵部署
./k8s/deploy-local.sh
```

---

## 📦 管線步驟詳解

### 1. Parse (解析)
- **輸入**: `data/sample_oasis.log`
- **輸出**: `/tmp/windows.json`
- **功能**: 提取衛星通聯視窗

### 2. Scenario (場景生成)
- **輸入**: `/tmp/windows.json`
- **輸出**: `/tmp/scenario.json`
- **功能**: 建立拓撲和事件時間表

### 3. Metrics (指標計算)
- **輸入**: `/tmp/scenario.json`
- **輸出**: `/tmp/metrics.csv`
- **功能**: 計算延遲和吞吐量

### 4. Scheduler (調度)
- **輸入**: `/tmp/scenario.json`
- **輸出**: `/tmp/schedule.csv`
- **功能**: 分配波束和檢測衝突

---

## 🎯 自訂參數

### 修改輸入數據
編輯 `k8s/job-test-real.yaml`：
```yaml
args:
  - "-c"
  - |
    # 修改這裡的路徑
    python scripts/parse_oasis_log.py YOUR_LOG_FILE.log -o /tmp/windows.json
    # ... 其他步驟
```

### 使用自己的數據
```bash
# 1. 創建 ConfigMap 包含你的數據
kubectl create configmap my-data --from-file=mylog.log -n tasa-satnet

# 2. 修改 Job YAML 掛載 ConfigMap
# 3. 更新命令使用你的數據文件
```

---

## 🔍 故障排除

### 問題 1: Job 一直 Pending
```bash
# 檢查 Pod 狀態
kubectl describe pod -n tasa-satnet <pod-name>

# 常見原因：
# - 映像拉取失敗
# - 資源不足
```

### 問題 2: 找不到數據文件
```bash
# 驗證映像中有數據
docker run --rm tasa-satnet-pipeline:latest ls -la data/

# 應該看到：
# -rwxr-xr-x 1 root root  217 Oct  8 00:26 sample_oasis.log
```

### 問題 3: 權限錯誤
```bash
# 確認 Docker daemon 正在運行
docker ps

# 確認 K8s 正在運行
kubectl cluster-info
```

---

## 📚 進階使用

### 持久化輸出
```yaml
# 在 Job 中掛載 PVC
volumeMounts:
- name: output-volume
  mountPath: /output

volumes:
- name: output-volume
  persistentVolumeClaim:
    claimName: tasa-reports-pvc
```

### 平行處理多個 Log
```bash
# 創建多個 Job
for i in 1 2 3; do
  kubectl create job pipeline-$i \
    --image=tasa-satnet-pipeline:latest \
    --namespace=tasa-satnet \
    -- python scripts/parse_oasis_log.py data/log$i.log -o /output/result$i.json
done
```

### 查看所有 Job 結果
```bash
kubectl get jobs -n tasa-satnet
kubectl logs -n tasa-satnet -l app=tasa-test --tail=50
```

---

## 🧹 清理資源

### 刪除 Job (保留其他資源)
```bash
kubectl delete job tasa-test-pipeline -n tasa-satnet
```

### 完全移除
```bash
kubectl delete namespace tasa-satnet
```

### 刪除本地映像
```bash
docker rmi tasa-satnet-pipeline:latest
```

---

## 📈 性能參考

### 資源使用
```yaml
Container:
  CPU 請求: 200m
  CPU 限制: 1000m
  記憶體請求: 256Mi
  記憶體限制: 1Gi
```

### 執行時間
- 小型數據 (2 windows): **4 秒**
- 中型數據 (100 windows): **~20 秒** (估計)
- 大型數據 (1000 windows): **~60 秒** (估計)

---

## 🎉 驗證成功

✅ **所有測試通過** (2025-10-08)  
✅ **真實 K8s 部署驗證**  
✅ **4 秒完成完整管線**  
✅ **生產就緒**

---

## 📞 更多資訊

- 📄 完整驗證報告: `docs/REAL-DEPLOYMENT-COMPLETE.md`
- 🐛 問題追蹤: `docs/ISSUES-AND-SOLUTIONS.md`
- 🧪 測試文檔: `tests/test_deployment.py`
- 🔧 部署腳本: `k8s/deploy-local.ps1` 或 `k8s/deploy-local.sh`

---

**最後更新**: 2025-10-08  
**狀態**: ✅ 生產就緒  
**K8s 測試**: PASSED  
