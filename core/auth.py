import os
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()


USER_DATABASE: Dict[str, Dict[str, Any]] = {
    "alice": {
        "password": os.getenv("DEMO_ADMIN_PASSWORD", "admin-demo"),
        "tenant_id": "InsureLLM",
        "role": "admin",
    },
    "bob": {
        "password": os.getenv("DEMO_EMPLOYEE_PASSWORD", "employee-demo"),
        "tenant_id": "InsureLLM",
        "role": "employee",
    },
    "carol": {
        "password": os.getenv("DEMO_EXECUTIVE_PASSWORD", "executive-demo"),
        "tenant_id": "InsureLLM",
        "role": "executive",
    },
}


def verify_credentials(username: str, password: str) -> Dict[str, Any]:
    """Validate demo credentials and return session state."""
    user = USER_DATABASE.get(username.lower().strip())

    if user and user["password"] == password:
        return {
            "authenticated": True,
            "username": username,
            "tenant_id": user["tenant_id"],
            "role": user["role"],
            "error": None,
        }

    return {
        "authenticated": False,
        "username": None,
        "tenant_id": None,
        "role": None,
        "error": "❌ Invalid username or password.",
    }