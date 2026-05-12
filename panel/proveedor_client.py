"""
Cliente API para proveedor de TV
Protocolo de encriptación RSA + AES para canales de TV.

Uso:
    from proveedor_client import LumixClient
    client = LumixClient("email", "password")
    channels = client.get_stix_channels()
    details = client.get_channel_details(1693)
    clearkey = client.get_clearkey_license(1693)
    claro_channels = client.get_claro_channels()
    payway, media = client.resolve_claro_channel("1162248")
"""

import requests
import json
import time
import base64
import hashlib
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import unpad


class LumixClient:
    BASE = "https://lumixtv.es"

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        self._aes_key = None

    # ── Encryption protocol ──────────────────────────────

    def _rsa_encrypt(self, data):
        r = self.s.get(f"{self.BASE}/SECURE/public_key.pem")
        key = RSA.import_key(r.text)
        return base64.b64encode(PKCS1_v1_5.new(key).encrypt(data.encode())).decode().strip()

    def _get_aes_key(self):
        if self._aes_key:
            return self._aes_key
        nonce = str(int(time.time()))
        enc_nonce = self._rsa_encrypt(nonce)
        r = self.s.post(f"{self.BASE}/SECURE/firma.php",
                        data={"email": self.email, "password": self.password, "nonce": enc_nonce})
        temp = hashlib.sha256(nonce.encode()).digest()[:16]
        self._aes_key = unpad(AES.new(temp, AES.MODE_ECB)
                              .decrypt(base64.b64decode(r.json()["encrypted_key"])), 16).decode()
        return self._aes_key

    def _decrypt(self, data_b64):
        data = "".join(data_b64.strip().split())
        return unpad(AES.new(self._get_aes_key().encode(), AES.MODE_ECB)
                     .decrypt(base64.b64decode(data)), 16).decode()

    def _post(self, url, extra=None):
        body = {"email": self.email, "password": self.password}
        if extra:
            body.update(extra)
        r = self.s.post(url, data=json.dumps(body), headers={"Content-Type": "application/json"})
        if len(r.text) < 50:
            return r.text
        try:
            return self._decrypt(r.text)
        except Exception:
            return r.text

    def _rsa_post(self, url, extra_form=None):
        """POST with RSA-encrypted nonce form data (for firma.php, clearkey, etc.)"""
        nonce = str(int(time.time()))
        enc_nonce = self._rsa_encrypt(nonce)
        form = {"email": self.email, "password": self.password, "nonce": enc_nonce}
        if extra_form:
            form.update(extra_form)
        r = self.s.post(url, data=form)
        temp = hashlib.sha256(nonce.encode()).digest()[:16]
        return unpad(AES.new(temp, AES.MODE_ECB)
                     .decrypt(base64.b64decode(r.json()["encrypted_key"])), 16).decode()

    # ── STIX V2 Channels ─────────────────────────────────

    def get_stix_channels(self):
        """Returns list of categories with channels."""
        data = self._post(f"{self.BASE}/canales/STIX_V2/app.php")
        return json.loads(data)

    def get_channel_details(self, channel_id):
        """Returns streaming URL + DRM info for a channel."""
        data = self._post(f"{self.BASE}/canales/STIX_V2/get_detalles.php", {"id": channel_id})
        return json.loads(data)[0]

    def get_clearkey_license(self, channel_id):
        """Returns ClearKey license JSON (keys, kid, type)."""
        return json.loads(
            self._rsa_post(f"{self.BASE}/clearkey/llaves.php", {"id": channel_id})
        )

    # ── CLARO V2 / Flow Channels ─────────────────────────

    def get_claro_channels(self):
        """Returns dict of categories with Claro channels (groupid, nombre, logo)."""
        data = self._post(f"{self.BASE}/canales/CLARO_V2/index.php")
        return json.loads(data)

    def get_claro_config(self):
        """Returns remote config: claro_base_url, claro_hks, claro_authpt."""
        data = self._post(f"{self.BASE}/canales/CLARO_V2/dinamic.php")
        return json.loads(data)

    def resolve_claro_channel(self, group_id, region="argentina"):
        """Resolves a Claro/Flow channel streaming URL.
        Returns (payway_token, media_info) where media_info has:
          video_url, server_url, challenge (token + material_id), certificate_url
        """
        config = self.get_claro_config()
        base = config.get("claro_base_url", "https://mfwkweb-api.clarovideo.net")
        authpt = config.get("claro_authpt", "tfg1h3j4k6fd7")
        hks = config.get("claro_hks", "2n9ru0n9kgrr9vv4b893bo7570")

        # Step 1: Payway token
        params_pw = {
            "device_id": "web", "device_category": "web", "device_model": "web",
            "device_type": "web", "device_so": "Chrome", "format": "json",
            "device_manufacturer": "generic", "authpn": "webclient",
            "authpt": authpt, "api_version": "v5.93",
            "region": region, "HKS": hks,
        }
        r = self.s.get(f"{base}/services/payway/linealchannels", params=params_pw)
        payway_token = r.json()["response"]["paqs"]["paq"][0]["payway_token"]

        # Step 2: Get media
        params_media = {
            "device_category": "web", "group_id": group_id,
            "device_model": "web", "device_type": "web", "format": "json",
            "device_manufacturer": "generic", "authpn": "webclient",
            "authpt": authpt, "stream_type": "dashwv",
            "crDomain": "https://www.clarovideo.com", "api_version": "v5.94",
            "device_id": "693e9af84d3dfcc71e640e005bdc5e2e",
            "preview": "0", "css": "0", "region": region,
            "payway_token": payway_token,
        }
        r = self.s.get(f"{base}/services/player/getmedia", params=params_media)
        media = r.json()["response"]["media"]
        return payway_token, media

    # ── Convenience ──────────────────────────────────────

    def print_summary(self):
        stix = self.get_stix_channels()
        claro = self.get_claro_channels()
        print(f"STIX_V2: {len(stix)} categorías, {sum(len(c['samples']) for c in stix)} canales")
        print(f"CLARO_V2: {len(claro)} categorías")


if __name__ == "__main__":
    import sys
    email = sys.argv[1] if len(sys.argv) > 1 else "devnetsoluciones@gmail.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "123456"
    client = LumixClient(email, password)
    client.print_summary()
