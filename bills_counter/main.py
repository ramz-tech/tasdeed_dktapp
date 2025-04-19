import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog,
    QProgressBar, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
from logic import load_accounts, generate_bill, save_to_excel

class BillCollectorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Electricity Bill Collector - TASDEED")
        self.setGeometry(300, 100, 420, 500)
        self.setStyleSheet("background-color: #f4f9f6;")

        self.accounts_df = None
        self.success_bills_df = []
        self.failed_accounts = []
        self.current_index = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_next_account)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.logo_label = QLabel(self)
        try:
            pixmap = QPixmap("tasdeed.png").scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
            self.logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.logo_label)
        except:
            pass

        self.title_label = QLabel("Upload Account Excel File")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0c2340;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.select_button = QPushButton("Select File")
        self.select_button.setStyleSheet("background-color: #88c057; color: white; padding: 10px;")
        self.select_button.clicked.connect(self.load_excel)
        layout.addWidget(self.select_button)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #555;")
        self.file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.file_label)

        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #0c2340;")
        layout.addWidget(self.progress_label)

        self.progress = QProgressBar(self)
        self.progress.setStyleSheet("height: 20px;")
        layout.addWidget(self.progress)

        self.collect_button = QPushButton("Collect Bills")
        self.collect_button.setEnabled(False)
        self.collect_button.setStyleSheet("background-color: #0094d9; color: white; padding: 10px;")
        self.collect_button.clicked.connect(self.collect_bills)
        layout.addWidget(self.collect_button)

        self.success_button = QPushButton("Download Success Bills")
        self.success_button.setStyleSheet("background-color: #88c057; color: white;")
        self.success_button.clicked.connect(self.download_bills)
        self.success_button.setVisible(False)
        layout.addWidget(self.success_button)

        self.error_button = QPushButton("Download Error Report")
        self.error_button.setStyleSheet("background-color: #f44336; color: white;")
        self.error_button.clicked.connect(self.download_error_report)
        self.error_button.setVisible(False)
        layout.addWidget(self.error_button)

        self.setLayout(layout)

    def load_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel Files (*.xlsx)")
        if path:
            self.accounts_df = load_accounts(path)
            self.file_label.setText(os.path.basename(path))
            self.collect_button.setEnabled(True)

    def collect_bills(self):
        self.success_bills_df = []
        self.failed_accounts = []
        self.accounts = self.accounts_df["account_number"].tolist()
        self.progress.setMaximum(len(self.accounts))
        self.progress.setValue(0)
        self.progress_label.setText(f"0/{len(self.accounts)}")
        self.current_index = 0
        self.timer.start(1)

    def process_next_account(self):
        if self.current_index >= len(self.accounts):
            self.timer.stop()
            self.show_summary()
            return

        account = self.accounts[self.current_index]
        try:
            bill = generate_bill(account)
            self.success_bills_df.append(bill)
        except Exception as e:
            self.failed_accounts.append({
                "account_number": account,
                "bill_id": None,
                "bill_date": None,
                "consumption_kwh": None,
                "rate_per_kwh": None,
                "total_amount": None,
                "error": str(e)
            })

        self.current_index += 1
        self.progress.setValue(self.current_index)
        self.progress_label.setText(f"{self.current_index}/{len(self.accounts)}")

    def show_summary(self):
        success_count = len(self.success_bills_df)
        total = len(self.accounts_df)
        self.title_label.setText(f"Bills Collected: {success_count}/{total}")
        self.success_button.setVisible(True)
        self.error_button.setVisible(True)
        if self.failed_accounts:
            QMessageBox.warning(self, "Some Bills Failed", "Some bills failed to be collected. Please download the error report.")

    def download_bills(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "success_bills.xlsx", "Excel Files (*.xlsx)")
        if path:
            save_to_excel(self.success_bills_df, path)
            QMessageBox.information(self, "Saved", "Bills saved successfully!")

    def download_error_report(self):
        if not self.failed_accounts:
            QMessageBox.information(self, "No Errors", "All bills were collected successfully.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save File", "error_report.xlsx", "Excel Files (*.xlsx)")
        if path:
            save_to_excel(self.failed_accounts, path)
            QMessageBox.information(self, "Saved", "Error report saved successfully!")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BillCollectorApp()
    window.show()
    sys.exit(app.exec_())
