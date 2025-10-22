import json
from pathlib import Path
from typing import Dict, List

SPEC_ROOT = Path("config/platforms/registries/youtube/versions/v1/spec")
POLICY_ROOT = Path("config/platforms/registries/youtube/versions/v1/policies")

OPS = json.loads((SPEC_ROOT / "operations.json").read_text())["operations"]
PERMS = json.loads((POLICY_ROOT / "permissions.json").read_text())

def required_scope_keys_for_operation(op_name: str) -> List[str]:
    return OPS[op_name]["required_scopes"]

def allowed_operations_for_role(role: str) -> List[str]:
    return PERMS["roles"][role]["allows"]

def assert_allowed(role: str, op_name: str):
    allowed = set(allowed_operations_for_role(role))
    if op_name not in allowed:
        raise PermissionError(f"Role '{role}' is not allowed to perform '{op_name}'.")
