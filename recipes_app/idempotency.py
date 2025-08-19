# utils/idempotency.py
import uuid, json
from typing import Any, Dict, Optional

# Свой namespace: фиксируем один раз (можно захардкодить)
NAMESPACE = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

def _canonical(obj: Any) -> str:
    """
    Привести к каноническому JSON (сортировка ключей, без пробелов).
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def make_request_uuid(
    body: Dict[str, Any],
    *,
    path: str,
    user_id: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None
) -> uuid.UUID:
    """
    Делаем стабильный UUID v5 на основе канонического тела + контекста.
    """
    payload = {
        "path": path,          # /api/v1/recipes/  или /api/v1/recipes/{id}/ingredients/
        "user_id": user_id,    # чтобы разные пользователи не коллидировали
        "body": body or {},
        "extra": extra or {}   # сюда можно положить recipe_id, и т.п.
    }
    return uuid.uuid5(NAMESPACE, _canonical(payload))
