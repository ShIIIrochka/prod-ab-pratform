def get_aerich_config(db_uri) -> dict[str, dict]:
    return {
        "connections": {"default": db_uri},
        "apps": {
            "models": {
                "models": ["src.infra.adapters.db.models", "aerich.models"],
                "default_connection": "default",
            },
        },
    }
