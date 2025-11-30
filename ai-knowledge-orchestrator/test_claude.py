#!/usr/bin/env python3
"""
Test script for Claude API integration in mine_knowledge.py
Tests the judge_chunk_claude function with a sample input.
"""

import json
import sys
from pathlib import Path

# Add current directory to path to import from mine_knowledge.py
sys.path.insert(0, str(Path(__file__).parent))

# Import the function and config
from mine_knowledge import judge_chunk_claude, CONFIG, log

def test_claude_integration():
    """Test Claude API integration with sample input."""

    # Sample conversation chunk
    sample_chunk = """
**USER:** How do I implement a binary search tree in Python?

**ASSISTANT:** A binary search tree (BST) is a data structure where each node has at most two children, and the left subtree contains values less than the node's value, while the right subtree contains values greater. Here's a basic implementation:

```python
class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

class BST:
    def __init__(self):
        self.root = None

    def insert(self, value):
        if self.root is None:
            self.root = Node(value)
        else:
            self._insert_recursive(self.root, value)

    def _insert_recursive(self, node, value):
        if value < node.value:
            if node.left is None:
                node.left = Node(value)
            else:
                self._insert_recursive(node.left, value)
        else:
            if node.right is None:
                node.right = Node(value)
            else:
                self._insert_recursive(node.right, value)

    def search(self, value):
        return self._search_recursive(self.root, value)

    def _search_recursive(self, node, value):
        if node is None or node.value == value:
            return node is not None
        elif value < node.value:
            return self._search_recursive(node.left, value)
        else:
            return self._search_recursive(node.right, value)
```

This is a solid foundation. You can add methods for deletion, traversal, etc.
"""

    print("\n" + "="*60)
    print("🧪 TESTING CLAUDE API INTEGRATION")
    print("="*60 + "\n")

    # Get API key from CONFIG
    api_key = CONFIG.get('claude_api_key', 'sk-ant-YOUR_CLAUDE_API_KEY_HERE')

    log(f"Using Claude API key: {'***' + api_key[-4:] if api_key != 'sk-ant-YOUR_CLAUDE_API_KEY_HERE' else 'PLACEHOLDER (will fail)'}")

    # First test: API call with current key
    log("TEST 1: API call with configured key")
    try:
        log("Calling judge_chunk_claude with sample content...")
        result = judge_chunk_claude(sample_chunk, api_key)

        # Validate response structure
        print("\n🔍 RESPONSE VALIDATION:")
        print(f"  - Type: {type(result)}")
        print(f"  - Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")

        required_keys = ['score', 'reasoning', 'tags', 'suggested_title']
        missing_keys = [k for k in required_keys if k not in result]
        extra_keys = [k for k in result.keys() if k not in required_keys]

        if missing_keys:
            print(f"  ❌ Missing required keys: {missing_keys}")
        else:
            print("  ✅ All required keys present")

        if extra_keys:
            print(f"  ℹ️  Extra keys: {extra_keys}")

        # Check data types and values
        if 'score' in result:
            score = result['score']
            if isinstance(score, (int, float)) and 0 <= score <= 10:
                print(f"  ✅ Score: {score} (valid range)")
            else:
                print(f"  ❌ Score: {score} (invalid type or range)")

        if 'reasoning' in result:
            reasoning = result['reasoning']
            if isinstance(reasoning, str) and len(reasoning.strip()) > 0:
                print(f"  ✅ Reasoning: '{reasoning[:50]}...' (non-empty string)")
            else:
                print(f"  ❌ Reasoning: {reasoning} (invalid)")

        if 'tags' in result:
            tags = result['tags']
            if isinstance(tags, list) and all(isinstance(t, str) for t in tags):
                print(f"  ✅ Tags: {tags} (list of strings)")
            else:
                print(f"  ❌ Tags: {tags} (invalid format)")

        if 'suggested_title' in result:
            title = result['suggested_title']
            if isinstance(title, str):
                print(f"  ✅ Suggested Title: '{title}' (string)")
            else:
                print(f"  ❌ Suggested Title: {title} (not a string)")

        # Pretty print the full response
        print("\n📄 FULL RESPONSE:")
        print(json.dumps(result, indent=2))

        # Success summary
        print("\n✅ TEST 1 COMPLETED SUCCESSFULLY")
        print("The judge_chunk_claude function executed without unhandled exceptions.")
        print("Response parsing and structure validation completed.")

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

        if "API key" in str(e).lower() or "authentication" in str(e).lower():
            print("\n🔑 API KEY ISSUE: The API key appears to be invalid or not set.")
            print("Please update CONFIG['claude_api_key'] with a valid Claude API key.")
        elif "timeout" in str(e).lower():
            print("\n⏱️  TIMEOUT: API request timed out.")
            print("Check your internet connection and API service status.")
        else:
            print("\n🔧 GENERAL ERROR: Check the error details above.")

    # Test 2: Error handling with invalid key
    print("\n" + "-"*50)
    print("TEST 2: Error handling with invalid API key")
    print("-"*50)

    invalid_key = "sk-ant-INVALID_KEY_FOR_TESTING"
    log(f"Testing with invalid key: {invalid_key[:10]}...")

    try:
        log("Calling judge_chunk_claude with invalid key...")
        error_result = judge_chunk_claude(sample_chunk[:100], invalid_key)  # Shorter content for faster test

        print("\n🔍 ERROR RESPONSE VALIDATION:")
        print(f"  - Type: {type(error_result)}")
        print(f"  - Keys: {list(error_result.keys()) if isinstance(error_result, dict) else 'Not a dict'}")

        # Check if fallback values are used
        expected_fallbacks = {
            'score': 5.0,
            'reasoning': str,  # Should be a string
            'tags': [],  # Should be empty list
            'suggested_title': ''  # Should be empty string
        }

        all_fallbacks_correct = True
        for key, expected in expected_fallbacks.items():
            if key in error_result:
                value = error_result[key]
                if expected == str:
                    if isinstance(value, str):
                        print(f"  ✅ {key}: '{value[:30]}...' (string)")
                    else:
                        print(f"  ❌ {key}: {value} (expected string)")
                        all_fallbacks_correct = False
                elif isinstance(expected, (list, str, float, int)):
                    if value == expected:
                        print(f"  ✅ {key}: {value} (correct fallback)")
                    else:
                        print(f"  ❌ {key}: {value} (expected {expected})")
                        all_fallbacks_correct = False
                else:
                    print(f"  ❌ {key}: Unexpected expected value type")
                    all_fallbacks_correct = False
            else:
                print(f"  ❌ Missing key: {key}")
                all_fallbacks_correct = False

        if all_fallbacks_correct:
            print("\n✅ TEST 2 PASSED: Error handling correctly returned fallback values")
        else:
            print("\n❌ TEST 2 PARTIAL: Error handling worked but fallback values incorrect")

        print("\n📄 ERROR RESPONSE:")
        print(json.dumps(error_result, indent=2))

    except Exception as e:
        print(f"\n💥 TEST 2 CRASHED: {e}")
        print("The function did not handle errors gracefully!")
        traceback.print_exc()

def main():
    try:
        test_claude_integration()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error in test script: {e}")

if __name__ == "__main__":
    main()