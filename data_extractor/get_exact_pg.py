import asyncio
import base64
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
        search_text = "q72272"
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
        documents_url = f"http://172.16.136.81//DOCUMENTS?r={r_value.replace('"', '')}"
        await page.goto(documents_url)
        # Wait for the page to fully load
        await page.wait_for_load_state("networkidle")
        print(f"Navigated to documents page: {documents_url}")

        result = await page.evaluate("""() => {
            return fetch("http://172.16.136.81/api/DocumentApi/GetDocumentPageData?categoryCode=DOCUMENT_CATEGORY&typeCode=DOCUMENT_TYPE", {
                headers: {
                  "Accept": "*/*",
                  "Accept-Language": "en-US,en;q=0.9",
                  "Connection": "keep-alive",
                  "Referer": document.location.href, // leverage current location
                  "Sec-GPC": "1",
                  "User-Agent": navigator.userAgent
                },
                credentials: "include" // ensures cookies are sent
            }).then(r => r.json());
        }""")

        import datetime

        def is_in_current_month(date_str):
            """
            Check if the given date string (in "YYYY-MM-DDTHH:MM:SS" format) is in the current month.

            Parameters:
                date_str (str): A date string in the ISO format "YYYY-MM-DDTHH:MM:SS".

            Returns:
                bool: True if the date is in the same month and year as the current date, False otherwise.

            Raises:
                ValueError: If date_str does not match the expected format.
            """
            try:
                # Convert the string to a datetime object
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError as e:
                raise ValueError("Date string does not match format 'YYYY-MM-DDTHH:MM:SS'") from e

            # Get current date and time
            now = datetime.datetime.now()

            # Compare year and month
            return (date_obj.year == now.year) and (date_obj.month == now.month)
        # Print the final document API output
        print("Document Page Data response:")
        documents = result.get("Data", {}).get("Documents", [])
        print(result.get("Data", {}).get("Documents", []))
        print(documents[0])
        dict_doc = documents[-1]
        dowmloud = is_in_current_month(dict_doc['CreationDate'])
        if dowmloud:
            pass

        pdf_url = f"http://172.16.136.81/Documents/GetDocumentFile?documentId={dict_doc['Id']}&fileType=PDF&openInNewTab=true?"

        # Pass the URL as an argument to the page.evaluate function
        base64_pdf = await page.evaluate(
            """(url) => {
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
                     // Convert the ArrayBuffer to a binary string
                     let binary = '';
                     let bytes = new Uint8Array(buffer);
                     for (let i = 0; i < bytes.byteLength; i++) {
                         binary += String.fromCharCode(bytes[i]);
                     }
                     // Convert binary string to Base64
                     return btoa(binary);
                 });
             }""", pdf_url
        )

        # Decode the base64 string back to binary data in Python
        pdf_data = base64.b64decode(base64_pdf)

        # Save PDF to file
        with open('output.pdf', 'wb') as f:
            f.write(pdf_data)

        print("PDF saved as output.pdf")

        # Close browser after completion
        await browser.close()


# Run the asynchronous main function
asyncio.run(main())
