import os
from dotenv import load_dotenv
from pathlib import Path

env_path = os.path.join(os.path.dirname(__file__), "..", "config.env")
load_dotenv(env_path)

# Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(Path.home() / ".repozen" / "uploads"))