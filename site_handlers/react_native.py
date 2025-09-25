"""
React Native Documentation Site Handler
Handles scraping of React Native documentation from reactnative.dev
"""

import asyncio
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
from .base_handler import BaseSiteHandler
import re


class ReactNativeHandler(BaseSiteHandler):
    """Handler for React Native documentation site"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://reactnative.dev"
        self.docs_url = "https://reactnative.dev/docs/getting-started"
        self.site_name = "React Native"
    
    def get_site_config(self) -> Dict[str, Any]:
        """Get React Native site configuration"""
        return {
            'base_url': self.base_url,
            'docs_url': self.docs_url,
            'site_name': self.site_name,
            'selector': {
                'main_content': 'article'
            }
        }
    
    async def get_all_doc_urls(self, page) -> List[Dict[str, Any]]:
        """Extract all React Native documentation URLs"""
        print("Extracting all React Native documentation URLs...")
        
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
        
        doc_metadata = []
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

                        doc = await self.generate_file_entry(href, page_title, section_title)                        
                        doc_metadata.append(doc)
                except Exception as e:
                    print(f"Error processing section: {e}")
                    continue
        
        print(f"Found {len(doc_metadata)} documentation URLs across {len(self.sections)} sections")
        return doc_metadata
    
    async def handle_site_specific_content(self, page):
        """Handle React Native specific content (tabs, info boxes, etc.)"""
        try:
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
                print(f"Error handling interactive elements: {e}")
            
            # Wait for content to load after changes
            await asyncio.sleep(1)
            
            
        except Exception as e:
            print(f"Error handling React Native specific content: {e}")
    
    def get_css_overrides(self) -> str:
        """Get React Native specific CSS overrides for PDF generation"""
        return """
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
        """
    
    def get_toc_title(self) -> str:
        """Get React Native specific TOC title"""
        return "React Native Documentation"
    
    def get_merged_pdf_name(self) -> str:
        """Get React Native specific merged PDF name"""
        return "React_Native_Documentation.pdf"

    async def generate_file_entry(self, url: str, title: str, section: str) -> Dict[str, Any]:
        """Generate a clean filename from URL"""
        path = urlparse(url).path

        filename = path.replace('/docs/', '').replace('/', '_').strip('_')
        if not filename:
            filename = "getting_started"
        
        # Clean filename
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        filename = re.sub(r'_+', '_', filename)  # Remove multiple underscores

        index = len(self.visited_urls) - 1
        pdf_filename = f"{index:03d}_{filename}.pdf"
        
        return {
            'title': title or filename.replace('_', ' ').title(),
            'url': url,
            'section': section,
            'pdf_filename': pdf_filename,
        }
    