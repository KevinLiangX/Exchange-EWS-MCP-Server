import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve the project root assuming config.py is in src/ews_exchange_mcp/
project_root = Path(__file__).resolve().parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


EWS_ENDPOINT = os.getenv("EWS_ENDPOINT")
EWS_USERNAME = os.getenv("EWS_USERNAME")
EWS_PASSWORD = os.getenv("EWS_PASSWORD")
EWS_DOMAIN = os.getenv("EWS_DOMAIN", "")
EWS_EXCHANGE_VERSION = os.getenv("EWS_EXCHANGE_VERSION", "Exchange2013")
EWS_EMAIL_SIGNATURE = os.getenv("EWS_EMAIL_SIGNATURE", "")
NODE_TLS_REJECT_UNAUTHORIZED = os.getenv("NODE_TLS_REJECT_UNAUTHORIZED", "1")

if not EWS_ENDPOINT or not EWS_USERNAME or not EWS_PASSWORD:
    raise ValueError("Missing essential EWS credentials (EWS_ENDPOINT, EWS_USERNAME, EWS_PASSWORD) in environment variables.")
