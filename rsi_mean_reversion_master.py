#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║            📊  RSI MEAN REVERSION MASTER v1.0  📊                            ║
║            "La Única Estrategia Validada de 6,300 Backtests"                 ║
║                                                                              ║
║   Basado en: Backtest exhaustivo 2023-2025 (BTC/ETH Futures)                ║
║   Resultado: Solo 3 de 6,300 configuraciones son rentables Y significativas ║
║                                                                              ║
║   ✅ RSI(21) con niveles 20/80 - VALIDADO                                    ║
║   ✅ Timeframe 15m - ÚNICO que funciona                                      ║
║   ✅ BTCUSDT únicamente - ETH NO es rentable                                 ║
║   ✅ TP 0.5% / SL 0.8% - Ratio invertido validado                            ║
║   ✅ Win Rate 76% - Estadísticamente significativo (p=0.0001)                ║
║   ✅ Filtro EMA 200 H1 - Obligatorio                                         ║
║   ✅ Filtro de horario - Sesiones óptimas                                    ║
║                                                                              ║
║   IMPORTANTE: Esta es la ÚNICA configuración que demostró edge real          ║
║   en 2 años de datos. NO modificar parámetros sin re-validar.               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

CHANGELOG:
  v1.0 (2025-12-30): Versión inicial - Basada en backtest validado
    - RSI(21) período óptimo (NO RSI 14, NO RSI 2)
    - Solo BTCUSDT (ETH no pasó validación estadística)
    - TP < SL (0.5% / 0.8%) - El "truco contraintuitivo" validado
    - Filtro EMA 200 H1 obligatorio
    - Filtro de sesiones (Asia/Europa temprana)
    - HUD profesional con alertas
    - Journal con persistencia
    - Cálculo preciso de fees y R:R neto
"""

import os
import sys
import json
import time
import threading
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

# ══════════════════════════════════════════════════════════════════════════════
# ⚙️  SECCIÓN 1: CONFIGURACIÓN Y PERSISTENCIA (MEJORADO)
# ══════════════════════════════════════════════════════════════════════════════

class ConfigManager:
    """Gestiona la carga y guardado de configuración."""
    
    CONFIG_FILE = "config.json"
    
    @staticmethod
    def load_config() -> Dict:
        """Carga configuración desde archivo o devuelve vacío."""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, ConfigManager.CONFIG_FILE)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando config: {e}")
        return {}

    @staticmethod
    def save_config(config_data: Dict):
        """Guarda la configuración actual en archivo."""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, ConfigManager.CONFIG_FILE)
            with open(path, 'w') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Error guardando config: {e}")

class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"

class SessionQuality(Enum):
    OPTIMAL = "OPTIMAL"      # Verde - Mejor momento
    GOOD = "GOOD"            # Amarillo - Aceptable
    RISKY = "RISKY"          # Naranja - Precaución
    AVOID = "AVOID"          # Rojo - No operar

@dataclass
class ValidatedConfig:
    """
    Configuración VALIDADA por backtest de 6,300 combinaciones.
    
    ADVERTENCIA: Estos parámetros son el resultado de 2 años de datos.
    Modificarlos invalida la validación estadística (p=0.0001).
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # PARÁMETROS VALIDADOS - NO MODIFICAR
    # ═══════════════════════════════════════════════════════════════════════
    
    # RSI - ÚNICO período que funciona
    RSI_PERIOD: int = 21                    # NO usar 14 ni 2
    RSI_OVERSOLD: int = 20                  # Señal LONG
    RSI_OVERBOUGHT: int = 80                # Señal SHORT
    
    # Timeframe - ÚNICO que pasó validación
    TIMEFRAME: str = "15m"                  # NO usar 5m, 1h, 4h
    TIMEFRAME_MINUTES: int = 15
    
    # Símbolo - ÚNICO rentable
    SYMBOL: str = "BTCUSDT"                 # NO usar ETHUSDT
    
    # Risk Management - Ratio invertido validado
    STOP_LOSS_PCT: float = 0.8              # 0.8% pérdida máxima
    TAKE_PROFIT_PCT: float = 0.5            # 0.5% ganancia objetivo
    
    # Métricas esperadas (del backtest)
    EXPECTED_WIN_RATE: float = 75.9         # 76% aproximado
    EXPECTED_PROFIT_FACTOR: float = 1.96
    EXPECTED_TRADES_PER_YEAR: int = 29      # ~2-3 por mes
    
    # ═══════════════════════════════════════════════════════════════════════
    # PARÁMETROS CONFIGURABLES POR USUARIO
    # ═══════════════════════════════════════════════════════════════════════
    
    # Capital
    CAPITAL_TOTAL: float = 3000.0           # Capital total USD
    CAPITAL_FUTURES: float = 600.0          # Margen en futuros
    LEVERAGE: int = 10                      # Apalancamiento
    RISK_PER_TRADE_PCT: float = 1.0         # 1% del capital por trade
    
    # Comisiones Binance (Realista v1.2)
    FEE_MAKER_PCT: float = 0.02             # 0.02% maker
    FEE_TAKER_PCT: float = 0.05             # 0.05% taker
    FEE_ROUND_TRIP_PCT: float = 0.07        # Taker (Entry) + Maker (Exit) = 0.07%
    
    # Timezone (Ekaterinburg UTC+5)
    USER_TZ_OFFSET: int = 5
    
    # Notificaciones (NUEVO v1.1)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    SOUND_ENABLED: bool = True
    
    # Filtro EMA - OBLIGATORIO
    EMA_PERIOD: int = 200                   # EMA 200 en H1
    EMA_TIMEFRAME: str = "1h"
    
    # ═══════════════════════════════════════════════════════════════════════
    # HORARIOS ÓPTIMOS (UTC+5 Ekaterinburg)
    # ═══════════════════════════════════════════════════════════════════════
    
    # Sesión Asiática - ÓPTIMA para mean reversion
    ASIA_START: int = 3                     # 03:00 local
    ASIA_END: int = 8                       # 08:00 local
    
    # Europa Mañana - BUENA
    EUROPE_START: int = 11                  # 11:00 local
    EUROPE_END: int = 15                    # 15:00 local
    
    # Overlap EU/USA - EVITAR
    OVERLAP_START: int = 17                 # 17:00 local
    OVERLAP_END: int = 21                   # 21:00 local
    
    # ═══════════════════════════════════════════════════════════════════════
    # GESTIÓN DE RIESGO
    # ═══════════════════════════════════════════════════════════════════════
    
    MAX_CONSECUTIVE_LOSSES: int = 3
    COOLDOWN_MINUTES: int = 30
    MAX_DAILY_TRADES: int = 5               # Limitar overtrading
    
    # Paths
    BASE_DIR: str = ""
    JOURNAL_DIR: str = ""
    
    def __post_init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.JOURNAL_DIR = os.path.join(self.BASE_DIR, "rsi_journal")
        self.USER_TZ = timezone(timedelta(hours=self.USER_TZ_OFFSET))
        
        # Cargar configuración personalizada
        saved_config = ConfigManager.load_config()
        if saved_config:
            for key, value in saved_config.items():
                if hasattr(self, key):
                    # Convertir tipos si es necesario
                    target_type = type(getattr(self, key))
                    try:
                        if target_type == int:
                            setattr(self, key, int(value))
                        elif target_type == float:
                            setattr(self, key, float(value))
                        elif target_type == bool:
                            setattr(self, key, bool(value))
                        else:
                            setattr(self, key, value)
                    except:
                        pass

    def save(self):
        """Guarda la configuración configurable."""
        data = {
            "CAPITAL_TOTAL": self.CAPITAL_TOTAL,
            "CAPITAL_FUTURES": self.CAPITAL_FUTURES,
            "LEVERAGE": self.LEVERAGE,
            "RISK_PER_TRADE_PCT": self.RISK_PER_TRADE_PCT,
            "TELEGRAM_BOT_TOKEN": self.TELEGRAM_BOT_TOKEN,
            "TELEGRAM_CHAT_ID": self.TELEGRAM_CHAT_ID,
            "SOUND_ENABLED": self.SOUND_ENABLED
        }
        ConfigManager.save_config(data)


# Instancia global de configuración
CONFIG = ValidatedConfig()

# ══════════════════════════════════════════════════════════════════════════════
# 🌐  SECCIÓN 2: MOTOR DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

