"""
Exchange Proxy Configuration Routes
Sprint A4.5: Proxy settings for geo-restricted exchanges
"""

import os
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exchange", tags=["exchange_config"])

PROXY_CONFIG_FILE = "/app/backend/proxy_config.json"


class ProxyConfig(BaseModel):
    enabled: bool = False
    host: str = ""
    port: str = ""
    username: str = ""
    password: str = ""


class ProxyConfigRequest(BaseModel):
    proxy: ProxyConfig


@router.get("/proxy-config")
async def get_proxy_config():
    """Get current proxy configuration"""
    try:
        if os.path.exists(PROXY_CONFIG_FILE):
            with open(PROXY_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return {"ok": True, "proxy": config.get("proxy", {})}
        else:
            return {"ok": True, "proxy": {"enabled": False}}
    except Exception as e:
        logger.error(f"Failed to load proxy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proxy-config")
async def update_proxy_config(request: ProxyConfigRequest):
    """Update proxy configuration"""
    try:
        config = {"proxy": request.proxy.dict()}
        
        with open(PROXY_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Proxy config updated: enabled={request.proxy.enabled}")
        
        # Also update .env file for persistence
        env_path = "/app/backend/.env"
        if request.proxy.enabled and request.proxy.host and request.proxy.port:
            proxy_url = f"http://{request.proxy.host}:{request.proxy.port}"
            if request.proxy.username and request.proxy.password:
                proxy_url = f"http://{request.proxy.username}:{request.proxy.password}@{request.proxy.host}:{request.proxy.port}"
            
            # Read existing .env
            env_lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()
            
            # Remove existing HTTPS_PROXY line
            env_lines = [line for line in env_lines if not line.startswith('HTTPS_PROXY=')]
            
            # Add new proxy
            env_lines.append(f'\nHTTPS_PROXY={proxy_url}\n')
            env_lines.append(f'HTTP_PROXY={proxy_url}\n')
            
            with open(env_path, 'w') as f:
                f.writelines(env_lines)
            
            logger.info(f"Proxy added to .env: {proxy_url}")
        
        return {"ok": True, "proxy": request.proxy.dict()}
    except Exception as e:
        logger.error(f"Failed to update proxy config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-connection")
async def test_exchange_connection():
    """Test exchange connection"""
    try:
        from modules.exchange.service_v2 import get_exchange_service
        
        exchange_service = get_exchange_service()
        
        # Try to get exchange status
        status = await exchange_service.get_status()
        
        return {
            "ok": True,
            "connected": status.get("connected", False),
            "mode": status.get("mode"),
            "error": status.get("error") if not status.get("connected") else None
        }
    except Exception as e:
        logger.error(f"Exchange connection test failed: {e}")
        return {
            "ok": False,
            "connected": False,
            "error": str(e)
        }
