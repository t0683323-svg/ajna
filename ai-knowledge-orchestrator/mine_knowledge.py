#!/usr/bin/env python3
"""
AI Knowledge Orchestrator - Mining Pipeline
Extracts valuable insights from AI conversation exports (ChatGPT, Claude, Gemini)
Outputs: Obsidian-compatible Markdown files + dashboard data.json
"""

import os
import sys
import json
import hashlib
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter

import requests
import anthropic

# ============================================================================
# CONFIGURATION
# ============================================================================
CONFIG = {
    "chunk_size": 800,              # Tokens per chunk (approximate)
    "overlap": 100,                 # Overlap between chunks
    "gold_threshold": 8.0,          # Min score for "gold" tier
    "silver_threshold": 5.0,        # Min score for "silver" tier
    "similarity_threshold": 0.85,   # Dedup threshold (Jaccard similarity)
    "deepseek_api_key": "sk-YOUR_API_KEY_HERE",  # Replace with your key
    "deepseek_api_url": "https://api.deepseek.com/v1/chat/completions",
    "deepseek_model": "deepseek-chat",
    "claude_api_key": "sk-ant-YOUR_CLAUDE_API_KEY_HERE",  # Replace with your Claude key
    "claude_api_url": "https://api.anthropic.com",  # Anthropic API URL (for reference)
    "claude_model": "claude-3-haiku-20240307",  # Claude model
    "claude_max_tokens": 500,       # Max tokens for Claude responses
    "use_claude": False,            # Set to True to use Claude instead of DeepSeek
    "request_timeout": 60,          # API timeout in seconds
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def log(message: str, level: str = "INFO"):
    """Simple logging with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "STEP": "🔄"}
    icon = icons.get(level, "•")
    print(f"[{timestamp}] {icon} {message}")

def generate_id(text: str) -> str:
    """Generate short unique ID from text."""
    return hashlib.md5(text.encode()).hexdigest()[:8]

def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 chars for English)."""
    return len(text) // 4

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    
    # Approximate words per chunk (assuming avg 5 chars/word + space)
    words_per_chunk = chunk_size * 4 // 6
    overlap_words = overlap * 4 // 6
    
    start = 0
    while start < len(words):
        end = start + words_per_chunk
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap_words
        if start <= 0 and end >= len(words):
            break
    
    return chunks if chunks else [text]

def jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0

# ============================================================================
# CONVERSATION LOADERS
# ============================================================================

def load_chatgpt_export(filepath: Path) -> List[Dict[str, Any]]:
    """Load ChatGPT conversations.json export."""
    conversations = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle both array and object formats
    if isinstance(data, dict):
        data = data.get('conversations', data.get('items', [data]))
    
    for conv in data:
        title = conv.get('title', 'Untitled')
        created = conv.get('create_time', conv.get('created', ''))
        
        # Extract message content
        messages = []
        mapping = conv.get('mapping', {})
        
        if mapping:
            # New ChatGPT export format
            for node in mapping.values():
                msg = node.get('message')
                if msg and msg.get('content', {}).get('parts'):
                    role = msg.get('author', {}).get('role', 'user')
                    content = '\n'.join(str(p) for p in msg['content']['parts'] if p)
                    if content.strip():
                        messages.append(f"**{role.upper()}:** {content}")
        else:
            # Simple format
            for msg in conv.get('messages', []):
                role = msg.get('role', msg.get('author', 'user'))
                content = msg.get('content', msg.get('text', ''))
                if isinstance(content, list):
                    content = '\n'.join(str(c) for c in content)
                if content.strip():
                    messages.append(f"**{role.upper()}:** {content}")
        
        if messages:
            text = '\n\n'.join(messages)
            conversations.append({
                'title': title,
                'text': text,
                'source': 'ChatGPT',
                'created': str(created) if created else '',
                'id': generate_id(text)
            })
    
    return conversations

def load_claude_export(filepath: Path) -> List[Dict[str, Any]]:
    """Load Claude conversation export."""
    conversations = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        data = data.get('conversations', data.get('chats', [data]))
    
    for conv in data:
        title = conv.get('title', conv.get('name', 'Untitled'))
        created = conv.get('created_at', conv.get('created', ''))
        
        messages = []
        for msg in conv.get('messages', conv.get('chat_messages', [])):
            role = msg.get('sender', msg.get('role', 'user'))
            content = msg.get('text', msg.get('content', ''))
            
            if isinstance(content, list):
                # Handle content blocks
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        parts.append(block.get('text', str(block)))
                    else:
                        parts.append(str(block))
                content = '\n'.join(parts)
            
            if content.strip():
                messages.append(f"**{role.upper()}:** {content}")
        
        if messages:
            text = '\n\n'.join(messages)
            conversations.append({
                'title': title,
                'text': text,
                'source': 'Claude',
                'created': str(created) if created else '',
                'id': generate_id(text)
            })
    
    return conversations

def load_gemini_export(filepath: Path) -> List[Dict[str, Any]]:
    """Load Gemini/manual export."""
    conversations = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        data = [data]
    
    for conv in data:
        title = conv.get('title', 'Gemini Conversation')
        text = conv.get('text', conv.get('content', ''))
        created = conv.get('created', conv.get('date', ''))
        
        if text.strip():
            conversations.append({
                'title': title,
                'text': text,
                'source': 'Gemini',
                'created': str(created) if created else '',
                'id': generate_id(text)
            })
    
    return conversations

def load_conversations(input_dir: Path) -> List[Dict[str, Any]]:
    """Load all conversations from input directory."""
    all_conversations = []
    
    for filepath in input_dir.glob('*.json'):
        filename = filepath.name.lower()
        log(f"Loading: {filepath.name}")
        
        try:
            if 'chatgpt' in filename or 'conversations' in filename:
                convs = load_chatgpt_export(filepath)
                log(f"  → Loaded {len(convs)} ChatGPT conversations", "SUCCESS")
            elif 'claude' in filename:
                convs = load_claude_export(filepath)
                log(f"  → Loaded {len(convs)} Claude conversations", "SUCCESS")
            elif 'gemini' in filename:
                convs = load_gemini_export(filepath)
                log(f"  → Loaded {len(convs)} Gemini conversations", "SUCCESS")
            else:
                # Try generic load
                convs = load_gemini_export(filepath)
                log(f"  → Loaded {len(convs)} generic conversations", "SUCCESS")
            
            all_conversations.extend(convs)
        except Exception as e:
            log(f"  → Failed to load: {e}", "ERROR")
    
    return all_conversations

# ============================================================================
# DEEPSEEK AI JUDGING
# ============================================================================

JUDGE_PROMPT = """You are an expert knowledge curator. Evaluate this AI conversation chunk for its value as a permanent knowledge artifact.

SCORING CRITERIA (1-10):
- 9-10: Breakthrough insight, novel technique, highly reusable pattern
- 7-8: Solid technical content, good reference material
- 5-6: Useful but common knowledge, might be worth keeping
- 3-4: Context-dependent, limited reuse value
- 1-2: Trivial, small talk, troubleshooting noise

EVALUATION TASK:
1. Score the content (1-10, can use decimals like 7.5)
2. Provide 2-3 sentence reasoning
3. Extract 3-5 relevant tags (lowercase, hyphenated)
4. Suggest a concise title if the original is poor

CONTENT TO EVALUATE:
---
{content}
---

Respond in JSON format ONLY:
{{"score": 7.5, "reasoning": "...", "tags": ["tag1", "tag2"], "suggested_title": "..."}}"""

def judge_chunk(content: str, api_key: str) -> Dict[str, Any]:
    """Use DeepSeek to judge a conversation chunk."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": CONFIG["deepseek_model"],
        "messages": [
            {"role": "user", "content": JUDGE_PROMPT.format(content=content[:4000])}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }

    try:
        response = requests.post(
            CONFIG["deepseek_api_url"],
            headers=headers,
            json=payload,
            timeout=CONFIG["request_timeout"]
        )
        response.raise_for_status()

        result = response.json()
        content_text = result['choices'][0]['message']['content']

        # Parse JSON from response
        json_match = re.search(r'\{[^{}]*\}', content_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"score": 5.0, "reasoning": "Failed to parse", "tags": [], "suggested_title": ""}

    except requests.exceptions.Timeout:
        log("API timeout - retrying with smaller content...", "WARNING")
        return {"score": 5.0, "reasoning": "API timeout", "tags": [], "suggested_title": ""}
    except Exception as e:
        log(f"API error: {e}", "ERROR")
        return {"score": 5.0, "reasoning": str(e), "tags": [], "suggested_title": ""}

def judge_chunk_claude(content: str, api_key: str) -> Dict[str, Any]:
    """Use Claude to judge a conversation chunk."""
    try:
        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=CONFIG["claude_model"],
            max_tokens=CONFIG["claude_max_tokens"],
            temperature=0.3,
            system="You are an expert knowledge curator. Evaluate this AI conversation chunk for its value as a permanent knowledge artifact.",
            messages=[
                {"role": "user", "content": JUDGE_PROMPT.format(content=content[:4000])}
            ]
        )

        content_text = response.content[0].text

        # Parse JSON from response
        json_match = re.search(r'\{[^{}]*\}', content_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"score": 5.0, "reasoning": "Failed to parse", "tags": [], "suggested_title": ""}

    except anthropic.APITimeoutError:
        log("Claude API timeout - retrying with smaller content...", "WARNING")
        return {"score": 5.0, "reasoning": "API timeout", "tags": [], "suggested_title": ""}
    except Exception as e:
        log(f"Claude API error: {e}", "ERROR")
        return {"score": 5.0, "reasoning": str(e), "tags": [], "suggested_title": ""}

def process_conversations(conversations: List[Dict], api_key: str) -> List[Dict]:
    """Process all conversations through the judging pipeline."""
    all_insights = []
    total = len(conversations)
    
    for idx, conv in enumerate(conversations, 1):
        log(f"Processing [{idx}/{total}]: {conv['title'][:50]}...")
        
        text = conv['text']
        chunks = chunk_text(text, CONFIG['chunk_size'], CONFIG['overlap'])
        
        for chunk_idx, chunk in enumerate(chunks):
            # Judge this chunk
            if CONFIG.get('use_claude', False):
                judgment = judge_chunk_claude(chunk, api_key)
            else:
                judgment = judge_chunk(chunk, api_key)
            
            insight = {
                'title': judgment.get('suggested_title') or conv['title'],
                'original_title': conv['title'],
                'content': chunk,
                'full_content': text if len(chunks) == 1 else chunk,
                'score': judgment.get('score', 5.0),
                'reasoning': judgment.get('reasoning', ''),
                'tags': judgment.get('tags', []),
                'source': conv['source'],
                'created': conv['created'],
                'id': f"{conv['source']}-{conv['id']}-{chunk_idx}",
                'chunk_index': chunk_idx,
                'total_chunks': len(chunks)
            }
            
            all_insights.append(insight)
        
        # Progress indicator
        if idx % 10 == 0:
            gold_count = len([i for i in all_insights if i['score'] >= CONFIG['gold_threshold']])
            log(f"  Progress: {idx}/{total} conversations, {gold_count} gold insights so far", "INFO")
    
    return all_insights

# ============================================================================
# DEDUPLICATION
# ============================================================================

def deduplicate_insights(insights: List[Dict], threshold: float = 0.85) -> Tuple[List[Dict], int]:
    """Remove duplicate insights using Jaccard similarity."""
    if not insights:
        return [], 0
    
    # Sort by score (highest first) to keep best duplicates
    sorted_insights = sorted(insights, key=lambda x: x['score'], reverse=True)
    
    unique = []
    removed = 0
    
    for insight in sorted_insights:
        is_duplicate = False
        
        for existing in unique:
            similarity = jaccard_similarity(insight['content'], existing['content'])
            if similarity >= threshold:
                is_duplicate = True
                removed += 1
                break
        
        if not is_duplicate:
            unique.append(insight)
    
    return unique, removed

# ============================================================================
# OUTPUT GENERATION
# ============================================================================

def save_markdown(insight: Dict, output_dir: Path, tier: str):
    """Save an insight as a Markdown file."""
    tier_dir = output_dir / tier
    tier_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{insight['source']}-{insight['id']}.md"
    filepath = tier_dir / filename
    
    tags_str = ', '.join(insight['tags']) if insight['tags'] else 'uncategorized'
    
    content = f"""---
title: {insight['title']}
score: {insight['score']}
source: {insight['source']}
tags: {tags_str}
date: {insight['created'] or datetime.now().strftime('%Y-%m-%d')}
---

# {insight['title']}

**Score:** {insight['score']}/10  
**Reasoning:** {insight['reasoning']}  
**Tags:** {tags_str}

## Content

{insight['content']}

---
*Source: {insight['source']} - ID: {insight['id']}*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath

def generate_dashboard_data(insights: List[Dict], stats: Dict, output_dir: Path):
    """Generate data.json for the web dashboard."""
    
    # Collect all tags with counts
    all_tags = []
    for insight in insights:
        all_tags.extend(insight.get('tags', []))
    tag_counts = Counter(all_tags)
    
    # Top insights (gold tier, sorted by score)
    gold_insights = [i for i in insights if i['score'] >= CONFIG['gold_threshold']]
    top_insights = sorted(gold_insights, key=lambda x: x['score'], reverse=True)[:10]
    
    dashboard_data = {
        "generated_at": datetime.now().isoformat(),
        "metrics": {
            "total_conversations": stats['total_conversations'],
            "total_insights": stats['total_insights'],
            "gold_count": stats['gold_count'],
            "silver_count": stats['silver_count'],
            "trash_count": stats['trash_count'],
            "duplicates_removed": stats['duplicates_removed'],
            "dedup_rate": round(stats['dedup_rate'], 1),
            "signal_to_noise": round(stats['snr'], 1)
        },
        "pipeline_status": {
            "loading": 100,
            "chunking": 100,
            "judging": 100,
            "deduplication": 100,
            "output": 100
        },
        "distribution": {
            "gold": stats['gold_count'],
            "silver": stats['silver_count'],
            "trash": stats['trash_count']
        },
        "tag_cloud": dict(tag_counts.most_common(30)),
        "top_insights": [
            {
                "title": i['title'],
                "score": i['score'],
                "source": i['source'],
                "tags": i['tags'][:3],
                "reasoning": i['reasoning'][:100] + "..." if len(i['reasoning']) > 100 else i['reasoning']
            }
            for i in top_insights
        ],
        "sources": {
            "ChatGPT": len([i for i in insights if i['source'] == 'ChatGPT']),
            "Claude": len([i for i in insights if i['source'] == 'Claude']),
            "Gemini": len([i for i in insights if i['source'] == 'Gemini'])
        }
    }
    
    data_path = output_dir / 'data.json'
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2)
    
    return data_path

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_pipeline(input_dir: Path, output_dir: Path, api_key: str):
    """Run the complete mining pipeline."""
    
    print("\n" + "="*60)
    print("🔮 AI KNOWLEDGE ORCHESTRATOR - Mining Pipeline")
    print("="*60 + "\n")
    
    # Step 1: Load conversations
    log("STEP 1: Loading conversations from exports/", "STEP")
    conversations = load_conversations(input_dir)
    
    if not conversations:
        log("No conversations found! Check your exports/ folder.", "ERROR")
        sys.exit(1)
    
    log(f"Total conversations loaded: {len(conversations)}", "SUCCESS")
    
    # Step 2: Process with AI (DeepSeek or Claude)
    ai_name = "Claude" if CONFIG.get('use_claude', False) else "DeepSeek"
    log(f"STEP 2: Chunking and judging with {ai_name} AI", "STEP")
    insights = process_conversations(conversations, api_key)
    log(f"Total chunks processed: {len(insights)}", "SUCCESS")
    
    # Step 3: Deduplicate
    log("STEP 3: Removing duplicates (similarity threshold {:.0%})".format(CONFIG['similarity_threshold']), "STEP")
    unique_insights, removed = deduplicate_insights(insights, CONFIG['similarity_threshold'])
    log(f"Duplicates removed: {removed}", "SUCCESS")
    
    # Step 4: Categorize and save
    log("STEP 4: Saving to Markdown files", "STEP")
    
    gold = [i for i in unique_insights if i['score'] >= CONFIG['gold_threshold']]
    silver = [i for i in unique_insights if CONFIG['silver_threshold'] <= i['score'] < CONFIG['gold_threshold']]
    trash = [i for i in unique_insights if i['score'] < CONFIG['silver_threshold']]
    
    for insight in gold:
        save_markdown(insight, output_dir, 'gold')
    for insight in silver:
        save_markdown(insight, output_dir, 'silver')
    for insight in trash:
        save_markdown(insight, output_dir, 'trash')
    
    log(f"  - Gold: {len(gold)} files → {output_dir}/gold/", "SUCCESS")
    log(f"  - Silver: {len(silver)} files → {output_dir}/silver/", "SUCCESS")
    log(f"  - Trash: {len(trash)} files → {output_dir}/trash/", "SUCCESS")
    
    # Step 5: Generate dashboard data
    log("STEP 5: Generating data.json for dashboard", "STEP")
    
    total_before_dedup = len(insights)
    stats = {
        'total_conversations': len(conversations),
        'total_insights': len(unique_insights),
        'gold_count': len(gold),
        'silver_count': len(silver),
        'trash_count': len(trash),
        'duplicates_removed': removed,
        'dedup_rate': (removed / total_before_dedup * 100) if total_before_dedup > 0 else 0,
        'snr': (len(gold) / len(unique_insights) * 100) if unique_insights else 0
    }
    
    data_path = generate_dashboard_data(unique_insights, stats, output_dir)
    log(f"Dashboard data: {data_path}", "SUCCESS")
    
    # Final summary
    print("\n" + "="*60)
    print("✨ MINING COMPLETE!")
    print("="*60)
    print(f"📊 Total Conversations: {stats['total_conversations']}")
    print(f"💎 Gold Insights: {stats['gold_count']} (score ≥ {CONFIG['gold_threshold']})")
    print(f"🥈 Silver Insights: {stats['silver_count']} (score {CONFIG['silver_threshold']}-{CONFIG['gold_threshold']})")
    print(f"🗑️  Trash: {stats['trash_count']} (score < {CONFIG['silver_threshold']})")
    print(f"🔄 Deduplication: {stats['duplicates_removed']} removed ({stats['dedup_rate']:.1f}%)")
    print(f"📈 Signal-to-Noise: {stats['snr']:.1f}%")
    print()
    print(f"📂 Output: {output_dir.absolute()}")
    print(f"🌐 Dashboard data: {data_path.absolute()}")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="AI Knowledge Orchestrator - Extract insights from AI conversation exports"
    )
    parser.add_argument(
        '--input', '-i',
        type=Path,
        default=Path('exports'),
        help='Input directory containing JSON exports (default: exports/)'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('knowledge-base'),
        help='Output directory for knowledge base (default: knowledge-base/)'
    )
    parser.add_argument(
        '--api-key', '-k',
        type=str,
        default=None,
        help='DeepSeek API key (overrides config)'
    )
    parser.add_argument(
        '--gold-threshold',
        type=float,
        default=None,
        help=f'Gold tier threshold (default: {CONFIG["gold_threshold"]})'
    )
    parser.add_argument(
        '--similarity-threshold',
        type=float,
        default=None,
        help=f'Dedup similarity threshold (default: {CONFIG["similarity_threshold"]})'
    )
    
    args = parser.parse_args()
    
    # Apply CLI overrides
    use_claude = CONFIG.get('use_claude', False)
    if use_claude:
        api_key = args.api_key or CONFIG['claude_api_key']
        if api_key == "sk-ant-YOUR_CLAUDE_API_KEY_HERE":
            log("Please configure your Claude API key!", "ERROR")
            log("Edit mine_knowledge.py line 25, or use --api-key flag", "INFO")
            sys.exit(1)
    else:
        api_key = args.api_key or CONFIG['deepseek_api_key']
        if api_key == "sk-YOUR_API_KEY_HERE":
            log("Please configure your DeepSeek API key!", "ERROR")
            log("Edit mine_knowledge.py line 24, or use --api-key flag", "INFO")
            sys.exit(1)
    
    if args.gold_threshold:
        CONFIG['gold_threshold'] = args.gold_threshold
    if args.similarity_threshold:
        CONFIG['similarity_threshold'] = args.similarity_threshold
    
    # Validate input directory
    if not args.input.exists():
        log(f"Input directory not found: {args.input}", "ERROR")
        log("Create it and add your AI conversation exports (JSON files)", "INFO")
        sys.exit(1)
    
    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)
    
    # Run the pipeline
    run_pipeline(args.input, args.output, api_key)

if __name__ == "__main__":
    main()
