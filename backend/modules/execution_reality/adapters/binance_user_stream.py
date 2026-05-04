"""Binance User Data Stream (WebSocket)

Слушает execution reports от Binance и превращает их в канонические события.
"""

import asyncio
import json
import logging
from typing import Optional

try:
    import websockets
except ImportError:
    websockets = None

logger = logging.getLogger(__name__)


class BinanceUserStream:
    """WebSocket listener для Binance User Data Stream"""

    def __init__(
        self,
        stream_url: str,
        mapper,
        event_store,
        event_bus,
        listen_key_provider
    ):
        """
        Args:
            stream_url: wss://stream.binance.com:9443/ws
            mapper: BinanceMapperV2
            event_store: ExecutionEventStore
            event_bus: ExecutionEventBus
            listen_key_provider: BinanceListenKeyProvider
        """
        self.stream_url = stream_url
        self.mapper = mapper
        self.event_store = event_store
        self.event_bus = event_bus
        self.listen_key_provider = listen_key_provider
        self._running = False
        self._ws_task: Optional[asyncio.Task] = None

    async def start(self):
        """Запустить user stream listener (с автореконнектом)"""
        if websockets is None:
            logger.error("websockets library not installed, cannot start user stream")
            return

        self._running = True
        logger.info("🚀 Starting Binance User Stream...")

        while self._running:
            try:
                listen_key = await self.listen_key_provider.get_listen_key()
                url = f"{self.stream_url}/{listen_key}"

                logger.info(f"Connecting to user stream: {url[:50]}...")

                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=20
                ) as ws:
                    logger.info("✅ User stream connected")

                    async for raw_message in ws:
                        if not self._running:
                            break

                        try:
                            msg = json.loads(raw_message)
                            await self.handle_message(msg)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse message: {e}")
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")

            except Exception as e:
                logger.error(f"User stream connection error: {e}")
                if self._running:
                    logger.info("Reconnecting in 3 seconds...")
                    await asyncio.sleep(3)

        logger.info("User stream stopped")

    async def handle_message(self, msg: dict):
        """Обработать сообщение из user stream"""
        event_type = msg.get("e")

        if event_type == "executionReport":
            # Главное событие: execution report
            event = self.mapper.map_execution_report(msg)
            if event:
                await self.event_store.append(event)
                await self.event_bus.publish(event)
                logger.info(f"📥 ExecutionReport → {event.event_type} | {event.client_order_id}")

        elif event_type == "outboundAccountPosition":
            # Обновление баланса
            event = self.mapper.map_balance_update(msg)
            if event:
                await self.event_store.append(event)
                await self.event_bus.publish(event)
                logger.debug(f"📥 Balance snapshot received")

        else:
            # Неизвестный event type (например listStatus и т.д.)
            logger.debug(f"Unhandled user stream event: {event_type}")

    def stop(self):
        """Остановить user stream"""
        logger.info("Stopping user stream...")
        self._running = False

    async def start_background(self):
        """Запустить user stream в фоновой задаче"""
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = asyncio.create_task(self.start())
            logger.info("User stream started in background")
        else:
            logger.warning("User stream already running")