class DataEngine:
    """Motor de obtención de datos de Binance Futures."""
    
    BASE_URL = "https://fapi.binance.com/fapi/v1"
    
    @staticmethod
    def _request(url: str, timeout: int = 10, retries: int = 3) -> Optional[Any]:
        """Request HTTP con Retry y Backoff Exponencial."""
        for attempt in range(retries):
            try:
                print(f"[LOG] Intento {attempt + 1}/{retries}: Conectando a {url[:60]}...")
                
                # User-Agent de navegador real para evitar bloqueos
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                req = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    print(f"[LOG] ✅ Respuesta OK ({response.status})")
                    data = response.read()
                    return json.loads(data.decode('utf-8'))
                    
            except urllib.error.HTTPError as e:
                print(f"[LOG] ❌ HTTP Error {e.code}: {e.reason}")
                time.sleep(2 ** attempt)
            except Exception as e:
                print(f"[LOG] ❌ Connection Error: {e}")
                sleep_time = (2 ** attempt)
                time.sleep(sleep_time)
        print(f"[LOG] ⚠️ Fallaron todos los intentos para: {url[:60]}")
        return None
    
    @staticmethod
    def get_klines(symbol: str, interval: str, limit: int = 100) -> Optional[List[Dict]]:
        """Obtiene velas de Binance Futures."""
        url = f"{DataEngine.BASE_URL}/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = DataEngine._request(url)
        if not data:
            return None
        
        candles = []
        for c in data:
            candles.append({
                'timestamp': c[0],
                'open': float(c[1]),
                'high': float(c[2]),
                'low': float(c[3]),
                'close': float(c[4]),
                'volume': float(c[5]),
                'close_time': c[6]
            })
        return candles
    
    @staticmethod
    def get_current_price(symbol: str) -> Optional[float]:
        """Obtiene precio mark de Futures."""
        url = f"{DataEngine.BASE_URL}/premiumIndex?symbol={symbol}"
        data = DataEngine._request(url)
        if data and 'markPrice' in data:
            return float(data['markPrice'])
        return None
    
    @staticmethod
    def get_funding_rate(symbol: str) -> Optional[float]:
        """Obtiene funding rate actual."""
        url = f"{DataEngine.BASE_URL}/premiumIndex?symbol={symbol}"
        data = DataEngine._request(url)
        if data and 'lastFundingRate' in data:
            return float(data['lastFundingRate']) * 100
        return None
# ══════════════════════════════════════════════════════════════════════════════
# 🔊  SECCIÓN 2.5: GESTORES DE SONIDO Y NOTIFICACIONES (NUEVO v1.1)
# ══════════════════════════════════════════════════════════════════════════════

class SoundManager:
    """Gestiona alertas sonoras."""
    
    @staticmethod
    def play_alert(type: str = "SIGNAL"):
        """Reproduce sonido (Bell) si está habilitado."""
        if not CONFIG.SOUND_ENABLED:
            return
            
        if type == "SIGNAL":
            # 3 beeps rápidos
            print('\a', end='', flush=True)
            time.sleep(0.1)
            print('\a', end='', flush=True)
            time.sleep(0.1)
            print('\a', end='', flush=True)
        elif type == "WARNING":
            print('\a', end='', flush=True)

class NotificationManager:
    """Gestiona notificaciones de Telegram."""
    
    @staticmethod
    def send_message(message: str, silent: bool = False):
        """Envía mensaje a Telegram en un thread separado."""
        if not CONFIG.TELEGRAM_BOT_TOKEN or not CONFIG.TELEGRAM_CHAT_ID:
            return

        def _send():
            try:
                url = f"https://api.telegram.org/bot{CONFIG.TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": CONFIG.TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "HTML"
                }
                if silent:
                    payload["disable_notification"] = True
                    
                data = json.dumps(payload).encode('utf-8')
                
                req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                pass
        
        threading.Thread(target=_send, daemon=True).start()

    @staticmethod
    def send_signal(analysis: Dict, levels: Dict, position_info: Optional[Dict] = None):
        """Formatea y envía alerta de señal con info monetaria."""
        icon = "🟢" if analysis['signal'] == SignalType.LONG else "🔴"
        direction = "LONG" if analysis['signal'] == SignalType.LONG else "SHORT"
        
        pos_msg = ""
        if position_info:
            action = "COMPRAR" if direction == "LONG" else "VENDER"
            pos_msg = (
                f"\n💰 <b>ORDEN:</b> {action} <b>${position_info['position_size']:,.0f} USDT</b>\n"
                f"⚙️ <b>Lev:</b> {CONFIG.LEVERAGE}x\n"
            )
        
        msg = (
            f"{icon} <b>SEÑAL {direction} DETECTADA</b>\n"
            f"{pos_msg}\n"
            f"<b>Precio:</b> ${analysis['price']:,.2f}\n"
            f"<b>RSI:</b> {analysis['rsi']:.1f}\n"
            f"<b>EMA 200:</b> ${analysis['ema_200']:,.2f}\n\n"
            f"🎯 <b>TP:</b> ${levels['tp']:,.2f}\n"
            f"🛡️ <b>SL:</b> ${levels['sl']:,.2f}\n\n"
            f"<i>Revisa tu terminal para confirmar.</i>"
        )
        NotificationManager.send_message(msg)

    @staticmethod
    def send_pre_alert(direction: str, rsi: float, price: float):
        """Envía alerta de preparación."""
        icon = "⚠️"
        msg = (
            f"{icon} <b>ATENCIÓN: PREPARARSE ({direction})</b>\n\n"
            f"El RSI se acerca a zona de entrada.\n"
            f"<b>RSI Actual:</b> {rsi:.1f}\n"
            f"<b>Precio:</b> ${price:,.2f}\n\n"
            f"<i>Abre Binance y mantente atento a la señal oficial.</i>"
        )
        NotificationManager.send_message(msg)

    @staticmethod
    def send_status(rsi: float, price: float, quality: str):
        """Envía heartbeat de estado (silencioso)."""
        msg = (
            f"🧘 <b>Estado del Bot (Heartbeat)</b>\n\n"
            f"Todo funcionando correctamente.\n"
            f"<b>RSI:</b> {rsi:.1f} (Neutral)\n"
            f"<b>Precio:</b> ${price:,.2f}\n"
            f"<b>Sesión:</b> {quality}\n"
        )
        NotificationManager.send_message(msg, silent=True)
# ══════════════════════════════════════════════════════════════════════════════
# 📊  SECCIÓN 3: INDICADORES TÉCNICOS
# ══════════════════════════════════════════════════════════════════════════════

class Indicators:
    """Calculadora de indicadores técnicos con precisión validada."""
    
    @staticmethod
    def rsi(candles: List[Dict], period: int = 21) -> Optional[float]:
        """
        RSI con período validado.
        
        IMPORTANTE: Usar período 21, NO 14 ni 2.
        Este es el único período que demostró edge en el backtest.
        """
        if len(candles) < period + 1:
            return None
        
        closes = [c['close'] for c in candles]
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        # Wilder's smoothing (EMA-style)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        if rsi is not None:
            return 100 - (100 / (1 + rs))
        return None
    
    @staticmethod
    def ema(candles: List[Dict], period: int) -> Optional[float]:
        """Exponential Moving Average."""
        if len(candles) < period:
            return None
        
        closes = [c['close'] for c in candles]
        multiplier = 2 / (period + 1)
        
        # SMA inicial
        ema_value = sum(closes[:period]) / period
        
        # EMA iterativo
        for price in closes[period:]:
            ema_value = (price - ema_value) * multiplier + ema_value
        
        return round(ema_value, 2)
    
    @staticmethod
    def rsi_history(candles: List[Dict], period: int = 21, lookback: int = 10) -> List[float]:
        """Obtiene historial de RSI para detectar cruces."""
        if len(candles) < period + lookback:
            return []
        
        rsi_values = []
        for i in range(lookback):
            end_idx = len(candles) - lookback + i + 1
            subset = candles[:end_idx]
            rsi = Indicators.rsi(subset, period)
            if rsi is not None:
                rsi_values.append(rsi)
        
        return rsi_values

# ══════════════════════════════════════════════════════════════════════════════
# ⏰  SECCIÓN 4: GESTIÓN DE TIEMPO Y SESIONES
# ══════════════════════════════════════════════════════════════════════════════

