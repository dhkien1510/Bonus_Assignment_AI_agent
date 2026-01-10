# Configuration for Agent-S Testing
# Edit this file to change API keys and model settings

# =============================================================================
# LLM CONFIGURATION (Main reasoning model)
# =============================================================================
ENGINE_CONFIG = {
    "engine_type": "open_router",  # Options: 'openai', 'anthropic', 'gemini', 'azure_openai', 'vllm', 'open_router'
    "model": "google/gemini-2.5-flash",
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "sk-or-v1-",
}

# =============================================================================
# GROUNDING MODEL CONFIGURATION (Visual grounding model)
# =============================================================================
GROUNDING_CONFIG = {
    "engine_type": "open_router",  # Options: 'openai', 'anthropic', 'gemini', 'huggingface', 'vllm'
    "model": "bytedance/ui-tars-1.5-7b",
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "sk-or-v1-",
    "grounding_width": 1920,
    "grounding_height": 1080,
}

# =============================================================================
# TEST CONFIGURATION
# =============================================================================
TEST_CONFIG = {
    "mode": "pyautogui",  # Options: 'pyautogui', 'playwright'
    "task_id": None,      # Set to specific task ID (e.g., "PS-1") or None for all tasks
    "max_tasks": 20,       # Test with 2 tasks only
    "env_config": "env_config.json",
    "tasks_file": "dataset/prestashop_tasks.json",
}

# =============================================================================
# RATE LIMITING (for API with request limits)
# =============================================================================
RATE_LIMIT_CONFIG = {
    "enabled": False,               # Tắt rate limiting vì dùng OpenRouter (không giới hạn như Gemini API trực tiếp)
    "requests_per_minute": 30,      # OpenRouter thường cho phép nhiều request hơn
    "delay_between_requests": 2,    # Giảm xuống 2 giây
}
