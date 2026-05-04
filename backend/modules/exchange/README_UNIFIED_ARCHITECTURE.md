# Exchange Layer — Unified Architecture

## ✅ Что сделано

### 1. Unified Protocol (`base.py`)
- `ExchangeAdapter` — базовый протокол для всех адаптеров
- Все методы возвращают нормализованные модели
- Exchange-agnostic API

### 2. Normalized Models (`models.py`)
- `AccountInfo` — информация об аккаунте
- `Balance` — баланс (asset, free, locked, total)
- `Position` — позиция (symbol, side, qty, pnl, etc.)
- `Order` — ордер (order_id, symbol, side, type, status, etc.)
- `Fill` — fill/trade (fill_id, order_id, price, qty, fee, etc.)

### 3. Paper Adapter V2 (`paper_adapter_v2.py`)
- Реализует `ExchangeAdapter` protocol
- Возвращает нормализованные модели (`Balance`, `Order`, `Fill`)
- Упрощённая логика execution (TODO: восстановить full execution quality)

### 4. Exchange Service V2 (`service_v2.py`)
- Unified facade для всех адаптеров
- Поддерживает переключение: `PAPER` / `BINANCE_TESTNET` / `BYBIT_DEMO`
- Singleton pattern

## 🔌 Как использовать

### Backend

```python
from modules.exchange.service_v2 import get_exchange_service

# Get service
service = get_exchange_service()

# Connect to Paper
await service.connect("PAPER", {"initial_balance": 10000})

# Get adapter
adapter = service.get_adapter()

# Use unified methods
account_info = await adapter.get_account_info()
balances = await adapter.get_balances()
positions = await adapter.get_positions()
orders = await adapter.get_open_orders()
fills = await adapter.get_fills()

# Place order
order = await adapter.place_order({
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "quantity": 0.05
})
```

### API Routes

Существующие routes в `routes.py` уже работают с service.

## 📝 Следующие шаги (P0.1)

### ЭТАП 4: Binance Testnet Adapter

1. Создать `binance_adapter.py`
2. Реализовать `ExchangeAdapter` protocol
3. Интеграция с Binance Testnet API
4. Signature & auth
5. Нормализация данных

### Минимальные методы для старта:
- `connect()`
- `get_account_info()`
- `get_balances()`
- `get_positions()`
- `place_order()`
- `get_fills()`

### ЭТАП 5: Exchange Service Integration

1. Добавить `BinanceAdapter` в `service_v2.py`
2. Тестирование подключения
3. UI для API keys (System workspace)

## ⚠️ ВАЖНО

### НЕ ДЕЛАТЬ:
- ❌ Начинать с UI для API keys
- ❌ Писать Binance-specific logic в routes
- ❌ Возвращать сырые данные Binance в API

### ДЕЛАТЬ:
- ✅ Всегда возвращать нормализованные модели
- ✅ Все exchange-specific логика — внутри адаптера
- ✅ Routes / UI работают только с нормализованными моделями

## 🎯 Acceptance Criteria P0.1

**ЭТАП 1-3 (DONE):**
- [x] `ExchangeAdapter` protocol
- [x] Normalized models
- [x] Paper adapter v2

**ЭТАП 4-5 (TODO):**
- [ ] Binance Testnet connects
- [ ] Account info normalized
- [ ] Balances normalized
- [ ] Orders normalized
- [ ] Fills normalized
- [ ] Place order works
- [ ] Service facade supports Binance

## 📊 Статус

| Component | Status |
|-----------|--------|
| Protocol | ✅ DONE |
| Models | ✅ DONE |
| Paper V2 | ✅ DONE |
| Service V2 | ✅ DONE |
| Binance Adapter | ⏳ TODO |
| Bybit Adapter | ⏳ TODO |
| Routes Integration | ⏳ TODO |

## 🚀 Готов к ЭТАП 4

**Следующая команда:**
```bash
Создать binance_adapter.py
```
