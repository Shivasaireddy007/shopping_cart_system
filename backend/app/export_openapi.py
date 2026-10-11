"""Write the OpenAPI spec for the frontend's generated types and the API docs.

    uv run python -m app.export_openapi ../docs/openapi.json
"""

import json
import sys
from pathlib import Path

from app.main import app

if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    target.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {target}")
