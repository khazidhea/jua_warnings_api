"""General helper functions for the API"""


from fastapi import HTTPException


def parse_parameters(query: str) -> set[str]:
    """Parses a comma-separated list into a set of strings"""
    parts = {part.strip() for part in query.split(",") if part.strip()}

    if not parts:
        raise HTTPException(status_code=400, detail="Invalid parameters")

    return parts
