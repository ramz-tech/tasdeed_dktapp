import os
import uuid
import json
import logging
import asyncio
import tempfile
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional

import aiohttp
from aiohttp import web
import aiohttp_jinja2
import jinja2
from aiohttp.web import WebSocketResponse

# Import the extraction functionality
from data_extractor.get_exact_pg import PortalClient
from data_transform.core_utils import extract_pdf_data, save_text_to_xlsx, delete_pdf, _dummy_data

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

# Global storage for active tasks and their WebSocket connections
active_tasks = {}


class ExtractionTask:
    """Class to manage an extraction task and its state"""

    def __init__(self, task_id: str, user_type: str, accounts_list: List[str], output_directory: str):
        self.task_id = task_id
        self.user_type = user_type
        self.accounts_list = accounts_list
        self.output_directory = output_directory
        self.pdf_folder = os.path.join(tempfile.gettempdir(), f"pdf_temp_{task_id}")
        self.is_running = False
        self.is_cancelled = False
        self.connections = []  # WebSocket connections
        self.success_count = 0
        self.fail_count = 0
        self.current_progress = 0
        self.total_accounts = len(accounts_list)

        # Create output and temp directories
        os.makedirs(self.output_directory, exist_ok=True)
        os.makedirs(self.pdf_folder, exist_ok=True)

    async def start(self):
        """Start the extraction process"""
        if self.is_running:
            return

        self.is_running = True
        try:
            await self.process_accounts()
        except Exception as e:
            logger.error(f"Error in extraction task: {e}", exc_info=True)
            await self.broadcast({
                "type": "error",
                "message": str(e)
            })
        finally:
            self.is_running = False
            self.cleanup()

    async def process_accounts(self):
        """Process all accounts in the list"""
        try:
            username, password = get_user(self.user_type)
            client = PortalClient(username=username, password=password, cookies=[])
            # Use a task-specific output filename to avoid conflicts between concurrent tasks
            output_filename = f"output_{self.task_id}.csv"
            output_file = os.path.join(self.output_directory, output_filename)

            async with client:
                await self.broadcast({
                    "type": "progress",
                    "current": 0,
                    "total": self.total_accounts,
                    "message": "⏳ Processing..."
                })

                await client.login()

                for i, account_no in enumerate(self.accounts_list, 1):
                    if self.is_cancelled:
                        logger.info(f"Task {self.task_id} was cancelled")
                        break

                    try:
                        await self._process_account(client, account_no, i)
                    except Exception as e:
                        logger.error(f"Error processing account {account_no}: {e}", exc_info=True)
                        self.fail_count += 1
                        await self.broadcast({
                            "type": "progress",
                            "current": i,
                            "total": self.total_accounts,
                            "message": f"❌ Failed to process account: {account_no}"
                        })
                        await self.broadcast({
                            "type": "stats",
                            "success": self.success_count,
                            "failed": self.fail_count,
                            "total": self.total_accounts
                        })

                # Finalize the output
                if not self.is_cancelled:
                    output_file = await self._finalize_output(output_file)
                    await self.broadcast({
                        "type": "complete",
                        "success": self.success_count,
                        "failed": self.fail_count,
                        "total": self.total_accounts,
                        "output_file": output_file
                    })

                    # Clean up the task from active_tasks
                    if self.task_id in active_tasks:
                        del active_tasks[self.task_id]
                        logger.info(f"Removed completed task {self.task_id} from active_tasks")

        except Exception as e:
            logger.error(f"Error in process_accounts: {e}", exc_info=True)
            await self.broadcast({
                "type": "error",
                "message": str(e)
            })

    async def _process_account(self, client: PortalClient, account_no: str, current_index: int):
        """Process a single account"""
        try:
            # Update progress
            await self.broadcast({
                "type": "progress",
                "current": current_index,
                "total": self.total_accounts,
                "message": f"⏳ Processing account: {account_no}"
            })

            # Step 1: Search by text to get customer ID
            try:
                customer_id, customer_type = await client.search_by_text(account_no)
            except Exception as e:
                logger.error(f"Error searching for account {account_no}: {e}")
                await self.broadcast({
                    "type": "log",
                    "message": f"❌ Failed to search for account: {account_no}",
                    "level": "error"
                })
                # Use the task-specific output filename
                output_filename = f"output_{self.task_id}.csv"
                save_text_to_xlsx(self.output_directory, _dummy_data(account_no), output_filename)
                self.fail_count += 1
                return

            # Step 2: Search by ID to get parameters
            try:
                params = await client.search_by_id(customer_id, customer_type)
            except Exception as e:
                logger.error(f"Error getting details for account {account_no}: {e}")
                await self.broadcast({
                    "type": "log",
                    "message": f"❌ Failed to get details for account: {account_no}",
                    "level": "error"
                })
                # Use the task-specific output filename
                output_filename = f"output_{self.task_id}.csv"
                save_text_to_xlsx(self.output_directory, _dummy_data(account_no), output_filename)
                self.fail_count += 1
                return

            # Step 3: Navigate to documents page
            try:
                r_value = await client.create_navigation_url(params)
                await client.navigate_to_documents_page(r_value)
            except Exception as e:
                logger.error(f"Error navigating to documents for account {account_no}: {e}")
                await self.broadcast({
                    "type": "log",
                    "message": f"❌ Failed to navigate to documents for account: {account_no}",
                    "level": "error"
                })
                # Use the task-specific output filename
                output_filename = f"output_{self.task_id}.csv"
                save_text_to_xlsx(self.output_directory, _dummy_data(account_no), output_filename)
                self.fail_count += 1
                return

            # Step 4: Fetch document data
            try:
                document_data = await client.fetch_document_data()
                documents = document_data.get("Data", {}).get("Documents", [])
            except Exception as e:
                logger.error(f"Error fetching documents for account {account_no}: {e}")
                await self.broadcast({
                    "type": "log",
                    "message": f"❌ Failed to fetch documents for account: {account_no}",
                    "level": "error"
                })
                # Use the task-specific output filename
                output_filename = f"output_{self.task_id}.csv"
                save_text_to_xlsx(self.output_directory, _dummy_data(account_no), output_filename)
                self.fail_count += 1
                return

            # Check if documents exist
            if not documents:
                await self.broadcast({
                    "type": "log",
                    "message": f"⚠️ No bill found for account: {account_no}",
                    "level": "warning"
                })
                # Use the task-specific output filename
                output_filename = f"output_{self.task_id}.csv"
                save_text_to_xlsx(self.output_directory, _dummy_data(account_no), output_filename)
                self.fail_count += 1
                return

            # Get the latest document
            document = documents[-1]
            creation_date = document.get("CreationDate")

            # Check if document is from current month
            if not creation_date or not PortalClient.is_in_current_month(creation_date):
                await self.broadcast({
                    "type": "log",
                    "message": f"ℹ️ Old bill skipped for account: {account_no}",
                    "level": "info"
                })
                # Use the task-specific output filename
                output_filename = f"output_{self.task_id}.csv"
                save_text_to_xlsx(self.output_directory, _dummy_data(account_no), output_filename)
                self.fail_count += 1
                return

            # Step 5: Download and process PDF
            doc_id = document.get("Id")
            pdf_path = os.path.join(self.pdf_folder, f"{doc_id}.pdf")

            try:
                # Fetch and save PDF
                pdf_data = await client.fetch_pdf_data(document_id=doc_id)
                await client.save_pdf(pdf_data, filepath=pdf_path)

                # Extract data from PDF
                extracted_data = extract_pdf_data(pdf_path)
                # Use the task-specific output filename
                output_filename = f"output_{self.task_id}.csv"
                save_text_to_xlsx(self.output_directory, extracted_data, output_filename)

                # Delete PDF to save space
                delete_pdf(pdf_path)

                # Update success count and broadcast progress
                self.success_count += 1
                await self.broadcast({
                    "type": "progress",
                    "current": current_index,
                    "total": self.total_accounts,
                    "message": f"✅ Success: {account_no}"
                })

                await self.broadcast({
                    "type": "stats",
                    "success": self.success_count,
                    "failed": self.fail_count,
                    "total": self.total_accounts
                })

            except Exception as e:
                logger.error(f"Error processing PDF for account {account_no}: {e}")
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

                await self.broadcast({
                    "type": "log",
                    "message": f"❌ Failed to process PDF for account: {account_no}",
                    "level": "error"
                })

                # Use the task-specific output filename
                output_filename = f"output_{self.task_id}.csv"
                save_text_to_xlsx(self.output_directory, _dummy_data(account_no), output_filename)
                self.fail_count += 1

        except Exception as e:
            logger.error(f"Unexpected error processing account {account_no}: {e}", exc_info=True)
            self.fail_count += 1
            await self.broadcast({
                "type": "log",
                "message": f"❌ Unexpected error for account: {account_no}",
                "level": "error"
            })

    async def _finalize_output(self, output_file: str) -> str:
        """Finalize the output file and return the path to the renamed file"""
        try:
            # Generate a filename with the current month and year
            now = datetime.now()
            # Use #m-%Y format for Windows, %-m-%Y for other platforms
            month_format = "#m-%Y" if os.name == "nt" else "%-m-%Y"
            month_year = now.strftime(month_format)
            renamed = os.path.join(self.output_directory, f"{self.user_type.upper()}_{month_year}.csv")

            # Rename the output file
            if os.path.exists(output_file):
                if os.path.exists(renamed):
                    os.remove(renamed)  # Remove existing file if it exists
                os.rename(output_file, renamed)
                logger.info(f"Renamed output file to {renamed}")
                await self.broadcast({
                    "type": "log",
                    "message": f"📂 Output file renamed to: {os.path.basename(renamed)}",
                    "level": "info"
                })
            else:
                logger.warning(f"Output file {output_file} does not exist, cannot rename")
                await self.broadcast({
                    "type": "log",
                    "message": f"⚠️ Output file not found: {output_file}",
                    "level": "warning"
                })

            return renamed

        except Exception as e:
            logger.error(f"Error finalizing output: {e}", exc_info=True)
            await self.broadcast({
                "type": "log",
                "message": f"⚠️ Error finalizing output: {str(e)}",
                "level": "warning"
            })
            return output_file

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected WebSocket clients"""
        if not self.connections:
            return

        data = json.dumps(message)
        for ws in self.connections[:]:
            if not ws.closed:
                await ws.send_str(data)
            else:
                self.connections.remove(ws)

    def add_connection(self, ws: WebSocketResponse):
        """Add a WebSocket connection"""
        if ws not in self.connections:
            self.connections.append(ws)

    def remove_connection(self, ws: WebSocketResponse):
        """Remove a WebSocket connection"""
        if ws in self.connections:
            self.connections.remove(ws)

    def cancel(self):
        """Cancel the extraction process"""
        self.is_cancelled = True

    def cleanup(self):
        """Clean up temporary files"""
        try:
            # Clean up PDF folder
            if os.path.exists(self.pdf_folder):
                for file in os.listdir(self.pdf_folder):
                    try:
                        os.remove(os.path.join(self.pdf_folder, file))
                    except Exception as e:
                        logger.warning(f"Error removing temp file: {e}")

                try:
                    os.rmdir(self.pdf_folder)
                except Exception as e:
                    logger.warning(f"Error removing temp directory: {e}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)


def get_user(user_type: str):
    """Get username and password for the specified user type"""
    users = {
        "MAZOON": {"username": "emzec", "password": "emzec"},
        "MAJAN": {"username": "oneic_mjec", "password": "oman1234"},
        "TANVEER": {"username": "oneic", "password": "123456"},
        "MUSCAT": {"username": "ONIEC1", "password": "ONIEC1"}
    }
    user_data = users.get(user_type.upper(), users["MUSCAT"])
    return user_data["username"], user_data["password"]


async def index(request):
    """Render the index page"""
    return aiohttp_jinja2.render_template('index.html', request, {})


async def upload_file(request):
    """Handle file upload and start extraction process"""
    try:
        data = await request.post()

        # Get the uploaded file
        file_field = data.get('file')
        if not file_field:
            return web.json_response({"error": "No file uploaded"}, status=400)

        # Save the file temporarily with the correct extension
        file_ext = os.path.splitext(file_field.filename)[1].lower() or '.xlsx'
        temp_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}{file_ext}")
        with open(temp_file, 'wb') as f:
            f.write(file_field.file.read())

        # Get output directory
        output_dir = data.get('output_dir')
        if not output_dir:
            return web.json_response({"error": "Output directory is required"}, status=400)

        # Convert to absolute path if needed
        if not os.path.isabs(output_dir):
            output_dir = os.path.abspath(output_dir)

        # Read the Excel file
        try:
            df = pd.read_excel(temp_file, dtype={"ACCOUNTNO": str}) if temp_file.endswith(".xlsx") else pd.read_csv(temp_file, dtype={"ACCOUNTNO": str})
        except Exception as e:
            logger.error(f"Error reading file: {e}", exc_info=True)
            return web.json_response({"error": f"Error reading file: {str(e)}"}, status=400)

        # Check for required columns
        if "ACCOUNTNO" not in df.columns or "SUBTYPE" not in df.columns:
            return web.json_response({"error": "File must contain ACCOUNTNO and SUBTYPE columns"}, status=400)

        # Get user type
        subtypes = df["SUBTYPE"].dropna().unique()
        if len(subtypes) != 1:
            return web.json_response({"error": "Only one user SUBTYPE should exist in the file"}, status=400)

        user_type = subtypes[0]

        # Get account list
        accounts_list = [str(acc) for acc in df.get("ACCOUNTNO", []) if pd.notna(acc)]
        if len(accounts_list) == 0:
            return web.json_response({"error": "No valid accounts found in the ACCOUNTNO column"}, status=400)

        # Create a task ID
        task_id = str(uuid.uuid4())

        # Create and start the extraction task
        task = ExtractionTask(task_id, user_type, accounts_list, output_dir)
        active_tasks[task_id] = task

        # Start the task in the background
        asyncio.create_task(task.start())

        # Clean up the temporary file
        try:
            os.remove(temp_file)
        except Exception as e:
            logger.warning(f"Error removing temp file: {e}")

        return web.json_response({
            "task_id": task_id,
            "total_accounts": len(accounts_list),
            "user_type": user_type,
            "output_dir": output_dir
        })

    except Exception as e:
        logger.error(f"Error in upload_file: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)


async def websocket_handler(request):
    """Handle WebSocket connections for real-time updates"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Get task ID from URL
    task_id = request.match_info.get('task_id')
    task = active_tasks.get(task_id)

    if not task:
        await ws.send_json({"type": "error", "message": "Task not found"})
        await ws.close()
        return ws

    # Add this connection to the task
    task.add_connection(ws)

    try:
        # Send initial stats
        await ws.send_json({
            "type": "stats",
            "success": task.success_count,
            "failed": task.fail_count,
            "total": task.total_accounts
        })

        # Keep the connection open until closed by client
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f'WebSocket connection closed with exception {ws.exception()}')

    finally:
        # Remove this connection from the task
        task.remove_connection(ws)

    return ws


async def cancel_task(request):
    """Cancel an extraction task"""
    try:
        data = await request.json()
        task_id = data.get('task_id')

        if not task_id or task_id not in active_tasks:
            return web.json_response({"error": "Task not found"}, status=404)

        task = active_tasks[task_id]
        task.cancel()

        return web.json_response({"status": "cancelled"})

    except Exception as e:
        logger.error(f"Error in cancel_task: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)


def setup_routes(app):
    """Set up the application routes"""
    app.router.add_get('/', index)
    app.router.add_post('/api/upload', upload_file)
    app.router.add_post('/api/cancel', cancel_task)
    app.router.add_get('/ws/{task_id}', websocket_handler)

    # Static files
    app.router.add_static('/static/', path=os.path.join(os.path.dirname(__file__), 'static'), name='static')


def create_app():
    """Create and configure the application"""
    app = web.Application()

    # Set up Jinja2 templates
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))
    )

    # Set up routes
    setup_routes(app)

    return app


if __name__ == '__main__':
    # Create the application
    app = create_app()

    # Run the server
    web.run_app(app, host='0.0.0.0', port=8080)
