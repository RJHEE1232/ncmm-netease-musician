#!/usr/bin/env python3
"""Publish a private (self-only visible) image-text note (动态/笔记) to NetEase Cloud Music.

Why not ``ncmm note``? The upstream hardcodes privacySetting="0" (public) and
overwrites socialSpaceVisible to 1, so a note published through ncmm is always
public. This script reimplements the EAPI flow used by the mobile client and
publishes with privacySetting="1" (self-only):

  EAPI encrypt (AES-128-ECB + PKCS7, hex uppercase)  ->  form `params=<HEX>`
  image upload: NOS token alloc -> PUT to upload node -> event img info
  publish:      POST /eapi/note/share/friends/resource
  verify:       check privacySetting in publish response + /eapi/event/get

Requires: pycryptodome, requests. Cookie jar: data/cookie.json (ncmm login
output, Resty jar format: {domain: {name: {Name, Value, ...}}}).

Privacy rule: this script never prints cookie values or MUSIC_U. Use
``--selftest`` to validate crypto against upstream test vectors offline.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import secrets
import sys
import time
import urllib.parse
from pathlib import Path

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:  # pragma: no cover
    print("missing dependency: pip install pycryptodome", file=sys.stderr)
    raise

try:
    import requests
except ImportError:  # pragma: no cover
    print("missing dependency: pip install requests", file=sys.stderr)
    raise

# ---------------------------------------------------------------------------
# EAPI crypto (mirrors upstream pkg/crypto + api/api.go)
# ---------------------------------------------------------------------------
EAPI_KEY = b"e82ckenh8dichen8"
EAPI_SEP = "36cd479b6b5"
EAPI_SLAT = "nobody{}use{}md5forencrypt"
EAPI_UA = "NeteaseMusic 9.4.95/6806 (iPhone; iOS 16.6.1; zh_CN)"


def go_json_dumps(obj: object) -> str:
    """Match Go encoding/json.Marshal: compact separators, no ASCII escaping,
    but HTML chars and U+2028/U+2029 escaped."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return (
        s.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def eapi_params(url: str, obj: object) -> str:
    """Encrypt an EAPI request body; returns the `params` value (HEX upper)."""
    api_url = url.replace("eapi", "api", 1)  # only first occurrence, as upstream
    data = go_json_dumps(obj)
    digest = hashlib.md5(EAPI_SLAT.format(api_url, data).encode("utf-8")).hexdigest()
    text = f"{api_url}-{EAPI_SEP}-{data}-{EAPI_SEP}-{digest}"
    cipher = AES.new(EAPI_KEY, AES.MODE_ECB)
    ct = cipher.encrypt(pad(text.encode("utf-8"), AES.block_size))
    return ct.hex().upper()


def eapi_decrypt(raw: bytes) -> bytes:
    """Decrypt an EAPI response body (plain if it starts with '{')."""
    if raw.startswith(b"{"):
        return raw
    cipher = AES.new(EAPI_KEY, AES.MODE_ECB)
    try:
        plain = unpad(cipher.decrypt(raw), AES.block_size)
    except ValueError:
        plain = cipher.decrypt(raw)
    if plain.startswith(b"\x1f\x8b"):
        try:
            plain = gzip.decompress(plain)
        except Exception:
            pass
    return plain


