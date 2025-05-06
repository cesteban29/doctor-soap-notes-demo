# SOAP Note Generator

A tool for generating SOAP notes from medical transcripts using GPT-4.

takes PriMock 57 (dataset of medical meeting transcripts and notes) and turns it into a Braintrust demo that auto-generates SOAP (Subjective / Objective / Assessment / Plan) notes from each consultation transcript and scores the results against the clinician-written notes that ship with the dataset

## Setup

1. Run the setup script:
```bash
./setup.sh
```

This will:
- Create a Python virtual environment
- Install all required dependencies
- Configure VS Code settings for the virtual environment
- Run the ETL pipeline (etl/build.py & etl/filter_complete.py)
    - this will generate a data/soap_dataset.jsonl file with cleaned data (some placeholder text) and a data/soap_dataset_complete.jsonl with no placeholders
- Insert the data/soap_dataset_complete.jsonl dataset into Braintrust by running the braintrust/insert_soap_dataset.py file

2. Activate the virtual environment:
```bash
source .venv/bin/activate
```

3. Push the prompts & scorers to Braintrust
```
braintrust push {file}
```
Push these files:
- braintrust/prompts/system1.py
- braintrust/prompts/system2.py
- braintrust/scorers/plan_llm_judge.py
- braintrust/scorers/not_missing.py


4. Insert the SOAP data
```bash
python3 insert_soap_dataset.py
```

## Development

- The virtual environment will be automatically detected by VS Code/Cursor
- All dependencies are managed in `requirements.txt`
- To add new dependencies:
  1. Install them: `pip install <package-name>`
  2. Update requirements: `pip freeze > requirements.txt`
