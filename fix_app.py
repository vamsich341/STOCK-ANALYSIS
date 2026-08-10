import re

# Read the file
with open('app.py', 'r') as f:
    content = f.read()

# Fix the import - remove old ones and keep the correct one
content = re.sub(
    r'from services\.stock_api import StockAPIClient\nfrom services\.agent import StockAnalysisAgent',
    '',
    content
)

# Fix the initialization section  
old_init = '''# Initialize services
massive_client = MassiveAPIClient(Config.MASSIVE_API_KEY)
analysis_agent = StockAnalysisAgent(massive_client)'''

new_init = '''# Initialize services
massive_client = MassiveAPIClient(Config.MASSIVE_API_KEY)
embeddings_service = EmbeddingsService(api_key=Config.OPENAI_API_KEY)
toolkit = AgentToolkit(get_db_connection, massive_client, embeddings_service)
analysis_agent = StockAnalysisAgent(toolkit, api_key=Config.OPENAI_API_KEY)'''

content = content.replace(old_init, new_init)

# Write back
with open('app.py', 'w') as f:
    f.write(content)

print("File fixed successfully")
