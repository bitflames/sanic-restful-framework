import re
import secrets
import string


def camel_to_snake(name):
    """Convert camelCase class names to lowercase underscore format"""

    # Insert underline and lower case where position changes
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def generate_code(length: int = 5) -> str:
    """Randomly generate a pure digital verification code with the specified number of digits. The default value is 5 digits"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))
