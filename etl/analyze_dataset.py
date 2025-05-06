#!/usr/bin/env python3
"""Analyze the SOAP dataset to find empty sections."""

import json
from collections import defaultdict
from pathlib import Path

def analyze_dataset(jsonl_path):
    """Analyze which sections are empty in the dataset."""
    empty_sections = defaultdict(list)
    total = 0
    complete = 0
    
    with open(jsonl_path) as f:
        for i, line in enumerate(f, 1):
            data = json.loads(line)
            has_empty = False
            
            for section, content in data['expected'].items():
                if content == f"No {section} information available.":
                    empty_sections[section].append(i)
                    has_empty = True
            
            total += 1
            if not has_empty:
                complete += 1
    
    print(f"\nDataset Analysis:")
    print(f"Total rows: {total}")
    print(f"Complete rows: {complete}")
    print(f"Rows with empty sections: {total - complete}")
    print("\nEmpty sections breakdown:")
    for section, rows in empty_sections.items():
        print(f"{section}: {len(rows)} rows")
        print(f"Example rows: {rows[:5]}")
    
    # Print a few examples of rows with empty sections
    print("\nChecking first row with empty sections:")
    with open(jsonl_path) as f:
        for i, line in enumerate(f, 1):
            data = json.loads(line)
            if any(content == f"No {section} information available." 
                  for section, content in data['expected'].items()):
                print(f"\nRow {i} sections:")
                for section, content in data['expected'].items():
                    print(f"\n{section}:")
                    print(content[:200] + "..." if len(content) > 200 else content)
                break

if __name__ == "__main__":
    analyze_dataset("data/soap_dataset2.jsonl") 