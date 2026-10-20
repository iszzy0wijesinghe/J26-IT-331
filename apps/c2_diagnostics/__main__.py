"""Launch with: python -m apps.c2_diagnostics."""

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "apps.c2_diagnostics.api:app",
        host="127.0.0.1",
        port=8032,
        reload=False,
    )
