#!/usr/bin/env python3
"""
AI Knowledge Orchestrator - Dashboard Server
Simple Flask app to view knowledge from Qdrant
"""

from flask import Flask, jsonify, request, render_template_string
from datetime import datetime
import json
from pathlib import Path

# Try Qdrant import
try:
    from qdrant_integration import QdrantIntegration, EmbeddingGenerator, QDRANT_AVAILABLE, EMBEDDINGS_AVAILABLE
except ImportError:
    QDRANT_AVAILABLE = False
    EMBEDDINGS_AVAILABLE = False

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔮 AJNA Knowledge Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { 
            text-align: center; 
            font-size: 2.5rem; 
            margin-bottom: 2rem;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .stat-value { font-size: 2rem; font-weight: bold; color: #00d4ff; }
        .stat-label { font-size: 0.9rem; color: #888; margin-top: 0.5rem; }
        .search-box {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        .search-input {
            width: 100%;
            padding: 1rem;
            font-size: 1rem;
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
        }
        .search-input:focus { outline: none; border-color: #00d4ff; }
        .results { display: grid; gap: 1rem; }
        .result-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 1.5rem;
            border-left: 4px solid #00d4ff;
        }
        .result-card.gold { border-left-color: #ffd700; }
        .result-card.silver { border-left-color: #c0c0c0; }
        .result-title { font-size: 1.2rem; font-weight: bold; margin-bottom: 0.5rem; }
        .result-score { 
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-size: 0.8rem;
            background: rgba(0,212,255,0.2);
        }
        .result-content { margin-top: 1rem; color: #aaa; font-size: 0.9rem; }
        .tags { margin-top: 0.5rem; }
        .tag {
            display: inline-block;
            padding: 0.2rem 0.5rem;
            background: rgba(123,44,191,0.3);
            border-radius: 4px;
            font-size: 0.75rem;
            margin-right: 0.5rem;
        }
        .status { 
            text-align: center; 
            padding: 1rem; 
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .status.online { border: 1px solid #00ff88; }
        .status.offline { border: 1px solid #ff4444; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔮 AJNA Knowledge Dashboard</h1>
        
        <div id="status" class="status">Loading...</div>
        
        <div class="stats-grid" id="stats"></div>
        
        <div class="search-box">
            <input type="text" class="search-input" id="searchInput" 
                   placeholder="🔍 Szukaj w bazie wiedzy..." 
                   onkeypress="if(event.key==='Enter')search()">
        </div>
        
        <div class="results" id="results"></div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                
                document.getElementById('status').className = 'status online';
                document.getElementById('status').innerHTML = 
                    `✅ Qdrant: ${data.qdrant_status || 'connected'} | 
                     Embeddings: ${data.embeddings ? '✅' : '❌'}`;
                
                const statsHtml = `
                    <div class="stat-card">
                        <div class="stat-value">${data.points_count || 0}</div>
                        <div class="stat-label">Total Insights</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.gold_count || 0}</div>
                        <div class="stat-label">🏆 Gold</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.silver_count || 0}</div>
                        <div class="stat-label">🥈 Silver</div>
                    </div>
                `;
                document.getElementById('stats').innerHTML = statsHtml;
                
            } catch (e) {
                document.getElementById('status').className = 'status offline';
                document.getElementById('status').innerHTML = '❌ Cannot connect to backend';
            }
        }
        
        async function search() {
            const query = document.getElementById('searchInput').value;
            if (!query) return;
            
            try {
                const res = await fetch('/api/search?q=' + encodeURIComponent(query));
                const data = await res.json();
                
                if (data.results && data.results.length > 0) {
                    const html = data.results.map(r => `
                        <div class="result-card ${r.tier || ''}">
                            <div class="result-title">${r.title || 'Untitled'}</div>
                            <span class="result-score">Score: ${r.similarity?.toFixed(2) || r.score}</span>
                            <div class="tags">
                                ${(r.tags || []).map(t => `<span class="tag">${t}</span>`).join('')}
                            </div>
                            <div class="result-content">${(r.content || '').substring(0, 300)}...</div>
                        </div>
                    `).join('');
                    document.getElementById('results').innerHTML = html;
                } else {
                    document.getElementById('results').innerHTML = 
                        '<div class="result-card">Brak wyników dla: ' + query + '</div>';
                }
            } catch (e) {
                document.getElementById('results').innerHTML = 
                    '<div class="result-card">Błąd wyszukiwania: ' + e.message + '</div>';
            }
        }
        
        loadStats();
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/stats')
def get_stats():
    stats = {
        "qdrant_available": QDRANT_AVAILABLE,
        "embeddings": EMBEDDINGS_AVAILABLE,
    }
    
    if QDRANT_AVAILABLE:
        try:
            qdrant = QdrantIntegration()
            qdrant_stats = qdrant.get_stats()
            stats.update(qdrant_stats)
            stats["qdrant_status"] = "connected"
        except Exception as e:
            stats["qdrant_status"] = f"error: {e}"
    
    # Try to load from data.json as fallback
    data_json = Path("knowledge-base/data.json")
    if data_json.exists():
        with open(data_json) as f:
            dashboard_data = json.load(f)
        stats["gold_count"] = dashboard_data.get("metrics", {}).get("gold_count", 0)
        stats["silver_count"] = dashboard_data.get("metrics", {}).get("silver_count", 0)
    
    return jsonify(stats)

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Missing query parameter 'q'", "results": []})
    
    results = []
    
    if QDRANT_AVAILABLE and EMBEDDINGS_AVAILABLE:
        try:
            embedder = EmbeddingGenerator()
            qdrant = QdrantIntegration()
            
            query_vector = embedder.encode_single(query)
            search_results = qdrant.search(query_vector, limit=10)
            
            results = [
                {
                    "id": r["id"],
                    "similarity": r["score"],
                    "title": r["payload"].get("title", "Untitled"),
                    "content": r["payload"].get("content", ""),
                    "score": r["payload"].get("score", 0),
                    "tier": r["payload"].get("tier", ""),
                    "tags": r["payload"].get("tags", []),
                    "source": r["payload"].get("source", ""),
                }
                for r in search_results
            ]
        except Exception as e:
            return jsonify({"error": str(e), "results": []})
    else:
        # Fallback: search in data.json
        data_json = Path("knowledge-base/data.json")
        if data_json.exists():
            with open(data_json) as f:
                data = json.load(f)
            
            query_lower = query.lower()
            for insight in data.get("top_insights", []):
                if query_lower in insight.get("title", "").lower() or \
                   query_lower in insight.get("reasoning", "").lower():
                    results.append({
                        "title": insight.get("title"),
                        "content": insight.get("reasoning"),
                        "score": insight.get("score"),
                        "tags": insight.get("tags", []),
                        "source": insight.get("source"),
                    })
    
    return jsonify({"query": query, "results": results})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🔮 AJNA Knowledge Dashboard Server")
    print("="*60)
    print(f"Qdrant: {'✅ Available' if QDRANT_AVAILABLE else '❌ Not available'}")
    print(f"Embeddings: {'✅ Available' if EMBEDDINGS_AVAILABLE else '❌ Not available'}")
    print("\n🌐 Starting server at http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
