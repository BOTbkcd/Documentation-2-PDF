#!/usr/bin/env python3
"""
React Native Documentation Scraper using Playwright
Better PDF generation and more reliable scraping with PDF merging
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright
import re
from PyPDF2 import PdfMerger

class PlaywrightDocScraper:
    def __init__(self, output_dir="react_native_docs"):
        self.base_url = "https://reactnative.dev"
        self.docs_url = "https://reactnative.dev/docs/getting-started"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.individual_pdfs_dir = self.output_dir / "individual_pdfs"
        self.individual_pdfs_dir.mkdir(exist_ok=True)
        self.visited_urls = set()
        self.doc_metadata = [] 
        self.sections = []
        self.cached = False
    
    async def get_all_doc_urls(self, page):
        """Extract all documentation URLs from the sidebar navigation"""
        print("Extracting all documentation URLs...")
        
        await page.goto(self.docs_url)
        await page.wait_for_load_state('networkidle')
        
        # Wait for sidebar to load
        try:
            await page.wait_for_selector('.menu__list', timeout=10000)
        except Exception as e:
            print(f"Error waiting for sidebar: {e}")
            return []
        
        # First, expand all collapsible menu sections
        print("Expanding collapsible menu sections...")
        
        iterationCount = 0
        while iterationCount < 2:
            collapsible_items = await page.query_selector_all('.menu__list-item--collapsed .menu__list-item-collapsible a')
            print(f"Found {len(collapsible_items)} collapsible sections in iteration {iterationCount+1}")
            for i, item in enumerate(collapsible_items):
                try:
                    # Click to expand the section
                    await item.click()
                    # Wait a bit for the content to load
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    print(f"Error expanding section {i+1}: {e}")
                    continue
            
            iterationCount += 1

        # Wait for all expansions to complete
        await asyncio.sleep(1)
        print("All sections expanded, now extracting URLs...")
        
        # Get all links for each section in sidebar
        sections = await page.query_selector_all('.theme-doc-sidebar-item-category-level-1')
        for section in sections:
            section_title = await (await section.query_selector('> .menu__list-item-collapsible a')).text_content()
            self.sections.append(section_title)

            sidebar_links = await section.query_selector_all('> ul .menu__list-item > a')
            for link in sidebar_links:
                try:
                    href = await link.get_attribute('href')
                    page_title = await link.text_content()
                    if href and '/docs/' in href and href not in self.visited_urls:
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                        self.visited_urls.add(href)
                        await self.generate_file_entry(href, page_title, section_title)                        
                except Exception as e:
                    print(f"Error processing section: {e}")
                    continue
        
        print(f"Found {len(self.doc_metadata)} documentation URLs across {len(self.sections)} sections")
        return self.doc_metadata


    async def generate_file_entry(self, url, title, section):
        """Generate a clean filename from URL"""
        path = urlparse(url).path

        filename = path.replace('/docs/', '').replace('/', '_').strip('_')
        if not filename:
            filename = "getting_started"
        
        # Clean filename
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        index = len(self.doc_metadata)
        pdf_filename = f"{index:03d}_{filename}.pdf"
        pdf_path = self.individual_pdfs_dir / pdf_filename
        
        self.doc_metadata.append({
            'path': pdf_path,
            'title': title or filename.replace('_', ' ').title(),
            'url': url,
            'section': section,
            'filename': filename,
        })

    async def handle_tabs_and_lazy_loading(self, page):
        """Handle tabbed content and lazy loading issues"""
        try:
            print("Handling tabs and lazy loading...")
            
            try:
                tablists = await page.query_selector_all('[role="tablist"]')
                for tablist in tablists:
                    try:
                        # To load the default tab, first click its neighbor & then click the default tab again
                        active_button = await tablist.query_selector('[role="tab"][aria-selected="true"]')
                        neighbor_button = await tablist.query_selector('[role="tab"][aria-selected="false"]')
                        isVisible = await active_button.is_visible()
                        if isVisible:
                            await neighbor_button.click()
                            await asyncio.sleep(0.1)  # Wait for tab activation
                            await active_button.click()                        
                            await asyncio.sleep(0.1)  # Wait for tab activation
                    except Exception as e:
                        print(f"Error clicking tab: {e}")
                        continue
                
                infoBoxes = await page.query_selector_all('.alert--info summary')
                for box in infoBoxes:
                    try:
                        isVisible = await box.is_visible()
                        if isVisible:
                            await box.click()
                    except Exception as e:
                        print(f"Error clicking tab: {e}")
                        continue
            except Exception as e:
                print(f"Error handling tab buttons: {e}")
            
            # Wait for content to load after changes
            await asyncio.sleep(1)
            
            print("✓ Tab and lazy loading handling completed")
            
        except Exception as e:
            print(f"Error handling tabs and lazy loading: {e}")

    async def save_page_as_pdf(self, page, doc, index):
        """Save a single page as PDF using Playwright's built-in PDF generation"""
        try:

            if self.cached and os.path.exists(doc['path']):
                print("Found in cache")
                return
            
            # Navigate to the page
            await page.goto(doc['url'], wait_until='networkidle')
            
            # Wait for main content to load
            await page.wait_for_selector('article', timeout=10000)
            
            # Handle tabs and lazy loading before PDF generation
            await self.handle_tabs_and_lazy_loading(page)
            
            # Add a title page marker for better organization
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
            
            # Hide navigation and other elements that shouldn't be in PDF
            await page.add_style_tag(content="""
                nav, .navbar, .menu, header, footer, 
                .sidebar, .ad, .advertisement, .docsRating, 
                .social-share, .edit-page-link, .theme-back-to-top-button,
                .pagination-nav, .theme-toggle,
                .navbar__sidebar, .docusaurus-highlight-code-line {
                    display: none !important;
                }
                
                body {
                    font-size: 15px;
                }
                .main-wrapper {
                    padding-left: 0 !important;
                }
                
                .container {
                    max-width: none !important;
                }
                
                article {
                    max-width: 100% !important;
                    margin: 0 !important;
                }
                
                pre {
                    overflow: hidden !important;
                    word-wrap: break-word !important;
                    font-size: 0.85em !important;
                    line-height: 1.3 !important;
                }
                
                code {
                    word-wrap: break-word !important;
                    font-size: 0.9em !important;
                }
                
                /* Better table formatting */
                table {
                    font-size: 0.9em !important;
                    width: 100% !important;
                }
                
                /* Ensure images fit properly */
                img {
                    max-width: 100% !important;
                    height: auto !important;
                }
            """)
            
            # Wait a bit for styles to apply
            await asyncio.sleep(1)
            
            await page.pdf(
                path=str(doc['path']),
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
                # footer_template=f'''
                #     <div style="font-size: 10px; color: #666; width: 100%; text-align: center; margin: 0 15mm;">
                #         <span style="float: left;">React Native Documentation</span>
                #         <span style="float: right;>Page <span class="pageNumber"></span></span>
                #     </div>
                # '''
            )
            
            print(f"✓ Saved: {doc['filename']}")
            return True
            
        except Exception as e:
            print(f"✗ Error processing {doc['url']}: {e}")
            return False

    def create_table_of_contents(self):
        """Create a section-organized table of contents PDF"""
        print("Creating section-organized table of contents...")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>React Native Documentation - Table of Contents</title>
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
                <h1>React Native Documentation</h1>
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
        for section in self.sections:
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
        total_sections = len(self.sections)
        total_articles = len(self.doc_metadata)
        
        html_content += f"""
            </div>
            
            <div class="section-summary">
                <strong>Documentation Summary:</strong><br>
                📚 {total_sections} sections covering {total_articles} articles<br>
                🔗 Complete React Native documentation from reactnative.dev
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
                # footer_template=f'''
                #     <div style="font-size: 10px; color: #666; width: 100%; text-align: center; margin: 0 15mm;">
                #         <span style="float: left;">React Native Documentation - Table of Contents</span>
                #         <span style="float: right;>Page <span class="pageNumber"></span></span>
                #     </div>
                # '''
            )
            
            await toc_page.close()
            
            # Insert TOC at the beginning of our PDF list
            self.doc_metadata.insert(0, {
                'path': toc_path,
                'title': 'Table of Contents',
                'url': 'Table of Contents',
                'index': -1
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
                pdf_path = doc['path']
                if pdf_path.exists():
                    print(f"Adding: {pdf_path.name}")
                    merger.append(str(pdf_path))
                else:
                    print(f"Warning: {pdf_path} not found, skipping...")
            
            # Create the merged PDF
            merged_pdf_path = self.output_dir / f"React_Native_Documentation.pdf"
            merger.write(str(merged_pdf_path))
            merger.close()
            
            print(f"\n✅ Successfully created merged PDF: {merged_pdf_path}")
            print(f"📄 File size: {merged_pdf_path.stat().st_size / (1024*1024):.1f} MB")
            
            return merged_pdf_path
            
        except Exception as e:
            print(f"✗ Error merging PDFs: {e}")
            return None

    async def scrape_all_docs(self):
        print("Starting React Native Documentation Scraping...")
        print(f"Output directory: {self.output_dir.absolute()}")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set longer timeouts to handle slow connections
            page.set_default_timeout(120000)  # 2 minutes for all operations
            
            # Get all documentation URLs
            all_docs = await self.get_all_doc_urls(page)

            if not all_docs:
                print("No URLs found. Exiting...")
                await browser.close()
                return
            
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


async def main(cached):
    try:
        from playwright.async_api import async_playwright
        from PyPDF2 import PdfMerger
    except ImportError as e:
        print("Please install required packages:")
        print("pip install playwright PyPDF2")
        print("playwright install chromium")
        return
    
    scraper = PlaywrightDocScraper()
    
    try:
        scraper.cached = cached
        await scraper.scrape_all_docs()
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cached",
        action="store_true",  # This makes it a boolean flag
        help="Fetch only those documentation pages that are not present in cache"
    )
    args = parser.parse_args()

    cached = True if args.cached else False
    asyncio.run(main(cached))
