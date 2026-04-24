from pathlib import Path


class HTMLLoader:
    """Loads a 10-K HTML file from disk and returns its contents as a string."""

    def load(self, path: str) -> str:
        """
        Read the HTML file at the given path.

        Args:
            path: Absolute or relative path to the .html file.

        Returns:
            Full HTML text with UTF-8 encoding; encoding errors are ignored.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"10-K HTML file not found: {file_path.resolve()}")

        return file_path.read_text(encoding="utf-8", errors="ignore")
