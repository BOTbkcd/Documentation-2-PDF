# Site Handlers Module

from .react_native import ReactNativeHandler
from .nextjs import NextJSHandler

# Registry of available site handlers
SITE_HANDLERS = {
    'react-native': ReactNativeHandler,
    'nextjs': NextJSHandler,
}

def get_handler(site_name):
    """Get a site handler by name"""
    site_name = site_name.lower().replace('_', '-')
    if site_name in SITE_HANDLERS:
        return SITE_HANDLERS[site_name]
    else:
        available = ', '.join(SITE_HANDLERS.keys())
        raise ValueError(f"Unknown site '{site_name}'. Available sites: {available}")

def list_available_sites():
    """List all available site handlers"""
    return list(SITE_HANDLERS.keys())
