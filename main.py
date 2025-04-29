import asyncio
import os
import logging
import subprocess
import pandas as pd
import sys
import glob
import shutil
from datetime import datetime
from typing import Tuple, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Install Playwright with proper error handling
try:
    if not shutil.which("playwright"):
        logger.info("Installing Playwright...")
        subprocess.run(["pip", "install", "playwright"], check=True)
        subprocess.run(["playwright", "install"], check=True)
        subprocess.run(["python", "-m", "playwright", "install"], check=True)
except subprocess.CalledProcessError as e:
    logger.error(f"Failed to install Playwright. Exit code: {e.returncode}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error installing Playwright: {e}")
    sys.exit(1)

from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QProgressBar, QMessageBox, QStackedLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from data_extractor.get_exact_pg import PortalClient
from data_transform.core_utils import extract_pdf_data, save_text_to_csv, delete_pdf


def resource_path(filename: str) -> str:
    """Get absolute path to resource."""
    try:
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, filename)
        return os.path.join(os.path.abspath("."), filename)
    except Exception as e:
        logger.error(f"Failed to get resource path for {filename}: {e}")
        return filename


class ExtractionThread(QThread):
    update_progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, user_type: str, accounts_list: List[str], output_directory: str, pdf_folder: str):
        super().__init__()
        self.user_type = user_type
        self.accounts_list = accounts_list
        self.output_directory = output_directory
        self.pdf_folder = pdf_folder
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        try:
            asyncio.run(self.async_task())
        except asyncio.CancelledError:
            logger.info("Extraction task cancelled")
            self.error.emit("Task cancelled by user")
        except Exception as e:
            logger.error(f"Critical error in extraction thread: {e}", exc_info=True)
            self.error.emit(f"Critical error: {str(e)}")

    async def async_task(self):
        try:
            username, password = get_user(self.user_type)
            client = PortalClient(username=username, password=password, cookies=[])
            output_file = os.path.join(self.output_directory, "output.csv")

            async with client:
                self.update_progress.emit(0, len(self.accounts_list), "⏳ Processing...")
                await client.login()
                total = len(self.accounts_list)

                for i, account_no in enumerate(self.accounts_list, 1):
                    if not self._is_running:
                        raise asyncio.CancelledError()

                    try:
                        await self._process_account(client, account_no, i, total)
                    except Exception as e:
                        logger.error(f"Error processing account {account_no}: {e}", exc_info=True)
                        self.update_progress.emit(i, total, f"❌ Failed to access this account : {account_no}")

                await self._finalize_output(output_file)

        except Exception as e:
            logger.error(f"Error in async task: {e}", exc_info=True)
            self.error.emit(str(e))
            return

    async def _process_account(self, client: PortalClient, account_no: str, i: int, total: int):
        try:
            customer_id, customer_type = await client.search_by_text(account_no)
        except Exception as e:
            logger.error(f"Error searching for account {account_no}: {e}")
            self.update_progress.emit(i, total, f"❌ Failed to access this account: {account_no}") # Search failed
            raise ValueError(f"Could not find account {account_no}: {str(e)}")

        try:
            params = await client.search_by_id(customer_id, customer_type)
        except Exception as e:
            logger.error(f"Error getting details for account {account_no}: {e}")
            self.update_progress.emit(i, total, f"❌ Failed to access this account: {account_no}") # Details lookup failed
            raise ValueError(f"Could not get details for account {account_no}: {str(e)}")

        try:
            r_value = await client.create_navigation_url(params)
            await client.navigate_to_documents_page(r_value)
        except Exception as e:
            logger.error(f"Error navigating to documents for account {account_no}: {e}")
            self.update_progress.emit(i, total, f"❌ Failed to access this account: {account_no}") # Navigation failed
            raise ValueError(f"Could not navigate to documents for account {account_no}: {str(e)}")

        try:
            document_data = await client.fetch_document_data()
            documents = document_data.get("Data", {}).get("Documents", [])
        except Exception as e:
            logger.error(f"Error fetching documents for account {account_no}: {e}")
            self.update_progress.emit(i, total, f"❌ Failed to fetch data form bill: {account_no} ")
            raise ValueError(f"Could not fetch documents for account {account_no}: {str(e)}")

        if not documents:
            self.update_progress.emit(i, total, f"⚠️ No bill found for {account_no}")
            return

        document = documents[-1]
        creation_date = document.get("CreationDate")
        if not creation_date or not PortalClient.is_in_current_month(creation_date):
            self.update_progress.emit(i, total, f"ℹ️ Old bill skipped: {account_no}")
            return

        doc_id = document.get("Id")
        pdf_path = os.path.join(self.pdf_folder, f"{doc_id}.pdf")

        try:
            pdf_data = await client.fetch_pdf_data(document_id=doc_id)
            await client.save_pdf(pdf_data, filepath=pdf_path)
            extracted_data = extract_pdf_data(pdf_path)
            save_text_to_csv(self.output_directory, extracted_data)
            delete_pdf(pdf_path)
            self.update_progress.emit(i, total, f"✅ Success: {account_no}")
        except Exception as e:
            logger.error(f"Error processing PDF for account {account_no}: {e}")
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            raise ValueError(f"Error processing bill for account {account_no}: {str(e)}")

    async def _finalize_output(self, output_file: str):
        try:
            now = datetime.now()
            month_year = now.strftime("%#m-%Y") if os.name == "nt" else now.strftime("%-m-%Y")
            renamed = os.path.join(self.output_directory, f"{self.user_type.upper()}_{month_year}.csv")

            # Rename the output file
            try:
                if os.path.exists(output_file):
                    shutil.move(output_file, renamed)
                else:
                    logger.warning(f"Output file {output_file} does not exist, cannot rename")
                    raise FileNotFoundError(f"Output file {output_file} not found")
            except (OSError, shutil.Error) as e:
                logger.error(f"Error renaming output file: {e}")
                raise ValueError(f"Could not rename output file: {str(e)}")

            # Clean up temporary PDF files
            try:
                pdf_files = glob.glob(os.path.join(self.pdf_folder, "*.pdf"))
                for f in pdf_files:
                    try:
                        os.remove(f)
                    except OSError as e:
                        logger.warning(f"Could not remove temporary file {f}: {e}")
            except Exception as e:
                logger.warning(f"Error cleaning up temporary files: {e}")
                # Don't raise here, as this is not critical

            self.finished.emit(renamed)
        except Exception as e:
            logger.error(f"Error finalizing output: {e}", exc_info=True)
            raise ValueError(f"Error finalizing extraction process: {str(e)}")


