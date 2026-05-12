"""
Flow CDN Token resolver.
Takes a streaming URL and Authorization header, returns URL with fresh CDN token.
"""
import requests
from urllib.parse import urlencode, quote

CDN_TOKEN_URL = "https://cdn-token.app.flow.com.ar/cdntoken/v2/generator"


def resolve_flow_token(stream_url, auth_header=None):
    """Get a fresh CDN token and append it to the streaming URL.
    
    Args:
        stream_url: The original MPD/M3U8 URL
        auth_header: Optional Authorization header (Bearer JWT)
    
    Returns:
        URL with ?cdntoken=... appended, or original URL if fails
    """
    if not stream_url:
        return stream_url

    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    path_encoded = quote(stream_url, safe="")
    url = f"{CDN_TOKEN_URL}?path={path_encoded}"

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            token = r.json().get("token")
            if token:
                sep = "&" if "?" in stream_url else "?"
                return f"{stream_url}{sep}cdntoken={token}"
    except Exception as e:
        pass

    return stream_url
