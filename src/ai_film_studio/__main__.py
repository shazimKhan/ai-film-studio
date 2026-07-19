"""Module entry point for ``python -m ai_film_studio``."""

from ai_film_studio.cli.app import app


def main() -> None:
    """Run the AI Film Studio CLI."""
    app()


if __name__ == "__main__":
    main()

