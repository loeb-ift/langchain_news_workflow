import os

# Always run tests in mock mode (no Ollama calls)
os.environ.setdefault("OLLAMA_MOCK", "true")