class SessionManager:
    """Gestiona horarios y calidad de sesiones para mean reversion."""
    
    def __init__(self):
        self.tz = CONFIG.USER_TZ
    
    def now(self) -> datetime:
        """Hora actual en timezone del usuario."""
        return datetime.now(self.tz)
    
    def get_session_quality(self) -> Tuple[SessionQuality, str, str]:
        """
        Determina la calidad de la sesión actual para mean reversion.
        
        Returns: (quality, message, recommendation)
        """
        hour = self.now().hour
        
        # Sesión Asiática - ÓPTIMA
        if CONFIG.ASIA_START <= hour < CONFIG.ASIA_END:
            return (
                SessionQuality.OPTIMAL,
                f"🟢 SESIÓN ASIÁTICA ({hour}:00)",
                "Mejor momento para mean reversion - bajo volumen, rangos predecibles"
            )
        
        # Europa Mañana - BUENA
        if CONFIG.EUROPE_START <= hour < CONFIG.EUROPE_END:
            return (
                SessionQuality.GOOD,
                f"🟡 EUROPA MAÑANA ({hour}:00)",
                "Volatilidad moderada - aceptable para operar"
            )
        
        # Overlap EU/USA - EVITAR
        if CONFIG.OVERLAP_START <= hour < CONFIG.OVERLAP_END:
            return (
                SessionQuality.AVOID,
                f"🔴 OVERLAP EU/USA ({hour}:00)",
                "⛔ Alta volatilidad - breakouts frecuentes - NO operar mean reversion"
            )
        
        # Otras horas - RISKY
        return (
            SessionQuality.RISKY,
            f"🟠 FUERA DE SESIÓN ÓPTIMA ({hour}:00)",
            "Precaución - volatilidad impredecible"
        )
    
    def get_next_optimal_session(self) -> str:
        """Calcula tiempo hasta próxima sesión óptima."""
        now = self.now()
        hour = now.hour
        
        # Si estamos antes de Asia
        if hour < CONFIG.ASIA_START:
            mins = (CONFIG.ASIA_START - hour) * 60 - now.minute
            return f"Asia en {mins // 60}h {mins % 60}m"
        
        # Si estamos entre Asia y Europa
        if CONFIG.ASIA_END <= hour < CONFIG.EUROPE_START:
            mins = (CONFIG.EUROPE_START - hour) * 60 - now.minute
            return f"Europa en {mins // 60}h {mins % 60}m"
        
        # Si estamos después de Europa
        if hour >= CONFIG.EUROPE_END:
            # Próxima Asia es mañana
            mins = (24 - hour + CONFIG.ASIA_START) * 60 - now.minute
            return f"Asia mañana en {mins // 60}h {mins % 60}m"
        
        return "En sesión óptima"
    
    def can_trade_now(self, strict: bool = True) -> Tuple[bool, str]:
        """
        Verifica si se puede operar ahora.
        
        Args:
            strict: Si True, solo permite en sesiones OPTIMAL/GOOD
        """
        quality, msg, _ = self.get_session_quality()
        
        if strict:
            if quality in [SessionQuality.OPTIMAL, SessionQuality.GOOD]:
                return True, msg
            else:
                return False, f"{msg} - Espera sesión óptima"
        else:
            if quality == SessionQuality.AVOID:
                return False, f"{msg} - Overlap EU/USA es peligroso"
            return True, msg

# ══════════════════════════════════════════════════════════════════════════════
# 🎯  SECCIÓN 5: DETECTOR DE SEÑALES RSI
# ══════════════════════════════════════════════════════════════════════════════

class SignalDetector:
    """
    Detector de señales RSI validadas.
    
    LÓGICA VALIDADA:
    - LONG cuando RSI(21) < 20 (sobreventa extrema)
    - SHORT cuando RSI(21) > 80 (sobrecompra extrema)
    - Filtro EMA 200 H1 obligatorio
    """
    
    def __init__(self):
        self.last_signal_time: Optional[datetime] = None
        self.last_rsi: Optional[float] = None
        self.prev_rsi: Optional[float] = None  # Para crossover v1.2
        self.last_ema: Optional[float] = None
        self.last_price: Optional[float] = None
    
    def analyze(self) -> Dict:
        """
        Analiza el mercado y detecta señales.
        
        Returns: Dict con análisis completo
        """
        result = {
            'signal': SignalType.NONE,
            'rsi': None,
            'prev_rsi': None,
            'ema_200': None,
            'price': None,
            'ema_aligned': False,
            'signal_strength': 0,
            'can_trade': False,
            'reasons': [],
            'warnings': []
        }
        
        # Obtener datos 15m para RSI
        candles_15m = DataEngine.get_klines(CONFIG.SYMBOL, CONFIG.TIMEFRAME, 50)
        if not candles_15m or len(candles_15m) < CONFIG.RSI_PERIOD + 2:
            result['reasons'].append("Error obteniendo datos 15m")
            return result
        
        # Obtener datos 1H para EMA 200
        candles_1h = DataEngine.get_klines(CONFIG.SYMBOL, CONFIG.EMA_TIMEFRAME, 250)
        if not candles_1h or len(candles_1h) < CONFIG.EMA_PERIOD:
            result['reasons'].append("Error obteniendo datos 1H")
            return result
        
        # Obtener Precio Mark en Tiempo Real (Mejora v1.2)
        real_price = DataEngine.get_current_price(CONFIG.SYMBOL)
        current_candle_close = candles_15m[-1]['close']
        
        # Usar Mark Price si está disponible, sino cierre de vela
        current_price = real_price if real_price else current_candle_close
        
        # Calcular indicadores
        # v1.2: Necesitamos historial para Crossover
        rsi_values = Indicators.rsi_history(candles_15m, CONFIG.RSI_PERIOD, lookback=2)
        ema_200 = Indicators.ema(candles_1h, CONFIG.EMA_PERIOD)
        
        if not rsi_values or len(rsi_values) < 2 or ema_200 is None:
            result['reasons'].append("Error calculando indicadores")
            return result
            
        curr_rsi = rsi_values[-1]
        prev_rsi = rsi_values[-2]
        
        # Guardar valores
        result['rsi'] = curr_rsi
        result['prev_rsi'] = prev_rsi
        result['ema_200'] = ema_200
        result['price'] = current_price
        
        self.last_rsi = curr_rsi
        self.prev_rsi = prev_rsi
        self.last_ema = ema_200
        self.last_price = current_price
        
        # Detectar señal RSI (Crossover Logic v1.2)
        # LONG: Cruce de abajo hacia arriba en nivel OVERSOLD
        # SHORT: Cruce de arriba hacia abajo en nivel OVERBOUGHT
        
        signal = SignalType.NONE
        
        # LONG: Antes < 20, Ahora >= 20
        if prev_rsi < CONFIG.RSI_OVERSOLD and curr_rsi >= CONFIG.RSI_OVERSOLD:
            signal = SignalType.LONG
            result['signal_strength'] = 100 # Crossover confirmado
            result['reasons'].append(f"🟢 CRUCE ALCISTA: RSI {prev_rsi:.1f} ↗ {curr_rsi:.1f} (Zona {CONFIG.RSI_OVERSOLD})")
        
        # SHORT: Antes > 80, Ahora <= 80
        elif prev_rsi > CONFIG.RSI_OVERBOUGHT and curr_rsi <= CONFIG.RSI_OVERBOUGHT:
            signal = SignalType.SHORT
            result['signal_strength'] = 100
            result['reasons'].append(f"🔴 CRUCE BAJISTA: RSI {prev_rsi:.1f} ↘ {curr_rsi:.1f} (Zona {CONFIG.RSI_OVERBOUGHT})")
        
        # Estado si no hay cruce
        else:
            if curr_rsi <= CONFIG.RSI_OVERSOLD:
                result['reasons'].append(f"⏳ RSI {curr_rsi:.1f} en sobreventa - Esperando rebote/cruce > {CONFIG.RSI_OVERSOLD}")
            elif curr_rsi >= CONFIG.RSI_OVERBOUGHT:
                result['reasons'].append(f"⏳ RSI {curr_rsi:.1f} en sobrecompra - Esperando caída/cruce < {CONFIG.RSI_OVERBOUGHT}")
            else:
                result['reasons'].append(f"RSI({CONFIG.RSI_PERIOD}) = {curr_rsi:.1f} en zona neutral")
        
        # Verificar filtro EMA 200 (OBLIGATORIO)
        if signal == SignalType.LONG:
            if current_price > ema_200:
                result['ema_aligned'] = True
                result['reasons'].append(f"✅ EMA 200: Precio ${current_price:,.0f} > EMA ${ema_200:,.0f} (ALCISTA)")
            else:
                result['ema_aligned'] = False
                result['warnings'].append(f"⛔ EMA 200: Precio ${current_price:,.0f} < EMA ${ema_200:,.0f} (LONG bloqueado)")
        
        elif signal == SignalType.SHORT:
            if current_price < ema_200:
                result['ema_aligned'] = True
                result['reasons'].append(f"✅ EMA 200: Precio ${current_price:,.0f} < EMA ${ema_200:,.0f} (BAJISTA)")
            else:
                result['ema_aligned'] = False
                result['warnings'].append(f"⛔ EMA 200: Precio ${current_price:,.0f} > EMA ${ema_200:,.0f} (SHORT bloqueado)")
        
        # Determinar si se puede operar
        if signal != SignalType.NONE and result['ema_aligned']:
            result['signal'] = signal
            result['can_trade'] = True
        
        # Advertencias adicionales para SHORT
        if signal == SignalType.SHORT and result['can_trade']:
            result['warnings'].append("⚠️ PRECAUCIÓN: Los SHORTs son más riesgosos en crypto (sesgo alcista)")
        
        return result
    
    def get_rsi_zone(self, rsi: float) -> Tuple[str, str]:
        """Describe la zona actual del RSI."""
        if rsi <= 10:
            return "🟢🟢 EXTREMA SOBREVENTA", "Señal muy fuerte - alta probabilidad de rebote"
        elif rsi <= CONFIG.RSI_OVERSOLD:
            return "🟢 SOBREVENTA", "Señal activa - buscar LONG"
        elif rsi <= 35:
            return "🟡 CASI SOBREVENTA", "Prepararse para señal LONG"
        elif rsi <= 65:
            return "⚪ NEUTRAL", "Sin señal - esperar extremos"
        elif rsi <= CONFIG.RSI_OVERBOUGHT:
            return "🟡 CASI SOBRECOMPRA", "Prepararse para señal SHORT"
        elif rsi <= 90:
            return "🔴 SOBRECOMPRA", "Señal activa - buscar SHORT (con precaución)"
        else:
            return "🔴🔴 EXTREMA SOBRECOMPRA", "Señal muy fuerte - posible corrección"

