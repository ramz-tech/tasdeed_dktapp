import asyncio
from urllib.parse import urlparse, parse_qs

from playwright.async_api import async_playwright


USERNAME = "emzec"
PASSWORD = "emzec"
# Example: cookies = [{"name": "cookie_name", "value": "cookie_value", "domain": "172.16.136.81", "path": "/"}, ...]
cookies = []  # Insert cookie dictionaries if necessary


async def main():
    async with async_playwright() as p:
        # Launch the browser (set headless=False for debugging)
        browser = await p.chromium.launch(headless=True)
        # Create a browser context (set ignore_https_errors=True if needed)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        # ----- Step 1. Login to the portal -----
        login_url = "http://172.16.136.81/Account/Login"
        await page.goto(login_url)
        # Wait for username input to be visible and fill in credentials
        await page.wait_for_selector("input#Username", state="visible")
        await page.fill("input#Username", USERNAME)
        await page.fill("input#Password", PASSWORD)
        # Wait for the login button to be visible and click it
        await page.wait_for_selector("button.btn.btn-primary.btn-block", state="visible")
        await page.click("button.btn.btn-primary.btn-block")

        # Wait for network activity to settle (i.e. the login to finish)
        await page.wait_for_load_state("networkidle")

        # Optionally, add external cookies if you have them
        if cookies:
            await context.add_cookies(cookies)

        # ----- Step 2. Call SearchByText API -----
        search_text = "00527651"
        search_url = f"http://172.16.136.81/api/SearchApi/SearchByText?text={search_text}"
        search_response = await context.request.get(search_url)
        search_json = await search_response.json()

        # Extract Customer ID from the "Customers" array returned in "Data"
        customer_id = search_json["Data"]["Customers"][0]["Id"]
        print(f"Customer ID from SearchByText: {customer_id}")

        # ----- Step 3. Call SearchById API using the customer ID -----
        search_by_id_url = f"http://172.16.136.81/api/SearchApi/SearchById?id={customer_id}&searchType=Customer"
        search_by_id_response = await context.request.get(search_by_id_url)
        search_by_id_json = await search_by_id_response.json()
        data = search_by_id_json["Data"]

        # Extract IDs and extra parameters from the JSON response.
        # "ca": Customer ID (from Customers array)
        ca = data["Customers"][0]["Id"]

        # "p": Contact ID and its "Context" (we expect at least one Contact)
        if data["Contacts"]:
            p_val = data["Contacts"][0]["Id"]
            st = data["Contacts"][0]["Context"]  # Expected to be "Contact"
        else:
            print("No contacts found in the response.")
            return

        # "s" and "ua": site ID and its AccountId (from Sites array)
        if data["Sites"]:
            site = data["Sites"][0]
            s = site.get("Id")
            ua = site.get("AccountId")
            pt = site.get("ProductType")  # e.g., "POWER"
        else:
            print("No site data found in the response.")
            return

        # "ct": Customer Type (from Customers array, e.g. "COMPANY")
        ct = data["Customers"][0]["CustomerType"]

        print(f"Extracted values: p = {p_val}, ca = {ca}, s = {s}, ua = {ua}, pt = {pt}, ct = {ct}, st = {st}")

        # ----- Step 4. Call CreateNavigationUrl API -----
        nav_url = (
            f"http://172.16.136.81/Search/CreateNavigationUrl?"
            f"p={p_val}&ca={ca}&s={s}&ua={ua}&pt={pt}&ct={ct}&st={st}"
        )
        nav_response = await context.request.get(nav_url)
        nav_text = await nav_response.text()
        print(f"Navigation URL returned: {nav_text}")

        # Parse the returned URL to extract the "r" query parameter.
        # The returned string is assumed to be something like "/CONTACTS/CONTACTSUMMARY?r=someEncodedValue"
        parsed = urlparse("http://dummy" + nav_text)  # add dummy base to parse properly
        qs = parse_qs(parsed.query)
        r_value_list = qs.get("r")
        if not r_value_list:
            print("Error: 'r' parameter not found in navigation URL")
            return
        r_value = r_value_list[0]
        print(f"Extracted r value: {r_value}")

        # ----- Step 5. Navigate to the DOCUMENTS page using the r value -----
        documents_url = f"http://172.16.136.81//DOCUMENTS?r={r_value}"
        await page.goto(documents_url)
        # Wait for the page to fully load
        await page.wait_for_load_state("networkidle")
        print(f"Navigated to documents page: {documents_url}")
        html = await page.content()
        print(html)  # Print the HTML content of the body for debugging

        # ----- Step 6. Call GetDocumentPageData API -----
        doc_api_url = ("http://172.16.136.81/api/DocumentApi/GetDocumentPageData?"
                       "categoryCode=DOCUMENT_CATEGORY&typeCode=DOCUMENT_TYPE")
        doc_headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Referer": "http://172.16.136.81//CONTACTS/CONTACTSUMMARY?r=" + r_value,
            "Sec-GPC": "1",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        }

        current_cookies = await context.cookies()
        print("Current cookies:", current_cookies)
        await asyncio.sleep(5)  # Optional: wait for a second to ensure the request is completed
        doc_response = await context.request.get(doc_api_url)
        doc_json = await doc_response.json()

        # Print the final document API output
        print("Document Page Data response:")
        print(doc_json)

        # Close browser after completion
        await browser.close()


# Run the asynchronous main function
asyncio.run(main())
