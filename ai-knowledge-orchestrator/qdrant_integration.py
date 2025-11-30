#!/usr/bin/env python3
"""
AI Knowledge Orchestrator - Qdrant & n8n Integration
Extends mine_knowledge.py with vector storage and workflow triggers
"""

import os
import json
import uuid
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Try to import Qdrant and sentence-transformers
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("⚠️  qdrant-client not installed. Run: pip install qdrant-client")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠️  sentence-transformers not installed. Run: pip install sentence-transformers")

# ============================================================================
# CONFIGURATION
# ============================================================================
QDRANT_CONFIG = {
    "host": os.getenv("QDRANT_HOST", "localhost"),
    "port": int(os.getenv("QDRANT_PORT", 6333)),
    "collection_name": os.getenv("QDRANT_COLLECTION", "ajna_knowledge"),
    "vector_size": 384,  # all-MiniLM-L6-v2 output size
}

N8N_CONFIG = {
    "webhook_url": os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook-test/be9364df-390e-47af-bdd0-67243b1691ba"),
    "enabled": os.getenv("N8N_ENABLED", "true").lower() == "true",
    "http_method": "POST",  # Standard webhook method
}

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class QdrantIntegration:
    """Handles vector storage in Qdrant."""
    
    def __init__(self):
        if not QDRANT_AVAILABLE:
            raise RuntimeError("qdrant-client not installed")
        
        print(f"🔧 Connecting to Qdrant at {QDRANT_CONFIG['host']}:{QDRANT_CONFIG['port']}...")
        self.client = QdrantClient(
            host=QDRANT_CONFIG["host"],
            port=QDRANT_CONFIG["port"]
        )
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collection_name = QDRANT_CONFIG["collection_name"]
        
        try:
            collections = self.client.get_collections()
            exists = any(c.name == collection_name for c in collections.collections)
            
            if not exists:
                print(f"📂 Creating collection '{collection_name}'...")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=QDRANT_CONFIG["vector_size"],
                        distance=models.Distance.COSINE
                    )
                )
            print(f"✅ Collection '{collection_name}' ready")
        except Exception as e:
            print(f"❌ Qdrant error: {e}")
            raise
    
    def upsert_insights(self, insights: List[Dict], embeddings: List[List[float]]) -> int:
        """Store insights with their embeddings in Qdrant."""
        if len(insights) != len(embeddings):
            raise ValueError("Insights and embeddings count mismatch")
        
        points = []
        for insight, embedding in zip(insights, embeddings):
            point_id = str(uuid.uuid4())
            payload = {
                "id": insight.get("id", point_id),
                "title": insight.get("title", "Untitled"),
                "content": insight.get("content", "")[:1000],  # Truncate for storage
                "score": insight.get("score", 0),
                "source": insight.get("source", "unknown"),
                "tags": insight.get("tags", []),
                "tier": self._get_tier(insight.get("score", 0)),
                "created": insight.get("created", ""),
                "indexed_at": datetime.now().isoformat(),
            }
            
            points.append(models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            ))
        
        if points:
            self.client.upsert(
                collection_name=QDRANT_CONFIG["collection_name"],
                points=points
            )
        
        return len(points)
    
    def _get_tier(self, score: float) -> str:
        if score >= 8.0:
            return "gold"
        elif score >= 5.0:
            return "silver"
        return "trash"
    
    def search(self, query_vector: List[float], limit: int = 10, tier: Optional[str] = None) -> List[Dict]:
        """Search for similar insights."""
        filter_condition = None
        if tier:
            filter_condition = models.Filter(
                must=[models.FieldCondition(
                    key="tier",
                    match=models.MatchValue(value=tier)
                )]
            )
        
        results = self.client.search(
            collection_name=QDRANT_CONFIG["collection_name"],
            query_vector=query_vector,
            limit=limit,
            query_filter=filter_condition
        )
        
        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload
            }
            for r in results
        ]
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        info = self.client.get_collection(QDRANT_CONFIG["collection_name"])
        return {
            "collection": QDRANT_CONFIG["collection_name"],
            "points_count": getattr(info, 'points_count', 0),
            "vectors_count": getattr(info, 'vectors_count', getattr(info, 'points_count', 0)),
            "status": info.status.value if hasattr(info.status, 'value') else str(info.status),
        }


