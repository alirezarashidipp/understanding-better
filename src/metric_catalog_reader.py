from pathlib import Path

import yaml

SECTIONS = yaml.safe_load(
    (Path(__file__).resolve().parent.parent / "input_format.yml").read_text(encoding="utf-8")
)["global_metrics_format"]["sections"]
Catalog = dict[str, dict[str, list[str]]]


def read_global_metrics(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError("metrics/metrics.md was not found.")
    return path.read_text(encoding="utf-8-sig")


def parse_global_metrics(text: str) -> Catalog:
    catalog: Catalog = {}
    category = ""
    section = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            category = _category_name(line[3:])
            if category.casefold() in {name.casefold() for name in catalog}:
                raise ValueError(f"Catalog contains duplicate category '{category}'.")
            catalog[category] = {name: [] for name in SECTIONS.values()}
            section = ""
            continue
        if line.startswith(("* **", "- **")):
            section = _plain_text(line[2:])
            continue
        if category and section in catalog[category] and line.startswith(("* ", "- ")):
            value = _plain_text(line[2:])
            values = catalog[category][section]
            if value.casefold() in {item.casefold() for item in values}:
                raise ValueError(
                    f"Catalog category '{category}' has duplicate {section} value '{value}'."
                )
            values.append(value)

    if not catalog:
        raise ValueError("metrics.md must contain at least one category.")
    for category, sections in catalog.items():
        missing = [name for name, values in sections.items() if not values]
        if missing:
            raise ValueError(f"Catalog category '{category}' is missing: {', '.join(missing)}.")
    return catalog


def _category_name(value: str) -> str:
    name = _plain_text(value)
    prefix, separator, remainder = name.partition(". ")
    return remainder if separator and prefix.isdigit() else name


def _plain_text(value: str) -> str:
    return value.replace("**", "").strip()
