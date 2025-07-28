# PDF Outline Extraction System

A robust system for extracting document titles and hierarchical headings (H1, H2, H3) from PDF files using advanced font analysis and semantic pattern recognition.

## Features

- **Intelligent Title Detection**: Extracts document titles from PDF metadata and typography analysis
- **Hierarchical Heading Extraction**: Identifies H1, H2, and H3 headings with proper nesting
- **Multi-language Support**: Handles various writing systems including RTL (Right-to-Left) scripts
- **Font-based Analysis**: Uses font size ratios, bold formatting, and position analysis
- **Semantic Recognition**: Detects numbered sections (1., 1.1, 1.1.1) and common heading keywords
- **Duplicate Prevention**: Excludes title text from headings to avoid redundancy
- **JSON Output**: Structured output with page numbers and heading levels

## Technical Approach

### Font Analysis
- Analyzes font size ratios relative to body text
- Detects bold formatting and typography patterns
- Uses position analysis for title identification in top 40% of first page

### Semantic Pattern Recognition
- Recognizes numbered section patterns (1., 1.1, 1.1.1)
- Identifies multilingual heading keywords
- Filters out non-heading content (addresses, URLs, etc.)

### Text Processing
- Unicode text normalization (NFC)
- Support for RTL scripts (Arabic, Hebrew)
- Removes directional formatting characters

## Dependencies

### Core Libraries
- **PyMuPDF (1.23.14)**: PDF text extraction and document analysis

### Built-in Python Modules
- **unicodedata**: Text normalization and character analysis
- **json**: Output formatting
- **pathlib**: File system operations
- **re**: Pattern matching and text processing

## Installation & Usage

### Prerequisites
- Docker
- Input PDF files

### Build the Docker Image
```bash
docker build --platform linux/amd64 -t pdf-outline-extractor:latest .
```

### Run the Container

#### On Windows (Git Bash/Command Prompt):
```bash
docker run --rm -v "F:\Adobe-Challenge\Challenge_1a\sample_dataset":/app/sample_dataset --network none pdf-outline-extractor:latest
```

#### On Linux/macOS:
```bash
docker run --rm -v $(pwd)/sample_dataset:/app/sample_dataset --network none pdf-outline-extractor:latest
```

### Usage Steps
1. Place PDF files in the `sample_dataset/pdfs/` directory
2. Run the Docker container using the appropriate command above for your operating system
3. JSON output files will be generated in the `sample_dataset/outputs/` directory
4. Each PDF file `filename.pdf` produces a corresponding `filename.json`

### Local Development
You can also run the script directly without Docker:
```bash
python process_pdfs.py
```

This will process PDFs from `sample_dataset/pdfs/` and output JSON files to `sample_dataset/outputs/`.

## Output Format

The system generates JSON files with the following structure:

```json
{
  "title": "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Chapter 1: Introduction",
      "page": 1
    },
    {
      "level": "H2", 
      "text": "1.1 Background",
      "page": 2
    },
    {
      "level": "H3",
      "text": "1.1.1 Historical Context",
      "page": 3
    }
  ]
}
```

### Output Schema
- **title**: Document title (string, required)
- **outline**: Array of heading objects (required)
  - **level**: Heading hierarchy - "H1", "H2", or "H3" (required)
  - **text**: Heading text content (required)
  - **page**: Page number where heading appears, 1-based (required)

## Performance Notes

- Processes up to 50 pages per document for performance optimization
- Analyzes first 5 pages for document structure learning
- Handles large documents efficiently with memory management

## Error Handling

- Graceful handling of corrupted or unreadable PDF files
- Continues processing remaining files if individual files fail
- Detailed error logging for troubleshooting

## File Structure

```
.
├── Dockerfile
├── requirements.txt
├── process_pdfs.py
├── README.md
├── sample_dataset/
│   ├── pdfs/
│   │   └── ... (place your PDF files here)
│   ├── outputs/
│   │   └── ... (output JSON files will be generated here)
│   └── schema/
│       └── output_schema.json
```

## License

This project is designed for PDF document analysis and outline extraction tasks.
# Adobe_Challenge_1a
