from data_extractor.get_exact_pg import PortalClient
import asyncio

import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run(username: str , password: str, accounts_list: list[str]):
    # Instantiate PortalClient with credentials and account number.
    client = PortalClient(username=username, password=password, cookies=[])
    async with client:
        # Step 1: Login
        await client.login()

        for account_no in accounts_list:
            try:
                # Step 2: Search by text to get customer ID
                customer_id = await client.search_by_text(account_no)

                # Step 3: Search by ID to extract necessary parameters
                params = await client.search_by_id(customer_id)

                # Step 4: Create Navigation URL and extract r value
                r_value = await client.create_navigation_url(params)

                # Step 5: Navigate to the documents page
                await client.navigate_to_documents_page(r_value)

                # Step 6: Fetch document data from API
                document_data = await client.fetch_document_data()
                documents = document_data.get("Data", {}).get("Documents", [])
                if not documents:
                    logger.error("No documents found in document data.")
                    return

                # step 7: Handel the right document
                document = documents[-1]
                creation_date = document.get('CreationDate')
                if not creation_date:
                    logger.error("Creation date missing from document data.")
                    return

                try:
                    if not PortalClient.is_in_current_month(creation_date):
                        logger.info("Document is not from the current month. Aborting further PDF fetch.")
                        return
                except ValueError as e:
                    logger.error(f"Date format error: {e}")
                    return

                # Step 8: Fetch PDF data for the document and save it
                doc_id = document.get("Id")
                pdf_data = await client.fetch_pdf_data(document_id=doc_id)
                await client.save_pdf(pdf_data, filepath=f'{doc_id}.pdf')
                logger.info(f"PDF saved successfully for document ID {doc_id}.")
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                continue

