import ast
import json
import re


def extract_markdown_block(text: str, language: str = "") -> str:
    """Extracts code/json from markdown blocks (e.g. ```python ... ```).

    Handles:
    - Optional trailing newline before closing fence (V-1)
    - CRLF and LF line endings (V-2)
    """
    # Normalize line endings to LF before matching (prevents CRLF failure on Windows)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Try to find a block with the specific language first
    if language:
        pattern = rf"```{language}\s*\n(.*?)\n?```"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Fallback to any markdown block
    pattern = r"```(?:\w+)?\s*\n(.*?)\n?```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no markdown block, assume the whole string is the artifact
    return text.strip()


class ExecutionVerifier:
    def verify(self, code_string: str) -> bool:
        """
        Verify if the given code string is syntactically valid Python code.
        Automatically inspects and extracts from markdown artifacts.
        Empty strings are rejected (V-3).
        """
        clean_code = extract_markdown_block(code_string, "python")
        if not clean_code.strip():
            return False  # Empty code is not a meaningful verified output
        try:
            ast.parse(clean_code)
            return True
        except (SyntaxError, ValueError, TypeError):
            return False


class SchemaVerifier:
    def verify(self, json_string: str) -> bool:
        """
        Verify if the given string is valid JSON.
        Automatically inspects and extracts from markdown artifacts.
        Bare primitives (null, true, 42) are rejected for structured output use-cases.
        """
        clean_json = extract_markdown_block(json_string, "json")
        if not clean_json.strip():
            return False
        try:
            parsed = json.loads(clean_json)
            # Reject bare JSON primitives \u2014 expect a structured object or array
            if not isinstance(parsed, (dict, list)):
                return False
            return True
        except (json.JSONDecodeError, TypeError):
            return False