def selftest() -> None:
    """Validate against upstream crypto_test.go vectors."""
    expect_enc = (
        "E556EA4892989E4A1B98043B56CD3C77C6DBE3D0261A0FA8ACF45E2882DBABFD13F52E0"
        "5D9EF39C101A7A46DD0E0CD0979A2DD9CE30975861F6F4E86855FE00AD841C36BA9017"
        "7218D0D8D32A54A0DC4"
    )
    got_enc = eapi_params("/test/url", "test value")
    assert got_enc == expect_enc, f"encrypt mismatch:\n got={got_enc}\nwant={expect_enc}"

    expect_dec = b'{"code":200,"data":true}'
    got_dec = eapi_decrypt(
        bytes.fromhex("DCC52B3013E9B66C038F8E027E580ECEDF84E0F44CB93FC365BED7B646A9BC08")
    )
    assert got_dec == expect_dec, f"decrypt mismatch: {got_dec!r}"

    # complex payload decrypt vector (includes escaped quotes)
    big_hex = (
        "1BDAA66BB859333CCCE0A53AE6D1E6E61F5C1663DE05CFFB8C87BCE2FDC6F9ECAB1F5341B2F"
        "BCB5CBBACDA665D6F1A10B007189F44A13DB2463BB3EBF2639CF10A3E14D47E97975942FF6"
        "26F17CE4A658E17F19C52EDACCB199F262EA09723E644C46E3880B4754AE1A2A1F4712268C"
        "52AEA6F5D0158780D82BDC30C930756181972480BE18A2ECD68A276C68E5214491F2323B3C"
        "87ECA2AF9532A4F483D55B8C5187D558AF5699D2C2437C1D98CB5AD7B90402CCDB12DF9505"
        "21A86D854646BF8422708A649C1B8B752AF70AD5B3868F939FD0E9BEAA8BAE0D05BB0D4D88"
        "BE1A6BFAA8F5BBECD6F92368480E657D2200F8ACE7740ACAAA5634297D6661704EE7F74779E"
        "833DF2241939FC60C5D92569E31285E4F4A4F737CC8E89316DE7BBC8FB99E94B87DC05C190"
        "EA228637B2C0D182152BFAC603EF671A9A0B2F907D98F30E8A4614F236B3ED78392F039EDA"
        "D3C3CE5A856EE51BCDE2173F428CD1BB0239"
    )
    want_big = (
        '/api/music/partner/work/evaluate-36cd479b6b5-{"taskId":"185640294","workId":"1312207",'
        '"score":"3","tags":"3-C-1","customTags":"[]","comment":"","extraResource":"true",'
        '"syncYunCircle":"false","syncComment":"true","extraScore":"{\\"1\\":3,\\"2\\":2,\\"3\\":4}",'
        '"source":"mp-music-partner","header":"{}","e_r":true}-36cd479b6b5-f891fb9aa53a9b84280a53c43ff84de8'
    ).encode("utf-8")
    got_big = eapi_decrypt(bytes.fromhex(big_hex))
    assert got_big == want_big, f"big decrypt mismatch:\n got={got_big[:120]!r}\nwant={want_big[:120]!r}"

    print("[selftest] OK: EAPI encrypt/decrypt matches upstream test vectors")


