from __future__ import annotations

import hashlib

from uuid import UUID


def generate_deterministic_decision_id(
    subject_id: str,
    flag_key: str,
    experiment_id: UUID | None,
    variant_id: str | None,
) -> UUID:
    seed_parts = [
        subject_id,
        flag_key,
        str(experiment_id) if experiment_id else "none",
        variant_id if variant_id else "none",
    ]
    seed = ":".join(seed_parts)

    h = hashlib.sha256(seed.encode()).digest()

    # Создаём UUID v4 из хеша
    # Это обеспечивает детерминизм: одинаковый seed → одинаковый UUID
    return UUID(bytes=h[:16], version=4)
