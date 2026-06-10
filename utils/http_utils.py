# -*- coding: utf-8 -*-
"""
Utilidades HTTP: retry exponencial para scrapers.

Uso:
    from utils.http_utils import retry_request, get_with_retry

    # Decorador en funciones existentes:
    @retry_request(max_attempts=3, backoff=2.0)
    def get_games(self):
        response = requests.get(self.url, timeout=10)
        ...

    # Helper directo:
    data = get_with_retry(url, headers=..., timeout=10)
"""

import time
import logging
import functools
import requests

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def retry_request(max_attempts: int = 3, backoff: float = 2.0, exceptions: tuple = None):
    """
    Decorador de retry con backoff exponencial para funciones que hacen HTTP.

    Args:
        max_attempts: Número máximo de intentos (incluye el primero).
        backoff: Multiplicador de espera. Intento 1=backoff^0, 2=backoff^1, etc.
        exceptions: Tupla de excepciones que activan el retry.
                    Por defecto: (requests.Timeout, requests.ConnectionError, requests.HTTPError).
    """
    if exceptions is None:
        exceptions = (requests.Timeout, requests.ConnectionError, requests.HTTPError)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        wait = backoff ** attempt
                        logger.warning(
                            f"[retry] {func.__name__} falló ({type(e).__name__}). "
                            f"Intento {attempt + 1}/{max_attempts}. Esperando {wait:.1f}s..."
                        )
                        time.sleep(wait)
                    else:
                        logger.error(
                            f"[retry] {func.__name__} agotó {max_attempts} intentos: {e}"
                        )
            raise last_exc
        return wrapper
    return decorator


def get_with_retry(
    url: str,
    headers: dict = None,
    params: dict = None,
    timeout: int = 10,
    max_attempts: int = 3,
    backoff: float = 2.0,
) -> dict | None:
    """
    GET con retry exponencial. Retorna el JSON parseado o None si falla.

    Args:
        url: URL a consultar.
        headers: Cabeceras HTTP opcionales.
        params: Query params opcionales.
        timeout: Timeout en segundos.
        max_attempts: Reintentos totales.
        backoff: Multiplicador de espera entre reintentos.

    Returns:
        dict con el JSON de la respuesta, o None en caso de error.
    """
    last_exc = None
    for attempt in range(max_attempts):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            if resp.status_code in _RETRYABLE_STATUS:
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            last_exc = e
            if attempt < max_attempts - 1:
                wait = backoff ** attempt
                logger.warning(
                    f"[get_with_retry] {url} → {type(e).__name__}. "
                    f"Intento {attempt + 1}/{max_attempts}. Esperando {wait:.1f}s..."
                )
                time.sleep(wait)
        except Exception as e:
            logger.error(f"[get_with_retry] Error no reintentable en {url}: {e}")
            return None

    logger.error(f"[get_with_retry] Agotados {max_attempts} intentos para {url}: {last_exc}")
    return None
