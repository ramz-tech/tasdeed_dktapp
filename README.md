# tasdeed_dktapp
desktop application that automates the process of retrieving and extracting billing information for multiple matter accounts from an Oracle CRM website.


Workflow:

    User Input:

        The application should allow the user to upload an Excel sheet.

        The Excel file must contain a column named m_account, which lists the matter accounts.

    Pre-checks:

        Before starting, the app must ensure:

            The user's VPN is connected.

            The Oracle CRM website is accessible.

    Process per Matter Account: For each account in the m_account list:

        Use APIs and/or Playwright (browser automation library) to log in and fetch the latest PDF bill for the account.

        (The exact steps for extracting the PDF bill are demonstrated in the reference video — you will need to figure out how to automate these steps.)

    Data Extraction:

        After downloading the PDF, use the existing data extraction function (already provided) to extract the required information from the PDF.

    Post-processing:

        After extracting the data:

            Delete the PDF file to save disk space.

            Save the extracted data into a database for record-keeping.

    Data Output:

        For each Excel file the user uploads:

            Generate a separate CSV file containing all extracted data related to that upload.

            Allow the user to download the CSV file from the application.

Requirements:

    High Performance:
    The application must be optimized to handle large input files (potentially more than 1000 accounts) efficiently. Proper resource management (memory, disk usage, and processing threads) is critical.
    
    Reliability:
    If a PDF cannot be retrieved or processed for any account, the app should log the error and continue processing the remaining accounts without crashing.

    UI/UX:
    Provide clear status updates and progress indicators (e.g., how many accounts have been processed, success/failure notifications).

Notes:

    Database Storage: All extracted information should be stored in the database immediately after extraction.

    Resource Management: Efficiently delete temporary PDF files after extraction to prevent system slowdown.

    Dependencies: Use Playwright for web automation and any necessary libraries for Excel reading, PDF processing, and database operations.
