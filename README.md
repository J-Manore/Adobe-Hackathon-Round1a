# Adobe-Hackathon-ConnectingTheDots-Round1A

## Overview

Repository for Round 1A, Adobe India Hackathon 2025: Connecting the Dots.  
The core objective is to extract a structured outline from PDF documents—specifically, the document title and hierarchical headings (H1, H2, H3)—with a solution that is robust, containerized, and portable.

---

## Submission Checklist

**Checklist corresponding to the official requirements:**

- **Project and Dockerfile:**  
  - The repository serves as a self-contained project, with a working `Dockerfile` present at the root.

- **Dockerfile:**  
  - The included `Dockerfile` produces a working, self-contained image.

- **Dependencies:**  
  - All dependencies (notably PyMuPDF) are installed within the container at build time, ensuring fully offline execution.

- **README:**  
  - Explanation of approach, dependencies, and build/run steps below.

---

## Features

- Extracts document title and hierarchical headings (H1–H3), with page numbers.
- Handles multiple input types: 
  - General documents
  - PDFs with embedded Table of Contents (TOC)
  - Forms  
  - Poster-like single-page documents
- All PDFs in `/app/input` are automatically processed; outputs are written to `/app/output` as JSON.
- Fully Dockerized—results are reproducible across environments.
- Multilingual and rules-based, with no model dependencies.

---

## Tech Stack

- **Language:** Python 3.9
- **Libraries:**  
  - PyMuPDF (`fitz`) – for PDF parsing and layout
  - Standard Python (`re`, `json`, `os`, `collections`, `typing`)
- **Platform:** Linux (amd64), CPU-only
- **Model Usage:** None (all logic is heuristic/rules-based)

---

## Input & Output Format

- **Input:** `/app/input` (read-only)
- **Output:** `/app/output`

For each `filename.pdf` in the input directory, the script produces `filename.json` in the output directory, like:

```json
{
  "title": "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Section Heading",
      "page": 2
    }
    // more outline entries...
  ]
}
```

---

## Supported Document Types

| Type      | Detection Logic                              | Handling Strategy                                   |
|-----------|---------------------------------------------|-----------------------------------------------------|
| TOC-Based | Has internal PDF Table of Contents           | Extract outline from embedded TOC                   |
| Forms     | Keywords: name:, date:, form, signature, etc | Extract only title (first line); outline is empty   |
| Posters   | Single page, <400 words                      | Largest font block is title, next is H1             |
| General   | Everything else                              | Heuristic on font/numbering/layout for headings     |

---

## Heading Extraction Approach

- **Font clustering**: Groups blocks by rounded font size/bold for heading detection.
- **Regex/numbering**: Picks up patterns like 1., 1.1, A., etc., to infer heading levels.
- **Filtering**: Skips headers/footers, large body text, and non-headings using heuristics.
- **Title detection**: Prefers metadata, largest prominent block, or centered early-page text.

---

## Performance & Constraints

| Requirement                    | Status         |
|---------------------------------|---------------|
| ≤10s runtime (50-page PDF)      | Met           |
| No internet at runtime          | Met           |
| ≤16GB RAM                       | Met           |
| Platform: amd64                 | Met           |
| Auto-process all PDFs           | Met           |
| Open Source only                | Met           |

---

## Building & Running

**Build:**
```bash
docker build --platform linux/amd64 -t pdf-processor .
```

**Run:**
```bash
docker run --rm `  -v "${PWD}/input:/app/input:ro" `  -v "${PWD}/output:/app/output" `  --network none pdf-processor
```
- Input PDFs go in `input/`  
- Results (`*.json`) will appear in `output/`

---

## Directory Layout

```
Adobe-Hackathon-ConnectingTheDots-Round1A/
├── Dockerfile
├── requirements.txt
├── extract_outline.py   # Main script
├── README.md
├── input/               # Test PDFs (local)
└── output/              # Output JSON (local)
```

---

## Notes

The solution is designed for adaptability; it does not rely on hardcoded layout rules or strings.  
Output JSON is deduplicated and strictly follows the required schema.  
Code is modular and ready for further development if needed.
