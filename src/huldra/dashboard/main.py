"""Main FastAPI application with static file serving and CLI."""

import importlib.resources
from pathlib import Path

import typer
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router as api_router


def get_frontend_dir() -> Path | None:
    """Get frontend dist directory, works for installed package and development."""
    # Try importlib.resources (installed package)
    try:
        ref = importlib.resources.files("huldra.dashboard").joinpath("frontend/dist")
        with importlib.resources.as_file(ref) as path:
            if path.exists() and (path / "index.html").exists():
                return path
    except (TypeError, FileNotFoundError):
        pass

    # Fallback to relative path (development)
    dev_path = Path(__file__).parent / "frontend" / "dist"
    if dev_path.exists() and (dev_path / "index.html").exists():
        return dev_path

    return None # TODO: Maybe i should throw here instead?


def create_app(*, serve_frontend: bool = False) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Huldra Dashboard",
        description="Monitoring dashboard for Huldra experiments",
        version="0.1.0",
    )

    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=["http://localhost:5173"],  # Vite dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routes
    app.include_router(api_router)

    # Serve frontend only if explicitly requested
    if serve_frontend:
        frontend_dir = get_frontend_dir()
        if frontend_dir:
            # Mount static assets
            assets_dir = frontend_dir / "assets"
            if assets_dir.exists():
                app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

            # SPA catch-all route
            @app.get("/{full_path:path}")
            async def serve_spa(full_path: str) -> FileResponse:
                """Serve the React SPA for all non-API routes."""
                assert frontend_dir is not None
                file_path = frontend_dir / full_path
                if file_path.is_file() and not full_path.startswith("api"):
                    return FileResponse(file_path)
                return FileResponse(frontend_dir / "index.html")

    return app


# Default app instance (API only)
app = create_app()

# App instance with frontend serving
app_with_frontend = create_app(serve_frontend=True)

# Create Typer app for CLI
cli_app = typer.Typer(
    help="Huldra Dashboard - Monitor your experiments",
    invoke_without_command=False,
    no_args_is_help=True,
)


@cli_app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """Start the dashboard server with React frontend."""
    uvicorn.run(
        "huldra.dashboard.main:app_with_frontend",
        host=host,
        port=port,
        reload=reload,
    )


@cli_app.command()
def api(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """Start the API server only (no frontend)."""
    uvicorn.run(
        "huldra.dashboard.main:app",
        host=host,
        port=port,
        reload=reload,
    )


def cli() -> None:
    """CLI entry point."""
    cli_app()


if __name__ == "__main__":
    cli()


