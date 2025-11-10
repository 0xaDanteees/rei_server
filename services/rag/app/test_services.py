from openai import OpenAI
from settings import settings

# Validate API key is loaded
if not settings.OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in .env. Check reicam_server/.env file.")

print(f"✓ API Key loaded: {settings.OPENAI_API_KEY[:20]}...")

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Use valid model and correct API
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Write a one-sentence bedtime story about a unicorn."}
    ]
)

print(f"✓ Response: {response.choices[0].message.content}")