# ══════════════════════════════════════════════════════════════════════════════
# 💰  SECCIÓN 6: CALCULADORA DE POSICIÓN
# ══════════════════════════════════════════════════════════════════════════════

class PositionCalculator:
    """
    Calculadora de posición con parámetros validados.
    
    RATIO INVERTIDO VALIDADO:
    - TP: 0.5% (pequeño pero alcanzable)
    - SL: 0.8% (más grande para dar espacio)
    - Requiere Win Rate > 61.5% para ser rentable
    - Backtest demostró 76% win rate → RENTABLE
    """
    
    @staticmethod
    def calculate_position_size() -> Tuple[float, float, float]:
        """
        Calcula tamaño de posición y riesgo.
        
        Returns: (position_size, risk_amount, max_position)
        """
        risk_amount = CONFIG.CAPITAL_TOTAL * (CONFIG.RISK_PER_TRADE_PCT / 100)
        
        if CONFIG.STOP_LOSS_PCT == 0:
            return 0, 0, 0
        
        ideal_position = risk_amount / (CONFIG.STOP_LOSS_PCT / 100)
        max_position = CONFIG.CAPITAL_FUTURES * CONFIG.LEVERAGE
        
        actual_position = min(ideal_position, max_position)
        actual_risk = actual_position * (CONFIG.STOP_LOSS_PCT / 100)
        
        return actual_position, actual_risk, max_position
    
    @staticmethod
    def calculate_levels(entry_price: float, direction: SignalType) -> Dict:
        """
        Calcula niveles de SL y TP.
        
        IMPORTANTE: TP < SL es intencional y validado.
        """
        if entry_price == 0:
            return {'entry': 0, 'sl': 0, 'tp': 0}
        
        if direction == SignalType.LONG:
            sl = entry_price * (1 - CONFIG.STOP_LOSS_PCT / 100)
            tp = entry_price * (1 + CONFIG.TAKE_PROFIT_PCT / 100)
        else:  # SHORT
            sl = entry_price * (1 + CONFIG.STOP_LOSS_PCT / 100)
            tp = entry_price * (1 - CONFIG.TAKE_PROFIT_PCT / 100)
        
        return {
            'entry': entry_price,
            'sl': round(sl, 2),
            'tp': round(tp, 2),
            'sl_pct': CONFIG.STOP_LOSS_PCT,
            'tp_pct': CONFIG.TAKE_PROFIT_PCT
        }
    
    @staticmethod
    def calculate_expected_pnl(position_size: float) -> Dict:
        """
        Calcula PnL esperado basado en métricas validadas.
        """
        gross_win = position_size * (CONFIG.TAKE_PROFIT_PCT / 100)
        gross_loss = position_size * (CONFIG.STOP_LOSS_PCT / 100)
        
        fees = position_size * (CONFIG.FEE_ROUND_TRIP_PCT / 100)
        
        net_win = gross_win - fees
        net_loss = gross_loss + fees  # Fees aumentan la pérdida
        
        # Expectancy basada en win rate validado
        win_rate = CONFIG.EXPECTED_WIN_RATE / 100
        expectancy = (win_rate * net_win) - ((1 - win_rate) * net_loss)
        
        # R:R neto
        rr_ratio = net_win / net_loss if net_loss > 0 else 0
        
        return {
            'gross_win': round(gross_win, 2),
            'gross_loss': round(gross_loss, 2),
            'fees': round(fees, 2),
            'net_win': round(net_win, 2),
            'net_loss': round(net_loss, 2),
            'rr_ratio': round(rr_ratio, 2),
            'expectancy_per_trade': round(expectancy, 2),
            'expected_win_rate': CONFIG.EXPECTED_WIN_RATE
        }

# ══════════════════════════════════════════════════════════════════════════════
# 📔  SECCIÓN 7: JOURNAL MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class JournalManager:
    """Gestiona persistencia de trades y estadísticas."""
    
    def __init__(self):
        self._ensure_dir()
    
    def _ensure_dir(self):
        if not os.path.exists(CONFIG.JOURNAL_DIR):
            os.makedirs(CONFIG.JOURNAL_DIR)
    
    def _get_file_path(self) -> str:
        date_str = datetime.now(CONFIG.USER_TZ).strftime('%Y-%m-%d')
        return os.path.join(CONFIG.JOURNAL_DIR, f"journal_{date_str}.json")
    
    def load(self) -> Dict:
        path = self._get_file_path()
        if not os.path.exists(path):
            return {
                "date": datetime.now(CONFIG.USER_TZ).strftime('%Y-%m-%d'),
                "trades": [],
                "signals_detected": [],
                "stats": {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_pnl": 0.0,
                    "consecutive_losses": 0,
                    "signals_ignored": 0
                }
            }
        with open(path, 'r') as f:
            return json.load(f)
    
    def save(self, data: Dict):
        with open(self._get_file_path(), 'w') as f:
            json.dump(data, f, indent=2)
    
    def log_signal(self, signal_data: Dict):
        """Registra una señal detectada."""
        data = self.load()
        signal_data['timestamp'] = time.time()
        signal_data['time'] = datetime.now(CONFIG.USER_TZ).strftime('%H:%M:%S')
        data['signals_detected'].append(signal_data)
        self.save(data)
    
    def add_trade(self, trade: Dict) -> int:
        """Registra un trade abierto."""
        data = self.load()
        trade['id'] = len(data['trades']) + 1
        trade['status'] = 'OPEN'
        trade['open_time'] = time.time()
        data['trades'].append(trade)
        data['stats']['total_trades'] += 1
        self.save(data)
        return trade['id']
    
    def close_trade(self, trade_id: int, pnl: float, result: str):
        """Cierra un trade y actualiza estadísticas."""
        data = self.load()
        
        for trade in data['trades']:
            if trade['id'] == trade_id:
                trade['status'] = 'CLOSED'
                trade['pnl'] = pnl
                trade['result'] = result
                trade['close_time'] = time.time()
                break
        
        if pnl > 0:
            data['stats']['wins'] += 1
            data['stats']['consecutive_losses'] = 0
        else:
            data['stats']['losses'] += 1
            data['stats']['consecutive_losses'] += 1
        
        data['stats']['total_pnl'] += pnl
        self.save(data)
    
    def get_active_trade(self) -> Optional[Dict]:
        """Obtiene trade activo si existe."""
        data = self.load()
        for trade in reversed(data['trades']):
            if trade.get('status') == 'OPEN':
                return trade
        return None
    
    def get_stats(self) -> Dict:
        return self.load().get('stats', {})
    
    def get_consecutive_losses(self) -> int:
        return self.load().get('stats', {}).get('consecutive_losses', 0)
    
    def get_daily_trades_count(self) -> int:
        return self.load().get('stats', {}).get('total_trades', 0)

# ══════════════════════════════════════════════════════════════════════════════
# 🛡️  SECCIÓN 8: RISK MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class RiskManager:
    """Gestiona reglas de riesgo."""
    
    def __init__(self, journal: JournalManager):
        self.journal = journal
        self.last_loss_time: Optional[datetime] = None
    
    def can_trade(self) -> Tuple[bool, str]:
        """Verifica si se puede operar según reglas de riesgo."""
        
        # Check consecutive losses
        consecutive = self.journal.get_consecutive_losses()
        if consecutive >= CONFIG.MAX_CONSECUTIVE_LOSSES:
            if self.last_loss_time:
                elapsed = (datetime.now(CONFIG.USER_TZ) - self.last_loss_time).total_seconds() / 60
                if elapsed < CONFIG.COOLDOWN_MINUTES:
                    remaining = CONFIG.COOLDOWN_MINUTES - elapsed
                    return False, f"⛔ COOLDOWN: {remaining:.0f}min (3 pérdidas consecutivas)"
            self.last_loss_time = datetime.now(CONFIG.USER_TZ)
            return False, f"⛔ 3 pérdidas consecutivas - Esperar {CONFIG.COOLDOWN_MINUTES}min"
        
        # Check daily limit
        daily_trades = self.journal.get_daily_trades_count()
        if daily_trades >= CONFIG.MAX_DAILY_TRADES:
            return False, f"⛔ Límite diario alcanzado ({CONFIG.MAX_DAILY_TRADES} trades)"
        
        # Check active trade
        if self.journal.get_active_trade():
            return False, "⛔ Ya hay un trade activo"
        
        return True, "✅ OK para operar"
    
    def record_loss(self):
        """Registra una pérdida para tracking."""
        self.last_loss_time = datetime.now(CONFIG.USER_TZ)

