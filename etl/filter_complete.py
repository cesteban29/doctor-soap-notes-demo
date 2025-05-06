#!/usr/bin/env python3
import json
from pathlib import Path

# Paths for input and output datasets
INPUT = Path('data/soap_dataset.jsonl')
OUTPUT = Path('data/soap_dataset_complete.jsonl')

# Define the placeholder text for incomplete sections
placeholders = {
    'subjective': 'No subjective information available.',
    'objective': 'No objective information available.',
    'assessment': 'No assessment information available.',
    'plan': 'No plan information available.',
}

# Filter and write only complete records
def main():
    with INPUT.open('r') as infile, OUTPUT.open('w') as outfile:
        for line in infile:
            if not line.strip():
                continue
            record = json.loads(line)
            expected = record.get('expected', {})
            # Keep only records without any placeholder values
            if all(expected.get(k) != placeholders[k] for k in placeholders):
                json.dump(record, outfile)
                outfile.write('\n')
    print(f"Filtered complete records to {OUTPUT}")

if __name__ == '__main__':
    main() 