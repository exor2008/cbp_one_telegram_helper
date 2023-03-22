from pathlib import Path

PATH = Path("bot", "token.txt")


def __getattr__(name: str):
    if name == "token":
        return open(PATH).read()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