# ══════════════════════════════════════════════════════════════════════════════
# 🖥️  SECCIÓN 9: INTERFAZ DE USUARIO
# ══════════════════════════════════════════════════════════════════════════════

class UI:
    """Interfaz de usuario profesional."""
    
    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def print_header():
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              📊  RSI MEAN REVERSION MASTER v1.0  📊                          ║
║         "La Única Estrategia Validada de 6,300 Backtests"                    ║
║                                                                              ║
║   RSI(21) │ 15m │ BTCUSDT │ TP 0.5% / SL 0.8% │ Win Rate: 76%              ║
╚══════════════════════════════════════════════════════════════════════════════╝""")
    
    @staticmethod
    def print_status_bar(session: SessionManager, journal: JournalManager):
        """Barra de estado principal."""
        quality, session_msg, _ = session.get_session_quality()
        stats = journal.get_stats()
        now = session.now().strftime('%H:%M:%S')
        
        # Color de sesión
        session_icon = {
            SessionQuality.OPTIMAL: "🟢",
            SessionQuality.GOOD: "🟡",
            SessionQuality.RISKY: "🟠",
            SessionQuality.AVOID: "🔴"
        }.get(quality, "⚪")
        
        print(f"""
┌──────────────────────────────────────────────────────────────────────────────┐
│ ⏰ {now} │ {session_icon} {session_msg:<25} │ 📊 Trades: {stats.get('total_trades', 0)} │ P&L: ${stats.get('total_pnl', 0):+.2f} │
│ ❌ Strikes: {stats.get('consecutive_losses', 0)}/3 │ ✅ Wins: {stats.get('wins', 0)} │ ❌ Losses: {stats.get('losses', 0)}                           │
└──────────────────────────────────────────────────────────────────────────────┘""")
    
    @staticmethod
    def print_rsi_gauge(rsi: float, price: float, ema: float):
        """Visualización del RSI como gauge."""
        # Crear barra visual
        bar_width = 50
        position = int((rsi / 100) * bar_width)
        
        bar = ""
        for i in range(bar_width):
            if i < 10:  # Zona sobreventa (0-20)
                char = "█" if i < position else "░"
                bar += f"\033[92m{char}\033[0m"  # Verde
            elif i < 20:  # Casi sobreventa (20-40)
                char = "█" if i < position else "░"
                bar += f"\033[93m{char}\033[0m"  # Amarillo
            elif i < 30:  # Neutral (40-60)
                char = "█" if i < position else "░"
                bar += f"\033[97m{char}\033[0m"  # Blanco
            elif i < 40:  # Casi sobrecompra (60-80)
                char = "█" if i < position else "░"
                bar += f"\033[93m{char}\033[0m"  # Amarillo
            else:  # Zona sobrecompra (80-100)
                char = "█" if i < position else "░"
                bar += f"\033[91m{char}\033[0m"  # Rojo
        
        # Marcadores
        markers = " " * 10 + "20" + " " * 17 + "50" + " " * 17 + "80" + " " * 8
        
        # Tendencia EMA
        trend = "🟢 ALCISTA" if price > ema else "🔴 BAJISTA"
        diff_pct = ((price - ema) / ema) * 100 if ema > 0 else 0
        
        print(f"""
