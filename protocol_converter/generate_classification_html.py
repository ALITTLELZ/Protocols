#!/usr/bin/env python3
"""
Generate a self-contained HTML viewer for protocol classification results.

Reads classification_results.json, embeds README and transfer_actions data,
and outputs classification_viewer.html.

Usage:
    python generate_classification_html.py
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_JSON = os.path.join(SCRIPT_DIR, "classification_results.json")
ORIGINAL_DIR = os.path.join(SCRIPT_DIR, "original")
TRANSFER_DIR = os.path.join(SCRIPT_DIR, "transfer_actions_copy3")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "classification_viewer.html")


def read_readme(protocol_name):
    """Read full README.md content for a protocol."""
    readme_path = os.path.join(ORIGINAL_DIR, protocol_name, "README.md")
    if not os.path.exists(readme_path):
        return None
    with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def read_transfer_actions(protocol_name):
    """Read transfer_actions JSON for a protocol."""
    json_path = os.path.join(TRANSFER_DIR, f"{protocol_name}.json")
    if not os.path.exists(json_path):
        return None
    with open(json_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def generate_html(data, readmes, transfers):
    """Generate the self-contained HTML string."""

    # Prepare embedded data
    embedded = {
        "classification": data,
        "readmes": readmes,
        "transfers": transfers,
    }
    json_data = json.dumps(embedded, ensure_ascii=False)

    html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Protocol Classification Viewer</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }

.header {
    background: #1a1a2e; color: #fff; padding: 16px 24px;
    display: flex; flex-wrap: wrap; align-items: center; gap: 16px;
}
.header h1 { font-size: 20px; font-weight: 600; }
.header .stats {
    display: flex; gap: 12px; flex-wrap: wrap; font-size: 13px;
}
.header .stat {
    background: rgba(255,255,255,0.12); padding: 4px 10px; border-radius: 4px;
    cursor: pointer; transition: background 0.15s, box-shadow 0.15s;
    user-select: none;
}
.header .stat:hover { background: rgba(255,255,255,0.22); }
.header .stat.active { background: rgba(255,255,255,0.35); box-shadow: 0 0 0 2px rgba(255,255,255,0.5); }
.stat-common { border-left: 3px solid #4caf50; }
.stat-specialized { border-left: 3px solid #ff9800; }
.stat-non_bio { border-left: 3px solid #f44336; }
.stat-core { border-left: 3px solid #2196f3; }
.stat-total { border-left: 3px solid #aaa; }

.container { display: flex; height: calc(100vh - 60px); }

/* Left panel */
.left-panel {
    width: 360px; min-width: 280px; background: #fff;
    border-right: 1px solid #ddd; display: flex; flex-direction: column;
    overflow: hidden;
}
.search-box {
    padding: 10px 12px; border-bottom: 1px solid #eee;
}
.search-box input {
    width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 6px;
    font-size: 13px; outline: none;
}
.search-box input:focus { border-color: #2196f3; }
.tree {
    flex: 1; overflow-y: auto; padding: 6px 0; font-size: 13px;
}
.tree-category {
    cursor: pointer; padding: 6px 12px; font-weight: 600;
    display: flex; align-items: center; gap: 6px;
    user-select: none;
}
.tree-category:hover { background: #f0f0f0; }
.tree-category .arrow { transition: transform 0.15s; display: inline-block; font-size: 10px; }
.tree-category .arrow.open { transform: rotate(90deg); }
.tree-category .badge {
    font-size: 11px; font-weight: 400; color: #888; margin-left: auto;
}
.tree-sub {
    cursor: pointer; padding: 5px 12px 5px 28px; font-weight: 500;
    display: flex; align-items: center; gap: 6px;
    user-select: none; color: #555;
}
.tree-sub:hover { background: #f0f0f0; }
.tree-sub .badge { font-size: 11px; font-weight: 400; color: #999; margin-left: auto; }
.tree-sub .core-badge { font-size: 11px; color: #2196f3; margin-left: 4px; }
.tree-children { display: none; }
.tree-children.open { display: block; }
.tree-item {
    padding: 4px 12px 4px 44px; cursor: pointer;
    display: flex; align-items: center; gap: 4px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tree-item:hover { background: #e8f0fe; }
.tree-item.selected { background: #d2e3fc; font-weight: 500; }
.tree-item .core-star { color: #ff9800; font-size: 12px; }
.tree-item-sub {
    padding-left: 56px;
}

/* Right panel */
.right-panel {
    flex: 1; display: flex; flex-direction: column; overflow: hidden;
    background: #fff;
}
.detail-header {
    padding: 16px 20px; border-bottom: 1px solid #eee; background: #fafafa;
}
.detail-header h2 { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.detail-meta {
    display: flex; flex-wrap: wrap; gap: 8px; font-size: 13px;
}
.detail-meta .tag {
    padding: 2px 8px; border-radius: 4px; font-size: 12px;
}
.tag-common { background: #e8f5e9; color: #2e7d32; }
.tag-specialized { background: #fff3e0; color: #e65100; }
.tag-non_bio { background: #ffebee; color: #c62828; }
.tag-sub { background: #e3f2fd; color: #1565c0; }
.tag-core { background: #fff8e1; color: #f57f17; }
.detail-reason {
    margin-top: 8px; font-size: 13px; color: #555; line-height: 1.5;
}

.tabs {
    display: flex; border-bottom: 1px solid #eee; background: #fafafa;
}
.tab {
    padding: 10px 20px; cursor: pointer; font-size: 13px; font-weight: 500;
    border-bottom: 2px solid transparent; color: #666;
}
.tab:hover { color: #333; }
.tab.active { color: #1a73e8; border-bottom-color: #1a73e8; }

.tab-content {
    flex: 1; overflow-y: auto; padding: 16px 20px;
}
.tab-pane { display: none; }
.tab-pane.active { display: block; }

/* README rendering */
.readme-content { line-height: 1.7; font-size: 14px; }
.readme-content h1 { font-size: 22px; margin: 16px 0 8px; border-bottom: 1px solid #eee; padding-bottom: 6px; }
.readme-content h2 { font-size: 18px; margin: 14px 0 6px; }
.readme-content h3 { font-size: 15px; margin: 12px 0 4px; }
.readme-content p { margin: 8px 0; }
.readme-content ul, .readme-content ol { margin: 8px 0 8px 24px; }
.readme-content li { margin: 2px 0; }
.readme-content code { background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 13px; }
.readme-content pre { background: #f5f5f5; padding: 12px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
.readme-content a { color: #1a73e8; text-decoration: none; }
.readme-content a:hover { text-decoration: underline; }
.readme-content img { max-width: 100%; }
.readme-content hr { border: none; border-top: 1px solid #eee; margin: 12px 0; }

/* JSON viewer */
.json-content {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 12px; line-height: 1.6; white-space: pre-wrap; word-break: break-all;
    background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 8px;
    overflow-x: auto;
}
.json-key { color: #9cdcfe; }
.json-string { color: #ce9178; }
.json-number { color: #b5cea8; }
.json-bool { color: #569cd6; }
.json-null { color: #569cd6; }

.placeholder {
    color: #999; font-size: 14px; text-align: center; padding: 60px 20px;
}
.no-data { color: #999; font-style: italic; }
</style>
</head>
<body>

<div class="header">
    <h1>Protocol Classification Viewer</h1>
    <div class="stats" id="stats"></div>
</div>

<div class="container">
    <div class="left-panel">
        <div class="search-box">
            <input type="text" id="search" placeholder="搜索 protocol 编码...">
        </div>
        <div class="tree" id="tree"></div>
    </div>
    <div class="right-panel">
        <div class="detail-header" id="detail-header">
            <div class="placeholder">← 从左侧选择一个 protocol 查看详情</div>
        </div>
        <div class="tabs" id="tabs" style="display:none;">
            <div class="tab active" data-tab="readme">README</div>
            <div class="tab" data-tab="transfer">Transfer Actions</div>
        </div>
        <div class="tab-content" id="tab-content">
            <div class="tab-pane active" id="pane-readme"></div>
            <div class="tab-pane" id="pane-transfer"></div>
        </div>
    </div>
</div>

<script>
const DATA = """ + json_data + r""";

const cls = DATA.classification;
const readmes = DATA.readmes;
const transfers = DATA.transfers;
const protocols = cls.protocols || [];

// Build stats
const statsEl = document.getElementById('stats');
const summary = cls.summary || {};
const subSummary = cls.sub_summary || {};
const coreCount = cls.core_count || 0;
statsEl.innerHTML = `
    <span class="stat stat-total active" data-filter="all">总计: ${cls.total || protocols.length}</span>
    <span class="stat stat-common" data-filter="common">Common: ${summary.common || 0}</span>
    <span class="stat stat-specialized" data-filter="specialized">Specialized: ${summary.specialized || 0}</span>
    <span class="stat stat-non_bio" data-filter="non_bio">Non-bio: ${summary.non_bio || 0}</span>
    <span class="stat stat-core" data-filter="core">★ Core: ${coreCount}</span>
`;

// Category filter state
let activeCategoryFilter = 'all';

// Stat click handlers
document.querySelectorAll('.stat[data-filter]').forEach(stat => {
    stat.addEventListener('click', () => {
        const filter = stat.dataset.filter;
        // Toggle: click same filter again → back to all
        if (activeCategoryFilter === filter && filter !== 'all') {
            activeCategoryFilter = 'all';
        } else {
            activeCategoryFilter = filter;
        }
        // Update active state
        document.querySelectorAll('.stat[data-filter]').forEach(s => s.classList.remove('active'));
        document.querySelector(`.stat[data-filter="${activeCategoryFilter}"]`).classList.add('active');
        renderTree(searchInput.value);
    });
});

const treeEl = document.getElementById('tree');

function renderTree(filterText) {
    treeEl.innerHTML = '';
    const ft = (filterText || '').toLowerCase();
    const cf = activeCategoryFilter;

    // Helper: match search text
    function matchSearch(p) {
        if (!ft) return true;
        return p.name.toLowerCase().includes(ft);
    }

    // Helper: match category filter
    function matchCategory(p) {
        if (cf === 'all') return true;
        if (cf === 'core') return p.is_core === true;
        return p.classification === cf;
    }

    // Combined filter
    function matchAll(p) {
        return matchSearch(p) && matchCategory(p);
    }

    // Render common with sub-categories
    const showCommon = cf === 'all' || cf === 'common' || cf === 'core';
    if (showCommon) {
        const commonProtos = protocols.filter(p => p.classification === 'common');
        const matchedCommon = commonProtos.filter(matchAll);
        if (matchedCommon.length > 0) {
            const catDiv = document.createElement('div');

            const catHeader = document.createElement('div');
            catHeader.className = 'tree-category';
            catHeader.innerHTML = `<span class="arrow open">\u25b6</span> Common <span class="badge">${matchedCommon.length}</span>`;
            catDiv.appendChild(catHeader);

            const catChildren = document.createElement('div');
            catChildren.className = 'tree-children open';

            // Group by sub_category
            const subGroups = {};
            const unsorted = [];
            for (const p of matchedCommon) {
                const sc = p.sub_category;
                if (sc) {
                    if (!subGroups[sc]) subGroups[sc] = [];
                    subGroups[sc].push(p);
                } else {
                    unsorted.push(p);
                }
            }

            // Render each sub-category
            const subOrder = Object.keys(subGroups).sort((a, b) => subGroups[b].length - subGroups[a].length);
            for (const sc of subOrder) {
                const items = subGroups[sc];
                const coreInGroup = items.filter(p => p.is_core).length;

                const subHeader = document.createElement('div');
                subHeader.className = 'tree-sub';
                subHeader.innerHTML = `<span class="arrow">\u25b6</span> ${sc} <span class="badge">${items.length}</span>${coreInGroup > 0 ? `<span class="core-badge">\u2605${coreInGroup}</span>` : ''}`;
                catChildren.appendChild(subHeader);

                const subChildren = document.createElement('div');
                subChildren.className = 'tree-children';

                for (const p of items) {
                    const item = document.createElement('div');
                    item.className = 'tree-item tree-item-sub';
                    item.dataset.name = p.name;
                    item.innerHTML = `${p.is_core ? '<span class="core-star">\u2605</span> ' : ''}${p.name}`;
                    item.addEventListener('click', () => selectProtocol(p.name));
                    subChildren.appendChild(item);
                }
                catChildren.appendChild(subChildren);

                subHeader.addEventListener('click', () => {
                    subChildren.classList.toggle('open');
                    subHeader.querySelector('.arrow').classList.toggle('open');
                });
            }

            // Unsorted common
            if (unsorted.length > 0) {
                for (const p of unsorted) {
                    const item = document.createElement('div');
                    item.className = 'tree-item';
                    item.dataset.name = p.name;
                    item.innerHTML = `${p.is_core ? '<span class="core-star">\u2605</span> ' : ''}${p.name}`;
                    item.addEventListener('click', () => selectProtocol(p.name));
                    catChildren.appendChild(item);
                }
            }

            catDiv.appendChild(catChildren);
            treeEl.appendChild(catDiv);

            catHeader.addEventListener('click', () => {
                catChildren.classList.toggle('open');
                catHeader.querySelector('.arrow').classList.toggle('open');
            });
        }
    }

    // Render specialized and non_bio
    for (const cat of ['specialized', 'non_bio', 'unknown']) {
        // Skip categories excluded by the filter
        if (cf !== 'all' && cf !== cat) continue;

        const catProtos = protocols.filter(p => p.classification === cat);
        const matched = catProtos.filter(matchAll);
        if (matched.length === 0) continue;

        const label = cat === 'non_bio' ? 'Non-bio' : cat.charAt(0).toUpperCase() + cat.slice(1);
        const catDiv = document.createElement('div');

        const catHeader = document.createElement('div');
        catHeader.className = 'tree-category';
        catHeader.innerHTML = `<span class="arrow">\u25b6</span> ${label} <span class="badge">${matched.length}</span>`;
        catDiv.appendChild(catHeader);

        const catChildren = document.createElement('div');
        catChildren.className = 'tree-children';

        for (const p of matched) {
            const item = document.createElement('div');
            item.className = 'tree-item';
            item.dataset.name = p.name;
            item.textContent = p.name;
            item.addEventListener('click', () => selectProtocol(p.name));
            catChildren.appendChild(item);
        }

        catDiv.appendChild(catChildren);
        treeEl.appendChild(catDiv);

        catHeader.addEventListener('click', () => {
            catChildren.classList.toggle('open');
            catHeader.querySelector('.arrow').classList.toggle('open');
        });
    }
}

// Select protocol
let selectedName = null;
function selectProtocol(name) {
    selectedName = name;

    // Update selection highlight
    document.querySelectorAll('.tree-item.selected').forEach(el => el.classList.remove('selected'));
    const item = document.querySelector(`.tree-item[data-name="${CSS.escape(name)}"]`);
    if (item) item.classList.add('selected');

    const proto = protocols.find(p => p.name === name);
    if (!proto) return;

    // Detail header
    const headerEl = document.getElementById('detail-header');
    let metaHtml = `<span class="tag tag-${proto.classification}">${proto.classification}</span>`;
    if (proto.sub_category) {
        metaHtml += ` <span class="tag tag-sub">${proto.sub_category}</span>`;
    }
    if (proto.is_core) {
        metaHtml += ` <span class="tag tag-core">★ Core</span>`;
    }

    let reasonHtml = '';
    if (proto.reason) {
        reasonHtml += `<div class="detail-reason"><b>分类理由:</b> ${escapeHtml(proto.reason)}</div>`;
    }
    if (proto.sub_reason) {
        reasonHtml += `<div class="detail-reason"><b>子分类理由:</b> ${escapeHtml(proto.sub_reason)}</div>`;
    }

    headerEl.innerHTML = `
        <h2>${escapeHtml(name)}</h2>
        <div class="detail-meta">${metaHtml}</div>
        ${reasonHtml}
    `;

    // Show tabs
    document.getElementById('tabs').style.display = 'flex';

    // README
    const readmePane = document.getElementById('pane-readme');
    const readme = readmes[name];
    if (readme) {
        readmePane.innerHTML = `<div class="readme-content">${renderMarkdown(readme)}</div>`;
    } else {
        readmePane.innerHTML = '<div class="no-data">No README.md found</div>';
    }

    // Transfer Actions
    const transferPane = document.getElementById('pane-transfer');
    const transfer = transfers[name];
    if (transfer) {
        transferPane.innerHTML = `<div class="json-content">${syntaxHighlightJson(transfer)}</div>`;
    } else {
        transferPane.innerHTML = '<div class="no-data">No transfer actions data found</div>';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Simple markdown renderer
function renderMarkdown(md) {
    let html = escapeHtml(md);

    // Headings
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Horizontal rules
    html = html.replace(/^---+$/gm, '<hr>');

    // Bold and italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
    html = html.replace(/\*(.+?)\*/g, '<i>$1</i>');

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Links: [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    // Images: ![alt](url)
    html = html.replace(/!<a[^>]*>([^<]*)<\/a>/g, function(match, alt) {
        // Extract the URL from the originally linked anchor
        const urlMatch = match.match(/href="([^"]+)"/);
        if (urlMatch) return `<img src="${urlMatch[1]}" alt="${alt}" style="max-width:100%">`;
        return match;
    });

    // Unordered lists
    html = html.replace(/^[\*\-] (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Line breaks: <br/> or <br>
    html = html.replace(/&lt;br\/?&gt;/g, '<br>');

    // Paragraphs (double newline)
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';

    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');
    html = html.replace(/<p>\s*(<h[123]>)/g, '$1');
    html = html.replace(/(<\/h[123]>)\s*<\/p>/g, '$1');
    html = html.replace(/<p>\s*(<hr>)/g, '$1');
    html = html.replace(/(<hr>)\s*<\/p>/g, '$1');
    html = html.replace(/<p>\s*(<ul>)/g, '$1');
    html = html.replace(/(<\/ul>)\s*<\/p>/g, '$1');

    return html;
}

// JSON syntax highlighting
function syntaxHighlightJson(jsonStr) {
    let pretty;
    try {
        pretty = JSON.stringify(JSON.parse(jsonStr), null, 2);
    } catch {
        pretty = jsonStr;
    }

    pretty = escapeHtml(pretty);
    pretty = pretty.replace(/"([^"]+)"(?=\s*:)/g, '<span class="json-key">"$1"</span>');
    pretty = pretty.replace(/:\s*"([^"]*)"/g, ': <span class="json-string">"$1"</span>');
    pretty = pretty.replace(/:\s*(\d+\.?\d*)/g, ': <span class="json-number">$1</span>');
    pretty = pretty.replace(/:\s*(true|false)/g, ': <span class="json-bool">$1</span>');
    pretty = pretty.replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');

    return pretty;
}

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('pane-' + tab.dataset.tab).classList.add('active');
    });
});

// Search
const searchInput = document.getElementById('search');
searchInput.addEventListener('input', () => {
    renderTree(searchInput.value);
});

// Initial render
renderTree('');
</script>
</body>
</html>"""
    return html


def main():
    if not os.path.exists(INPUT_JSON):
        print(f"Error: {INPUT_JSON} not found. Run classify_protocols.py first.")
        sys.exit(1)

    print("Loading classification results...")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    protocols = data.get("protocols", [])
    print(f"Found {len(protocols)} protocols")

    # Collect README and transfer_actions for each protocol
    readmes = {}
    transfers = {}
    for p in protocols:
        name = p["name"]

        readme = read_readme(name)
        if readme:
            readmes[name] = readme

        transfer = read_transfer_actions(name)
        if transfer:
            transfers[name] = transfer

    print(f"Loaded {len(readmes)} READMEs, {len(transfers)} transfer actions")

    # Generate HTML
    print("Generating HTML...")
    html = generate_html(data, readmes, transfers)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    size_mb = os.path.getsize(OUTPUT_HTML) / (1024 * 1024)
    print(f"Done! Output: {OUTPUT_HTML} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
