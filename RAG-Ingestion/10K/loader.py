from pathlib import Path


class HTMLLoader:
    """
    Reads a 10-K filing document from disk and returns its contents as a string.

    Accepts any text-based format produced by sec-edgar-downloader:
      - .htm / .html  — rich HTML filings (parsed by TenKParser via BeautifulSoup)
      - .txt          — plain-text or SGML submissions (handled by TenKParser's
                        regex fallback)
    """

    def load(self, path: str) -> str:
        """
        Read the filing document at the given path.

        Args:
            path: Absolute or relative path to the filing file.

        Returns:
            Full file contents as a UTF-8 string; encoding errors are ignored.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"10-K filing file not found: {file_path.resolve()}")

        return file_path.read_text(encoding="utf-8", errors="ignore")
