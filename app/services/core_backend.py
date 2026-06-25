from uuid import UUID
from fastapi import HTTPException

import requests

from app.core.base.services import Service
from app.schemas.transactions import LogManualTransactionsRequest
from app.utils.settings import settings

INTERNAL_KEY = settings.INTERNAL_KEY
BASE_URL = settings.INTERNAL_BASE_URL

class CoreBackendService(Service):
    
    @staticmethod
    def _request(method: str, endpoint: str, **kwargs):
        url = f"{BASE_URL}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("x-internal-key", INTERNAL_KEY)
        
        # Clean up None values from params
        if "params" in kwargs and kwargs["params"]:
            kwargs["params"] = {k: v for k, v in kwargs["params"].items() if v is not None}
            
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def search_users(query: str):
        return CoreBackendService._request("GET", "/internal/users/search", params={"q": query})
        
    @staticmethod
    def get_all_users(page: int = 1, limit: int = 10, **kwargs):
        params = {"page": page, "limit": limit, **kwargs}
        return CoreBackendService._request("GET", "/internal/users/all", params=params)
    
    @staticmethod
    def get_user_by_id(id: UUID):
        try:
            return CoreBackendService._request("GET", f"/internal/users/{id}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def log_manual_transaction(payload) -> dict:
        """Proxies the log manual transaction request to the core backend."""
        payload_data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
        return CoreBackendService._request("POST", "/internal/wallet/transactions/manual", json=payload_data)

    @staticmethod
    def get_all_transactions(page: int = 1, limit: int = 10, **kwargs):
        params = {"page": page, "limit": limit, **kwargs}
        return CoreBackendService._request("GET", "/internal/wallet/transactions/all", params=params)
    
    @staticmethod
    def get_transaction_by_id(id: UUID):
        try:
            return CoreBackendService._request("GET", f"/internal/wallet/transactions/{id}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
