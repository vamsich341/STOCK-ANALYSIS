"""
LLM Agent - Orchestrates tool calling with GPT-4 for stock analysis
Replaces deterministic logic with intelligent tool selection and planning
"""

import logging
import json
import os
from typing import Dict, List, Optional, Any
import openai

from services.agent_tools import AgentToolkit

logger = logging.getLogger(__name__)

class StockAnalysisAgent:
    """LLM-powered agent for intelligent stock analysis"""
    
    def __init__(self, toolkit: AgentToolkit, api_key: Optional[str] = None):
        """Initialize the agent
        
        Args:
            toolkit: AgentToolkit instance with available tools
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.toolkit = toolkit
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        
        if self.api_key:
            openai.api_key = self.api_key
            self.model = "gpt-4-1106-preview"  # GPT-4 Turbo with function calling
            logger.info(f"LLM Agent initialized with model {self.model}")
        else:
            logger.warning("No OpenAI API key. Agent will use fallback logic.")
            self.model = None
        
        self.system_prompt = """You are an expert stock market analyst assistant with access to real-time data and analysis tools.

Your capabilities:
- Get real-time stock quotes and historical data
- Search for companies and news using semantic similarity
- Access detailed company information
- Manage watchlists and save analyses
- Create price alerts

When responding to user queries:
1. **Think step-by-step**: Break down complex questions into tool calls
2. **Explain your reasoning**: Tell the user what tools you're using and why
3. **Provide context**: Don't just return raw data - interpret it
4. **Be proactive**: Suggest related information or actions
5. **Cite sources**: Reference specific data points from tool results

Always start by using appropriate tools to gather data, then provide a comprehensive answer."""
    
    def execute_tool(self, tool_name: str, arguments: Dict) -> Dict[str, Any]:
        """Execute a tool and return the result
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
        
        Returns:
            Tool execution result
        """
        logger.info(f"Executing tool: {tool_name}({arguments})")
        
        # Map tool names to toolkit methods
        tool_map = {
            'get_quote': self.toolkit.get_quote,
            'get_historical': self.toolkit.get_historical,
            'search_semantic': self.toolkit.search_semantic,
            'get_company_info': self.toolkit.get_company_info,
            'get_news': self.toolkit.get_news,
            'add_to_watchlist': self.toolkit.add_to_watchlist,
            'save_analysis': self.toolkit.save_analysis,
            'create_alert': self.toolkit.create_alert
        }
        
        if tool_name not in tool_map:
            return {
                'success': False,
                'error': f'Unknown tool: {tool_name}'
            }
        
        try:
            tool_func = tool_map[tool_name]
            result = tool_func(**arguments)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run(self, user_query: str, user_id: Optional[int] = None, 
            conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Run the agent on a user query with tool calling
        
        Args:
            user_query: User's question or request
            user_id: Optional user ID for write operations
            conversation_history: Optional previous messages
        
        Returns:
            Dictionary with agent response and tool traces
        """
        logger.info(f"Agent processing query: {user_query}")
        
        if not self.api_key:
            return self._fallback_response(user_query)
        
        # Build conversation messages
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current query
        messages.append({"role": "user", "content": user_query})
        
        # Get tool definitions
        tools = AgentToolkit.get_tool_definitions()
        
        # Track tool executions
        tool_calls_made = []
        max_iterations = 5  # Prevent infinite loops
        
        try:
            for iteration in range(max_iterations):
                logger.info(f"Agent iteration {iteration + 1}/{max_iterations}")
                
                # Call LLM with function calling
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.3
                )
                
                assistant_message = response.choices[0].message
                
                # Check if agent wants to call tools
                if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                    # Add assistant message to conversation
                    messages.append(assistant_message)
                    
                    # Execute each tool call
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        # Inject user_id if needed and not provided
                        if user_id and tool_name in ['add_to_watchlist', 'save_analysis', 'create_alert']:
                            if 'user_id' not in arguments:
                                arguments['user_id'] = user_id
                        
                        # Execute tool
                        tool_result = self.execute_tool(tool_name, arguments)
                        
                        # Track tool call
                        tool_calls_made.append({
                            'tool': tool_name,
                            'arguments': arguments,
                            'result': tool_result
                        })
                        
                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": json.dumps(tool_result)
                        })
                    
                    # Continue loop to let agent process tool results
                    continue
                
                # No more tool calls - agent has final answer
                final_response = assistant_message.content
                
                return {
                    'success': True,
                    'response': final_response,
                    'tool_calls': tool_calls_made,
                    'model': self.model,
                    'iterations': iteration + 1
                }
            
            # Max iterations reached
            return {
                'success': False,
                'error': 'Max iterations reached',
                'tool_calls': tool_calls_made,
                'partial_response': messages[-1].get('content', 'Processing...')
            }
        
        except Exception as e:
            logger.error(f"Error in agent execution: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool_calls': tool_calls_made
            }
    
    def _fallback_response(self, user_query: str) -> Dict[str, Any]:
        """Fallback response when no OpenAI API key is available
        
        Args:
            user_query: User's question
        
        Returns:
            Fallback response
        """
        return {
            'success': False,
            'error': 'LLM agent requires OPENAI_API_KEY to be set',
            'fallback': True,
            'response': 'I need an OpenAI API key to provide intelligent analysis. '
                       'Please set OPENAI_API_KEY environment variable.'
        }
    
    def explain_capabilities(self) -> Dict[str, Any]:
        """Explain agent capabilities to users
        
        Returns:
            Dictionary describing what the agent can do
        """
        return {
            'agent_type': 'Stock Analysis LLM Agent',
            'model': self.model,
            'capabilities': {
                'read_tools': [
                    'get_quote: Get real-time stock quotes',
                    'get_historical: Fetch historical price data',
                    'search_semantic: Semantic search for companies and news',
                    'get_company_info: Detailed company information',
                    'get_news: Recent news articles'
                ],
                'write_tools': [
                    'add_to_watchlist: Add stocks to watchlist',
                    'save_analysis: Save AI-generated analysis',
                    'create_alert: Create price alerts'
                ],
                'features': [
                    'Multi-step reasoning and planning',
                    'Automatic tool selection',
                    'Contextual data interpretation',
                    'Proactive suggestions'
                ]
            },
            'example_queries': [
                "What's the current price of AAPL and how has it performed this month?",
                "Find me semiconductor companies with strong growth",
                "What are the latest news about Tesla?",
                "Add NVDA to my watchlist and set an alert if it drops below $800",
                "Analyze the tech sector and save your insights"
            ]
        }
