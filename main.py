import asyncio
import os
import logging
import pandas as pd
import sys
import glob
import shutil
from datetime import datetime

<<<<<<< HEAD
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QProgressBar, QMessageBox, QStackedLayout
=======
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QTextEdit,
    QFileDialog, QProgressBar, QMessageBox, QInputDialog
>>>>>>> b87f290660f96805e456457f5a9703f002c8c722
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
<<<<<<< HEAD
            self.update_progress.emit(0, len(self.accounts_list), "⏳ Logging in...")
            await client.login()
            self.update_progress.emit(0, len(self.accounts_list), "✅ Login successful. Starting processing...")

=======
            await client.login()
>>>>>>> b87f290660f96805e456457f5a9703f002c8c722
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
<<<<<<< HEAD
                    pass
                except Exception as e:
                    self.update_progress.emit(i, total, f"Error {account_no}: {str(e)}")

=======
                    self.update_progress.emit(i, total, f"Done: {account_no}")
                except Exception as e:
                    self.update_progress.emit(i, total, f"Error {account_no}: {str(e)}")

        # Rename file
>>>>>>> b87f290660f96805e456457f5a9703f002c8c722
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
<<<<<<< HEAD

        self.layout = QStackedLayout()
        self.setLayout(self.layout)

        self.init_page1()
        self.init_page2()
        self.layout.setCurrentIndex(0)

    def init_page1(self):
        self.page1 = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)

        logo = QLabel()
        pixmap = QPixmap("bills_counter/tasdeed.png").scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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

        self.back_btn = QPushButton("🔙 Finish")
        self.back_btn.setStyleSheet("background-color: #2196F3; color: white; font-size: 14px; padding: 8px; border-radius: 6px;")
        self.back_btn.clicked.connect(lambda: self.layout.setCurrentIndex(0))

        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(self.log)
        layout.addWidget(self.back_btn)
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

        self.worker = ExtractionThread(user_type, accounts_list, self.output_directory, pdf_folder)
        self.worker.update_progress.connect(self.update_ui)
        self.worker.finished.connect(self.done_ui)
        self.worker.start()
        self.layout.setCurrentIndex(1)
=======
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
        accounts_list = filtered_df.get("ACCOUNTNO", []).astype(str).tolist()
        if len(accounts_list) == 0:
            QMessageBox.warning(self, "No Accounts", "No accounts found for the selected user type. or the acount no column name is not ACCOUNTNO")
            return

        output_directory = "output"
        os.makedirs(output_directory, exist_ok=True)
        pdf_folder = ".pdf_temp"
        os.makedirs(pdf_folder, exist_ok=True)

        self.worker = ExtractionThread(user_type, accounts_list, output_directory, pdf_folder)
        self.worker.update_progress.connect(self.update_ui)
        self.worker.finished.connect(self.done_ui)
        self.worker.start()
>>>>>>> b87f290660f96805e456457f5a9703f002c8c722

    def update_ui(self, current, total, message):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.status.setText(f"Progress: {current} / {total}")
        self.log.append(message)

    def done_ui(self, output_file):
<<<<<<< HEAD
        self.log.append(f"✅ Done! File saved to: {output_file}")
=======
        QMessageBox.information(self, "Done", f"Extraction complete.\nSaved to: {output_file}")
>>>>>>> b87f290660f96805e456457f5a9703f002c8c722


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = Dashboard()
    dashboard.show()
    sys.exit(app.exec_())
