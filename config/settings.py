import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

def setup_openrouter_client():
    """
    Initialize the OpenRouter client using the OpenAI SDK
    with proper configuration.

    Returns:
        OpenAI: Configured OpenAI client pointing to OpenRouter
    """
    # Prefer explicit OPENROUTER_API_KEY, fall back to API_KEY for compatibility
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY")

    if not api_key:
        raise ValueError(
            "OpenRouter API key not found. Please set the OPENROUTER_API_KEY "
            "environment variable in your .env file (or API_KEY as a fallback)."
        )

    # Initialize the client with OpenRouter configuration
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        # Optional headers for OpenRouter leaderboard
        default_headers={
            "HTTP-Referer": os.getenv("YOUR_SITE_URL", "http://localhost:5000"),
            "X-Title": os.getenv("YOUR_SITE_NAME", "Stock Analysis using Agentic AI")
        }
    )

    return client

def test_connection():
    """Test the connection to OpenRouter API with a simple completion request."""
    try:
        client = setup_openrouter_client()

        # Make a simple test request
        completion = client.chat.completions.create(
            model= "x-ai/grok-4-fast:free",  # OpenRouter model format
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Tell me latest stock news!"}
            ],
        )

        print("✅ Successfully connected to OpenRouter API!")
        print(f"Model response: {completion.choices[0].message.content}")

    except Exception as e:
        print(f"❌ Error connecting to OpenRouter API: {e}")

if __name__ == "__main__":
    test_connection()
