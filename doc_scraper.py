#!/usr/bin/env python3
import argparse
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from PyPDF2 import PdfMerger

from site_handlers import get_handler, list_available_sites


class DocumentationScraper:
    """Generic documentation scraper that works with multiple sites"""
    
    def __init__(self, site_handler, output_dir=None):
        self.site_handler = site_handler
        self.config = site_handler.get_site_config()
        
        # Set output directory
        if output_dir is None:
            site_name = self.config['site_name'].lower().replace(' ', '_')
            output_dir = f"{site_name}_docs"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.individual_pdfs_dir = self.output_dir / "individual_pdfs"
        self.individual_pdfs_dir.mkdir(exist_ok=True)
        
        self.doc_metadata = []
        self.cached = False

    async def scrape_all_docs(self):
        print(f"Starting {self.config['site_name']} Documentation Scraping...")
        print(f"Output directory: {self.output_dir.absolute()}")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set longer timeouts to handle slow connections
            page.set_default_timeout(120000)  # 2 minutes for all operations
            
            # Get all documentation URLs using the site handler
            all_docs = await self.site_handler.get_all_doc_urls(page)

            if not all_docs:
                print("No URLs found. Exiting...")
                await browser.close()
                return
            
            self.doc_metadata = all_docs
            
            print(f"\nStarting to scrape {len(all_docs)} pages...")
            
            successful = 0
            failed = 0
            
            for i, doc in enumerate(all_docs, 1):
                print(f"\n[{i}/{len(all_docs)}] Processing: {doc['url']}")
                
                if await self.save_page_as_pdf(page, doc, i-1):
                    successful += 1
                else:
                    failed += 1
            
            # Create table of contents
            await self.create_toc_pdf(browser)
            
            await browser.close()
            
            print(f"\n{'='*50}")
            print(f"Scraping completed!")
            print(f"Successful: {successful}")
            print(f"Failed: {failed}")
            print(f"Total: {len(all_docs)}")
            
            # Merge all PDFs into one
            merged_pdf = self.merge_pdfs()
            
            if merged_pdf:
                print(f"\n🎉 Complete documentation available at: {merged_pdf}")
    
    async def save_page_as_pdf(self, page, doc, index):
        """Save a single page as PDF"""
        try:
            if self.cached and os.path.exists(self.individual_pdfs_dir / doc['pdf_filename']):
                print("Found in cache")
                return True
            
            # Navigate to the page
            await page.goto(doc['url'], wait_until='networkidle')
            
            # Wait for main content to load
            selectors = self.config.get('selectors', {})
            main_content_selector = selectors.get('main_content', 'article')
            await page.wait_for_selector(main_content_selector, timeout=10000)
            
            # Handle site-specific content
            await self.site_handler.handle_site_specific_content(page)
            
            # Add title page
            await self.add_title_page(page, doc, index)
            
            # Apply site-specific CSS overrides
            if hasattr(self.site_handler, 'get_css_overrides'):
                css_overrides = self.site_handler.get_css_overrides()
                await page.add_style_tag(content=css_overrides)
            
            # Wait for styles to apply
            await asyncio.sleep(1)
            
            # Generate PDF
            await page.pdf(
                path=str(self.individual_pdfs_dir / doc['pdf_filename']),
                format='A4',
                margin={
                    'top': '15mm',
                    'bottom': '15mm',
                    'left': '10mm',
                    'right': '10mm'
                },
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=True,
                header_template='<div></div>', 
                footer_template='<div></div>',
            )
            
            print(f"✓ Saved: {doc['filename']}")
            return True
            
        except Exception as e:
            print(f"✗ Error processing {doc['url']}: {e}")
            return False
    
    async def add_title_page(self, page, doc, index):
        """Add a title page to the document"""
        title_script = f"""
            const titleDiv = document.createElement('div');
            titleDiv.style.cssText = `
                text-align: center;
                padding: 50px 20px 20px 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                border-bottom: 2px solid #0066cc;
                margin-bottom: 30px;
            `;
            titleDiv.innerHTML = `
                <h1 style="color: #0066cc; margin: 0; font-size: 2.5em;">
                    {index + 1}. {doc['title']}
                </h1>
                <p style="color: #666; margin: 10px 0 0 0; font-size: 1.1em;">
                    {doc['url']}
                </p>
            `;
            
            const article = document.querySelector('article');
            if (article) {{
                article.insertBefore(titleDiv, article.firstChild);
            }}
        """
        await page.evaluate(title_script)
    
    def create_table_of_contents(self):
        """Create a section-organized table of contents"""
        print("Creating section-organized table of contents...")
        
        site_name = self.config['site_name']
        toc_title = self.site_handler.get_toc_title()
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{toc_title} - Table of Contents</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 40px 20px;
                    color: #333;
                }}
                
                .header {{
                    text-align: center;
                    margin-bottom: 50px;
                    border-bottom: 3px solid #0066cc;
                    padding-bottom: 30px;
                }}
                
                .header h1 {{
                    color: #0066cc;
                    font-size: 3em;
                    margin: 0;
                    font-weight: 300;
                }}
                
                .header p {{
                    color: #666;
                    font-size: 1.2em;
                    margin: 20px 0 0 0;
                }}
                
                .section-header {{
                    background: linear-gradient(135deg, #0066cc, #004499);
                    color: white;
                    padding: 15px 20px;
                    margin: 30px 0 10px 0;
                    border-radius: 8px;
                    font-size: 1.3em;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    page-break-inside: avoid;
                    page-break-after: avoid;
                }}
                
                .section-header:first-of-type {{
                    margin-top: 0;
                }}
                
                .toc-entry {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 20px;
                    margin: 2px 0;
                    border-left: 4px solid #e3f2fd;
                    background-color: #fafafa;
                    border-radius: 0 6px 6px 0;
                    page-break-inside: avoid;
                    transition: all 0.2s ease;
                }}
                
                .toc-entry:hover {{
                    background-color: #e3f2fd;
                    border-left-color: #0066cc;
                }}
                
                .toc-title {{
                    flex-grow: 1;
                    font-weight: 500;
                    color: #0066cc;
                    font-size: 1.05em;
                }}
                
                .toc-page {{
                    font-weight: bold;
                    color: #666;
                    margin-left: 20px;
                    background-color: #0066cc;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 0.9em;
                }}
                
                .toc-url {{
                    font-size: 0.8em;
                    color: #999;
                    font-style: italic;
                    margin-top: 4px;
                    opacity: 0.8;
                }}
                
                .generation-info {{
                    margin-top: 50px;
                    padding-top: 30px;
                    border-top: 1px solid #eee;
                    font-size: 0.9em;
                    color: #666;
                    text-align: center;
                }}
                
                .section-summary {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 20px 0;
                    border-left: 4px solid #0066cc;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{toc_title}</h1>
                <p>Complete Documentation Guide</p>
            </div>
            
            <div class="toc">
        """
        
        # Group PDFs by section
        sections_dict = {}
        for doc in self.doc_metadata:
            section = doc['section']
            if section not in sections_dict:
                sections_dict[section] = []
            sections_dict[section].append(doc)
        
        article_counter = 1
        for section in self.site_handler.sections:
            if section in sections_dict:
                docs = sections_dict[section]
                
                # Add section header
                html_content += f"""
                    <div class="section-header">{section}</div>
                """
                
                # Add articles in this section
                for doc in docs:
                    html_content += f"""
                        <div class="toc-entry">
                            <div>
                                <div class="toc-title">{article_counter}. {doc['title']}</div>
                                <div class="toc-url">{doc['url']}</div>
                            </div>
                        </div>
                    """
                    article_counter += 1
        
        # Add summary information
        total_sections = len(self.site_handler.sections)
        total_articles = len(self.doc_metadata)
        
        html_content += f"""
            </div>
            
            <div class="section-summary">
                <strong>Documentation Summary:</strong><br>
                📚 {total_sections} sections covering {total_articles} articles<br>
                🔗 Complete {site_name} documentation
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    async def create_toc_pdf(self, browser):
        """Create table of contents as a separate PDF"""
        try:
            toc_html = self.create_table_of_contents()
            toc_path = self.individual_pdfs_dir / "000_table_of_contents.pdf"
            
            # Create a new page for TOC
            toc_page = await browser.new_page()
            await toc_page.set_content(toc_html)
            
            await toc_page.pdf(
                path=str(toc_path),
                format='A4',
                margin={
                    'top': '15mm',
                    'bottom': '15mm',
                    'left': '10mm',
                    'right': '10mm'
                },
                print_background=True,
                display_header_footer=True,
                header_template='<div></div>',
                footer_template='<div></div>',
            )
            
            await toc_page.close()
            
            # Insert TOC at the beginning of our PDF list
            self.doc_metadata.insert(0, {
                'title': 'Table of Contents',
                'url': 'Table of Contents',
                'pdf_filename': "000_table_of_contents.pdf",
            })
            
            print("✓ Created table of contents")
            return True
            
        except Exception as e:
            print(f"✗ Error creating table of contents: {e}")
            return False
    
    def merge_pdfs(self):
        """Merge all individual PDFs into one master PDF"""
        print(f"\nMerging {len(self.doc_metadata)} PDF files...")
        
        try:
            merger = PdfMerger()
            
            for doc in self.doc_metadata:
                pdf_path = self.individual_pdfs_dir / doc['pdf_filename']
                if pdf_path.exists():
                    print(f"Adding: {pdf_path.name}")
                    merger.append(str(pdf_path))
                else:
                    print(f"Warning: {pdf_path} not found, skipping...")
            
            # Create the merged PDF
            merged_pdf_name = self.site_handler.get_merged_pdf_name()
            merged_pdf_path = self.output_dir / merged_pdf_name
            merger.write(str(merged_pdf_path))
            merger.close()
            
            print(f"\n✅ Successfully created merged PDF: {merged_pdf_path}")
            print(f"📄 File size: {merged_pdf_path.stat().st_size / (1024*1024):.1f} MB")
            
            return merged_pdf_path
            
        except Exception as e:
            print(f"✗ Error merging PDFs: {e}")
            return None


async def main():
    """Main function with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Generic Documentation Scraper - Convert documentation sites to PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available sites:
  {', '.join(list_available_sites())}

Examples:
  python doc_scraper.py --site react-native
  python doc_scraper.py --site react-native --output my_docs --cached
        """
    )
    
    parser.add_argument(
        "--site", "-s",
        help="Documentation site to scrape"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output directory (default: auto-generated based on site name)"
    )
    
    parser.add_argument(
        "--cached",
        action="store_true",
        help="Skip pages that already exist in cache"
    )
    
    parser.add_argument(
        "--list-sites",
        action="store_true",
        help="List all available documentation sites"
    )
    
    args = parser.parse_args()
    
    if args.list_sites:
        print("Available documentation sites:")
        for site in list_available_sites():
            print(f"  - {site}")
        return
    
    if not args.site:
        parser.error("--site is required unless using --list-sites")
    
    try:
        # Check dependencies
        from playwright.async_api import async_playwright
        from PyPDF2 import PdfMerger
    except ImportError as e:
        print("Please install required packages:")
        print("pip install playwright PyPDF2")
        print("playwright install chromium")
        return
    
    try:
        # Get the site handler
        handler_class = get_handler(args.site)
        site_handler = handler_class()
        
        # Create scraper
        scraper = DocumentationScraper(site_handler, args.output)
        scraper.cached = args.cached
        
        # Start scraping
        await scraper.scrape_all_docs()
        
    except ValueError as e:
        print(f"Error: {e}")
        return
    except Exception as e:
        print(f"An error occurred: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())
