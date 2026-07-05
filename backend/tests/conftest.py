import os

# Must be set before app.main is imported: Settings has required fields
# and get_settings() is lru_cached at first call.
os.environ["API_KEY"] = "test-api-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["GMAIL_CREDENTIALS_PATH"] = "credentials.json"