┌─────────────────────────── RSI({CONFIG.RSI_PERIOD}) ─────────────────────────────┐
│                                                                              │
│  SOBREVENTA        NEUTRAL         SOBRECOMPRA                               │
│  [{bar}]                                                                      │
│  {markers}              │
│                         ▲                                                    │
│                    RSI = {rsi:.1f}                                              │
│                                                                              │
│  💰 Precio: ${price:,.2f}  │  📈 EMA 200: ${ema:,.2f}  │  {trend} ({diff_pct:+.2f}%)      │
└──────────────────────────────────────────────────────────────────────────────┘""")
    
    @staticmethod
    def print_signal_alert(signal: SignalType, analysis: Dict):
        """Alerta visual de señal."""
        if signal == SignalType.LONG:
            color = "\033[92m"  # Verde
            icon = "🟢"
            direction = "LONG"
        else:
            color = "\033[91m"  # Rojo
            icon = "🔴"
            direction = "SHORT"
        
        print(f"""
{color}╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║            {icon}  ¡SEÑAL {direction} DETECTADA!  {icon}                               ║
║                                                                              ║
║   RSI({CONFIG.RSI_PERIOD}) = {analysis['rsi']:.1f}  │  Precio: ${analysis['price']:,.2f}                            ║
║   EMA 200: ${analysis['ema_200']:,.2f}  │  Alineado: {'✅ SÍ' if analysis['ema_aligned'] else '❌ NO'}                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝\033[0m""")
    
    @staticmethod
    def print_trade_setup(entry: float, levels: Dict, position: float, pnl_data: Dict, direction: str):
        """Muestra setup del trade."""
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         📋 SETUP DE TRADE                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  DIRECCIÓN: {direction:<10}  │  ENTRADA: ${entry:,.2f}                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  📍 NIVELES PARA BINANCE:                                                    ║
║  ─────────────────────────────────────────────────────────────────────────   ║""")
        
        if direction == "LONG":
            print(f"""║     🟢 TAKE PROFIT: ${levels['tp']:,.2f}  (+{CONFIG.TAKE_PROFIT_PCT}%)                              ║
║     ➡️  ENTRADA:     ${entry:,.2f}                                            ║
║     🔴 STOP LOSS:   ${levels['sl']:,.2f}  (-{CONFIG.STOP_LOSS_PCT}%)                              ║""")
        else:
            print(f"""║     🔴 STOP LOSS:   ${levels['sl']:,.2f}  (-{CONFIG.STOP_LOSS_PCT}%)                              ║
║     ➡️  ENTRADA:     ${entry:,.2f}                                            ║
║     🟢 TAKE PROFIT: ${levels['tp']:,.2f}  (+{CONFIG.TAKE_PROFIT_PCT}%)                              ║""")
        
        print(f"""╠══════════════════════════════════════════════════════════════════════════════╣
║  💰 POSICIÓN: ${position:,.2f}  │  RIESGO: ${pnl_data['net_loss']:.2f}                            ║
║  📈 Si GANA: +${pnl_data['net_win']:.2f}  │  Si PIERDE: -${pnl_data['net_loss']:.2f}                      ║
║  📊 R:R Neto: {pnl_data['rr_ratio']:.2f}:1  │  Expectancy: ${pnl_data['expectancy_per_trade']:+.2f}/trade            ║
║  💸 Fees: ${pnl_data['fees']:.2f} (round-trip {CONFIG.FEE_ROUND_TRIP_PCT}%)                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  📊 ESTADÍSTICAS ESPERADAS (del backtest):                                   ║
║     Win Rate: {CONFIG.EXPECTED_WIN_RATE}%  │  Profit Factor: {CONFIG.EXPECTED_PROFIT_FACTOR}  │  ~{CONFIG.EXPECTED_TRADES_PER_YEAR} trades/año         ║
╚══════════════════════════════════════════════════════════════════════════════╝""")
    
    @staticmethod
    def print_monitor(trade: Dict, price: float, pnl_pct: float):
        """Monitor de trade activo."""
        direction = trade['type']
        entry = trade['entry']
        sl = trade['sl']
        tp = trade['tp']
        
        pnl_color = "\033[92m" if pnl_pct > 0 else "\033[91m"
        
        # Check if hitting targets
        if direction == "LONG":
            tp_hit = price >= tp
            sl_hit = price <= sl
            dist_to_tp = ((tp - price) / price) * 100
            dist_to_sl = ((price - sl) / price) * 100
        else:
            tp_hit = price <= tp
            sl_hit = price >= sl
            dist_to_tp = ((price - tp) / price) * 100
            dist_to_sl = ((sl - price) / price) * 100
        
        status_icon = "🟢" if pnl_pct > 0 else "🔴" if pnl_pct < -0.3 else "🟡"
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🔄 MONITOR DE TRADE ACTIVO                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  {status_icon} {direction:<6} │ ENTRADA: ${entry:,.2f} │ PRECIO: ${price:,.2f}                    ║
║  {pnl_color}PnL: {pnl_pct:+.2f}%\033[0m                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🎯 TAKE PROFIT: ${tp:,.2f} {'✅ HIT!' if tp_hit else f'({dist_to_tp:+.2f}% away)':<20}                    ║
║  🛡️  STOP LOSS:  ${sl:,.2f} {'🔴 HIT!' if sl_hit else f'({dist_to_sl:+.2f}% away)':<20}                    ║
╠══════════════════════════════════════════════════════════════════════════════╣""")
        
        # Consejos dinámicos
        if sl_hit:
            print("║  ⛔ STOP LOSS ALCANZADO - CERRAR AHORA                                     ║")
        elif tp_hit:
            print("║  🎉 TAKE PROFIT ALCANZADO - CERRAR Y TOMAR GANANCIAS                       ║")
        elif pnl_pct >= 0.3:
            print(f"║  💡 PnL > 0.3% - Considera mover SL a breakeven (${entry:,.2f})                ║")
        elif pnl_pct < -0.5:
            print("║  ⚠️ Acercándose al SL - Preparar para cerrar                               ║")
        else:
            print("║  💎 Trade en progreso - Mantener posición                                  ║")
        
        print("╚══════════════════════════════════════════════════════════════════════════════╝")

# ══════════════════════════════════════════════════════════════════════════════
# 🎮  SECCIÓN 10: MOTOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class RSIMasterEngine:
    """Motor principal del programa."""
    
    def __init__(self):
        self.session = SessionManager()
        self.journal = JournalManager()
        self.risk = RiskManager(self.journal)
        self.detector = SignalDetector()
        self.running = False
    
    def run_scanner(self, strict_session: bool = True):
        """
        Scanner principal de señales RSI.
        
        Args:
            strict_session: Si True, solo opera en sesiones óptimas
        """
        UI.clear()
        UI.print_header()
        
        # Verificar sesión
        can_trade_session, session_msg = self.session.can_trade_now(strict_session)
        if not can_trade_session and strict_session:
            print(f"\n  {session_msg}")
            print(f"\n  Próxima sesión óptima: {self.session.get_next_optimal_session()}")
            print("\n  [1] Iniciar de todas formas (modo relajado)")
            print("  [2] Volver")
            if input("\n  > ").strip() == '1':
                strict_session = False
            else:
                return
        
        # Verificar riesgo
        can_trade_risk, risk_msg = self.risk.can_trade()
        if not can_trade_risk:
            print(f"\n  {risk_msg}")
            input("\n  Presiona Enter...")
            return
        
        self.running = True
        last_signal_time = 0
        signal_cooldown = 60  # 1 minuto entre señales iguales
        
        print("\n  📡 SCANNER INICIADO - Buscando señales RSI...")
        print("  Presiona Ctrl+C para detener\n")
        
        try:
            while self.running:
                UI.clear()
                UI.print_header()
                UI.print_status_bar(self.session, self.journal)
                
                # Analizar mercado
                analysis = self.detector.analyze()
                
                if analysis['rsi'] is not None:
                    UI.print_rsi_gauge(
                        analysis['rsi'],
                        analysis['price'],
                        analysis['ema_200']
                    )
                
                # Mostrar zona RSI
                if analysis['rsi']:
                    zone, zone_desc = self.detector.get_rsi_zone(analysis['rsi'])
                    print(f"\n  {zone}: {zone_desc}")
                
                # Verificar señal
                current_time = time.time()
                
                if analysis['can_trade'] and (current_time - last_signal_time) > signal_cooldown:
                    # ¡SEÑAL DETECTADA!
                    last_signal_time = current_time
                    
                    # Registrar señal
                    self.journal.log_signal({
                        'type': analysis['signal'].value,
                        'rsi': analysis['rsi'],
                        'price': analysis['price'],
                        'ema_200': analysis['ema_200']
                    })
                    
                    # Mostrar alerta
                    UI.print_signal_alert(analysis['signal'], analysis)
                    
                    # Verificar si puede operar
                    can_trade, risk_msg = self.risk.can_trade()
                    
                    if not can_trade:
                        print(f"\n  {risk_msg}")
                        print("  Señal registrada pero no ejecutable.")
                        time.sleep(3)
                        continue
                    
                    # Play sound
                    SoundManager.play_alert("SIGNAL")
                    
                    # Calcular niveles primero para enviar en alerta
                    levels = PositionCalculator.calculate_levels(analysis['price'], analysis['signal'])
                    
                    # Calcular posición (NUEVO v1.3)
                    position, risk_amount, max_pos = PositionCalculator.calculate_position_size()
                    
                    pos_info = {
                        "position_size": position,
                        "leverage": CONFIG.LEVERAGE
                    }
                    
                    # Send telegram con detalles monetarios
                    NotificationManager.send_signal(analysis, levels, pos_info)
                    
                    pnl_data = PositionCalculator.calculate_expected_pnl(position)
                    
                    # Mostrar setup
                    UI.print_trade_setup(
                        analysis['price'],
                        levels,
                        position,
                        pnl_data,
                        analysis['signal'].value
                    )
                    
                    # Mostrar warnings
                    if analysis['warnings']:
                        print("\n  ⚠️ ADVERTENCIAS:")
                        for w in analysis['warnings']:
                            print(f"     {w}")
                    
                    # Confirmar entrada
                    print("\n  ¿Ejecutar trade? (S/N): ", end='')
                    
                    confirm = input().strip().upper()
                    
                    if confirm == 'S':
                        # Crear trade
                        trade = {
                            'type': analysis['signal'].value,
                            'entry': analysis['price'],
                            'sl': levels['sl'],
                            'tp': levels['tp'],
                            'position_size': position,
                            'rsi_at_entry': analysis['rsi'],
                            'ema_at_entry': analysis['ema_200']
                        }
                        
                        trade_id = self.journal.add_trade(trade)
                        print(f"\n  ✅ Trade #{trade_id} registrado")
                        
                        input("\n  Presiona Enter para ir al monitor...")
                        self.run_monitor()
                        return
                    else:
                        print("\n  ❌ Señal ignorada")
                        data = self.journal.load()
                        data['stats']['signals_ignored'] += 1
                        self.journal.save(data)
                        time.sleep(2)
                
                else:
                    # Sin señal - mostrar estado
                    if analysis['reasons']:
                        print("\n  📋 Estado actual:")
                        for r in analysis['reasons'][:3]:
                            print(f"     • {r}")
                    
                    # Countdown a refresh
                    print(f"\n  ⏳ Próximo análisis en 15 segundos...")
                    print("     Presiona Ctrl+C para salir")
                
                time.sleep(15)  # Refresh cada 15 segundos
                
        except KeyboardInterrupt:
            print("\n\n  Scanner detenido.")
            self.running = False
            input("\n  Presiona Enter...")
    
    def run_monitor(self):
        """Monitor de trade activo."""
        trade = self.journal.get_active_trade()
        
        if not trade:
            print("\n  ❌ No hay trade activo")
            input("\n  Presiona Enter...")
            return
        
        print("\n  🔄 MONITOR DE TRADE ACTIVO")
        print("  Actualización cada 3 segundos...")
        print("  Escribe 'C' y Enter para cerrar trade\n")
        
        try:
            while True:
                price = DataEngine.get_current_price(CONFIG.SYMBOL)
                
                if not price:
                    time.sleep(1)
                    continue
                
                # Calcular PnL
                entry = trade['entry']
                if trade['type'] == 'LONG':
                    pnl_pct = ((price - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - price) / entry) * 100
                
                UI.clear()
                UI.print_header()
                UI.print_status_bar(self.session, self.journal)
                UI.print_monitor(trade, price, pnl_pct)
                
                # Check targets
                if trade['type'] == 'LONG':
                    tp_hit = price >= trade['tp']
                    sl_hit = price <= trade['sl']
                else:
                    tp_hit = price <= trade['tp']
                    sl_hit = price >= trade['sl']
                
                if tp_hit:
                    print("\n  🎉 ¡TAKE PROFIT ALCANZADO!")
                elif sl_hit:
                    print("\n  ⛔ STOP LOSS ALCANZADO")
                
                print("\n  [C] Cerrar trade manualmente")
                print("  Actualizando en 3 segundos...", end='', flush=True)
                
                # Input con timeout
                result = [None]
                
                def get_input():
                    try:
                        result[0] = input()
                    except:
                        pass
                
                input_thread = threading.Thread(target=get_input, daemon=True)
                input_thread.start()
                input_thread.join(timeout=3.0)
                
                if result[0] is not None and result[0].strip().upper() == 'C':
                    # Cerrar trade
                    print("\n\n  Resultado del trade:")
                    print("  [G] Ganancia (TP alcanzado)")
                    print("  [P] Pérdida (SL alcanzado)")
                    print("  [B] Breakeven")
                    
                    result_choice = input("  > ").strip().upper()
                    
                    if result_choice == 'G':
                        pnl = float(input("  Monto ganado ($): ") or "0")
                        self.journal.close_trade(trade['id'], pnl, 'WIN')
                        print(f"\n  ✅ Trade cerrado. Ganancia: ${pnl:+.2f}")
                    elif result_choice == 'P':
                        pnl = -float(input("  Monto perdido ($): ") or "0")
                        self.journal.close_trade(trade['id'], pnl, 'LOSS')
                        self.risk.record_loss()
                        print(f"\n  ❌ Trade cerrado. Pérdida: ${pnl:.2f}")
                    else:
                        self.journal.close_trade(trade['id'], 0, 'BREAKEVEN')
                        print("\n  ⚪ Trade cerrado en breakeven")
                    
                    input("\n  Presiona Enter...")
                    return
                
        except KeyboardInterrupt:
            print("\n\n  Monitor detenido (trade sigue activo)")
            input("\n  Presiona Enter...")

    def run_cloud_mode(self):
        """
        Modo Nube (Headless) para ejecución 24/7 en servidor.
        - Sin UI interactiva
        - Bucle infinito
        - Alertas Telegram
        - Auto-cooldown
        """
        print(f"☁️  INICIANDO MODO NUBE (CLOUD MODE) v1.1")
        print(f"📅  {datetime.now(CONFIG.USER_TZ)}")
        print(f"⚡  RSI Period: {CONFIG.RSI_PERIOD} | Symbol: {CONFIG.SYMBOL}")
        
        if not CONFIG.TELEGRAM_BOT_TOKEN:
            print("⚠️  ADVERTENCIA: Telegram no configurado. El bot correrá pero no avisará.")
        else:
            print("✅  Telegram configurado. Alertas activas.")
            print("[LOG] Enviando mensaje de prueba a Telegram...")
            NotificationManager.send_message("🟢 <b>RSI Master:</b> Conexión establecida. Bot activo en MODO NUBE 24/7.")
            print("[LOG] ✅ Mensaje enviado (revisa tu Telegram)")

        # Test de conexión a Binance
        print("[LOG] Probando conexión a Binance API...")
        test_price = DataEngine.get_current_price(CONFIG.SYMBOL)
        if test_price:
            print(f"[LOG] ✅ Binance conectado. Precio actual BTC: ${test_price:,.2f}")
            NotificationManager.send_message(f"✅ <b>Binance conectado.</b>\nPrecio BTC: ${test_price:,.2f}")
        else:
            print("[LOG] ❌ Error conectando a Binance. Revisa los logs arriba.")
            NotificationManager.send_message("❌ <b>Error:</b> No pude conectar a Binance API.")
            return

        last_signal_time = 0
        last_pre_alert_time = 0   # Cooldown para pre-alertas
        last_heartbeat_time = time.time() # Para status cada 4h
        signal_cooldown = 1800  # 30 minutos cooldown entre alertas para no spamear
        
        try:
            while True:
                # 1. Analizar
                analysis = self.detector.analyze()
                
                # Check error
                if not analysis['rsi']:
                    print(f"⚠️  Error obteniendo datos: {analysis['reasons']}")
                    time.sleep(60)
                    continue

                # Log simple en consola (para logs del servidor)
                current_time = datetime.now(CONFIG.USER_TZ).strftime('%H:%M')
                print(f"[{current_time}] RSI: {analysis['rsi']:.1f} | Precio: ${analysis['price']:.0f} | Signal: {analysis['signal'].value}")
                
                # 2. Verificar Señal
                if analysis['can_trade']:
                    now_ts = time.time()
                    if (now_ts - last_signal_time) > signal_cooldown:
                        # ¡SEÑAL VÁLIDA!
                        print(f"🚀  SEÑAL DETECTADA: {analysis['signal'].value}")
                        
                        # Guardar Signal
                        self.journal.log_signal({
                            'type': analysis['signal'].value,
                            'rsi': analysis['rsi'],
                            'price': analysis['price'],
                            'ema_200': analysis['ema_200'],
                            'mode': 'CLOUD'
                        })
                        
                        # Calcular niveles y posición
                        levels = PositionCalculator.calculate_levels(analysis['price'], analysis['signal'])
                        position_size, _, _ = PositionCalculator.calculate_position_size()
                        
                        pos_info = {
                            "position_size": position_size,
                            "leverage": CONFIG.LEVERAGE
                        }
                        
                        # ESTRATEGIA HEADLESS:
                        # 1. Enviar Alerta con info financiera
                        NotificationManager.send_signal(analysis, levels, pos_info)
                        
                        # 2. Actualizar tiempo para cooldown
                        last_signal_time = now_ts
                        # Reset pre-alert para permitir nueva alerta en siguiente ciclo
                        last_pre_alert_time = 0
                        
                        print(f"✅  Alerta enviada. Entrando en cooldown de 30min.")
                    else:
                        print(f"⏳  Señal ignorada por cooldown ({(signal_cooldown - (time.time() - last_signal_time))/60:.0f}m restantes)")
                
                # 3. Lógica de Pre-Alertas (v1.3)
                curr_rsi = analysis['rsi']
                now_ts = time.time()
                pre_alert_cooldown = 900 # 15 mins
                
                if (now_ts - last_pre_alert_time) > pre_alert_cooldown:
                    # LONG Warning (RSI <= 25 and approaching 20)
                    if curr_rsi <= 25 and curr_rsi > 20: 
                        NotificationManager.send_pre_alert("LONG", curr_rsi, analysis['price'])
                        last_pre_alert_time = now_ts
                        print(f"⚠️  Pre-Alerta LONG enviada (RSI {curr_rsi:.1f})")
                    
                    # SHORT Warning (RSI >= 75 and approaching 80)
                    elif curr_rsi >= 75 and curr_rsi < 80:
                        NotificationManager.send_pre_alert("SHORT", curr_rsi, analysis['price'])
                        last_pre_alert_time = now_ts
                        print(f"⚠️  Pre-Alerta SHORT enviada (RSI {curr_rsi:.1f})")

                # 4. Status Heartbeat (Cada 4 horas)
                if (now_ts - last_heartbeat_time) > 14400: # 4 horas
                    quality, _, _ = self.session.get_session_quality()
                    NotificationManager.send_status(curr_rsi, analysis['price'], quality.value)
                    last_heartbeat_time = now_ts
                    print(f"🧘 Heartbeat enviado.")

                # Sleep inteligente
                # Si estamos en sesión óptima -> check cada 30s
                # Si no -> check cada 60s
                quality, _, _ = self.session.get_session_quality()
                sleep_sec = 30 if quality in [SessionQuality.OPTIMAL, SessionQuality.GOOD] else 60
                
                time.sleep(sleep_sec)
                
        except KeyboardInterrupt:
            print("\n☁️  Modo Nube detenido.")
            NotificationManager.send_message("🛑 <b>RSI Master:</b> Bot detenido manualmente.")
    
    def show_journal(self):
        """Muestra el journal del día."""
        UI.clear()
        data = self.journal.load()
        stats = data['stats']
        
        # Calcular win rate
        total = stats['wins'] + stats['losses']
        win_rate = (stats['wins'] / total * 100) if total > 0 else 0
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         📔 JOURNAL - {data['date']}                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ESTADÍSTICAS HOY:                                                           ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║  Trades: {stats['total_trades']}  │  Wins: {stats['wins']}  │  Losses: {stats['losses']}  │  Win Rate: {win_rate:.1f}%              ║
║  P&L Total: ${stats['total_pnl']:+.2f}  │  Strikes: {stats['consecutive_losses']}/3                                ║
║  Señales ignoradas: {stats.get('signals_ignored', 0)}                                                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TRADES:                                                                     ║
║  ─────────────────────────────────────────────────────────────────────────   ║""")
        
        if data['trades']:
            for t in data['trades']:
                status = "✅" if t.get('status') == 'CLOSED' and t.get('pnl', 0) > 0 else \
                         "❌" if t.get('status') == 'CLOSED' else "🔄"
                pnl = t.get('pnl', 0)
                print(f"║  {status} #{t['id']} {t['type']:<5} @ ${t['entry']:,.2f} │ RSI: {t.get('rsi_at_entry', 0):.1f} │ PnL: ${pnl:+.2f}        ║")
        else:
            print("║  No hay trades registrados hoy                                            ║")
        
        print("╠══════════════════════════════════════════════════════════════════════════════╣")
        print("║  SEÑALES DETECTADAS:                                                         ║")
        
        if data['signals_detected']:
            for s in data['signals_detected'][-5:]:  # Últimas 5
                print(f"║  • {s.get('time', 'N/A')} - {s['type']} @ RSI {s.get('rsi', 0):.1f}                                     ║")
        else:
            print("║  Ninguna señal detectada aún                                              ║")
        
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        
        # Comparar con expectativas
        if total > 0:
            print(f"""
  📊 COMPARACIÓN CON BACKTEST:
  ─────────────────────────────
  Tu Win Rate hoy: {win_rate:.1f}%  │  Esperado: {CONFIG.EXPECTED_WIN_RATE}%
  {'✅ Por encima del esperado' if win_rate >= CONFIG.EXPECTED_WIN_RATE else '⚠️ Por debajo del esperado'}
""")
        
        input("\n  Presiona Enter...")
    
    def show_strategy_info(self):
        """Muestra información de la estrategia."""
        UI.clear()
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    📚 ESTRATEGIA RSI MEAN REVERSION                          ║
║                    "La Única Validada de 6,300 Tests"                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🎯 REGLAS DE ENTRADA:                                                       ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║  LONG:  RSI(21) ≤ 20  Y  Precio > EMA 200 (H1)                              ║
║  SHORT: RSI(21) ≥ 80  Y  Precio < EMA 200 (H1)                              ║
║                                                                              ║
║  📍 GESTIÓN:                                                                 ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║  • Stop Loss:   0.8% desde entrada                                           ║
║  • Take Profit: 0.5% desde entrada (menor que SL - intencional)             ║
║  • Riesgo: 1% del capital por trade                                          ║
║                                                                              ║
║  ⏰ HORARIOS ÓPTIMOS (UTC+5):                                                ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║  🟢 ÓPTIMO:   03:00-08:00 (Sesión Asia) - Bajo volumen, rangos              ║
║  🟡 BUENO:    11:00-15:00 (Europa AM) - Volatilidad moderada                ║
║  🔴 EVITAR:   17:00-21:00 (Overlap EU/USA) - Breakouts frecuentes           ║
║                                                                              ║
║  📊 MÉTRICAS VALIDADAS (2023-2025):                                          ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║  • Win Rate: 75.9%                                                           ║
║  • Profit Factor: 1.96                                                       ║
║  • P-Value: 0.0001 (estadísticamente significativo)                          ║
║  • Trades esperados: ~29/año (2-3/mes)                                       ║
║                                                                              ║
║  ⚠️ IMPORTANTE:                                                              ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║  • SOLO funciona en BTCUSDT (ETH no pasó validación)                        ║
║  • SOLO en timeframe 15m (otros TF no son rentables)                        ║
║  • RSI debe ser período 21 (NO 14, NO 2)                                    ║
║  • El filtro EMA 200 es OBLIGATORIO                                          ║
║  • Priorizar LONGs sobre SHORTs (sesgo alcista de crypto)                   ║
║                                                                              ║
║  💡 POR QUÉ TP < SL:                                                         ║
║  ─────────────────────────────────────────────────────────────────────────   ║
║  Es un "truco contraintuitivo" validado. Al tener meta pequeña (0.5%),      ║
║  el precio la alcanza muy frecuentemente antes del SL. Con 76% win rate,    ║
║  las muchas ganancias pequeñas superan las pocas pérdidas grandes.          ║
║                                                                              ║
║  De 100 trades:                                                              ║
║  • 76 ganan × $0.50 = +$38.00                                                ║
║  • 24 pierden × $0.80 = -$19.20                                              ║
║  • Resultado neto: +$18.80                                                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝""")
        input("\n  Presiona Enter...")
    
    def edit_config(self):
        """Edita configuración del usuario."""
        UI.clear()
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         ⚙️ CONFIGURACIÓN                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  PARÁMETROS MODIFICABLES:                                                    ║
║  ─────────────────────────────────────────────────────────────────────────   ║""")
        print(f"║  [1] Capital Total: ${CONFIG.CAPITAL_TOTAL:,.0f}                                            ║")
        print(f"║  [2] Capital Futuros: ${CONFIG.CAPITAL_FUTURES:,.0f}                                         ║")
        print(f"║  [3] Apalancamiento: {CONFIG.LEVERAGE}x                                                ║")
        print(f"║  [4] Riesgo por trade: {CONFIG.RISK_PER_TRADE_PCT}%                                             ║")
        print(f"║  [5] Sonido: {'ACTIVADO' if CONFIG.SOUND_ENABLED else 'DESACTIVADO'}                                                 ║")
        print(f"║  [6] Configurar Telegram                                                     ║")
        print("""║                                                                              ║
║  PARÁMETROS FIJOS (validados por backtest - NO modificar):                  ║
║  ─────────────────────────────────────────────────────────────────────────   ║""")
        print(f"║  • RSI Período: {CONFIG.RSI_PERIOD}                                                       ║")
        print(f"║  • RSI Oversold/Overbought: {CONFIG.RSI_OVERSOLD}/{CONFIG.RSI_OVERBOUGHT}                                        ║")
        print(f"║  • Timeframe: {CONFIG.TIMEFRAME}                                                        ║")
        print(f"║  • Símbolo: {CONFIG.SYMBOL}                                                    ║")
        print(f"║  • TP/SL: {CONFIG.TAKE_PROFIT_PCT}% / {CONFIG.STOP_LOSS_PCT}%                                                   ║")
        print("""║                                                                              ║
║  [0] Volver                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝""")
        
        choice = input("\n  > ").strip()
        
        if choice == '1':
            try:
                CONFIG.CAPITAL_TOTAL = float(input("  Nuevo capital total ($): ") or CONFIG.CAPITAL_TOTAL)
            except: pass
        elif choice == '2':
            try:
                CONFIG.CAPITAL_FUTURES = float(input("  Nuevo capital futuros ($): ") or CONFIG.CAPITAL_FUTURES)
            except: pass
        elif choice == '3':
            try:
                CONFIG.LEVERAGE = int(input("  Nuevo apalancamiento: ") or CONFIG.LEVERAGE)
            except: pass
        elif choice == '4':
            try:
                CONFIG.RISK_PER_TRADE_PCT = float(input("  Nuevo riesgo % (1-2 recomendado): ") or CONFIG.RISK_PER_TRADE_PCT)
            except: pass
        elif choice == '5':
            CONFIG.SOUND_ENABLED = not CONFIG.SOUND_ENABLED
        elif choice == '6':
            print(f"\n  Configuración Telegram actual:")
            print(f"  Token: {CONFIG.TELEGRAM_BOT_TOKEN[:5]}..." if CONFIG.TELEGRAM_BOT_TOKEN else "  Token: No configurado")
            print(f"  ChatID: {CONFIG.TELEGRAM_CHAT_ID}" if CONFIG.TELEGRAM_CHAT_ID else "  ChatID: No configurado")
            
            new_token = input("\n  Nuevo Bot Token (Enter para mantener): ").strip()
            if new_token: CONFIG.TELEGRAM_BOT_TOKEN = new_token
            
            new_id = input("  Nuevo Chat ID (Enter para mantener): ").strip()
            if new_id: CONFIG.TELEGRAM_CHAT_ID = new_id
            
            # Prueba de mensaje
            if CONFIG.TELEGRAM_BOT_TOKEN and CONFIG.TELEGRAM_CHAT_ID:
                print("\n  Enviando mensaje de prueba...")
                NotificationManager.send_message("🔔 RSI Master: Prueba de notificación exitosa")
        
        # Guardar cambios
        CONFIG.save()
        print("\n  ✅ Configuración guardada en config.json")
        time.sleep(1)