# ---------------------------------------------------------------------------
# Cookie jar helpers (Resty jar format)
# ---------------------------------------------------------------------------
def load_jar(path: Path) -> list[tuple[str, str]]:
    """Return [(name, value), ...] for every entry in the jar."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[tuple[str, str]] = []
    if isinstance(raw, dict):
        for cookies in raw.values():
            if not isinstance(cookies, dict):
                continue
            for name, ent in cookies.items():
                if not isinstance(ent, dict):
                    continue
                nm = ent.get("Name") or name
                val = ent.get("Value", "")
                out.append((str(nm), str(val)))
    return out


def jar_value(entries: list[tuple[str, str]], *names: str) -> str:
    for nm, val in entries:
        if nm in names and val:
            try:
                return urllib.parse.unquote(val)
            except Exception:
                return val
    return ""


def mask(value: str) -> str:
    return f"{len(value)} chars" if value else "(empty)"


# ---------------------------------------------------------------------------
# HTTP client with EAPI helpers
# ---------------------------------------------------------------------------
class EapiClient:
    def __init__(self, entries: list[tuple[str, str]], timeout: int = 60, retries: int = 3):
        self.entries = entries
        self.timeout = timeout
        self.retries = retries
        self.music_u = jar_value(entries, "MUSIC_U", "MUSIC_R_U")
        if not self.music_u:
            raise SystemExit("cookie jar has no MUSIC_U / MUSIC_R_U value")
        self.cookie_header = "; ".join(f"{n}={v}" for n, v in entries if v) + "; __remember_me=true"
        self.device_id = jar_value(entries, "deviceId") or jar_value(entries, "sDeviceId", "sdeviceId")
        self.sdevice_id = jar_value(entries, "sDeviceId", "sdeviceId")
        self.os = jar_value(entries, "os") or "android"
        self.osver = jar_value(entries, "osver")
        self.appver = jar_value(entries, "appver") or "9.4.95"
        self.buildver = jar_value(entries, "buildver") or "6806"
        self.session = requests.Session()

    def _headers(self, host: str) -> dict:
        h = {
            "Host": host,
            "Connection": "keep-alive",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",  # no br: requests cannot decode brotli; server then uses gzip
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-language": "zh-CN,zh-Hans;q=0.9",
            "Referer": "https://music.163.com",
            "User-Agent": EAPI_UA,
            "Cookie": self.cookie_header,
            "X-Client-Enc-State": "ENCRYPTED",
            "x-aeapi": "true",
            "X-MAM-CustomMark": "cronet",
            "x-os": self.os,
            "x-osver": self.osver,
            "x-appver": self.appver,
            "x-buildver": self.buildver,
            "x-music-u": self.music_u,
        }
        if self.device_id:
            h["x-deviceid"] = self.device_id
        if self.sdevice_id:
            h["x-sdeviceid"] = self.sdevice_id
        return h

    def _request(self, method: str, url: str, host: str, **kw) -> requests.Response:
        kw.setdefault("headers", self._headers(host))
        kw.setdefault("timeout", self.timeout)
        last: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                return self.session.request(method, url, **kw)
            except requests.RequestException as e:
                last = e
                if attempt < self.retries:
                    time.sleep(1.5 * attempt)
        raise last  # type: ignore[misc]

    def _decode_body(self, resp: requests.Response) -> bytes:
        """Return HTTP-decompressed body.

        requests already decodes gzip/deflate; guard against brotli (br) just
        in case the server sends it despite Accept-Encoding lacking br."""
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        body = resp.content
        if "gzip" in enc and body[:2] == b"\x1f\x8b":
            try:
                body = gzip.decompress(body)
            except Exception:
                pass
        elif "br" in enc:
            try:
                import brotli
            except ImportError:
                try:
                    import brotlicffi as brotli
                except ImportError:
                    brotli = None
            if brotli is None:
                raise RuntimeError(
                    "server returned Content-Encoding: br but brotli is not installed; "
                    "pip install brotli or keep Accept-Encoding: gzip, deflate"
                )
            try:
                body = brotli.decompress(body)
            except Exception:
                pass  # already decoded by requests
        return body

    def eapi_post(self, url: str, obj: object, retries: int | None = None) -> dict:
        host = urllib.parse.urlparse(url).hostname or ""
        old = self.retries
        if retries is not None:
            self.retries = retries
        try:
            last_err: Exception | None = None
            for attempt in range(1, self.retries + 1):
                try:
                    params = eapi_params(url, obj)
                    resp = self._request(
                        "POST", url, host, data=f"params={params}".encode("ascii")
                    )
                    body = eapi_decrypt(self._decode_body(resp))
                    try:
                        return json.loads(body)
                    except ValueError as e:
                        raise RuntimeError(
                            f"bad response after decrypt (http {resp.status_code}, "
                            f"Content-Encoding={resp.headers.get('Content-Encoding')!r}): "
                            f"{body[:120]!r}"
                        ) from e
                except (requests.RequestException, RuntimeError) as e:
                    last_err = e
                    if attempt < self.retries:
                        time.sleep(1.5 * attempt)
            raise last_err  # type: ignore[misc]
        finally:
            self.retries = old


# ---------------------------------------------------------------------------
# Image download + upload
# ---------------------------------------------------------------------------
def detect_image(data: bytes, url: str) -> tuple[str, str]:
    """Return (ext, mime) by magic bytes; fallback to URL extension."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif", "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    if data.startswith(b"BM"):
        return "bmp", "image/bmp"
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower().lstrip(".")
    if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
        return ("jpg" if ext == "jpeg" else ext), f"image/{'jpeg' if ext == 'jpeg' else ext}"
    return "jpg", "image/jpeg"


