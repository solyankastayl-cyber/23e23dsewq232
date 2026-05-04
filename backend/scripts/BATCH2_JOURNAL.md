# BATCH 2 - ОПЕРАЦИОННЫЙ ЖУРНАЛ

## Запуск: 2026-04-18 12:46:38 UTC

---

## ✅ КРИТИЧЕСКИЕ МОМЕНТЫ ЗАФИКСИРОВАНЫ

### 1. ✅ Главная коррекция
- **Interval:** 15 минут (фиксировано)
- **Обоснование:** Избежать micro-regime clustering, захватить разные состояния рынка

### 2. ✅ Horizon 4h — тайминг реальный
- **Horizon:** 4h (240 минут)
- **Первые resolved:** Ожидаются через 4h+ после старта (≈16:46 UTC)
- **Полная выборка:** 6-8 часов (≈18:46-20:46 UTC)
- **Target:** 35 resolved trades

### 3. ✅ Режим чистого сбора
- **NO filters:** min_score=0.0 ✅
- **NO timeframe filters:** ✅
- **NO score boosts:** ✅
- **NO penalties:** ✅
- **Mode:** PURE DISCOVERY (чистая правда)

### 4. ✅ Контроль качества
- **Monitoring script:** `/app/backend/scripts/batch2_monitor.sh`
- **Частота проверки:** Каждые 30-60 мин
- **Команда:** `bash /app/backend/scripts/batch2_monitor.sh`

**Красные флаги (остановить, если увидишь):**
- Один символ > 80%
- Один timeframe > 80%
- Только BUY или только SHORT
- Один cluster > 90%

### 5. ✅ Расширенная аналитика готова

**После завершения (35 resolved) запустить:**

```bash
# A. Debug endpoint
curl http://localhost:8001/api/debug/features-from-shadow?experiment_id=batch2_4h

# B. Расширенный анализ
python3 scripts/batch_analysis.py --experiment batch2_4h --action all
```

**Что будет в отчете:**
- ✅ Score buckets (0.5-0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0)
- ✅ Side breakdown (LONG vs SHORT winrate, pnl)
- ✅ Time spread (start_time, end_time, duration)
- ✅ Concentration analysis (symbols, clusters, timeframes)

### 6. ✅ Критерий успеха Batch 2

**НЕ красивые цифры, а СТАБИЛЬНОСТЬ:**

```
4H timeframe:
  winrate ≥ 55%
  pnl > 0
  score monotonic correlation
  
→ edge = REAL
```

### 7. ✅ Развилка после Batch 2

**Вариант A (edge подтверждён):**
→ Phase C: Paper Trading (real execution bridge)

**Вариант B (edge слабый/нестабильный):**
→ Phase B: Signal Refinement (улучшение логики)

---

## 🔧 ТЕХНИЧЕСКИЕ ПАРАМЕТРЫ

```yaml
Experiment ID:        batch2_4h
Horizon:              4h (240 min)
Cycle Interval:       15 min
Max per Cycle:        5-7 trades (adaptive)
Target:               35 resolved trades
Deduplication:        1 trade per symbol per cycle
Sampling:             Random (prevent ranking bias)
```

---

## 📊 ТЕКУЩИЙ СТАТУС

**Запущено:** 2026-04-18 12:46:38 UTC

| Метрика | Значение |
|---------|----------|
| Total trades | 20 |
| Resolved | 0 |
| Pending | 20 |
| Progress | 0/35 (0%) |
| Status | ⏳ Sleeping (cycle 1 → 2) |

**Ожидаемое завершение:** 2026-04-18 20:46 UTC (±2h)

---

## 🛠️ КОМАНДЫ УПРАВЛЕНИЯ

### Мониторинг:
```bash
# Быстрый статус
bash scripts/batch2_monitor.sh

# Полный лог
tail -f /tmp/batch2_live.log

# Подключиться к tmux
tmux attach -t batch2
```

### Контроль качества (каждые 30-60 мин):
```bash
python3 scripts/batch_analysis.py --experiment batch2_4h --action summary
```

### После завершения:
```bash
# Расширенный анализ
python3 scripts/batch_analysis.py --experiment batch2_4h --action all

# Debug endpoint
curl http://localhost:8001/api/debug/features-from-shadow?experiment_id=batch2_4h
```

### Аварийная остановка:
```bash
tmux kill-session -t batch2
```

---

## 🔬 НАУЧНЫЙ ПОДХОД

**Batch 1 дал:** Надежду (100% winrate на aligned, но статистическая ловушка)

**Batch 2 даст:** Правду (реален ли edge на 4H, независимо от 1H шума)

**Цель:** Подтвердить или опровергнуть гипотезу о 4H edge с минимум 35 independent observations.

---

## 🚫 ЗАПРЕЩЕНО ДО ПОЛУЧЕНИЯ ДАННЫХ

- ❌ Добавлять фильтры в `signal_ranking.py`
- ❌ Включать auto-run
- ❌ Запускать paper trading execution
- ❌ Оптимизировать до proof from data
- ❌ Трогать Batch 1 данные (experiment_id=market_dynamic)

---

**Режим:** OBSERVE ONLY

**Следующий шаг:** Wait for 35 resolved trades (4-8 hours)
