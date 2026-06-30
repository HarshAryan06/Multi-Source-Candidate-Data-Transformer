# Multi-Source Candidate Data Transformer

## Overview

This project combines candidate information from two different sources and generates a single, clean JSON profile.

**Sources used:**

* Recruiter CSV (structured data)
* Recruiter Notes (.txt) (unstructured data)

The project cleans, normalizes, merges, and validates the data before generating the final output.

---

## Features

* Read data from CSV and text files
* Normalize emails, phone numbers, and skills
* Merge information from multiple sources
* Handle missing or conflicting data
* Generate JSON output
* Support configurable output format

---

## Project Structure

```
project/
│
├── main.py
├── data/
│   └── sample/
│       ├── recruiter.csv
│       ├── notes.txt
│       ├── config_custom.json
│       └── config_strict.json
├── outputs/
└── tests/
```

---

## How It Works

1. Read candidate data from the CSV file.
2. Read recruiter notes.
3. Extract useful information.
4. Normalize the data.
5. Merge both sources.
6. Generate the final JSON output.

---

## Run the Project

Default output:

```bash
python main.py --csv data/sample/recruiter.csv --notes data/sample/notes.txt --out outputs/default_output.json
```

Using a custom configuration:

```bash
python main.py --csv data/sample/recruiter.csv --notes data/sample/notes.txt --config data/sample/config_custom.json --out outputs/custom_output.json
```

Process all candidates:

```bash
python main.py --all-candidates --csv data/sample/recruiter.csv --notes data/sample/notes.txt --out outputs/all_candidates_output.json
```

---

## Run Tests

```bash
python -m unittest discover -s tests
```

---

## Merge Rules

* Email is used as the primary match.
* Phone number is the secondary match.
* CSV data is preferred for basic details.
* Notes are used to add skills, location, experience, and headline.

---

## Output

The generated JSON can include fields such as:

* Name
* Email
* Phone
* Company
* Job Title
* Location
* Skills
* Experience

---

## Error Handling

The project handles:

* Missing files
* Empty notes
* Invalid emails
* Malformed CSV rows
* Missing values
* Conflicting information

---

## Technologies Used

* Python 3
* JSON
* CSV
* Python Standard Library
