# Documentation 2 PDF 📚

Python script that scrapes technical documentation websites and converts them into professional PDF documents with modern layout. Perfect for offline documentation access! 


## 🚀 Features

- **Complete Documentation Capture**: Automatically discovers and scrapes all documentation pages
- **Section-Based Organization**: Groups articles by their original documentation structure
- **Professional PDF Generation**: Creates high-quality PDFs with proper formatting and typography
- **Table of Contents**: Generates organized TOC with section headers
- **Interactive Content Handling**: Properly captures tabbed content and embedded examples
- **Rate Limiting**: Respectful scraping with built-in delays
- **Merged Output**: Combines all PDFs into one complete documentation file


## 🛠️ Installation

```bash
# Install dependencies
pip install playwright PyPDF2

# Install browser
playwright install chromium
```

## 📖 Usage

### Basic Usage
```bash
python playwright_scraper.py
```

### Output Structure
```
docs_output/
├── individual_pdfs/           # Individual page PDFs
│   ├── 000_table_of_contents.pdf
│   ├── 001_getting_started.pdf
│   └── ...
└── Complete_Documentation.pdf  # Merged PDF
```


## 🔧 Configuration

### Custom Output Directory
```python
scraper = PlaywrightDocScraper(output_dir="custom_docs")
```

### Framework Support
Currently supports:
- React Native documentation
- Extensible for other documentation frameworks

### Styling
Modify CSS in `add_style_tag` sections for:
- Custom fonts and colors
- Different page layouts
- Code block formatting

### Content Filtering
Edit URL discovery logic to:
- Skip specific sections
- Focus on particular topics
- Add custom filtering rules

### Common Issues
- **Timeout errors**: Increase timeout values in the script
- **Missing dependencies**: Reinstall `playwright` and `PyPDF2`


## ⚖️ License

This tool is for personal and educational use. Please respect:
- Website terms of service
- Rate limiting guidelines
- Content ownership rights

Provided as-is for educational purposes. Scraped content belongs to respective copyright holders.
