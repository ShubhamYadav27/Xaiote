import logging
import re
import json

class SensitiveDataFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        # Matches patterns like Bearer tokens, secrets, API keys
        self.patterns = [
            (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*"), r"\1[REDACTED]"),
            (re.compile(r"(?i)(api[_-]?key['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9\-]+"), r"\1[REDACTED]"),
            (re.compile(r"(?i)(secret['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9\-]+"), r"\1[REDACTED]"),
            (re.compile(r"(?i)(password['\"]?\s*[:=]\s*['\"]?)[^&'\" ]+"), r"\1[REDACTED]")
        ]

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.patterns:
                record.msg = pattern.sub(replacement, record.msg)
        return True

def setup_secure_logging():
    logger = logging.getLogger()
    
    # Check if filter is already added to avoid duplication
    if not any(isinstance(f, SensitiveDataFilter) for f in logger.filters):
        scrubber = SensitiveDataFilter()
        logger.addFilter(scrubber)
        for handler in logger.handlers:
            handler.addFilter(scrubber)

setup_secure_logging()
