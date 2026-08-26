#!/usr/bin/env python3
"""Convert Dialogflow ES intent JSON files and entity CSVs to Rasa NLU training data."""

import json
import csv
from pathlib import Path


def load_dialogflow_intents(intents_dir: Path) -> list[dict]:
    intents = []
    for json_file in sorted(intents_dir.glob("*.json")):
        with open(json_file, encoding="utf-8") as f:
            intents.append(json.load(f))
    return intents


def load_entity_csv(csv_path: Path) -> list[str]:
    values = set()
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            for val in row:
                stripped = val.strip().strip('"')
                if stripped:
                    values.add(stripped)
    return sorted(values)


def convert_training_phrase(parts: list[dict]) -> str:
    rasa_tokens = []
    for part in parts:
        text = part.get("text", "")
        entity_type = part.get("entityType")
        if entity_type:
            entity_name = entity_type.lstrip("@")
            rasa_tokens.append(f"[{text}]({entity_name})")
        else:
            rasa_tokens.append(text)
    return "".join(rasa_tokens).strip()


def convert_intents_to_rasa(intents: list[dict]) -> str:
    lines = ["version: \"3.1\"", "nlu:"]

    for intent in intents:
        intent_name = intent["displayName"]
        phrases = intent.get("trainingPhrases", [])

        lines.append(f"- intent: {intent_name}")
        lines.append("  examples: |")

        for phrase in phrases:
            parts = phrase.get("parts", [])
            rasa_example = convert_training_phrase(parts)
            if rasa_example:
                lines.append(f"    - {rasa_example}")

    return "\n".join(lines) + "\n"


def generate_lookup_table(entity_name: str, values: list[str]) -> str:
    lines = [
        f"  - lookup: {entity_name}",
        "    examples: |",
    ]
    for val in values:
        lines.append(f"      - {val}")
    return "\n".join(lines)


def generate_nlu_with_lookups(intents_yaml: str, lookup_tables: dict[str, list[str]]) -> str:
    lookup_lines = ["", "lookup_tables:"]
    for entity_name, values in sorted(lookup_tables.items()):
        lookup_lines.append(generate_lookup_table(entity_name, values))
    return intents_yaml + "\n".join(lookup_lines) + "\n"


def main():
    base_dir = Path(__file__).parent
    source_dir = base_dir / "data" / "dialogflow"
    intents_dir = source_dir / "intents"
    entities_dir = source_dir / "entities"
    output_nlu = base_dir / "data" / "nlu.yml"

    if not intents_dir.exists():
        print(f"Error: Intents directory not found at {intents_dir}")
        return

    print(f"Loading intents from {intents_dir}...")
    intents = load_dialogflow_intents(intents_dir)
    print(f"  Found {len(intents)} intents")

    print("Converting intents to Rasa NLU format...")
    nlu_yaml = convert_intents_to_rasa(intents)

    lookup_tables = {}
    if entities_dir.exists():
        print(f"Loading entities from {entities_dir}...")
        for csv_file in sorted(entities_dir.glob("*.csv")):
            entity_name = csv_file.stem.replace("_entity", "")
            values = load_entity_csv(csv_file)
            lookup_tables[entity_name] = values
            print(f"  {entity_name}: {len(values)} values")

    print("Generating lookup tables...")
    nlu_yaml = generate_nlu_with_lookups(nlu_yaml, lookup_tables)

    output_nlu.parent.mkdir(parents=True, exist_ok=True)
    with open(output_nlu, "w", encoding="utf-8") as f:
        f.write(nlu_yaml)

    print(f"\nDone! Generated {output_nlu}")
    print(f"  Total intents: {len(intents)}")
    print(f"  Total lookup tables: {len(lookup_tables)}")


if __name__ == "__main__":
    main()
