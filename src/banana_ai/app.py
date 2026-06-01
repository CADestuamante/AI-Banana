from banana_ai.config import AppConfig, load_config
from banana_ai.utils.logging import setup_logging


def main() -> None:
    config: AppConfig = load_config()
    setup_logging(config.app.log_level)
    # Placeholder entrypoint for UI and inference wiring.
    print(f"{config.app.name} skeleton is ready.")


if __name__ == "__main__":
    main()
