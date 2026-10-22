from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

templates = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "templates"), autoescape=select_autoescape(["html", "xml"]))
