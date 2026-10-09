"""文献雷达 wenxian-leida — 共享工具模块。

Python 3.9+ / requests. 处理:
- 配置加载 (config/domains.json)
- 两套 HTTP 会话: 外部(走系统代理 clash) vs Zotero本地(绕过代理)
- OpenAlex 摘要倒排索引重建
- 结果规范化 / 去重键
- 限流退避 (Semantic Scholar 429)
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SKILL_DIR, "config", "domains.json")
# local.json 存个人敏感值(邮箱/userID), 已被 .gitignore 排除, 不进仓库不随包分发
LOCAL_CONFIG_PATH = os.path.join(SKILL_DIR, "config", "local.json")

# clash-verge 会把系统代理套到 localhost, 必须对 Zotero 本地端点绕过
NO_PROXY_HOSTS = ("127.0.0.1", "localhost")


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)
    if os.path.exists(LOCAL_CONFIG_PATH):
        try:
            with open(LOCAL_CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                loc = json.load(f)
            st = cfg.setdefault("settings", {})
            for k, v in loc.items():
                if k == "zotero" and isinstance(v, dict):
                    st.setdefault("zotero", {}).update(v)
                elif isinstance(v, dict) and isinstance(st.get(k), dict):
                    st[k].update(v)
                else:
                    st[k] = v
        except Exception as e:
            sys.stderr.write(f"[warn] local.json 读取失败: {e}\n")
    return cfg


def external_session(use_proxy: bool = False) -> requests.Session:
    """外部 API (OpenAlex / S2 / Unpaywall / CORE)。

    实测: 本机 OpenAlex 等【直连可达且更快】, 而 clash 系统代理间歇性重置连接。
    故默认直连(use_proxy=False); 直连失败时 retry_get 会自动回退到系统代理。
    若某网络环境必须走代理才能出网, 把 use_proxy 设 True 即可。
    """
    s = requests.Session()
    s.trust_env = use_proxy
    if not use_proxy:
        s.proxies = {"http": None, "https": None}  # 强制直连, 绕过 clash
    s.headers.update({"User-Agent": "wenxian-leida/1.0 (research lit radar; mailto:researcher@example.org)"})
    return s


def local_session() -> requests.Session:
    """Zotero 本地 API (127.0.0.1:23119): 强制绕过代理。"""
    s = requests.Session()
    s.trust_env = False
    s.proxies = {"http": None, "https": None}
    s.headers.update({"User-Agent": "wenxian-leida/1.0"})
    return s


def retry_get(session: requests.Session, url: str, params: Optional[Dict] = None,
              headers: Optional[Dict] = None, max_tries: int = 4,
              backoff: float = 2.0) -> Optional[requests.Response]:
    """带指数退避的 GET。专治两件事:
    (1) S2 的 429 限流 -> 退避重试;
    (2) clash 代理间歇性重置连接 -> 直连失败时自动切换到系统代理(或反之)再试。
    """
    sess = session
    switches = 0          # 最多切换通道 2 次
    consecutive_429 = 0
    delay = backoff
    for attempt in range(max_tries * 3):
        try:
            r = sess.get(url, params=params, headers=headers or {}, timeout=40)
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
            if switches < 2:
                switches += 1
                now_proxy = bool(sess.trust_env)
                sess = external_session(use_proxy=not now_proxy)
                sys.stderr.write(f"[warn] {type(e).__name__}; 切换到{'系统代理' if not now_proxy else '直连'}\n")
                continue
            sys.stderr.write(f"[warn] GET {url} 连接失败: {str(e)[:70]}\n")
            time.sleep(delay); delay = min(delay * backoff, 30); continue
        except requests.RequestException as e:
            sys.stderr.write(f"[warn] GET {url} 网络错误: {str(e)[:70]}\n")
            time.sleep(delay); delay = min(delay * backoff, 30); continue
        if r.status_code == 429:
            consecutive_429 += 1
            # 持续 429 = 当前出口 IP 被限流 -> 换通道(换 IP)
            if consecutive_429 >= 3 and switches < 2:
                switches += 1
                now_proxy = bool(sess.trust_env)
                sess = external_session(use_proxy=not now_proxy)
                consecutive_429 = 0
                sys.stderr.write(f"[warn] 持续429; 切换到{'系统代理' if not now_proxy else '直连'}换出口IP\n")
                continue
            sys.stderr.write(f"[warn] 429 限流, 退避 {delay:.0f}s\n")
            time.sleep(delay); delay = min(delay * backoff, 30); continue
        if r.status_code >= 500:
            time.sleep(delay); delay = min(delay * backoff, 30); continue
        return r
    return None


def reconstruct_abstract(inv: Optional[Dict[str, List[int]]]) -> str:
    """OpenAlex 的 abstract_inverted_index -> 正常摘要文本。"""
    if not inv:
        return ""
    pos: Dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    if not pos:
        return ""
    return " ".join(pos[i] for i in sorted(pos))


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9一-鿿]+", "", (t or "").lower())


def dedup_key(rec: Dict[str, Any]) -> str:
    """优先 DOI, 退化到规范化标题。"""
    doi = (rec.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi.replace("https://doi.org/", "").replace("doi:", "")
    return "title:" + norm_title(rec.get("title", ""))


# ---------- 检索质量过滤(实战教训: 撤稿/supplement/预印本重复会混进库) ----------
STOPWORDS = {"the", "a", "an", "and", "or", "of", "on", "in", "for", "to", "with",
             "using", "use", "based", "by", "from", "at", "is", "are", "its", "their", "towards", "toward"}


def norm_title_strong(t: str) -> str:
    """更狠的标题归一化: 去掉英文虚词, 用于抓'预印本 vs 正式发表'这类跨版本重复。"""
    words = re.findall(r"[a-z0-9]+|[一-鿿]", (t or "").lower())
    return "".join(w for w in words if w not in STOPWORDS)


def quality_check(rec: Dict[str, Any]) -> Tuple[bool, str]:
    """返回 (保留?, 原因)。过滤撤稿文献与补充材料(实战抓到过 [Retracted] 和 -supplement)。"""
    title = (rec.get("title") or "").lower()
    doi = (rec.get("doi") or "").lower()
    if "[retracted" in title or title.startswith("retracted:") or "retraction of" in title:
        return False, "retracted"
    if "supplementary material" in title or title.startswith("supplement") or "-supplement" in doi:
        return False, "supplement"
    if title.startswith("corrigendum") or title.startswith("erratum"):
        return False, "corrigendum"
    return True, ""


def is_preprint(rec: Dict[str, Any]) -> bool:
    """标记预印本(保留但打标, 分诊时提示'引用前核对是否已正式发表')。"""
    doi = (rec.get("doi") or "").lower()
    venue = (rec.get("venue") or "").lower()
    return any(s in doi for s in ("ssrn", "researchsquare", "egusphere", "arxiv", "biorxiv", "essoar")) or \
           any(s in venue for s in ("ssrn", "research square", "egusphere", "arxiv", "biorxiv"))


def domain_records(cfg: Dict[str, Any], domain: str) -> Dict[str, Any]:
    d = cfg["domains"].get(domain.upper())
    if not d:
        raise SystemExit(f"[error] 未知领域 '{domain}', 可选: {list(cfg['domains'].keys())}")
    return d


def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
