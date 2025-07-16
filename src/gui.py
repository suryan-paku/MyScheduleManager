# src/gui.py

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QDateTimeEdit, QDateEdit, QTimeEdit, QMessageBox # 日時入力用の追加インポート
)
from PySide6.QtCore import QDateTime # QDateTimeオブジェクトを使用
from src.data_manager import DataManager # DataManager

class ScheduleApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Schedule Manager")
        self.setGeometry(100, 100, 900, 700) # ウィンドウサイズを少し大きくしました
        self.init_ui()
        self.data_manager = DataManager() # DataManager のインスタンスを作成

    def init_ui(self):
        # メインレイアウト（垂直方向）
        main_layout = QVBoxLayout()

        # --- 1. 予定入力フォーム ---
        form_layout = QVBoxLayout()
        form_layout.setSpacing(10) # 各要素間のスペース

        # ヘッダー
        header_label = QLabel("📅 新しい予定の登録")
        header_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 15px; color: #333;")
        form_layout.addWidget(header_label)

        # 各入力フィールドの追加
        # タイトル
        form_layout.addWidget(QLabel("タイトル:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("例: 家族と旅行、定例会議")
        form_layout.addWidget(self.title_input)

        # 開始日時
        form_layout.addWidget(QLabel("開始日時:"))
        self.start_datetime_input = QDateTimeEdit(QDateTime.currentDateTime()) # 現在日時を初期値に
        self.start_datetime_input.setCalendarPopup(True) # カレンダーポップアップを有効に
        self.start_datetime_input.setDisplayFormat("yyyy/MM/dd HH:mm")
        form_layout.addWidget(self.start_datetime_input)

        # 終了日時
        form_layout.addWidget(QLabel("終了日時:"))
        self.end_datetime_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600)) # 1時間後を初期値に
        self.end_datetime_input.setCalendarPopup(True)
        self.end_datetime_input.setDisplayFormat("yyyy/MM/dd HH:mm")
        form_layout.addWidget(self.end_datetime_input)

        # 区分
        form_layout.addWidget(QLabel("区分:"))
        self.category_input = QComboBox()
        self.category_input.addItems(["プライベート", "仕事", "学習", "その他"])
        form_layout.addWidget(self.category_input)

        # 場所
        form_layout.addWidget(QLabel("場所:"))
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("例: 箱根旅館、会議室A")
        form_layout.addWidget(self.location_input)

        # 内容
        form_layout.addWidget(QLabel("内容 (タスク等):"))
        self.description_input = QTextEdit() # 複数行入力用
        self.description_input.setPlaceholderText("例:\n□ 旅館チェックイン前に電話\n□ 温泉の予約")
        self.description_input.setFixedHeight(100) # 高さ固定
        form_layout.addWidget(self.description_input)

        # ボタン類
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("予定を保存")
        self.save_button.clicked.connect(self.save_schedule)
        button_layout.addWidget(self.save_button)

        self.sync_button = QPushButton("Googleカレンダーと同期")
        self.sync_button.clicked.connect(self.sync_google_calendar) # 後で実装
        button_layout.addWidget(self.sync_button)

        form_layout.addLayout(button_layout)

        main_layout.addLayout(form_layout)
        main_layout.addStretch() # 残りのスペースを埋める

        self.setLayout(main_layout)

    def save_schedule(self):
        # フォームからデータを取得
        title = self.title_input.text()
        start_dt = self.start_datetime_input.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        end_dt = self.end_datetime_input.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        category = self.category_input.currentText()
        location = self.location_input.text()
        description = self.description_input.toPlainText()

        # 必須項目チェック
        if not title or not start_dt or not end_dt:
            QMessageBox.warning(self, "入力エラー", "タイトル、開始日時、終了日時は必須です。")
            return

        # 日付の順序チェック
        start_qdatetime = self.start_datetime_input.dateTime()
        end_qdatetime = self.end_datetime_input.dateTime()
        if start_qdatetime >= end_qdatetime:
            QMessageBox.warning(self, "入力エラー", "終了日時は開始日時よりも後に設定してください。")
            return
            
        # DataManager を使って予定を保存
        schedule_id = self.data_manager.save_schedule(
            title, start_dt, end_dt, category, location, description
        )

        if schedule_id:
            # タスク部分の処理 (descriptionから解析して保存)
            # 行ごとに分割し、空行を除去
            task_lines = [line.strip() for line in description.split('\n') if line.strip()]
            if task_lines:
                self.data_manager.save_tasks(schedule_id, task_lines)

            QMessageBox.information(self, "保存完了", f"予定 '{title}' をデータベースに保存しました。")
            self._clear_form() # フォームをクリアするメソッドを呼び出す (後で実装)
        else:
            QMessageBox.critical(self, "保存失敗", "予定の保存中にエラーが発生しました。")
    
    def _clear_form(self):
        """入力フォームをクリアするヘルパーメソッド"""
        self.title_input.clear()
        self.start_datetime_input.setDateTime(QDateTime.currentDateTime())
        self.end_datetime_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.category_input.setCurrentIndex(0) # 最初の項目を選択
        self.location_input.clear()
        self.description_input.clear()

    def sync_google_calendar(self):
        # Googleカレンダー連携ロジックを呼び出す（calendar_api.pyに実装予定）
        QMessageBox.information(self, "同期", "Googleカレンダーとの同期機能を呼び出します。")
        # 実際にはAPIを呼び出して予定を送信する
    
    def closeEvent(self, event):
        """ウィンドウが閉じられるときにデータベース接続を閉じる"""
        self.data_manager.close()
        event.accept() # イベントを受け入れてウィンドウを閉じる

def run_gui():
    app = QApplication(sys.argv)
    window = ScheduleApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_gui()