"""
Django wrapper for LumixClient.
Handles caching, auth lifecycle, and stream resolution.
"""
import json
import time
from urllib.parse import urlencode

import requests
from django.core.cache import cache

from .proveedor_client import LumixClient
from .flow_cdn import resolve_flow_token


CACHE_PREFIX = "prov_"
CACHE_TTL = 3600
AES_CACHE_TTL = 7200


def _get_client():
    email = "devnetsoluciones@gmail.com"
    password = "123456"
    client = LumixClient(email, password)
    cached_key = cache.get(f"{CACHE_PREFIX}aes_key")
    if cached_key:
        client._aes_key = cached_key
    return client


def _save_client_state(client):
    if client._aes_key:
        cache.set(f"{CACHE_PREFIX}aes_key", client._aes_key, AES_CACHE_TTL)


def fetch_stix_channels(force=False):
    cache_key = f"{CACHE_PREFIX}stix_channels"
    if not force:
        cached = cache.get(cache_key)
        if cached:
            return cached
    client = _get_client()
    try:
        data = client.get_stix_channels()
        _save_client_state(client)
        cache.set(cache_key, data, CACHE_TTL)
        return data
    except Exception:
        cached = cache.get(cache_key)
        if cached:
            return cached
        raise


def fetch_claro_channels(force=False):
    cache_key = f"{CACHE_PREFIX}claro_channels"
    if not force:
        cached = cache.get(cache_key)
        if cached:
            return cached
    client = _get_client()
    try:
        data = client.get_claro_channels()
        _save_client_state(client)
        cache.set(cache_key, data, CACHE_TTL)
        return data
    except Exception:
        cached = cache.get(cache_key)
        if cached:
            return cached
        raise


def get_channel_details(channel_id):
    client = _get_client()
    try:
        data = client.get_channel_details(channel_id)
        _save_client_state(client)
        return data
    except Exception as e:
        raise


def resolve_stream(details):
    """Given channel details from lumixtv, resolve the playable URL.
    
    Returns dict with:
        url: final streaming URL (with CDN token if applicable)
        drm_scheme: None / 'clearkey' / 'widevine'
        clearkey: clearkey dict if applicable
        headers: dict of required HTTP headers
    """
    uri = details.get("uri", "")
    drm = details.get("drm_scheme") or None
    headers = details.get("headers") or {}
    auth_header = None

    if isinstance(headers, list):
        headers = {h.get("key", ""): h.get("value", "") for h in headers if "key" in h}

    # Extract Authorization header if present (for Flow CDN)
    if isinstance(headers, dict):
        auth_header = headers.get("Authorization")
        # The JWT might be in drm_license_uri too (format: clearkey URL with auth?)
    
    result = {
        "url": uri,
        "drm_scheme": drm,
        "clearkey": None,
        "headers": headers or {},
    }

    # ── Claro Andina (Widevine) ──
    if details.get("claroandina"):
        result["drm_scheme"] = "widevine"
        return result

    # ── Flow CDN (cvattv.com.ar) ──
    if "cvattv" in uri or "flow" in uri:
        resolved = resolve_flow_token(uri, auth_header)
        if resolved != uri:
            result["url"] = resolved
            # Remove stale auth header, token is now in URL
            if isinstance(result["headers"], dict):
                result["headers"].pop("Authorization", None)

    # ── ClearKey channels ──
    if drm == "clearkey":
        pass

    return result


def get_clearkey(channel_id):
    """Get ClearKey license keys for a channel."""
    client = _get_client()
    try:
        data = client.get_clearkey_license(channel_id)
        _save_client_state(client)
        return data
    except Exception as e:
        raise


def import_all_channels():
    """Fetch all channels from lumixtv, return as structured list."""
    channels = []

    stix = fetch_stix_channels(force=True)
    for cat_idx, category in enumerate(stix):
        cat_name = category.get("name", f"Categoria {cat_idx}")
        for sample in category.get("samples", []):
            channel_id = str(sample.get("id", ""))
            if not channel_id:
                continue
            channels.append({
                "source": "stix",
                "category": cat_name,
                "name": sample.get("name", ""),
                "logo": sample.get("logo", sample.get("image", "")),
                "proveedor_id": channel_id,
            })

    try:
        claro = fetch_claro_channels(force=True)
        for cat_idx, category in enumerate(claro):
            cat_name = category.get("name", f"Claro {cat_idx}")
            for sample in category.get("samples", []):
                channel_id = sample.get("group_id", "") or sample.get("id", "")
                if not channel_id:
                    continue
                channels.append({
                    "source": "claro",
                    "category": cat_name,
                    "name": sample.get("name", ""),
                    "logo": sample.get("logo", sample.get("image", "")),
                    "proveedor_id": channel_id,
                })
    except Exception:
        pass

    return channels


def sync_canales():
    """Sync all proveedor channels into Canal model."""
    from .models import Categoria, Canal

    imported = import_all_channels()
    created = 0
    updated = 0
    for ch in imported:
        cat, _ = Categoria.objects.get_or_create(nombre=ch["category"])
        canal, was_created = Canal.objects.update_or_create(
            proveedor_id=ch["proveedor_id"],
            proveedor_source=ch["source"],
            defaults={
                "nombre": ch["name"],
                "categoria": cat,
                "logo": ch["logo"] or None,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "total": len(imported)}
