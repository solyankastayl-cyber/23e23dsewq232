/**
 * Exchange Connection Panel — Week 3
 * 
 * UI для управления подключением к бирже (PAPER / BINANCE_TESTNET)
 * Текст UI на украинском (как запросил пользователь)
 */

import React, { useState, useEffect } from 'react';
import { Plug, Activity, TestTube, RefreshCw, Link, Unlink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export const ExchangeConnectionPanel = () => {
  const [mode, setMode] = useState('PAPER');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/exchange/status`);
      const data = await res.json();
      if (data.ok) setStatus(data);
    } catch (error) {
      console.error('Status fetch error:', error);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleConnect = async () => {
    setLoading(true);
    try {
      const payload = {
        mode,
        ...(mode !== 'PAPER' && { api_key: apiKey, api_secret: apiSecret }),
      };

      const res = await fetch(`${API_URL}/api/exchange/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      
      if (data.ok && data.connected) {
        toast.success(`Підключено до ${mode}`);
        fetchStatus();
        
        // Clear credentials
        setApiKey('');
        setApiSecret('');
      } else {
        toast.error(`Помилка: ${data.detail || 'Невідома помилка'}`);
      }
    } catch (error) {
      console.error('Connection error:', error);
      toast.error('Помилка підключення до біржі');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/exchange/disconnect`, {
        method: 'POST',
      });

      const data = await res.json();
      
      if (data.ok) {
        toast.success('Відключено від біржі');
        fetchStatus();
      }
    } catch (error) {
      console.error('Disconnect error:', error);
      toast.error('Помилка відключення');
    } finally {
      setLoading(false);
    }
  };

  const handleTestOrder = async () => {
    if (!status?.connected) {
      toast.error('Спочатку підключіться до біржі');
      return;
    }

    setTesting(true);
    try {
      const res = await fetch(`${API_URL}/api/exchange/test-order`, {
        method: 'POST',
      });

      const data = await res.json();
      
      if (data.ok && data.test_order) {
        const order = data.test_order;
        toast.success(
          `Тестовий ордер виконано: ${order.symbol} ${order.side} @ $${order.avg_fill_price}`,
          { duration: 5000 }
        );
      } else {
        toast.error(`Помилка: ${data.detail || 'Ордер не виконано'}`);
      }
    } catch (error) {
      console.error('Test order error:', error);
      toast.error('Помилка відправки тестового ордера');
    } finally {
      setTesting(false);
    }
  };

  const isConnected = status?.connected || false;
  const requiresCredentials = mode !== 'PAPER';

  return (
    <Card 
      className="bg-white border-[#e6eaf2]" 
      style={{ boxShadow: '2px 2px 8px rgba(0,5,48,0.06)' }}
      data-testid="exchange-connection-panel"
    >
      <CardHeader>
        <CardTitle className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
          <Plug className="w-4 h-4 text-[#04A584]" />
          Підключення біржі
        </CardTitle>
        <CardDescription className="text-xs text-gray-500">
          Управління підключенням до торгової біржі
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Status Indicator */}
        {status && (
          <Alert 
            className={`${
              isConnected 
                ? 'bg-green-50 border-green-200 text-green-800' 
                : 'bg-gray-50 border-gray-200 text-gray-600'
            }`}
            data-testid="connection-status"
          >
            <Activity className={`h-4 w-4 ${isConnected ? 'text-green-600' : 'text-gray-400'}`} />
            <AlertDescription className="text-xs font-medium ml-2">
              {isConnected 
                ? `Підключено: ${status.exchange || status.mode}` 
                : 'Не підключено'}
            </AlertDescription>
          </Alert>
        )}

        {/* Connection Form */}
        {!isConnected && (
          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="mode" className="text-xs font-medium text-gray-700">
                Режим
              </Label>
              <Select 
                value={mode} 
                onValueChange={setMode}
                data-testid="mode-select"
              >
                <SelectTrigger id="mode" className="text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PAPER">PAPER (Симуляція)</SelectItem>
                  <SelectItem value="BINANCE_TESTNET">BINANCE TESTNET</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {requiresCredentials && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="apiKey" className="text-xs font-medium text-gray-700">
                    API Key
                  </Label>
                  <Input
                    id="apiKey"
                    type="text"
                    placeholder="Введіть API ключ"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="text-sm"
                    data-testid="api-key-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="apiSecret" className="text-xs font-medium text-gray-700">
                    API Secret
                  </Label>
                  <Input
                    id="apiSecret"
                    type="password"
                    placeholder="Введіть API секрет"
                    value={apiSecret}
                    onChange={(e) => setApiSecret(e.target.value)}
                    className="text-sm"
                    data-testid="api-secret-input"
                  />
                </div>
              </>
            )}

            <Button
              onClick={handleConnect}
              disabled={loading || (requiresCredentials && (!apiKey || !apiSecret))}
              className="w-full bg-[#04A584] hover:bg-[#038c6f] text-white"
              data-testid="connect-button"
            >
              {loading ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Підключення...
                </>
              ) : (
                <>
                  <Link className="mr-2 h-4 w-4" />
                  ПІДКЛЮЧИТИ
                </>
              )}
            </Button>
          </div>
        )}

        {/* Connected Actions */}
        {isConnected && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <Button
                onClick={handleTestOrder}
                disabled={testing}
                variant="outline"
                className="text-sm"
                data-testid="test-order-button"
              >
                {testing ? (
                  <>
                    <RefreshCw className="mr-2 h-3 w-3 animate-spin" />
                    Надсилання...
                  </>
                ) : (
                  <>
                    <TestTube className="mr-2 h-3 w-3" />
                    Тестовий ордер
                  </>
                )}
              </Button>

              <Button
                onClick={handleDisconnect}
                disabled={loading}
                variant="outline"
                className="text-sm text-red-600 hover:text-red-700 hover:bg-red-50"
                data-testid="disconnect-button"
              >
                <Unlink className="mr-2 h-3 w-3" />
                Відключити
              </Button>
            </div>

            <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-100">
              Активна біржа: <span className="font-medium text-gray-700">{status?.exchange}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ExchangeConnectionPanel;
