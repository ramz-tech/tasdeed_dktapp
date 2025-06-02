#!/usr/bin/env python3
"""
Tasdeed Extraction Dashboard - Web Server Entry Point
"""

import os
import sys
import logging

# Add the parent directory to the path so we can import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web.server import create_app

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("web_app.log"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Create and run the application
        app = create_app()
        
        # Get port from environment or use default
        port = int(os.environ.get('PORT', 8080))
        
        # Log startup message
        logger.info(f"Starting web server on port {port}")
        logger.info("Press Ctrl+C to stop the server")
        
        # Run the server
        import aiohttp.web
        aiohttp.web.run_app(app, host='0.0.0.0', port=port)
    
    except Exception as e:
        logger.error(f"Error starting web server: {e}", exc_info=True)
        sys.exit(1)