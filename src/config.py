from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "checklists.yaml"


def load_checklists():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["tabs"]


def iter_item_keys(tabs):
    for tab in tabs:
        for section in tab.get("sections", []):
            for item in section.get("items", []):
                yield f"{tab['id']}.{section['id']}.{item['id']}"


def total_items(tabs):
    return sum(1 for _ in iter_item_keys(tabs))


def tab_item_keys(tab):
    keys = []
    for section in tab.get("sections", []):
        for item in section.get("items", []):
            keys.append(f"{tab['id']}.{section['id']}.{item['id']}")
    return keys
