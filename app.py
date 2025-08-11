"""
Threads Keyword Search Web App (FastAPI)

Quick start
-----------
1) 安裝套件：
   pip install fastapi uvicorn requests python-dateutil

2) 設定環境變數（擇一）：
   # Windows PowerShell
   $env:THREADS_TOKEN="<your_threads_access_token>"
   # macOS / Linux
   export THREADS_TOKEN="<your_threads_access_token>"

3) 本機啟動：
   python app.py
   # 瀏覽器開 http://localhost:8000
"""

from __future__ import annotations
import os, io, csv, time
from typing import Any, Dict, List, Optional

import requests
from dateutil import parser as dtparser
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

APP_TITLE = "Threads 關鍵字搜尋器"
GRAPH_BASE = "https://graph.threads.net"

app = FastAPI(title=APP_TITLE)

def _get_token() -> str:
    token = os.getenv("THREADS_TOKEN")
    if not token:
        raise RuntimeError("尚未設定環境變數 THREADS_TOKEN。請先設定你的 Threads API Access Token。")
    return token

def _get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}"}
    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise HTTPException(status_code=r.status_code, detail=r.text)
        except requests.RequestException as e:
            last_exc = e
            time.sleep(1.2 * (attempt + 1))
    if last_exc:
        raise HTTPException(status_code=502, detail=f"Threads API 連線失敗: {last_exc}")
    raise HTTPException(status_code=502, detail="Threads API 連線失敗")

def _to_unix(ts: Any) -> int:
    if ts is None or ts == "":
        return 0
    if isinstance(ts, (int, float)):
        return int(ts)
    return int(dtparser.parse(str(ts)).timestamp())

def keyword_search(q: str, limit: int = 100, since: Optional[str] = None, until: Optional[str] = None) -> List[Dict[str, Any]]:
    url = f"{GRAPH_BASE}/keyword_search"
    params: Dict[str, Any] = {"q": q, "limit": min(200, max(1, int(limit)))}
    if since:
        params["since"] = _to_unix(since)
    if until:
        params["until"] = _to_unix(until)
    return _get(url, params).get("data", [])

def get_post_fields(media_id: str, fields: Optional[str] = None) -> Dict[str, Any]:
    fields = fields or "id,permalink,like_count,reply_count,repost_count,text,username,created_time"
    url = f"{GRAPH_BASE}/{media_id}"
    return _get(url, {"fields": fields})

def search_and_filter(q: str, min_likes: int = 0, limit: int = 200, since: Optional[str] = None, until: Optional[str] = None) -> List[Dict[str, Any]]:
    raw = keyword_search(q, limit=limit, since=since, until=until)
    results: List[Dict[str, Any]] = []
    for item in raw:
        lk = item.get("like_count")
        if lk is None or ("permalink" not in item):
            try:
                detail = get_post_fields(item.get("id", ""))
                item.update(detail)
                lk = item.get("like_count", 0)
            except Exception:
                lk = lk or 0
        if (lk or 0) >= int(min_likes):
            results.append(item)
    results.sort(key=lambda x: x.get("like_count", 0), reverse=True)
    return results

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML_PAGE

@app.get("/api/search")
def api_search(
    q: str = Query(..., min_length=1, description="關鍵字"),
    min_likes: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    since: Optional[str] = Query(None, description="起始時間 YYYY-MM-DD 或 ISO"),
    until: Optional[str] = Query(None, description="結束時間 YYYY-MM-DD 或 ISO"),
):
    items = search_and_filter(q=q, min_likes=min_likes, limit=limit, since=since, until=until)
    return {"count": len(items), "items": items}

@app.get("/api/export")
def api_export(
    q: str = Query(...),
    min_likes: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    rows = search_and_filter(q=q, min_likes=min_likes, limit=limit, since=since, until=until)
    output = io.StringIO()
    fields = ["id","permalink","text","username","like_count","reply_count","repost_count","created_time"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    filename = f"threads_results.csv"
    return StreamingResponse(iter([output.getvalue().encode("utf-8-sig")]),
                             media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})

HTML_PAGE = r"""
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Threads 關鍵字搜尋器</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900">
  <div class="max-w-6xl mx-auto p-6">
    <header class="mb-6">
      <h1 class="text-2xl md:text-3xl font-bold">🔎 Threads 關鍵字搜尋器</h1>
      <p class="text-sm text-slate-600 mt-1">不用登入帳號，伺服器用官方 API Token 搜尋公開貼文，並以讚數過濾。</p>
    </header>

    <section class="bg-white rounded-2xl shadow p-4 md:p-6">
      <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
        <div class="md:col-span-4">
          <label clas
