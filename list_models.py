from dotenv import load_dotenv
load_dotenv()

import os
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("Models available to your key:\n")
for model in client.models.list():
    # Only show ones that support generateContent (text generation)
    actions = getattr(model, "supported_actions", None) or getattr(model, "supported_generation_methods", None)
    print(f"- {model.name}  (supports: {actions})")
