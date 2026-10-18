# Document Understanding Assistant

An AI/ML internship project developed as Project 2 for Arrowstack.

## Overview

The Document Understanding Assistant processes business documents in PDF and TXT formats. It extracts key information, generates summaries, and validates structured output.

## Features

- PDF and TXT document upload
- Baseline, rule-based document processing
- Local AI analysis using Ollama
- Entity extraction for people, organizations, dates, email addresses, and monetary amounts
- Document classification and summarization
- Structured JSON output and schema validation
- Comparison of baseline and local AI results
- Evaluation using sample documents

## Technology Stack

- Python
- Streamlit
- Ollama
- JSON Schema
- Pytest

## Getting Started

1. Clone or download this repository.
2. Create and activate a Python virtual environment.
3. Install the dependencies listed in `requirements.txt`.
4. Install and start Ollama, then download the configured model.
5. Run the application with:

   `streamlit run app.py`

## Evaluation

Run the tests:

`python -m pytest -q`

Run the evaluation script:

`python evaluate.py`

## Limitations

Extracted information and generated summaries may contain errors. Always verify important results against the original document.

## Data Notice

The included evaluation documents are synthetic samples intended for testing the application.

## Project Context

Arrowstack AI/ML Internship — Project 2: Document Understanding Assistant.
