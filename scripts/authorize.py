"""一次性获取 Zotero 本地 API 授权 key 并保存。

运行后 Zotero 会弹出授权对话框 —— 请在 Zotero 里点【允许/OK】。
key 只对本机 localhost 的 Zotero 有效(合法本地授权令牌), 保存到 config/zotero_key.txt。

用法: python authorize.py
"""
from __future__ import annotations
import json
import os
import sys

from wxl_common import load_config, local_session, SKILL_DIR

KEY_PATH = os.path.join(SKILL_DIR, "config", "zotero_localkey.txt")  # 旧本地key专用, 勿与 web key(zotero_key.txt/zotero_webkey.txt) 混淆


def get_server_id(sess, base: str) -> str:
    r = sess.get(f"{base}/api/users/0/items", params={"limit": "1"}, timeout=15)
    r.raise_for_status()
    return r.headers.get("Zotero-Server-ID", "")


def do_authorize(base: str = None, sess=None, quiet: bool = False) -> str:
    """触发授权弹窗, 返回并保存 key。可被其它脚本复用(如 401 时自动重授权)。"""
    cfg = load_config()
    base = base or cfg["settings"]["zotero"]["local_api"]
    sess = sess or local_session()
    sid = get_server_id(sess, base)
    if not sid:
        raise RuntimeError("拿不到 Zotero-Server-ID; 确认 Zotero 正在运行。")
    if not quiet:
        print(f"[info] Server-ID={sid}")
        print("[info] 正在请求授权... 请到 Zotero 弹窗点【允许】(等待最多120秒)")
    try:
        r = sess.post(f"{base}/api/local/authorize",
                      headers={"Zotero-Server-ID": sid, "Content-Type": "application/json"},
                      data=json.dumps({"appName": "wenxian-leida", "remember": True}), timeout=120)
    except Exception as e:
        raise RuntimeError(f"授权请求异常(可能超时/被拒): {e}")
    if r.status_code != 200:
        raise RuntimeError(f"授权未成功 HTTP {r.status_code}: {r.text[:200]}")
    j = r.json()
    key = j.get("key") or j.get("apiKey") or j.get("token") or ""
    if not key:
        raise RuntimeError(f"响应未识别到 key: {list(j.keys())}")
    with open(KEY_PATH, "w", encoding="utf-8") as f:
        f.write(key)
    if not quiet:
        print(f"[ok] 授权成功, key 已保存到 {KEY_PATH}")
    return key


def load_key() -> str:
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def main() -> None:
    try:
        do_authorize()
    except RuntimeError as e:
        sys.exit(f"[error] {e}")


if __name__ == "__main__":
    main()
