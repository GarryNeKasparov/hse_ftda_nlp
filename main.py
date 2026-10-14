"""ASGI entrypoint retained for local and Docker startup."""

import uvicorn

from law_links.http import create_app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8978)
