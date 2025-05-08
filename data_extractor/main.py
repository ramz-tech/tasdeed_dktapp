from data_extractor.get_exact_pg import PortalClient
import asyncio
from data_transform.core_utils import extract_pdf_data, save_text_to_csv, generate_csv_from_docs, delete_pdf
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_user(user_type):
    """
    Returns the username and password based on the user type.

    Args:
        user_type (str): The type of user (e.g., "MAZOON", "MAJAN", "TANVEER", "MUSCAT").

    Returns:
        tuple: A tuple containing the username and password.
    """
    users = {
        "MAZOON": {
            "username": "emzec",
            "password": "emzec"
        },
        "MAJAN": {
            "username": "oneic_mjec",
            "password": "oman1234"
        },
        "TANVEER": {
            "username": "oneic",
            "password": "123456"
        },
        "MUSCAT": {
            "username": "ONIEC1",
            "password": "ONIEC1"
        }
    }
    if user_type in users:
        return users[user_type.upper()]["username"], users[user_type.upper()]["password"]
    else:
        logger.error(f"User type '{user_type}' not recognized. Defaulting to MUSCAT.")
        return users["MUSCAT"]["username"], users["MUSCAT"]["password"]




async def main(user_type: str, accounts_list: list[str], output_directory: str):
    """
    Main function to handle the workflow of fetching and processing documents.

    Args:
        user_type (str): The user_type for authentication.
        accounts_list (list[str]): List of account numbers to process.
        output_directory (str): Directory to save the output files.
    """
    # Initialize the PortalClient with the provided username and password
    username, password = get_user(user_type)
    client = PortalClient(username=username, password=password, cookies=[])
    async with client:
        # Step 1: Login
        await client.login()

        for account_no in accounts_list:
            logger.info(f"Processing account number: {account_no}")
            try:
                # Step 2: Search by text to get customer ID
                customer_id, c_type = await client.search_by_text(account_no)

                # Step 3: Search by ID to extract necessary parameters
                params = await client.search_by_id(customer_id, c_type)

                # Step 4: Create Navigation URL and extract r value
                r_value = await client.create_navigation_url(params)

                # Step 5: Navigate to the documents page
                await client.navigate_to_documents_page(r_value)

                # Step 6: Fetch document data from API
                document_data = await client.fetch_document_data()
                documents = document_data.get("Data", {}).get("Documents", [])
                if not documents:
                    logger.error("No documents found in document data.")
                    # return

                # step 7: Handel the right document
                document = documents[-1]
                creation_date = document.get('CreationDate')
                if not creation_date:
                    logger.error("Creation date missing from document data.")
                    # return

                try:
                    if not PortalClient.is_in_current_month(creation_date):
                        logger.info("Document is not from the current month. Aborting further PDF fetch.")
                        # return
                except ValueError as e:
                    logger.error(f"Date format error: {e}")
                    # return

                # Step 8: Fetch PDF data for the document and save it
                doc_id = document.get("Id")
                pdf_data = await client.fetch_pdf_data(document_id=doc_id)
                await client.save_pdf(pdf_data, filepath=f'./{doc_id}.pdf')
                logger.info(f"PDF saved successfully for document ID {doc_id}.")


                # Step 9: Extract text from the PDF
                extracted_data =  extract_pdf_data(f'./{doc_id}.pdf')

                # Step 10: Save extracted text to CSV TODO: here we need to insert the data to the file if it is already exist
                save_text_to_csv(output_directory, extracted_data)
                logger.info(f"Data saved successfully for account number {account_no}.")
                delete_pdf(f'./{doc_id}.pdf')
                logger.info(f"PDF deleted successfully for document ID {doc_id}.")





            except Exception as e:
                logger.error(f"An error occurred: {e}")
                continue


if __name__ == "__main__":
    # Example usage
    import pandas as pd
    import time

    # Start the timer
    start_time = time.time()
    # Read the Excel file to get the list of account numbers
    df = pd.read_excel("/home/x/Desktop/tasdeed-projects_all/tasdeed_dktapp/NOORA-MAJAN 10-2024(1).xlsx", dtype={"ACCOUNTNO":str})  # Replace with the actual file path
    accounts_list = df["ACCOUNTNO"].astype(str).tolist()
    print(accounts_list)
    # Replace with the actual column name
    # For demonstration, using a hardcoded list of account numbers

    user_type = "MAZOON"  # Replace with the desired user type
    # accounts_list = ["02136715", "00118494"]  # Replace with actual account numbers
    output_directory = "test_output"  # Replace with the desired output directory

    # Run the main function
    asyncio.run(main(user_type, accounts_list, output_directory))
    end_time = time.time()

    # Calculate and print the elapsed time
    elapsed_time = end_time - start_time
    print("start time:", start_time)
    print("end time:", end_time)
    print(f"Execution time: {elapsed_time:.2f} seconds")