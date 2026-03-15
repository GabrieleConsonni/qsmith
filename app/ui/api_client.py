import os

import requests


API_BASE_URL = os.getenv("QSMITH_API_BASE_URL", "http://localhost:9082").rstrip("/")
API_TIMEOUT_SECONDS = float(os.getenv("QSMITH_API_TIMEOUT_SECONDS", "30"))


def api_get(path: str):
    response = requests.get(f"{API_BASE_URL}{path}", timeout=API_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict):
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=API_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def api_put(path: str, payload: dict):
    response = requests.put(f"{API_BASE_URL}{path}", json=payload, timeout=API_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def api_delete(path: str):
    response = requests.delete(f"{API_BASE_URL}{path}", timeout=API_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()