def download_image(client: EapiClient, url: str) -> tuple[bytes, str, str]:
    last: Exception | None = None
    for attempt in range(1, client.retries + 1):
        try:
            resp = client.session.get(
                url,
                timeout=client.timeout,
                headers={"User-Agent": EAPI_UA, "Accept": "image/*,*/*;q=0.8"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"download status {resp.status_code}")
            data = resp.content
            if not data:
                raise RuntimeError("empty image body")
            ext, mime = detect_image(data, resp.url or url)
            return data, ext, mime
        except (requests.RequestException, RuntimeError) as e:
            last = e
            if attempt < client.retries:
                time.sleep(1.5 * attempt)
    raise last  # type: ignore[misc]


def upload_image(client: EapiClient, data: bytes, ext: str, mime: str, filename: str) -> dict:
    """Run NOS token alloc -> PUT -> event img info. Returns pic dict."""
    md5hex = hashlib.md5(data).hexdigest()
    token_body = {
        "filename": filename,
        "local": "false",
        "nos_product": 0,
        "fileSize": len(data),
        "md5": md5hex,
        "ext": ext,
        "type": "image",
    }
    tok = client.eapi_post("https://music.163.com/eapi/nos/token/alloc", token_body)
    if tok.get("code") != 200:
        raise RuntimeError(f"nos token alloc failed: code={tok.get('code')} msg={tok.get('msg')}")
    result = tok.get("result") or {}
    bucket, object_key, token = result.get("bucket"), result.get("objectKey"), result.get("token")
    if not (bucket and object_key and token):
        raise RuntimeError(f"nos token alloc missing result: {tok}")

    # LBS upload node (plain endpoint; try https then http)
    node = ""
    for base in ("https://wanproxy.127.net", "http://wanproxy.127.net"):
        try:
            r = client.session.get(
                f"{base}/lbs?version=1.0&bucketname=cloudmusic", timeout=client.timeout
            )
            if r.status_code == 200:
                uploads = (r.json() or {}).get("upload") or []
                if uploads:
                    node = uploads[0]
                    break
        except Exception:
            continue
    if not node:
        raise RuntimeError("no upload node from wanproxy LBS")

    put_url = f"{node}/{bucket}/{object_key}?version=1.0&offset=0&complete=true"
    put_headers = {
        "X-Nos-Token": token,
        "Content-Type": mime,
        "User-Agent": EAPI_UA,
        "Accept": "*/*",
        "Referer": "https://music.163.com",
    }
    pr = client.session.put(put_url, data=data, headers=put_headers, timeout=client.timeout)
    if pr.status_code != 200:
        raise RuntimeError(f"PUT upload returned {pr.status_code}: {pr.text[:200]!r}")

    img = client.eapi_post(
        "https://music.163.com/eapi/upload/event/img/v1",
        {"imgid": result.get("docId"), "format": ext},
    )
    if img.get("code") != 200:
        raise RuntimeError(f"event img info failed: code={img.get('code')} msg={img.get('msg')}")
    pic = img.get("picInfo") or {}
    for key in ("originId", "squareId", "rectangleId"):
        if pic.get(key) is None:
            raise RuntimeError(f"event img info missing {key}: {img}")
    return {
        "originId": str(pic["originId"]),
        "squareId": str(pic["squareId"]),
        "rectangleId": str(pic["rectangleId"]),
        "pcSquareId": str(pic["squareId"]),
        "pcRectangleId": str(pic["rectangleId"]),
        "originJpgId": str(pic["originId"]),
        "width": pic.get("width") or 0,
        "height": pic.get("height") or 0,
        "index": 0,
    }


# ---------------------------------------------------------------------------
# Publish + verify
# ---------------------------------------------------------------------------
PUBLISH_URL = "https://interface3.music.163.com/eapi/note/share/friends/resource"
EVENT_GET_URL = "https://interface3.music.163.com/eapi/event/get"


def check_privacy(obj: dict, label: str) -> bool | None:
    """Return True if event privacySetting==1, False if ==0, None if unknown."""
    event = obj.get("event") or {}
    if "privacySetting" in event and isinstance(event["privacySetting"], int):
        return event["privacySetting"] == 1
    # fall back to event.json payload if present
    ej = event.get("json")
    if isinstance(ej, str) and ej.startswith("{"):
        try:
            inner = json.loads(ej)
        except json.JSONDecodeError:
            return None
        ext = inner.get("extJsonInfo") or {}
        if isinstance(ext.get("privacySetting"), int):
            return ext["privacySetting"] == 1
    if label:
        print(f"[verify] {label}: privacySetting not present in response (will re-check via event/get)")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cookie", default="data/cookie.json", help="ncmm login cookie jar (Resty json)")
    ap.add_argument("--image-url", action="append", default=[],
                    help="image URL(s); repeatable (default: https://picsum.photos/800/600)")
    ap.add_argument("--title", default="1", help="note title (default: 1)")
    ap.add_argument("--msg", default="1", help="note body (default: 1)")
    ap.add_argument("--no-verify", action="store_true", help="skip privacy re-check via /eapi/event/get")
    ap.add_argument("--selftest", action="store_true", help="run crypto self-test and exit")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return 0

    cookie_path = Path(args.cookie)
    if not cookie_path.is_file():
        print(f"error: cookie file not found: {cookie_path}", file=sys.stderr)
        return 2
    entries = load_jar(cookie_path)
    if not entries:
        print("error: cookie jar is empty", file=sys.stderr)
        return 2
    client = EapiClient(entries)
    print(f"[publish] cookie ok: entries={len(entries)} music_u={mask(client.music_u)}")

    urls = args.image_url or ["https://picsum.photos/800/600"]
    pics_json = "[]"
    if urls:
        pic_list = []
        for i, url in enumerate(urls):
            print(f"[publish] downloading image {i + 1}/{len(urls)}: {url}")
            data, ext, mime = download_image(client, url)
            print(f"[publish] image ok: ext={ext} mime={mime} bytes={len(data)}")
            pic = upload_image(client, data, ext, mime, f"note_{i + 1}.{ext}")
            pic_list.append(pic)
        pics_json = go_json_dumps(pic_list)
        print(f"[publish] uploaded {len(pic_list)} image(s)")

    publish_body = {
        "title": args.title,
        "msg": args.msg,
        "type": "noresource",
        "uuid": secrets.token_hex(16),
        "pics": pics_json,
        "addComment": False,
        "privacySetting": "1",
        "socialSpaceVisible": 0,
    }
    print(f"[publish] sending private note: title={args.title!r} msg={args.msg!r} images={len(urls)} privacy=1")
    reply = client.eapi_post(PUBLISH_URL, publish_body)
    code = reply.get("code")
    if code != 200:
        print(f"error: publish failed code={code} msg={reply.get('msg')} "
              f"(known risk: Actions IP may hit 250 risk control)", file=sys.stderr)
        return 1
    event_id = reply.get("id")
    event = reply.get("event") or {}
    print(f"[publish] ok: event_id={event_id} user_id={reply.get('userId')}")

    # primary check from publish response
    prv = check_privacy(reply, "publish-response")
    if prv is False:
        print("error: published note is NOT self-only (privacySetting=0)!", file=sys.stderr)
        return 1
    if prv is True:
        print("[verify] publish response privacySetting=1 (self-only) ✓")

    # re-check via event/get
    if not args.no_verify and event_id:
        try:
            got = client.eapi_post(EVENT_GET_URL, {"id": event_id})
            gcode = got.get("code")
            if gcode == 200:
                gprv = check_privacy(got, "event/get")
                if gprv is True:
                    print("[verify] event/get privacySetting=1 (self-only) ✓")
                elif gprv is False:
                    print("error: event/get shows privacySetting=0 (NOT self-only)!", file=sys.stderr)
                    return 1
                else:
                    print("[verify] event/get did not expose privacySetting; check manually in App")
            else:
                print(f"[verify] event/get returned code={gcode}; skip (check manually)")
        except Exception as e:
            print(f"[verify] event/get failed: {e}; check manually in App")

    print("[publish] done. Confirm in App: 我的主页/动态 should NOT show this note.")
    return 0


if __name__ == "__main__":
    sys.exit(main())