class EmbeddingGenerator:
    """Generates embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        if not EMBEDDINGS_AVAILABLE:
            raise RuntimeError("sentence-transformers not installed")
        
        print(f"🧠 Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("✅ Embedding model loaded")
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]
    
    def encode_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.model.encode(text).tolist()


class N8nNotifier:
    """Sends notifications to n8n workflows."""
    
    @staticmethod
    def notify(event: str, data: Dict) -> bool:
        """Send a webhook notification to n8n."""
        if not N8N_CONFIG["enabled"]:
            return False
        
        payload = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        
        try:
            response = requests.post(
                N8N_CONFIG["webhook_url"],
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                print(f"⚡ n8n notification sent: {event}")
                return True
            else:
                print(f"⚠️ n8n response: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"⚠️ n8n not reachable at {N8N_CONFIG['webhook_url']}")
            return False
        except Exception as e:
            print(f"❌ n8n error: {e}")
            return False


def integrate_with_pipeline(insights: List[Dict]) -> Dict:
    """
    Main integration function - call this after mine_knowledge.py processes insights.
    
    Args:
        insights: List of processed insights from mine_knowledge.py
    
    Returns:
        Integration stats
    """
    stats = {
        "total_insights": len(insights),
        "indexed_to_qdrant": 0,
        "n8n_notified": False,
        "errors": []
    }
    
    # Skip if no insights
    if not insights:
        print("⚠️ No insights to integrate")
        return stats
    
    # Step 1: Generate embeddings
    if EMBEDDINGS_AVAILABLE:
        try:
            embedder = EmbeddingGenerator()
            texts = [i.get("content", i.get("title", ""))[:512] for i in insights]
            embeddings = embedder.encode(texts)
            print(f"✅ Generated {len(embeddings)} embeddings")
        except Exception as e:
            stats["errors"].append(f"Embedding error: {e}")
            embeddings = None
    else:
        embeddings = None
        stats["errors"].append("Embeddings not available")
    
    # Step 2: Store in Qdrant
    if QDRANT_AVAILABLE and embeddings:
        try:
            qdrant = QdrantIntegration()
            indexed = qdrant.upsert_insights(insights, embeddings)
            stats["indexed_to_qdrant"] = indexed
            print(f"✅ Indexed {indexed} insights to Qdrant")
            
            # Get collection stats
            qdrant_stats = qdrant.get_stats()
            stats["qdrant_stats"] = qdrant_stats
        except Exception as e:
            stats["errors"].append(f"Qdrant error: {e}")
    
    # Step 3: Notify n8n
    n8n_data = {
        "insights_processed": len(insights),
        "gold_count": len([i for i in insights if i.get("score", 0) >= 8.0]),
        "indexed_count": stats["indexed_to_qdrant"],
        "collection": QDRANT_CONFIG["collection_name"],
    }
    stats["n8n_notified"] = N8nNotifier.notify("knowledge_mined", n8n_data)
    
    return stats


# ============================================================================
# STANDALONE USAGE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔮 AI Knowledge Orchestrator - Qdrant & n8n Integration")
    print("="*60 + "\n")
    
    # Check dependencies
    print("Checking dependencies:")
    print(f"  - Qdrant client: {'✅' if QDRANT_AVAILABLE else '❌'}")
    print(f"  - Sentence Transformers: {'✅' if EMBEDDINGS_AVAILABLE else '❌'}")
    print()
    
    # Load existing data.json if available
    data_json = Path("knowledge-base/data.json")
    if data_json.exists():
        print(f"📂 Loading {data_json}...")
        with open(data_json) as f:
            dashboard_data = json.load(f)
        
        # Create mock insights from top_insights
        mock_insights = [
            {
                "id": f"mock-{i}",
                "title": insight.get("title", "Untitled"),
                "content": insight.get("reasoning", ""),
                "score": insight.get("score", 5.0),
                "source": insight.get("source", "unknown"),
                "tags": insight.get("tags", []),
            }
            for i, insight in enumerate(dashboard_data.get("top_insights", []))
        ]
        
        if mock_insights:
            print(f"Found {len(mock_insights)} insights to index")
            stats = integrate_with_pipeline(mock_insights)
            print(f"\n📊 Integration Results: {json.dumps(stats, indent=2)}")
        else:
            print("No insights found in data.json")
    else:
        print("⚠️ No data.json found. Run mine_knowledge.py first!")
        print("\nStandalone test mode:")
        
        # Test with sample data
        test_insights = [
            {
                "id": "test-1",
                "title": "Sample Insight",
                "content": "This is a test insight for the knowledge orchestrator.",
                "score": 8.5,
                "source": "test",
                "tags": ["test", "sample"],
            }
        ]
        
        stats = integrate_with_pipeline(test_insights)
        print(f"\n📊 Test Results: {json.dumps(stats, indent=2)}")
