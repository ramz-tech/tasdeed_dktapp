import time

from playwright.sync_api import sync_playwright

USERNAME = "emzec"
PASSWORD = "emzec"

r = "YzH3JukRfPchf31k2aA3nZRDsvL4O%252BTR5gC1o8iBA9aL9vRlgtqwrjIf6rIRBJ3FQsZojHtD5h%252Fv%252Bb9BPN0MQZyHlCqIKxal%252FhfMHID%252FbNIjzedVCqd2mJYwEnlbmFrCzVvqR7KIny6WQfyQyTLjUnHrP7NmXoh3WF7ell5zxoS8sOHooO8Wv3%252B%252B%252Bnmj08rR"
def fetch_document_page_data():
    with sync_playwright() as p:
        # 1. Launch the browser and create a fresh context (for session storage).
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # 2. Go to login page and log in.
        page.goto("http://172.16.136.81/Account/Login")
        page.wait_for_selector("input#Username", state="visible")
        page.fill("input#Username", USERNAME)
        page.fill("input#Password", PASSWORD)

        # If there's a 'Login' button with these classes
        page.wait_for_selector("button.btn.btn-primary.btn-block", state="visible")
        page.click("button.btn.btn-primary.btn-block")

        # Wait for the page to fully load after login
        page.wait_for_load_state("networkidle")

        # 3. Navigate to the Documents page (optional if needed).
        page.goto(f"http://172.16.136.81/DOCUMENTS?r={r}")

        # Log all network requests
        page.on("request", lambda request: print(f"Request: {request.method} {request.url}"))

        # Log all network responses
        page.on("response", lambda response: print(f"Response: {response.status} {response.url}"))

        page.wait_for_load_state("networkidle")

        # 4. Reuse the same session to call the API endpoint.
        response = context.request.get(
            "http://172.16.136.81/api/DocumentApi/GetDocumentPageData?categoryCode=DOCUMENT_CATEGORY&typeCode=DOCUMENT_TYPE"
        )
        time.sleep(30)
        # 5. Print status, check success, and print the JSON response.
        print("Status:", response.status)       # e.g. 200
        print("OK?   :", response.ok)           # True if 2xx
        data = response.json()
        print("Response JSON:", data)

        # 6. Close browser
        browser.close()

if __name__ == "__main__":
    fetch_document_page_data()
