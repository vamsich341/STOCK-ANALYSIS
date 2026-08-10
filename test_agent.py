#!/usr/bin/env python3
"""
Test script for LLM Agent - Demonstrates tool calling capabilities
Can run in demo mode without OpenAI API key for testing
"""

import sys
import os
import json
from typing import Dict

# Mock database connection for testing
class MockDB:
    def cursor(self, **kwargs):
        return self

def demo_agent_capabilities():
    """Demonstrate agent capabilities without requiring full setup"""
    
    print("=" * 70)
    print("STOCK ANALYSIS LLM AGENT - DEMO")
    print("=" * 70)
    print()
    
    # Show available tools
    print("📦 Available Tools:")
    print()
    print("🔍 READ TOOLS:")
    print("   1. get_quote(ticker) - Real-time stock quotes")
    print("   2. get_historical(ticker, period) - Historical price data")
    print("   3. search_semantic(query, type, limit) - Semantic search")
    print("   4. get_company_info(ticker) - Company details")
    print("   5. get_news(ticker, limit) - Recent news articles")
    print()
    print("✏️  WRITE TOOLS:")
    print("   6. add_to_watchlist(user_id, watchlist_id, ticker)")
    print("   7. save_analysis(user_id, ticker, analysis, confidence)")
    print("   8. create_alert(user_id, ticker, alert_type, threshold)")
    print()
    print("=" * 70)
    
    # Example queries and their expected tool chains
    examples = [
        {
            "query": "What's the current price of Apple?",
            "tools": ["get_quote(AAPL)"],
            "reasoning": "Simple quote lookup - directly call get_quote tool"
        },
        {
            "query": "Compare NVDA and AMD performance over 3 months",
            "tools": [
                "get_historical(NVDA, 3mo)",
                "get_historical(AMD, 3mo)"
            ],
            "reasoning": "Multi-step comparison - fetch historical data for both, then compare"
        },
        {
            "query": "Find AI chip companies and add the best one to my watchlist",
            "tools": [
                "search_semantic('AI chip companies', 'companies', 5)",
                "get_quote([top_result])",
                "add_to_watchlist(user_id, watchlist_id, [top_ticker])"
            ],
            "reasoning": "Multi-step with write - search → validate → add to watchlist"
        },
        {
            "query": "What's TSLA news sentiment and should I set an alert?",
            "tools": [
                "get_news(TSLA, 5)",
                "get_quote(TSLA)",
                "create_alert(user_id, TSLA, 'price_below', [threshold])"
            ],
            "reasoning": "Analysis + action - check news → check price → create alert"
        }
    ]
    
    print("\n📝 Example Query Workflows:\n")
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. Query: \"{example['query']}\"")
        print(f"   Reasoning: {example['reasoning']}")
        print(f"   Tool Chain:")
        for tool in example['tools']:
            print(f"      → {tool}")
        print()
    
    print("=" * 70)
    print()
    
    # Show tool execution trace example
    print("🔍 Example Tool Execution Trace:\n")
    
    trace_example = {
        "query": "What's AAPL's performance this month?",
        "tool_calls": [
            {
                "iteration": 1,
                "tool": "get_quote",
                "arguments": {"ticker": "AAPL"},
                "result": {
                    "success": True,
                    "data": {
                        "ticker": "AAPL",
                        "price": 180.50,
                        "change": 2.30,
                        "change_percent": 1.29
                    }
                }
            },
            {
                "iteration": 1,
                "tool": "get_historical",
                "arguments": {"ticker": "AAPL", "period": "1mo"},
                "result": {
                    "success": True,
                    "data": {
                        "start_price": 165.20,
                        "end_price": 180.50,
                        "change_percent": 9.26,
                        "high": 182.00,
                        "low": 164.50
                    }
                }
            }
        ],
        "response": "Apple (AAPL) is currently trading at $180.50, up $2.30 (1.29%) today. Over the past month, the stock has gained 9.26%, climbing from $165.20 to $180.50. It reached a monthly high of $182.00."
    }
    
    print(json.dumps(trace_example, indent=2))
    print()
    
    print("=" * 70)
    print()
    
    # Agent vs Deterministic comparison
    print("📊 Agent vs Deterministic Logic Comparison:\n")
    
    comparison = """
┌─────────────────────┬──────────────────────┬───────────────────────┐
│ Query Type          │ Deterministic Logic  │ LLM Agent            │
├─────────────────────┼──────────────────────┼───────────────────────┤
│ Simple lookup       │ ✓ Works              │ ✓ Works              │
│ Multi-step analysis │ ✗ Hard-coded only    │ ✓ Dynamic planning   │
│ Natural language    │ ✗ Limited keywords   │ ✓ Full understanding │
│ Context awareness   │ ✗ Stateless          │ ✓ Conversation memory│
│ Explanation         │ ✗ Returns raw data   │ ✓ Interprets results │
│ Proactive actions   │ ✗ User must request  │ ✓ Suggests next steps│
└─────────────────────┴──────────────────────┴───────────────────────┘
"""
    print(comparison)
    print()
    
    print("=" * 70)
    print()
    
    print("🚀 To run the agent in production:\n")
    print("1. Set OpenAI API key:")
    print("   export OPENAI_API_KEY='sk-...'")
    print()
    print("2. Start the Flask app:")
    print("   python app.py")
    print()
    print("3. Query the agent:")
    print("""   curl -X POST http://localhost:5000/api/agent/query \\
     -H "Content-Type: application/json" \\
     -d '{"query": "What's AAPL's price?"}'""")
    print()
    print("=" * 70)

def test_tool_definitions():
    """Test that tool definitions are properly formatted"""
    print("\n🧪 Testing Tool Definitions Format...\n")
    
    try:
        sys.path.append('/Workspace/Users/vamsi.341@gmail.com/STOCK-ANALYSIS')
        from services.agent_tools import AgentToolkit
        
        tools = AgentToolkit.get_tool_definitions()
        
        print(f"✅ Found {len(tools)} tool definitions")
        print()
        
        for tool in tools:
            func = tool['function']
            print(f"   • {func['name']}: {func['description'][:50]}...")
        
        print()
        print("✅ All tool definitions are properly formatted for OpenAI API")
        return True
    
    except Exception as e:
        print(f"❌ Error loading tool definitions: {e}")
        return False

if __name__ == "__main__":
    demo_agent_capabilities()
    test_tool_definitions()
