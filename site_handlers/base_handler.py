"""
Base Site Handler Abstract Class
Defines the interface that all site-specific handlers must implement
"""

from abc import ABC, abstractmethod
import re
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse


class BaseSiteHandler(ABC):
    """Abstract base class for site-specific documentation handlers"""
    
    def __init__(self):
        self.base_url = None
        self.docs_url = None
        self.site_name = None
        self.visited_urls = set()
        self.sections = []
    
    @abstractmethod
    async def get_all_doc_urls(self, page) -> List[Dict[str, Any]]:
        """
        Extract all documentation URLs from the site
        
        Args:
            page: Playwright page object
            
        Returns:
            List of dictionaries containing:
            - url: Full URL to the documentation page
            - title: Page title
            - section: Section name the page belongs to
            - filename: Generated filename for the PDF
            - path: Path where PDF will be saved
        """
        pass
    
    @abstractmethod
    def get_site_config(self) -> Dict[str, Any]:
        """
        Get site-specific configuration
        
        Returns:
            Dictionary containing:
            - base_url: Base URL of the site
            - docs_url: Starting URL for documentation
            - site_name: Human-readable site name
            - selectors: Site-specific CSS selectors
        """
        pass
    
    @abstractmethod
    async def handle_site_specific_content(self, page):
        """
        Handle any site-specific content processing
        This is called before PDF generation for each page
        
        Args:
            page: Playwright page object
        """
        pass
    
    
    async def generate_file_entry(self, url: str, title: str, section: str) -> Dict[str, Any]:
        """Generate a clean filename from URL"""
        path = urlparse(url).path

        filename = path.replace('/docs/', '').replace('/', '_').strip('_')
        if not filename:
            filename = "getting_started"
        
        # Clean filename
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        index = len(self.visited_urls) - 1
        pdf_filename = f"{index:03d}_{filename}.pdf"
        
        return {
            'title': title or filename.replace('_', ' ').title(),
            'url': url,
            'section': section,
            'filename': filename,
            'pdf_filename': pdf_filename,
        }
    
    def get_toc_title(self) -> str:
        """
        Get the title for the table of contents
        Can be overridden by specific handlers
        
        Returns:
            Title string for TOC
        """
        return f"{self.site_name} Documentation"
    
    def get_merged_pdf_name(self) -> str:
        """
        Get the filename for the merged PDF
        Can be overridden by specific handlers
        
        Returns:
            Filename for merged PDF
        """
        site_clean = self.site_name.replace(' ', '_')
        return f"{site_clean}_Documentation.pdf"
    
    