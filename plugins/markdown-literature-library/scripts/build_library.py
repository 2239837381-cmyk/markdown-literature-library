#!/usr/bin/env python3
"""Build a standalone offline literature library from Markdown files.

Only the Python standard library is required. The generated page has no network
dependencies and keeps reading annotations in the browser's local storage.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any, Optional

TOPICS: dict[str, dict[str, Any]] = {
    "foundation": {"label": "概念与理论基础", "color": "#6a7282", "keywords": ["theory", "concept", "collective action", "community", "共同体", "理论", "概念", "集体行动"]},
    "psychology": {"label": "心理机制", "color": "#8a6570", "keywords": ["identity", "emotion", "efficacy", "motivation", "心理", "认同", "情绪", "效能", "动机"]},
    "organization": {"label": "组织与制度", "color": "#9a7b4d", "keywords": ["organization", "institution", "governance", "field", "组织", "制度", "治理", "场域", "同构"]},
    "network": {"label": "网络与传播", "color": "#627d79", "keywords": ["network", "communication", "diffusion", "online", "网络", "传播", "信息", "线上", "动员"]},
    "methods": {"label": "方法与证据", "color": "#756b89", "keywords": ["method", "experiment", "survey", "model", "review", "方法", "实验", "调查", "模型", "综述"]},
    "context": {"label": "实践与具体情境", "color": "#70806a", "keywords": ["environment", "community", "disaster", "politic", "practice", "环境", "社区", "灾害", "政治", "实践"]},
}


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            pass
    return path.read_text(encoding="utf-8", errors="replace")


def split_front_matter(text: str) -> tuple[dict[str, str], str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized
    closing = re.search(r"^---\s*$", normalized[4:], re.MULTILINE)
    if not closing:
        return {}, normalized
    end = 4 + closing.end()
    metadata: dict[str, str] = {}
    for line in normalized[4 : 4 + closing.start()].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip().lower()] = value.strip().strip("[]")
    return metadata, normalized[end:].lstrip("\n")


def first_title(body: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
    return re.sub(r"[*`_]+", "", match.group(1)).strip() if match else fallback


def first_excerpt(body: str) -> str:
    chunks: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "```", "|", ">")):
            continue
        if re.match(r"^[-*+]\s+", line):
            line = re.sub(r"^[-*+]\s+", "", line)
        chunks.append(line)
        if len(" ".join(chunks)) >= 240:
            break
    text = re.sub(r"\s+", " ", " ".join(chunks)).strip()
    return text[:240] + ("…" if len(text) > 240 else "")


def classify(text: str) -> list[str]:
    lowered = text.lower()
    found = [key for key, topic in TOPICS.items() if any(word.lower() in lowered for word in topic["keywords"])]
    return found or ["foundation"]


def build_documents(source: Path, recursive: bool) -> list[dict[str, Any]]:
    iterator = source.rglob("*") if recursive else source.glob("*")
    files = sorted(path for path in iterator if path.is_file() and path.suffix.lower() in {".md", ".markdown"})
    documents: list[dict[str, Any]] = []
    for path in files:
        raw = read_text(path)
        metadata, body = split_front_matter(raw)
        title = metadata.get("title") or first_title(body, path.stem)
        tags = metadata.get("tags") or metadata.get("keywords") or ""
        year = metadata.get("year") or (re.search(r"(?:19|20)\d{2}", raw).group(0) if re.search(r"(?:19|20)\d{2}", raw) else "")
        relative = path.relative_to(source).as_posix()
        digest = hashlib.sha1(relative.encode("utf-8")).hexdigest()[:12]
        documents.append({
            "id": f"doc-{digest}", "title": title, "filename": relative, "year": year,
            "tags": tags, "excerpt": first_excerpt(body), "markdown": body,
            "topics": classify(" ".join([title, tags, body])),
            "source_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        })
    return documents


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{--ink:#3d352c;--muted:#756b60;--paper:#efe9dc;--wood:#4a3b2d;--line:#b8aa96}*{box-sizing:border-box}body{margin:0;color:var(--ink);font:16px/1.7 "Microsoft YaHei","Noto Sans CJK SC",system-ui,sans-serif;background:radial-gradient(ellipse at 20% 0%,#fbf8ef,transparent 44%),linear-gradient(115deg,#d6c9b5,#eee8dc 54%,#c9bba7)}button,input,textarea{font:inherit}.top{position:sticky;top:0;z-index:10;display:flex;gap:18px;align-items:center;padding:14px clamp(16px,4vw,60px);background:linear-gradient(#443a30,#302921);color:#efe6d4;border-bottom:1px solid #a18b68}.brand{font:700 1.3rem Georgia,"Noto Serif SC",serif}.tabs{display:flex;gap:5px}.tabs button{color:#e7dbc7;background:transparent;border:0;padding:7px 10px;cursor:pointer}.tabs button.active{background:#b8a68a;color:#332b22;border-radius:5px}.search{margin-left:auto;max-width:330px;width:100%;padding:7px 12px;border-radius:20px;border:1px solid #9d8b72;background:#eee7da;color:#41382e}main{max-width:1440px;margin:auto;padding:28px clamp(16px,4vw,60px) 70px}.view{display:none}.view.active{display:block}.intro h1{font:700 clamp(2rem,4vw,3.6rem)/1.1 Georgia,"Noto Serif SC",serif;margin:.15em 0}.intro p{color:var(--muted);max-width:760px}.topic-map{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin-top:28px}.topic{min-height:160px;padding:20px;background:rgba(255,253,247,.72);border:1px solid var(--line);border-top:6px solid var(--topic);box-shadow:0 8px 18px #473d3020;cursor:pointer;text-align:left}.topic h2{font:700 1.3rem Georgia,"Noto Serif SC",serif;margin:0}.topic p{color:var(--muted);font-size:.88rem}.topic .count{font-size:.78rem;color:#705c40}.filters{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0}.filters button{border:1px solid #a99981;background:#f4eee3;color:#4b4034;border-radius:20px;padding:6px 10px;cursor:pointer}.filters button.active{background:#554735;color:#f2e7d4}.shelf{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));align-items:end;gap:9px;padding:27px 23px 40px;min-height:540px;background:linear-gradient(transparent 0 83%,#2d251e 83% 87%,#8c7257 87% 89%,#2f271f 89%),repeating-linear-gradient(90deg,#665343 0 26px,#574638 26px 48px,#765f4b 48px 70px);border:8px solid #45372b;box-shadow:inset 0 0 21px #1d160db3}.book{height:263px;position:relative;display:flex;flex-direction:column;justify-content:space-between;align-items:stretch;padding:13px 9px;border:0;border-radius:4px 4px 1px 1px;color:#ebdab6;background:var(--spine);box-shadow:3px 5px 8px #1b130966;cursor:pointer;overflow:hidden;filter:saturate(.63)}.book:before{content:"";position:absolute;inset:6px;border-top:1px solid #f3dda544;border-bottom:1px solid #f3dda533;pointer-events:none}.book:hover{transform:translateY(-12px);filter:brightness(1.1) saturate(.7)}.book .kind,.book .year{position:relative;text-align:center;font-size:.65rem;color:#f1ddb1;text-shadow:0 1px #1b1109}.book .title{position:relative;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:4;overflow:hidden;padding:8px 1px;text-align:center;font:700 .9rem/1.45 Georgia,"Noto Serif SC",serif;color:#f0ddb5;border-top:1px solid #efd9a88c;border-bottom:1px solid #efd9a866;text-shadow:0 1px #1b1109}.drawer{display:none;position:fixed;inset:0;z-index:30;padding:18px;background:#1e1811aa;align-items:center;justify-content:center}.drawer.open{display:flex}.open-book{width:min(1420px,100%);height:min(850px,94vh);display:grid;grid-template-columns:29% minmax(0,1fr) 280px;overflow:hidden;position:relative;background:#fffaf0;box-shadow:0 25px 80px #0008;animation:open .42s ease}.close{position:absolute;z-index:2;right:12px;top:12px;width:34px;height:34px;border-radius:50%;border:1px solid #fff8;background:#2a2119aa;color:#fff;font-size:20px;cursor:pointer}.cover{padding:clamp(27px,4vw,56px);display:flex;flex-direction:column;justify-content:space-between;color:#fff;background:linear-gradient(145deg,#6c5840,#303b44 64%,#b28b4e)}.cover h2{font:700 clamp(1.6rem,3vw,3rem)/1.25 Georgia,"Noto Serif SC",serif}.cover small{line-height:1.8}.reader{overflow:auto;padding:clamp(24px,4vw,52px);background:repeating-linear-gradient(to bottom,#fffaf0 0 31px,#eae1d2 32px)}.source{font-size:.76rem;color:#766c60;border-bottom:1px solid #ddd1be;padding-bottom:14px;margin-bottom:17px;word-break:break-all}.markdown{color:#3c3730}.markdown h1,.markdown h2,.markdown h3{font-family:Georgia,"Noto Serif SC",serif;line-height:1.3}.markdown h2{border-bottom:1px solid #d5c9b7;padding-bottom:.35em;margin-top:2em}.markdown blockquote{margin:1em 0;padding:.2em 1em;border-left:4px solid #a8824d;background:#d8bd8220;color:#61574a}.markdown pre{white-space:pre-wrap;padding:12px;background:#eee8dc;overflow:auto}.markdown code{background:#eee8dc;padding:1px 4px}.notes{overflow:auto;padding:25px 18px;background:linear-gradient(120deg,#d9d0c1,#eee8db 50%,#d3c6b2);border-left:1px solid #aa9a82}.note-head{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid #9f8e75;padding-bottom:12px}.note-head h3{font:700 1.2rem Georgia,"Noto Serif SC",serif;margin:0}.note-head button{height:min-content;border:1px solid #9a896e;background:#fff9ef99;border-radius:4px;padding:4px 7px;color:#554835;cursor:pointer;font-size:.75rem}.note-tip{font-size:.8rem;color:#716656}.note-list{display:grid;gap:10px}.empty{padding:16px 8px;text-align:center;border:1px dashed #a89881;color:#786c5c;font-size:.82rem}.note{position:relative;padding:10px;border-left:5px solid var(--note);background:#fffaf099}.note q{display:block;padding-right:15px;color:#514739;font: .82rem/1.55 Georgia,"Noto Serif SC",serif;cursor:pointer}.note textarea{width:100%;min-height:66px;margin-top:8px;resize:vertical;border:1px solid #bbaa91;background:#fffdf8b8;padding:6px;color:#40372d;font-size:.8rem}.remove{position:absolute;right:7px;top:6px;border:0;background:transparent;color:#766957;cursor:pointer}.menu{display:none;position:fixed;z-index:50;width:185px;padding:7px;background:#fff9ef;border:1px solid #9c896d;box-shadow:0 12px 25px #2c211855}.menu.open{display:block}.menu div{padding:3px 7px 7px;border-bottom:1px solid #e1d6c3;font-size:.72rem;color:#6f604d}.menu button{display:flex;align-items:center;gap:8px;width:100%;padding:7px;border:0;background:transparent;text-align:left;color:#42392e;cursor:pointer}.menu button:hover{background:#eee2ce}.swatch{width:12px;height:12px;border-radius:50%;background:var(--c)}mark.highlight{padding:0 .07em;border-radius:2px}.gold{background:#cba73e77}.blue{background:#75a2b577}.rose{background:#b8717b66}.green{background:#7da07570}@keyframes open{from{opacity:0;transform:translateY(22px) scale(.97)}to{opacity:1;transform:none}}@media(max-width:960px){.topic-map{grid-template-columns:1fr 1fr}.open-book{grid-template-columns:1fr;overflow:auto}.cover{min-height:210px}.reader,.notes{overflow:visible}.notes{border-left:0;border-top:1px solid #aa9a82}.menu{max-width:calc(100vw - 12px)}}@media(max-width:580px){.top{flex-wrap:wrap;gap:8px}.search{order:3;max-width:none}.topic-map{grid-template-columns:1fr}.shelf{grid-template-columns:repeat(auto-fill,minmax(88px,1fr));padding:20px 12px 36px}.book{height:218px}.drawer{padding:5px}}
</style></head><body><header class="top"><div class="brand">__TITLE__</div><nav class="tabs"><button class="active" data-view="map">研究脉络</button><button data-view="shelf">文献书架</button></nav><input id="search" class="search" placeholder="搜索标题、标签或正文"></header><main><section id="map" class="view active"><div class="intro"><h1>从概念、机制到组织、网络与情境</h1><p id="summary"></p></div><div id="topicMap" class="topic-map"></div></section><section id="shelf" class="view"><div class="intro"><h1>从书架中抽出一本文献</h1><p>每本书的题名来自 Markdown 标题；打开后可阅读原文并写下本地批注。</p></div><div id="filters" class="filters"></div><div id="shelfGrid" class="shelf"></div></section></main><div id="drawer" class="drawer" aria-hidden="true"><article class="open-book"><button id="close" class="close" aria-label="关闭">×</button><section id="cover" class="cover"></section><section class="reader"><div id="source" class="source"></div><div id="content" class="markdown"></div></section><aside class="notes"><div class="note-head"><h3>摘录与想法</h3><button id="clearNotes">清空</button></div><p class="note-tip">选中正文后点击鼠标右键，选择颜色即可摘录并添加批注。</p><div id="noteList" class="note-list"></div></aside></article></div><div id="menu" class="menu" role="menu"><div>添加高亮与批注</div><button data-color="gold"><i class="swatch" style="--c:#cba73e"></i>琥珀</button><button data-color="blue"><i class="swatch" style="--c:#75a2b5"></i>雾蓝</button><button data-color="rose"><i class="swatch" style="--c:#b8717b"></i>玫瑰</button><button data-color="green"><i class="swatch" style="--c:#7da075"></i>苔绿</button></div><script>
const documents=__DATA__,topics=__TOPICS__,storeKey='markdown-literature-library-notes-v1';let active='all',query='',currentId='',pendingRange=null;const spines=['#31556b','#79535c','#597063','#85663a','#675b78','#555f6c'];const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function inline(s){return esc(s).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\*([^*]+)\*/g,'<em>$1</em>')}function markdown(md){let h='',list=false;for(const raw of String(md||'').replace(/\r/g,'').split('\n')){const line=raw.trim();if(!line){if(list){h+='</ul>';list=false}continue}let m=line.match(/^(#{1,6})\s+(.+)/);if(m){if(list){h+='</ul>';list=false}h+=`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`;continue}if(/^>\s?/.test(line)){h+='<blockquote>'+inline(line.replace(/^>\s?/,''))+'</blockquote>';continue}m=line.match(/^[-*+]\s+(.+)/);if(m){if(!list){h+='<ul>';list=true}h+='<li>'+inline(m[1])+'</li>';continue}h+='<p>'+inline(line)+'</p>'}return h+(list?'</ul>':'')}function state(){try{return JSON.parse(localStorage.getItem(storeKey)||'{}')}catch{return {}}}function record(id){return state()[id]||{html:'',items:[]}}function save(id,r){const all=state();all[id]=r;try{localStorage.setItem(storeKey,JSON.stringify(all))}catch{}}function doc(){return documents.find(d=>d.id===currentId)}function showMap(){const map=document.getElementById('topicMap');map.innerHTML=Object.entries(topics).map(([id,t])=>{const count=documents.filter(d=>d.topics.includes(id)).length;return `<button class="topic" data-topic="${id}" style="--topic:${t.color}"><h2>${t.label}</h2><p>${t.description}</p><span class="count">${count} 份相关文献 · 点击查看</span></button>`}).join('');map.querySelectorAll('[data-topic]').forEach(b=>b.onclick=()=>{active=b.dataset.topic;view('shelf');renderShelf()})}function renderFilters(){const root=document.getElementById('filters');root.innerHTML=[['all','全部文献'],...Object.entries(topics).map(([id,t])=>[id,t.label])].map(([id,label])=>`<button class="${active===id?'active':''}" data-filter="${id}">${label}</button>`).join('');root.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{active=b.dataset.filter;renderFilters();renderShelf()})}function visible(){const q=query.toLowerCase();return documents.filter(d=>(active==='all'||d.topics.includes(active))&&(!q||[d.title,d.tags,d.filename,d.markdown].join(' ').toLowerCase().includes(q)))}function renderShelf(){renderFilters();const docs=visible(),root=document.getElementById('shelfGrid');root.innerHTML=docs.length?docs.map((d,i)=>`<button class="book" data-id="${d.id}" style="--spine:${spines[i%spines.length]}"><span class="kind">${esc(d.tags||'Markdown 文献')}</span><span class="title">${esc(d.title)}</span><span class="year">${esc(d.year||'文献库')}</span></button>`).join(''):'<div class="empty">没有找到匹配文献。</div>';root.querySelectorAll('[data-id]').forEach(b=>b.onclick=()=>openDoc(documents.find(d=>d.id===b.dataset.id),b))}function openDoc(d,b){if(!d)return;currentId=d.id;const r=record(d.id);document.getElementById('cover').innerHTML=`<div><small>Markdown 文献</small><h2>${esc(d.title)}</h2><small>${d.year?`年份：${esc(d.year)}<br>`:''}${d.tags?`关键词：${esc(d.tags)}`:''}</small></div><p>${esc(d.excerpt||'右页保留完整 Markdown 原文。')}</p>`;document.getElementById('source').textContent='来源文件：'+d.filename;document.getElementById('content').innerHTML=r.html||markdown(d.markdown);renderNotes(d);const drawer=document.getElementById('drawer');drawer.classList.add('open');drawer.setAttribute('aria-hidden','false');if(b){b.animate([{transform:'translateY(0)'},{transform:'translateY(-27px) rotate(-2deg)'},{transform:'translateY(-12px) rotate(-1deg)'}],{duration:480,easing:'cubic-bezier(.2,.8,.2,1)'})}}function renderNotes(d){const root=document.getElementById('noteList'),items=record(d.id).items||[];root.innerHTML=items.length?items.map(n=>`<article class="note" style="--note:${color(n.color)}"><button class="remove" data-remove="${n.id}" aria-label="删除">×</button><q data-focus="${n.id}">${esc(n.quote)}</q><textarea data-note="${n.id}" placeholder="写下你的批注…">${esc(n.note||'')}</textarea></article>`).join(''):'<div class="empty">还没有批注。</div>';root.querySelectorAll('[data-note]').forEach(el=>el.oninput=()=>{const r=record(d.id);r.items=r.items.map(n=>n.id===el.dataset.note?{...n,note:el.value}:n);save(d.id,r)});root.querySelectorAll('[data-remove]').forEach(el=>el.onclick=()=>removeNote(d,el.dataset.remove));root.querySelectorAll('[data-focus]').forEach(el=>el.onclick=()=>{const mark=document.querySelector(`[data-note-id="${el.dataset.focus}"]`);mark?.scrollIntoView({behavior:'smooth',block:'center'})})}function color(c){return({gold:'#cba73e',blue:'#75a2b5',rose:'#b8717b',green:'#7da075'})[c]||'#cba73e'}function removeNote(d,id){const content=document.getElementById('content'),mark=content.querySelector(`[data-note-id="${id}"]`);if(mark)mark.replaceWith(document.createTextNode(mark.textContent));const r=record(d.id);r.items=r.items.filter(n=>n.id!==id);r.html=content.innerHTML;save(d.id,r);renderNotes(d)}function hideMenu(){document.getElementById('menu').classList.remove('open');pendingRange=null}function inside(range){let n=range?.commonAncestorContainer;if(n?.nodeType===3)n=n.parentNode;return !!n&&document.getElementById('content').contains(n)}function apply(colorName){const d=doc(),content=document.getElementById('content'),range=pendingRange;if(!d||!range||range.collapsed||!inside(range))return hideMenu();const id=`n-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,mark=document.createElement('mark');mark.className=`highlight ${colorName}`;mark.dataset.noteId=id;try{mark.append(range.extractContents());range.insertNode(mark)}catch{return hideMenu()}const r=record(d.id);r.items=[...(r.items||[]),{id,color:colorName,quote:mark.textContent.replace(/\s+/g,' ').trim().slice(0,360),note:''}];r.html=content.innerHTML;save(d.id,r);renderNotes(d);window.getSelection().removeAllRanges();hideMenu()}function view(id){document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===id));document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===id))}document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{view(b.dataset.view);if(b.dataset.view==='shelf')renderShelf()});document.getElementById('search').oninput=e=>{query=e.target.value;renderShelf()};document.getElementById('close').onclick=()=>{hideMenu();document.getElementById('drawer').classList.remove('open')};document.getElementById('drawer').onclick=e=>{if(e.target===e.currentTarget)document.getElementById('close').click()};document.getElementById('content').oncontextmenu=e=>{const s=window.getSelection();if(!s||s.isCollapsed||!s.rangeCount||!inside(s.getRangeAt(0)))return;e.preventDefault();pendingRange=s.getRangeAt(0).cloneRange();const menu=document.getElementById('menu');menu.style.left=Math.min(e.clientX,innerWidth-195)+'px';menu.style.top=Math.min(e.clientY,innerHeight-205)+'px';menu.classList.add('open')};document.getElementById('menu').querySelectorAll('[data-color]').forEach(b=>b.onclick=()=>apply(b.dataset.color));document.getElementById('clearNotes').onclick=()=>{const d=doc();if(!d)return;document.getElementById('content').innerHTML=markdown(d.markdown);save(d.id,{html:'',items:[]});renderNotes(d)};document.addEventListener('click',e=>{if(!document.getElementById('menu').contains(e.target))hideMenu()});document.addEventListener('keydown',e=>{if(e.key==='Escape'){hideMenu();document.getElementById('drawer').classList.remove('open')}});document.getElementById('summary').textContent=`已读取 ${documents.length} 份 Markdown 文献；关系分类只依据文献中可见内容生成。`;showMap();renderShelf();
</script></body></html>"""