def get_user(user_type: str) -> Tuple[str, str]:
    users = {
        "MAZOON": {"username": "emzec", "password": "emzec"},
        "MAJAN": {"username": "oneic_mjec", "password": "oman1234"},
        "TANVEER": {"username": "oneic", "password": "123456"},
        "MUSCAT": {"username": "ONIEC1", "password": "ONIEC1"}
    }
    user_data = users.get(user_type.upper(), users["MUSCAT"])
    return user_data["username"], user_data["password"]


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tasdeed Extraction Dashboard")
        self.setWindowIcon(QIcon(resource_path("logo.png")))
        self.resize(500, 400)
        self.layout = QStackedLayout()
        self.setLayout(self.layout)

        self.success_count = 0
        self.fail_count = 0

        self.init_page1()
        self.init_page2()
        self.layout.setCurrentIndex(0)

    def init_page1(self):
        self.page1 = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)

        logo = QLabel()
        pixmap = QPixmap(resource_path("logo.png")).scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)

        self.select_file_btn = QPushButton("📂 Select Account File")
        self.select_output_btn = QPushButton("💾 Select Output Folder")
        self.start_btn = QPushButton("🚀 Start Extraction")

        for btn in [self.select_file_btn, self.select_output_btn, self.start_btn]:
            btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px; padding: 10px; border-radius: 8px;")
            btn.setCursor(Qt.PointingHandCursor)

        self.select_file_btn.clicked.connect(self.select_file)
        self.select_output_btn.clicked.connect(self.select_output_folder)
        self.start_btn.clicked.connect(self.start_extraction)

        layout.addWidget(logo)
        layout.addWidget(self.select_file_btn)
        layout.addWidget(self.select_output_btn)
        layout.addWidget(self.start_btn)
        self.page1.setLayout(layout)
        self.layout.addWidget(self.page1)

    def init_page2(self):
        self.page2 = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        self.label = QLabel("📊 Processor")
        self.label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.label.setStyleSheet("color: #333;")

        self.progress = QProgressBar()
        self.status = QLabel("Progress: 0 / 0")
        self.status.setStyleSheet("font-weight: bold;")

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background-color: #f9f9f9; font-family: Consolas;")

        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setStyleSheet("background-color: #f44336; color: white; font-size: 14px; padding: 8px; border-radius: 6px;")
        self.cancel_btn.clicked.connect(self.cancel_process)

        self.finish_btn = QPushButton("✅ Finish")
        self.finish_btn.setStyleSheet("background-color: #2196F3; color: white; font-size: 14px; padding: 8px; border-radius: 6px;")
        self.finish_btn.clicked.connect(lambda: self.layout.setCurrentIndex(0))

        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(self.log)
        layout.addWidget(self.cancel_btn)
        layout.addWidget(self.finish_btn)

        self.page2.setLayout(layout)
        self.layout.addWidget(self.page2)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel or CSV File", "", "Excel/CSV Files (*.xlsx *.csv)")
        if path:
            self.file_path = path
            self.select_file_btn.setText(f"✅ File: {os.path.basename(path)}")

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_directory = folder
            self.select_output_btn.setText(f"📁 Output: {folder}")

    def start_extraction(self):
        if not hasattr(self, "file_path") or not hasattr(self, "output_directory"):
            QMessageBox.warning(self, "Missing Info", "Please select both file and output folder.")
            return

        df = pd.read_excel(self.file_path) if self.file_path.endswith(".xlsx") else pd.read_csv(self.file_path)
        subtype = df["SUBTYPE"].dropna().unique()
        if len(subtype) != 1:
            QMessageBox.warning(self, "Multiple SUBTYPES", "Only one user SUBTYPE should exist in the file.")
            return

        user_type = subtype[0]
        accounts_list = [str(acc) for acc in df.get("ACCOUNTNO", []) if pd.notna(acc)]
        if len(accounts_list) == 0:
            QMessageBox.warning(self, "No Accounts", "No valid accounts found in the ACCOUNTNO column.")
            return

        pdf_folder = ".pdf_temp"
        os.makedirs(pdf_folder, exist_ok=True)

        self.success_count = 0
        self.fail_count = 0

        self.worker = ExtractionThread(user_type, accounts_list, self.output_directory, pdf_folder)
        self.worker.update_progress.connect(self.update_ui)
        self.worker.finished.connect(self.done_ui)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

        self.cancel_btn.show()
        self.finish_btn.hide()
        self.layout.setCurrentIndex(1)

    def update_ui(self, current, total, message):
        if "✅ Success" in message:
            self.success_count += 1
        elif "❌ Failed" in message or "Can not get" in message or "No bill found" in message or "Old bill skipped" in message:
            self.fail_count += 1
            self.log.append(message)

        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status.setText(f"Progress: {current} / {total}")

    def done_ui(self, output_file):
        total = self.success_count + self.fail_count
        self.log.append(f"\n✅ Done! File saved to: {output_file}")
        self.log.append(f"📊 Summary: Success: {self.success_count}, Failed: {self.fail_count}, Total Tried: {total}")
        self.cancel_btn.hide()
        self.finish_btn.show()

        copy_target_dir = os.path.join(self.output_directory)
        os.makedirs(copy_target_dir, exist_ok=True)
        try:
            source_dir = os.path.dirname(output_file)
            if os.path.normpath(source_dir) != os.path.normpath(copy_target_dir):
                shutil.copy(output_file, copy_target_dir)
                copied_path = os.path.join(copy_target_dir, os.path.basename(output_file))
                self.log.append(f"📂 Output also copied to: {copied_path}")
        except Exception as e:
            self.log.append(f"⚠️ Failed to copy file: {str(e)}")

    def handle_error(self, error_message):
        """Handle errors from the extraction thread."""
        QMessageBox.critical(self, "Error", f"An error occurred: {error_message}")
        self.log.append(f"❌ Error: {error_message}")
        self.cancel_btn.hide()
        self.finish_btn.show()

    def cancel_process(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        self.log.append("❌ Process cancelled.")
        self.layout.setCurrentIndex(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = Dashboard()
    dashboard.show()
    sys.exit(app.exec_())
