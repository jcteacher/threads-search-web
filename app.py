from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

HTML_PAGE = r"""
<!DOCTYPE html>
<html>
<head>
    <title>Threads Keyword Search</title>
</head>
<body>
    <h1>Threads Keyword Search</h1>
    <form method="get" action="/search">
        <label>關鍵字（可用逗號分隔多個）:</label>
        <input type="text" name="keywords" required>
        <label>最低讚數:</label>
        <input type="number" name="min_likes" value="0" min="0">
        <button type="submit">搜尋</button>
    </form>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_PAGE

@app.get("/search", response_class=HTMLResponse)
async def search(keywords: str, min_likes: int = 0):
    # 模擬搜尋邏輯（真實版本需呼叫 Threads API 或爬蟲）
    keywords_list = [k.strip() for k in keywords.split(",") if k.strip()]
    results = []
    for kw in keywords_list:
        results.append(f"假資料：{kw} - 讚數 {min_likes}+")
    
    html_results = "<h2>搜尋結果</h2><ul>"
    for r in results:
        html_results += f"<li>{r}</li>"
    html_results += "</ul>"
    html_results += '<a href="/">回首頁</a>'
    return html_results
