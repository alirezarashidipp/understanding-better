import argparse

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the MRM Model Review web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    return parser


def main(app_path: str = "api:create_app", factory: bool = True) -> None:
    arguments = build_parser().parse_args()
    uvicorn.run(
        app_path,
        factory=factory,
        host=arguments.host,
        port=arguments.port,
        reload=arguments.reload,
    )