def merge_index(documents: list[dict[str, Any]], index_path: Optional[Path]) -> None:
    if not index_path:
        return
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    cards = {card["id"]: card for card in payload.get("documents", [])}
    for document in documents:
        if document["id"] in cards:
            document["card"] = cards[document["id"]]


def change_manifest(documents: list[dict[str, Any]], previous: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    old = {item["id"]: item for item in previous.get("documents", [])}
    current = {item["id"]: item for item in documents}
    counts = {"added": 0, "updated": 0, "unchanged": 0, "removed": 0}
    manifest_docs = []
    for item in documents:
        before = old.get(item["id"])
        status = "added" if not before else ("unchanged" if before.get("source_hash") == item["source_hash"] else "updated")
        counts[status] += 1
        manifest_docs.append({key: item[key] for key in ("id", "filename", "title", "source_hash")})
    counts["removed"] = len(set(old) - set(current))
    return {"schema_version": 1, "documents": manifest_docs, "changes": counts}, counts


def build_page(documents: list[dict[str, Any]], title: str) -> str:
    safe_data = json.dumps(documents, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    topic_data = {key: {"label": value["label"], "color": value["color"], "description": "基于文献题名、标签与正文中的可见关键词归类。"} for key, value in TOPICS.items()}
    page = HTML_TEMPLATE.replace("__TITLE__", html.escape(title)).replace("__DATA__", safe_data).replace("__TOPICS__", json.dumps(topic_data, ensure_ascii=False))
    actions = '<div class="note-head"><h3>摘录与想法</h3><div class="note-actions"><select id="noteColor" aria-label="批注颜色"><option value="all">全部颜色</option><option value="gold">琥珀</option><option value="blue">雾蓝</option><option value="rose">玫瑰</option><option value="green">苔绿</option></select><button id="exportCurrent">导出本文</button><button id="exportAll">导出全部</button><button id="clearNotes">清空</button></div></div>'
    page = page.replace('<div class="note-head"><h3>摘录与想法</h3><button id="clearNotes">清空</button></div>', actions)
    page = page.replace("document.getElementById('source').textContent='来源文件：'+d.filename;", "document.getElementById('source').innerHTML='来源文件：'+esc(d.filename)+(d.card?paperCardHtml(d.card):'');")
    extra_css = '<style>.note-head{display:block}.note-actions{display:flex;gap:5px;flex-wrap:wrap;margin-top:9px}.note-actions select,.note-actions button{border:1px solid #9a896e;background:#fff9ef99;border-radius:4px;padding:4px 6px;color:#554835;font-size:.72rem}.paper-card{margin-top:12px;padding:10px;background:#f3ecdf;border:1px solid #cbbda8}.paper-card summary{cursor:pointer;font-weight:700}.paper-card dl{display:grid;grid-template-columns:80px 1fr;gap:5px;margin:10px 0}.paper-card dt{color:#7d684c}.paper-card dd{margin:0}.evidence{display:inline-block;margin-left:5px;padding:1px 4px;border-radius:3px;background:#ddd0ba;font-size:.65rem}</style>'
    extra_js = r"""<script>
function paperCardHtml(card){const fields=[['研究问题','research_question'],['理论框架','theory'],['方法','methods'],['主要发现','findings'],['局限','limitations']];return `<details class="paper-card"><summary>结构化文献卡</summary><dl>${fields.map(([label,key])=>`<dt>${label}</dt><dd>${esc(card[key]||'未找到明确内容')}<span class="evidence">${esc(card.evidence?.[key]||'not_found')}</span></dd>`).join('')}</dl></details>`}
function noteLabel(color){return({gold:'琥珀',blue:'雾蓝',rose:'玫瑰',green:'苔绿'})[color]||color}
function noteMarkdown(allDocuments){const filter=document.getElementById('noteColor').value,all=state(),selected=allDocuments?documents:[doc()].filter(Boolean);let output='# 文献批注\n\n';for(const d of selected){const items=(all[d.id]?.items||[]).filter(item=>filter==='all'||item.color===filter);if(!items.length)continue;output+=`## ${d.title}\n\n- 来源：${d.filename}\n\n`;for(const item of items){output+=`### ${noteLabel(item.color)}高亮\n\n> ${item.quote}\n\n${item.note||'（未填写批注）'}\n\n`}}return output}
function downloadNotes(allDocuments){const text=noteMarkdown(allDocuments);if(!text.includes('### '))return alert('当前筛选条件下没有可导出的批注。');const blob=new Blob([text],{type:'text/markdown;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=allDocuments?'全部文献批注.md':`${(doc()?.title||'文献').replace(/[\\/:*?"<>|]/g,'_')}-批注.md`;a.click();URL.revokeObjectURL(url)}
document.getElementById('exportCurrent').onclick=()=>downloadNotes(false);document.getElementById('exportAll').onclick=()=>downloadNotes(true);
</script>"""
    return page.replace("</style></head>", "</style>" + extra_css + "</head>").replace("</script></body>", "</script>" + extra_js + "</body>")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an offline literature library from Markdown files.")
    parser.add_argument("source", type=Path, help="Markdown source directory")
    parser.add_argument("output", type=Path, help="Output HTML path")
    parser.add_argument("--title", default="文献研究脉络库", help="HTML document title")
    parser.add_argument("--no-recursive", action="store_true", help="Read only the immediate source directory")
    parser.add_argument("--index", type=Path, help="Optional literature-index.json from analyze_literature.py")
    parser.add_argument("--manifest", type=Path, help="Incremental manifest path; default: output with .manifest.json")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_dir():
        parser.error(f"source is not a directory: {source}")
    documents = build_documents(source, recursive=not args.no_recursive)
    if not documents:
        parser.error("no .md or .markdown files found in source directory")
    output = args.output.expanduser().resolve()
    index_path = args.index.expanduser().resolve() if args.index else None
    if index_path and not index_path.is_file():
        parser.error(f"index is not a file: {index_path}")
    merge_index(documents, index_path)
    manifest_path = (args.manifest.expanduser().resolve() if args.manifest else output.with_suffix(".manifest.json"))
    try:
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    except (json.JSONDecodeError, OSError):
        previous_manifest = {}
    manifest, changes = change_manifest(documents, previous_manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_page(documents, args.title), encoding="utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"documents": len(documents), "output": str(output), "manifest": str(manifest_path), "changes": changes}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
