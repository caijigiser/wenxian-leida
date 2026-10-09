"""Zotero Web API 客户端 (api.zotero.org) —— 持久 key, 无弹窗, 云端写入后自动同步回本地。

为什么用它: 本地 API 的授权 key 秒级过期(remember:false), 撑不完批量写;
Web API key 持久不过期, 是 pyzotero 等工具的标准做法。

需要: config/zotero_webkey.txt 里存 Web API key(Read/Write 权限);
      settings.zotero.user_id 填自己的数字 userID(建议放 config/local.json,
      该文件不进 git; userID 在 zotero.org/settings/keys 页面可见)。
"""
from __future__ import annotations
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from wxl_common import external_session, load_config, norm_title, SKILL_DIR

WEBKEY_PATH = os.path.join(SKILL_DIR, "config", "zotero_webkey.txt")
# 用户可能把 web key 存进了 zotero_key.txt(旧本地key文件), 一并兼容读取
WEBKEY_ALT = os.path.join(SKILL_DIR, "config", "zotero_key.txt")
BASE = "https://api.zotero.org"


def load_webkey() -> str:
    for p in (WEBKEY_PATH, WEBKEY_ALT):
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8-sig") as f:  # utf-8-sig 自动去 BOM
                k = f.read().strip()
            if k:
                return k
    return ""


def get_user_id() -> str:
    cfg = load_config()
    return str(cfg["settings"]["zotero"].get("user_id", ""))


class ZoteroWeb:
    def __init__(self, user_id: str = None, key: str = None):
        self.user_id = user_id or get_user_id()
        self.key = key or load_webkey()
        if not self.key:
            raise SystemExit("[error] 未找到 Web API key。请把 key 存到 "
                             f"{WEBKEY_PATH} (创建: zotero.org/settings/keys, 需 Read/Write)。")
        self.sess = external_session()  # 直连 + 连接失败自动切代理(见 wxl_common)
        self.ver = self._fetch_version()

    # ---------- 底层请求(带通道兜底) ----------
    def _do(self, method: str, path: str, body: Any = None,
            params: Optional[Dict] = None, write: bool = False) -> Optional[requests.Response]:
        url = BASE + path
        headers = {"Zotero-API-Key": self.key, "Zotero-API-Version": "3"}
        if write:
            headers["If-Unmodified-Since-Version"] = str(self.ver)
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body)
        for use_proxy in (False, True):  # 直连优先, 失败切代理
            sess = self.sess if not use_proxy else external_session(use_proxy=True)
            try:
                r = sess.request(method, url, data=data, params=params, headers=headers, timeout=60)
            except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
                sys.stderr.write(f"[warn] {method} {path} {type(e).__name__}; 换通道\n")
                continue
            except requests.RequestException as e:
                sys.stderr.write(f"[warn] {method} {path} 错误: {str(e)[:80]}\n")
                continue
            if r.status_code == 429:
                sys.stderr.write("[warn] Web API 429, 退避 3s\n"); time.sleep(3); continue
            return r
        return None

    def _fetch_version(self) -> int:
        r = self._do("GET", f"/users/{self.user_id}/items", params={"limit": "1"})
        if r is None or r.status_code != 200:
            code = getattr(r, "status_code", "?")
            if code in (401, 403):
                raise SystemExit(f"[error] Web API key 无效/无权限 (HTTP {code})。请确认 key 有 Read/Write 权限。")
            raise SystemExit(f"[error] 取库版本失败 HTTP {code}")
        return int(r.headers.get("Last-Modified-Version", "0"))

    def _bump(self, r: requests.Response) -> None:
        nv = r.headers.get("Last-Modified-Version")
        if nv:
            self.ver = int(nv)

    # ---------- 去重: 读全库 DOI/标题 ----------
    def existing_dedup_keys(self) -> Dict[str, str]:
        keys: Dict[str, str] = {}
        start = 0
        while True:
            r = self._do("GET", f"/users/{self.user_id}/items",
                         params={"limit": "100", "start": str(start),
                                 "itemType": "-attachment -note", "format": "json"})
            if r is None or r.status_code != 200:
                sys.stderr.write(f"[warn] 读库中断 start={start}\n"); break
            batch = r.json()
            if not batch:
                break
            for it in batch:
                k = it.get("key", "")
                data = it.get("data", it)
                doi = (data.get("DOI") or "").strip().lower()
                title = data.get("title") or ""
                if doi:
                    keys["doi:" + doi.replace("https://doi.org/", "")] = k
                if title:
                    keys["title:" + norm_title(title)] = k
            if len(batch) < 100:
                break
            start += 100
        return keys

    # ---------- 分类 ----------
    def list_collections(self) -> List[Dict[str, Any]]:
        out = []
        start = 0
        while True:
            r = self._do("GET", f"/users/{self.user_id}/collections",
                         params={"limit": "100", "start": str(start)})
            if r is None or r.status_code != 200:
                break
            batch = r.json()
            out.extend(batch)
            if len(batch) < 100:
                break
            start += 100
        return out

    def ensure_collection(self, name: str) -> Optional[str]:
        for c in self.list_collections():
            data = c.get("data", c)
            if (data.get("name") or "").strip() == name:
                return c.get("key") or data.get("key")
        r = self._do("POST", f"/users/{self.user_id}/collections",
                     body={"0": {"name": name}}, write=True)
        if r is not None and r.status_code in (200, 201):
            self._bump(r)
            j = r.json()
            succ = j.get("successful", {})
            for _, v in succ.items():
                if isinstance(v, dict) and v.get("key"):
                    return v["key"]
        sys.stderr.write(f"[warn] 建分类 '{name}' 失败: {getattr(r,'status_code','?')} {getattr(r,'text','')[:150]}\n")
        return None

    # ---------- 建条目 ----------
    def create_items(self, items: List[Dict[str, Any]]) -> Dict[int, str]:
        """批量建条目, 返回 {原索引: 新key}。"""
        created: Dict[int, str] = {}
        B = 25
        for i in range(0, len(items), B):
            chunk = items[i:i + B]
            body = {str(j): it for j, it in enumerate(chunk)}
            r = self._do("POST", f"/users/{self.user_id}/items", body=body, write=True)
            if r is None or r.status_code not in (200, 201):
                sys.stderr.write(f"[warn] 批量写入失败: {getattr(r,'status_code','?')} {getattr(r,'text','')[:200]}\n")
                continue
            self._bump(r)
            j = r.json()
            for idx_str, v in (j.get("successful", {}) or {}).items():
                if isinstance(v, dict):
                    if v.get("key"):
                        created[i + int(idx_str)] = v["key"]
                    if v.get("version"):
                        self.ver = max(self.ver, int(v["version"]))  # 多批次时保持版本最新, 防 412
            for idx_str, v in (j.get("failed", {}) or {}).items():
                sys.stderr.write(f"[warn] 条目失败 #{idx_str}: {str(v)[:150]}\n")
            time.sleep(0.3)
        return created
