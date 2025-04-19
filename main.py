import asyncio
import os
import logging
import pandas as pd
import sys
import glob
import shutil
from datetime import datetime

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QProgressBar, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from data_extractor.get_exact_pg import PortalClient
from data_transform.core_utils import extract_pdf_data, save_text_to_csv, delete_pdf
from bills_counter.logic import load_accounts, generate_bill, save_to_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExtractionThread(QThread):
    update_progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(str)

    def __init__(self, user_type, accounts_list, output_directory, pdf_folder):
        super().__init__()
        self.user_type = user_type
        self.accounts_list = accounts_list
        self.output_directory = output_directory
        self.pdf_folder = pdf_folder

    def run(self):
        asyncio.run(self.async_task())

    async def async_task(self):
        username, password = get_user(self.user_type)
        client = PortalClient(username=username, password=password, cookies=[])
        output_file = os.path.join(self.output_directory, "output.csv")

        async with client:
            await client.login()
            total = len(self.accounts_list)
            for i, account_no in enumerate(self.accounts_list, 1):
                try:
                    customer_id = await client.search_by_text(account_no)
                    params = await client.search_by_id(customer_id)
                    r_value = await client.create_navigation_url(params)
                    await client.navigate_to_documents_page(r_value)
                    document_data = await client.fetch_document_data()
                    documents = document_data.get("Data", {}).get("Documents", [])
                    if not documents:
                        self.update_progress.emit(i, total, f"No documents for {account_no}")
                        continue
                    document = documents[-1]
                    creation_date = document.get("CreationDate")
                    if not creation_date or not PortalClient.is_in_current_month(creation_date):
                        self.update_progress.emit(i, total, f"Old doc skipped: {account_no}")
                        continue
                    doc_id = document.get("Id")
                    pdf_path = os.path.join(self.pdf_folder, f"{doc_id}.pdf")
                    pdf_data = await client.fetch_pdf_data(document_id=doc_id)
                    await client.save_pdf(pdf_data, filepath=pdf_path)
                    extracted_data = extract_pdf_data(pdf_path)
                    save_text_to_csv(self.output_directory, extracted_data)
                    delete_pdf(pdf_path)
                    self.update_progress.emit(i, total, f"Done: {account_no}")
                except Exception as e:
                    self.update_progress.emit(i, total, f"Error {account_no}: {str(e)}")

        # Rename file
        now = datetime.now()
        month_year = now.strftime("%#m-%Y") if os.name == "nt" else now.strftime("%-m-%Y")
        renamed = os.path.join(self.output_directory, f"{self.user_type.upper()}_{month_year}.csv")
        if os.path.exists(output_file):
            shutil.move(output_file, renamed)

        for f in glob.glob(os.path.join(self.pdf_folder, "*.pdf")):
            os.remove(f)

        self.finished.emit(renamed)


def get_user(user_type):
    users = {
        "MAZOON": {"username": "emzec", "password": "emzec"},
        "MAJAN": {"username": "oneic_mjec", "password": "oman1234"},
        "TANVEER": {"username": "oneic", "password": "123456"},
        "MUSCAT": {"username": "ONIEC1", "password": "ONIEC1"}
    }
    return users.get(user_type.upper(), users["MUSCAT"]).values()


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tasdeed Extraction Dashboard")
        self.setWindowIcon(QIcon("bills_counter/tasdeed.png"))
        self.resize(800, 700)
        self.layout = QVBoxLayout()

        # Add Logo
        logo = QLabel()
        pixmap = QPixmap("bills_counter/tasdeed.png")
        pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(logo)

        self.label = QLabel("Processing ...")
        self.progress = QProgressBar()
        self.status = QLabel("Progress: 0 / 0")
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.start_btn = QPushButton("Start Extraction")
        self.start_btn.clicked.connect(self.start_extraction)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.status)
        self.layout.addWidget(self.log)
        self.layout.addWidget(self.start_btn)
        self.setLayout(self.layout)

    def start_extraction(self):
        user_types = ["MAZOON", "MAJAN", "TANVEER", "MUSCAT"]
        user_type, ok = QInputDialog.getItem(self, "User Type", "Select user type:", user_types, 0, False)
        if not ok:
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Select Excel or CSV File", "", "Excel/CSV Files (*.xlsx *.csv)")
        if not file_path:
            QMessageBox.warning(self, "No File", "No file selected.")
            return

        df = pd.read_excel(file_path) if file_path.endswith(".xlsx") else pd.read_csv(file_path)
        filtered_df = df[df["SUBTYPE"].str.upper() == user_type.upper()]
        accounts_list = filtered_df["account_number"].astype(str).tolist()

        output_directory = "output"
        os.makedirs(output_directory, exist_ok=True)
        pdf_folder = ".pdf_temp"
        os.makedirs(pdf_folder, exist_ok=True)

        self.worker = ExtractionThread(user_type, accounts_list, output_directory, pdf_folder)
        self.worker.update_progress.connect(self.update_ui)
        self.worker.finished.connect(self.done_ui)
        self.worker.start()

    def update_ui(self, current, total, message):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status.setText(f"Progress: {current} / {total}")
        self.log.append(message)

    def done_ui(self, output_file):
        QMessageBox.information(self, "Done", f"Extraction complete.\nSaved to: {output_file}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = Dashboard()
    dashboard.show()
    sys.exit(app.exec_())
