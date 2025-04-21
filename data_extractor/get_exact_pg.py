import asyncio
import base64
import datetime
import logging
from urllib.parse import urlparse, parse_qs
import subprocess
from playwright.async_api import async_playwright, TimeoutError

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
        account_no (str): Account number for search.
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

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        try:
            self.browser  = await self.playwright.chromium.launch(headless=True)
        except Exception:
            subprocess.run(["playwright", "install", "chromium"])
            self.browser  = await self.playwright.chromium.launch(headless=True)

        self.context = await self.browser.new_context(ignore_https_errors=True,
                                                      accept_downloads=True,
                                                      viewport={"width": 1280, "height": 720})
        self.page = await self.context.new_page()
        if self.cookies:
            await self.context.add_cookies(self.cookies)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def login(self) -> None:
        """Logs into the portal using the provided credentials."""
        login_url = f"{self.base_url}/Account/Login"
        try:
            await self.page.goto(login_url)
            await self.page.wait_for_selector("input#Username", state="visible", timeout=10000)
            await self.page.fill("input#Username", self.username)
            await self.page.fill("input#Password", self.password)
            await self.page.wait_for_selector("button.btn.btn-primary.btn-block", state="visible", timeout=10000)
            await self.page.click("button.btn.btn-primary.btn-block")
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            logger.info("Login successful.")
        except TimeoutError as e:
            logger.error("Timeout during login process.")
            raise PortalError("Timeout during login process.") from e
        except Exception as e:
            logger.error(f"Error during login: {e}")
            raise PortalError("Login failed.") from e

    async def search_by_text(self, account_no) -> (str, str):
        """
        Searches by account number text and returns the customer ID.

        Returns:
            str: The customer ID retrieved from the search.
        """
        search_url = f"{self.base_url}/api/SearchApi/SearchByText?text={account_no}"
        try:
            a, b = 1,2
            response = await self.context.request.get(search_url)
            search_json = await response.json()
            rp_data = search_json.get("Data", {}).get("Customers") or search_json.get("Data", {}).get("Sites")
            rp_type = "Customer" if search_json.get("Data", {}).get("Customers") else "Site"
            if not rp_data:
                raise PortalError("No customers or sites found in search response.")

            customer_id = rp_data[0].get("Id")
            if not customer_id:
                raise PortalError("Customer ID not found in search response.")

            logger.info(f"Customer ID from SearchByText: {customer_id}, Account No: {account_no}")
            return customer_id, rp_type
        except Exception as e:
            logger.error(f"Error in search_by_text: {e}")
            raise PortalError("Search by text failed.") from e

    async def search_by_id(self, customer_id: str, customer_type: str) -> dict:
        """
        Searches by customer ID and extracts parameters required for navigation.

        Returns:
            dict: A dictionary of parameters extracted from the API response.
        """
        url = f"{self.base_url}/api/SearchApi/SearchById?id={customer_id}&searchType={customer_type}"
        try:
            response = await self.context.request.get(url)
            data_json = await response.json()
            data = data_json.get("Data")
            if not data:
                raise PortalError("No data found in searchById response.")

            # Extract customer information
            customers = data.get("Customers", [])
            if not customers:
                raise PortalError("No customers found in SearchById response.")
            customer_info = customers[0]
            ca = customer_info.get("Id")
            ct = customer_info.get("CustomerType")

            # Extract contacts information
            contacts = data.get("Contacts", [])
            if not contacts:
                raise PortalError("No contacts found in SearchById response.")
            contact_info = contacts[0]
            p_val = contact_info.get("Id")
            st = contact_info.get("Context")

            # Extract sites information
            sites = data.get("Sites", [])
            if not sites:
                raise PortalError("No sites found in SearchById response.")
            site_info = sites[0]
            s = site_info.get("Id")
            ua = site_info.get("AccountId")
            pt = site_info.get("ProductType")

            extracted = {"p": p_val, "ca": ca, "s": s, "ua": ua, "pt": pt, "ct": ct, "st": st}
            logger.info(f"Extracted parameters: {extracted}")
            return extracted
        except Exception as e:
            logger.error(f"Error in search_by_id: {e}")
            raise PortalError("Search by ID failed.") from e

    async def create_navigation_url(self, params: dict) -> str:
        """
        Calls CreateNavigationUrl API using the extracted parameters and retrieves the 'r' value.

        Returns:
            str: The extracted 'r' parameter value.
        """
        nav_url = (
            f"{self.base_url}/Search/CreateNavigationUrl?"
            f"p={params['p']}&ca={params['ca']}&s={params['s']}&ua={params['ua']}&pt={params['pt']}&ct={params['ct']}&st={params['st']}"
        )
        try:
            response = await self.context.request.get(nav_url)
            nav_text = await response.text()
            logger.info(f"Navigation URL returned: {nav_text}")
            parsed = urlparse("http://dummy" + nav_text)
            qs = parse_qs(parsed.query)
            r_value_list = qs.get("r")
            if not r_value_list:
                raise PortalError("Parameter 'r' not found in navigation URL.")
            r_value = r_value_list[0].replace('"', '')
            logger.info(f"Extracted r value: {r_value}")
            return r_value
        except Exception as e:
            logger.error(f"Error in create_navigation_url: {e}")
            raise PortalError("Failed to create navigation URL.") from e

    async def navigate_to_documents_page(self, r_value: str) -> None:
        """
        Navigates to the documents page using the provided 'r' value.
        """
        documents_url = f"{self.base_url}//DOCUMENTS?r={r_value}"
        try:
            await self.page.goto(documents_url)
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            logger.info(f"Navigated to documents page: {documents_url}")
        except Exception as e:
            logger.error(f"Error navigating to documents page: {e}")
            raise PortalError("Navigation to documents page failed.") from e

    async def fetch_document_data(self) -> dict:
        """
        Fetches document page data from the Document API.

        Returns:
            dict: The JSON response of the document data.
        """
        js_script = """
        () => {
            return fetch("http://172.16.136.81/api/DocumentApi/GetDocumentPageData?categoryCode=DOCUMENT_CATEGORY&typeCode=DOCUMENT_TYPE", {
                headers: {
                  "Accept": "*/*",
                  "Accept-Language": "en-US,en;q=0.9",
                  "Connection": "keep-alive",
                  "Referer": document.location.href,
                  "Sec-GPC": "1",
                  "User-Agent": navigator.userAgent
                },
                credentials: "include"
            }).then(r => r.json());
        }
        """
        try:
            result = await self.page.evaluate(js_script)
            logger.info("Document API data fetched successfully.")
            return result
        except Exception as e:
            logger.error(f"Error fetching document data: {e}")
            raise PortalError("Fetching document data failed.") from e

    async def fetch_pdf_data(self, document_id: str) -> bytes:
        """
        Fetches a PDF file as binary data for a given document ID.

        Returns:
            bytes: The binary PDF data.
        """
        pdf_url = f"{self.base_url}/Documents/GetDocumentFile?documentId={document_id}&fileType=PDF&openInNewTab=true?"
        js_fetch_pdf = """
        (url) => {
            return fetch(url, {
                headers: {
                  "Accept": "*/*",
                  "Accept-Language": "en-US,en;q=0.9",
                  "Connection": "keep-alive",
                  "Referer": document.location.href,
                  "Sec-GPC": "1",
                  "User-Agent": navigator.userAgent
                },
                credentials: "include"
            })
            .then(r => r.arrayBuffer())
            .then(buffer => {
                let binary = '';
                let bytes = new Uint8Array(buffer);
                for (let i = 0; i < bytes.byteLength; i++) {
                    binary += String.fromCharCode(bytes[i]);
                }
                return btoa(binary);
            });
        }
        """
        try:
            base64_pdf = await self.page.evaluate(js_fetch_pdf, pdf_url)
            pdf_data = base64.b64decode(base64_pdf)
            logger.info("PDF data fetched successfully.")
            return pdf_data
        except Exception as e:
            logger.error(f"Error fetching PDF data: {e}")
            raise PortalError("Fetching PDF data failed.") from e

    async def save_pdf(self, pdf_data: bytes, filepath: str = 'output.pdf') -> None:
        """
        Saves the given binary PDF data to a file.

        Args:
            pdf_data (bytes): The binary PDF data.
            filepath (str): File path to save the PDF.
        """
        try:
            with open(filepath, 'wb') as f:
                f.write(pdf_data)
            logger.info(f"PDF saved as {filepath}.")
        except Exception as e:
            logger.error(f"Error saving PDF file: {e}")
            raise PortalError("Saving PDF file failed.") from e

    @staticmethod
    def is_in_current_month(date_str: str) -> bool:
        """
        Check if the provided date string (in "YYYY-MM-DDTHH:MM:SS" format) is in the current month.

        Args:
            date_str (str): Date string in ISO format.

        Returns:
            bool: True if the date is in the current month, False otherwise.
        """
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        except ValueError as e:
            raise ValueError("Date string does not match format 'YYYY-MM-DDTHH:MM:SS'") from e
        now = datetime.datetime.now()
        return (date_obj.year == now.year) and (date_obj.month == now.month)


