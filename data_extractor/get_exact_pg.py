import asyncio
import base64
import datetime
import logging
from urllib.parse import urlparse, parse_qs
import subprocess
from playwright.async_api import async_playwright, TimeoutError
from functools import lru_cache
from typing import Tuple, Dict, Optional, Union, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PortalError(Exception):
    """Custom exception for portal-related errors."""
    pass


class PortalClient:
    """
    A client to interact with a web portal for login, search, and document retrieval.

    Attributes:
        username (str): Portal username.
        password (str): Portal password.
        cookies (list): A list of cookie dictionaries (if needed).
        base_url (str): Base URL of the portal.
    """

    def __init__(self, username: str, password: str,
                 cookies: list = None, base_url: str = "http://172.16.136.81"):
        self.username = username
        self.password = password
        self.cookies = cookies if cookies is not None else []
        self.base_url = base_url
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._is_logged_in = False

    async def __aenter__(self):
        # Launch browser more efficiently
        self.playwright = await async_playwright().start()
        try:
            # Launch with optimized settings
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--disable-gpu', '--disable-dev-shm-usage', '--no-sandbox']
            )
        except Exception:
            # Install only if necessary
            subprocess.run(["playwright", "install", "chromium"])
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--disable-gpu', '--disable-dev-shm-usage', '--no-sandbox']
            )

        # Create context with optimized settings
        self.context = await self.browser.new_context(
            ignore_https_errors=True,
            accept_downloads=True,
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
        )

        if self.cookies:
            await self.context.add_cookies(self.cookies)

        # Create page once
        self.page = await self.context.new_page()

        # Disable unnecessary features
        await self.page.context.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Ensure proper cleanup
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def login(self, timeout: int = 10000) -> None:
        """
        Logs into the portal using the provided credentials.

        Args:
            timeout (int): Timeout for login operations in milliseconds
        """
        if self._is_logged_in:
            logger.info("Already logged in.")
            return

        login_url = f"{self.base_url}/Account/Login"
        try:
            # Navigate with proper waiting
            await self.page.goto(login_url, wait_until="domcontentloaded", timeout=timeout)

            # Fill credentials efficiently
            await asyncio.gather(
                self.page.wait_for_selector("input#Username", state="visible", timeout=timeout),
                self.page.wait_for_selector("input#Password", state="visible", timeout=timeout)
            )

            await asyncio.gather(
                self.page.fill("input#Username", self.username),
                self.page.fill("input#Password", self.password)
            )

            # Click login button and wait for navigation
            await self.page.wait_for_selector("button.btn.btn-primary.btn-block", state="visible", timeout=timeout)
            await self.page.click("button.btn.btn-primary.btn-block")
            await self.page.wait_for_load_state("networkidle", timeout=timeout)

            self._is_logged_in = True
            logger.info("Login successful.")
        except TimeoutError as e:
            logger.error("Timeout during login process.")
            raise PortalError(f"Login timeout after {timeout}ms") from e
        except Exception as e:
            logger.error(f"Error during login: {e}")
            raise PortalError(f"Login failed: {str(e)}") from e

    @lru_cache(maxsize=32)
    async def search_by_text(self, account_no: str) -> Tuple[str, str]:
        """
        Searches by account number text and returns the customer ID and type.
        Uses caching to avoid repetitive searches.

        Args:
            account_no (str): Account number to search for

        Returns:
            Tuple[str, str]: The customer ID and type retrieved from the search
        """
        search_url = f"{self.base_url}/api/SearchApi/SearchByText?text={account_no}"
        try:
            # Use more efficient request method
            response = await self.context.request.get(search_url, timeout=5000)

            if response.status != 200:
                raise PortalError(f"Search API returned status {response.status}")

            search_json = await response.json()

            # More efficient data extraction
            data = search_json.get("Data", {})
            rp_data = data.get("Customers") or data.get("Sites")
            rp_type = "Customer" if data.get("Customers") else "Site"

            if not rp_data:
                raise PortalError(f"No results found for account: {account_no}")

            customer_id = rp_data[0].get("Id")
            if not customer_id:
                raise PortalError("Customer ID not found in search response")

            logger.info(f"Found: ID={customer_id}, Type={rp_type}, Account={account_no}")
            return customer_id, rp_type
        except Exception as e:
            logger.error(f"Search by text failed: {e}")
            raise PortalError(f"Search by text failed: {str(e)}") from e

    async def search_by_id(self, customer_id: str, customer_type: str) -> Dict[str, Any]:
        """
        Searches by customer ID and extracts parameters required for navigation.

        Args:
            customer_id (str): Customer ID to search for
            customer_type (str): Type of customer (Customer or Site)

        Returns:
            Dict[str, Any]: Navigation parameters extracted from the response
        """
        url = f"{self.base_url}/api/SearchApi/SearchById?id={customer_id}&searchType={customer_type}"
        try:
            # More efficient request
            response = await self.context.request.get(url, timeout=5000)

            if response.status != 200:
                raise PortalError(f"SearchById API returned status {response.status}")

            data_json = await response.json()
            data = data_json.get("Data")

            if not data:
                raise PortalError("No data found in searchById response")

            # Extract all required parameters at once
            extract_params = {}

            # Extract customer information
            customers = data.get("Customers", [])
            if not customers:
                raise PortalError("No customers found in SearchById response")

            customer_info = customers[0]
            extract_params["ca"] = customer_info.get("Id")
            extract_params["ct"] = customer_info.get("CustomerType")

            # Extract contacts information
            contacts = data.get("Contacts", [])
            if not contacts:
                raise PortalError("No contacts found in SearchById response")

            contact_info = contacts[0]
            extract_params["p"] = contact_info.get("Id")
            extract_params["st"] = contact_info.get("Context")

            # Extract sites information
            sites = data.get("Sites", [])
            if not sites:
                raise PortalError("No sites found in SearchById response")

            site_info = sites[0]
            extract_params["s"] = site_info.get("Id")
            extract_params["ua"] = site_info.get("AccountId")
            extract_params["pt"] = site_info.get("ProductType")

            logger.info(f"Extracted parameters: {extract_params}")
            return extract_params
        except Exception as e:
            logger.error(f"Search by ID failed: {e}")
            raise PortalError(f"Search by ID failed: {str(e)}") from e

    async def create_navigation_url(self, params: Dict[str, Any]) -> str:
        """
        Creates navigation URL using the extracted parameters and retrieves the 'r' value.

        Args:
            params (Dict[str, Any]): Navigation parameters

        Returns:
            str: The extracted 'r' parameter value
        """
        # Build query string more efficiently
        query_parts = [f"{k}={v}" for k, v in params.items() if v is not None]
        nav_url = f"{self.base_url}/Search/CreateNavigationUrl?{'&'.join(query_parts)}"

        try:
            response = await self.context.request.get(nav_url, timeout=5000)

            if response.status != 200:
                raise PortalError(f"Navigation URL API returned status {response.status}")

            nav_text = await response.text()

            # More efficient URL parsing
            if not nav_text or "r=" not in nav_text:
                raise PortalError("Invalid navigation URL returned")

            # Parse just the r parameter directly
            r_start = nav_text.find("r=") + 2
            r_end = nav_text.find("&", r_start) if "&" in nav_text[r_start:] else len(nav_text)
            r_value = nav_text[r_start:r_end].replace('"', '')

            logger.info(f"Extracted r value: {r_value}")
            return r_value
        except Exception as e:
            logger.error(f"Failed to create navigation URL: {e}")
            raise PortalError(f"Failed to create navigation URL: {str(e)}") from e

    async def navigate_to_documents_page(self, r_value: str, timeout: int = 10000) -> None:
        """
        Navigates to the documents page using the provided 'r' value.

        Args:
            r_value (str): Navigation parameter value
            timeout (int): Timeout for navigation in milliseconds
        """
        documents_url = f"{self.base_url}/DOCUMENTS?r={r_value}"
        try:
            # More efficient navigation
            await self.page.goto(documents_url, wait_until="domcontentloaded", timeout=timeout)
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            logger.info(f"Navigated to documents page")
        except Exception as e:
            logger.error(f"Navigation to documents page failed: {e}")
            raise PortalError(f"Navigation to documents page failed: {str(e)}") from e

    async def fetch_document_data(self) -> Dict[str, Any]:
        """
        Fetches document page data from the Document API.

        Returns:
            Dict[str, Any]: The document data
        """
        # More efficient JS execution
        js_script = """
        async () => {
            try {
                const response = await fetch("http://172.16.136.81/api/DocumentApi/GetDocumentPageData?categoryCode=DOCUMENT_CATEGORY&typeCode=DOCUMENT_TYPE", {
                    headers: {
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Connection": "keep-alive",
                        "Referer": document.location.href,
                        "User-Agent": navigator.userAgent
                    },
                    credentials: "include"
                });

                if (!response.ok) {
                    throw new Error(`HTTP error: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                return {error: error.toString()};
            }
        }
        """
        try:
            result = await self.page.evaluate(js_script)

            if result.get("error"):
                raise PortalError(f"Document API error: {result['error']}")

            logger.info("Document API data fetched successfully")
            return result
        except Exception as e:
            logger.error(f"Fetching document data failed: {e}")
            raise PortalError(f"Fetching document data failed: {str(e)}") from e

    async def fetch_pdf_data(self, document_id: str) -> bytes:
        """
        Fetches a PDF file as binary data for a given document ID.

        Args:
            document_id (str): Document ID to fetch

        Returns:
            bytes: The binary PDF data
        """
        pdf_url = f"{self.base_url}/Documents/GetDocumentFile?documentId={document_id}&fileType=PDF&openInNewTab=true"

        # More efficient JS for PDF retrieval
        js_fetch_pdf = """
        async (url) => {
            try {
                const response = await fetch(url, {
                    headers: {
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Connection": "keep-alive",
                        "Referer": document.location.href,
                        "User-Agent": navigator.userAgent
                    },
                    credentials: "include"
                });

                if (!response.ok) {
                    throw new Error(`HTTP error: ${response.status}`);
                }

                const buffer = await response.arrayBuffer();
                const bytes = new Uint8Array(buffer);
                let binary = '';

                // Process in chunks for better memory usage
                const chunkSize = 1024;
                for (let i = 0; i < bytes.byteLength; i += chunkSize) {
                    const chunk = bytes.slice(i, Math.min(i + chunkSize, bytes.byteLength));
                    binary += String.fromCharCode.apply(null, chunk);
                }

                return btoa(binary);
            } catch (error) {
                return {error: error.toString()};
            }
        }
        """
        try:
            result = await self.page.evaluate(js_fetch_pdf, pdf_url)

            if isinstance(result, dict) and result.get("error"):
                raise PortalError(f"PDF fetch error: {result['error']}")

            pdf_data = base64.b64decode(result)
            logger.info(f"PDF data fetched successfully ({len(pdf_data)} bytes)")
            return pdf_data
        except Exception as e:
            logger.error(f"Fetching PDF data failed: {e}")
            raise PortalError(f"Fetching PDF data failed: {str(e)}") from e

    async def save_pdf(self, pdf_data: bytes, filepath: str = 'output.pdf') -> None:
        """
        Saves the given binary PDF data to a file.

        Args:
            pdf_data (bytes): The binary PDF data
            filepath (str): File path to save the PDF
        """
        try:
            # More efficient file writing
            with open(filepath, 'wb') as f:
                f.write(pdf_data)
            logger.info(f"PDF saved as {filepath} ({len(pdf_data)} bytes)")
        except Exception as e:
            logger.error(f"Saving PDF file failed: {e}")
            raise PortalError(f"Saving PDF file failed: {str(e)}") from e

    @staticmethod
    def is_in_current_month(date_str: str) -> bool:
        """
        Check if the provided date string is in the current month.

        Args:
            date_str (str): Date string in ISO format

        Returns:
            bool: True if the date is in the current month, False otherwise
        """
        try:
            # More efficient date parsing
            year_str, month_str = date_str.split('-')[:2]
            year = int(year_str)
            month = int(month_str)

            # Get current date only once
            now = datetime.datetime.now()
            return (year == now.year) and (month == now.month)
        except Exception as e:
            logger.error(f"Date parsing error: {e}")
            raise ValueError(f"Invalid date string format: {date_str}") from e

    # New utility methods to make processing more efficient

    async def get_document_by_account(self, account_no: str) -> bytes:
        """
        Convenience method to fetch a document by account number in one operation.

        Args:
            account_no (str): Account number to search for

        Returns:
            bytes: PDF document data
        """
        # Ensure we're logged in
        if not self._is_logged_in:
            await self.login()

        # Execute all search steps
        customer_id, customer_type = await self.search_by_text(account_no)
        search_params = await self.search_by_id(customer_id, customer_type)
        r_value = await self.create_navigation_url(search_params)
        await self.navigate_to_documents_page(r_value)

        # Get document data
        doc_data = await self.fetch_document_data()

        # Find most recent document
        documents = doc_data.get("Data", {}).get("Documents", [])
        if not documents:
            raise PortalError(f"No documents found for account {account_no}")

        # Sort by date
        documents.sort(key=lambda x: x.get("Date", ""), reverse=True)
        latest_doc = documents[0]

        # Fetch PDF
        pdf_data = await self.fetch_pdf_data(latest_doc.get("Id"))
        return pdf_data

    async def fetch_multiple_documents(self, account_numbers: list) -> dict:
        """
        Fetch documents for multiple accounts in parallel.

        Args:
            account_numbers (list): List of account numbers to fetch

        Returns:
            dict: Dictionary mapping account numbers to their PDF data
        """
        # Ensure we're logged in
        if not self._is_logged_in:
            await self.login()

        # Process in batches to avoid overloading
        batch_size = 3
        results = {}

        for i in range(0, len(account_numbers), batch_size):
            batch = account_numbers[i:i + batch_size]
            tasks = [self.get_document_by_account(account) for account in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for account, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to fetch document for {account}: {result}")
                    results[account] = None
                else:
                    results[account] = result

        return results