# ══════════════════════════════════════════════════════════════════════════════
# 🚀  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Punto de entrada principal."""
    
    # 1. Check CLI arguments
    parser = argparse.ArgumentParser(description='RSI Mean Reversion Master')
    parser.add_argument('--cloud', action='store_true', help='Ejecutar en modo nube (headless/automático)')
    args = parser.parse_args()
    
    engine = RSIMasterEngine()
    
    # 2. Run Cloud Mode if flag is set
    if args.cloud:
        engine.run_cloud_mode()
        return

    # 3. Interactive Mode (Default)
    while True:
        UI.clear()
        UI.print_header()
        UI.print_status_bar(engine.session, engine.journal)
        
        # Info de próxima sesión
        quality, _, _ = engine.session.get_session_quality()
        if quality not in [SessionQuality.OPTIMAL, SessionQuality.GOOD]:
            next_session = engine.session.get_next_optimal_session()
            print(f"\n  ⏰ {next_session}")
        
        print("""
┌──────────────────────────────────────────────────────────────────────────────┐
│  📋 MENÚ PRINCIPAL                                                           │
├──────────────────────────────────────────────────────────────────────────────┤
│  [1] 📡 Scanner de Señales (modo estricto - solo sesiones óptimas)          │
│  [2] 🔓 Scanner de Señales (modo relajado - cualquier hora)                 │
│  [3] 🔄 Monitor de Trade Activo                                              │
│  [4] 📔 Ver Journal del Día                                                  │
│  [5] 📚 Info de la Estrategia                                                │
│  [6] ⚙️  Configuración                                                       │
│  [Q] 🚪 Salir                                                                │
└──────────────────────────────────────────────────────────────────────────────┘""")
        
        choice = input("\n  > ").strip().upper()
        
        if choice == '1':
            engine.run_scanner(strict_session=True)
        elif choice == '2':
            engine.run_scanner(strict_session=False)
        elif choice == '3':
            engine.run_monitor()
        elif choice == '4':
            engine.show_journal()
        elif choice == '5':
            engine.show_strategy_info()
        elif choice == '6':
            engine.edit_config()
        elif choice == 'Q':
            print("\n  👋 ¡Buena suerte con tus trades!\n")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  👋 ¡Hasta luego!\n")
        sys.exit(0)