#!/usr/bin/env python3
# Standard library imports
import os
import json
from typing import Any, Dict
# Braintrust library import for dataset management
from braintrust import init_dataset

# Construct the path to the JSONL file containing SOAP note examples
# Goes up one directory level (..) from the current file's location
file_path = os.path.join(os.path.dirname(__file__), "..", "data/soap_dataset_complete.jsonl")


def create_soap_dataset(file_path: str) -> None:
    """
    Create a dataset by inserting each JSONL record into a braintrust dataset.
    
    Args:
        file_path (str): Path to the JSONL file containing SOAP note examples
    """
    # Initialize a new Braintrust dataset for SOAP note evaluation
    dataset = init_dataset("SOAP-gen-demo", "Completed SOAP Notes Dataset")
    
    # Open and process the JSONL file line by line
    with open(file_path, "r") as f:
        for line in f:
            # Remove any leading/trailing whitespace
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Parse the JSON object from the current line
            record: Dict[str, Any] = json.loads(line)
            
            # Insert the record into the dataset
            # Each record should have:
            # - input: The patient information or transcript
            # - expected: The expected SOAP note output
            dataset.insert(
                input=record["input"],
                expected=record["expected"],
            )

    # Ensure all records are saved to the dataset
    dataset.flush()
    print("Dataset insertion completed.")


# Only run the script if it's being executed directly (not imported)
if __name__ == "__main__":
    create_soap_dataset(file_path) 