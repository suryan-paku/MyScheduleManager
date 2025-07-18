# src/gui.py

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QDateTimeEdit, QMessageBox, QCheckBox,
    QListWidget, QListWidgetItem, QStackedWidget, QScrollArea # リスト表示用に追加
)
from PySide6.QtCore import QDateTime, Qt

from src.data_manager import DataManager

class ScheduleApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Schedule Manager")
        self.setGeometry(100, 100, 1000, 700) # ウィンドウサイズを少し広げました
        self.data_manager = DataManager()
        self.editing_schedule_id = None  # 編集中の予定ID
        self.is_edit_mode = False  # 編集モードフラグ
        self.init_ui()
        self._load_schedules_to_list() # アプリ起動時に予定を読み込む

    def init_ui(self):
        main_layout = QHBoxLayout()

        # --- 左側: 予定入力フォーム ---
        form_panel_layout = QVBoxLayout()
        form_panel_layout.setSpacing(10)

        self.header_label = QLabel("📅 新しい予定の登録")
        self.header_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 15px; color: #333;")
        form_panel_layout.addWidget(self.header_label)

        # ... (タイトル、開始日時、終了日時、区分、場所の入力フィールドはそのまま) ...
        form_panel_layout.addWidget(QLabel("タイトル:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("例: 家族と旅行、定例会議")
        form_panel_layout.addWidget(self.title_input)

        form_panel_layout.addWidget(QLabel("開始日時:"))
        self.start_datetime_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.start_datetime_input.setCalendarPopup(True)
        self.start_datetime_input.setDisplayFormat("yyyy/MM/dd HH:mm")
        form_panel_layout.addWidget(self.start_datetime_input)

        form_panel_layout.addWidget(QLabel("終了日時:"))
        self.end_datetime_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.end_datetime_input.setCalendarPopup(True)
        self.end_datetime_input.setDisplayFormat("yyyy/MM/dd HH:mm")
        form_panel_layout.addWidget(self.end_datetime_input)

        form_panel_layout.addWidget(QLabel("区分:"))
        self.category_input = QComboBox()
        self.category_input.addItems(["プライベート", "仕事", "学習", "その他"])
        form_panel_layout.addWidget(self.category_input)

        form_panel_layout.addWidget(QLabel("場所:"))
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("例: 箱根旅館、会議室A")
        form_panel_layout.addWidget(self.location_input)

        # --- ここから変更/追加 ---
        # 予定の内容（詳細説明）用フィールド
        form_panel_layout.addWidget(QLabel("内容 (詳細説明):"))
        self.details_content_input = QTextEdit() # 新しい名前
        self.details_content_input.setPlaceholderText("例: 家族構成や旅行先の注意点など、タスクではない詳細情報。")
        self.details_content_input.setFixedHeight(80) # 高さを調整
        form_panel_layout.addWidget(self.details_content_input)

        # タスクリスト入力用フィールド
        form_panel_layout.addWidget(QLabel("タスクリスト (1行に1タスク):")) # ラベルも変更
        self.task_input = QTextEdit() # 新しい名前
        self.task_input.setPlaceholderText("例:\n- 旅館チェックイン前に電話\n- 温泉の予約")
        self.task_input.setFixedHeight(80) # 高さを調整
        form_panel_layout.addWidget(self.task_input)
        # --- ここまで変更/追加 ---

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("予定を保存")
        self.save_button.clicked.connect(self.save_schedule)
        button_layout.addWidget(self.save_button)

        self.sync_button = QPushButton("Googleカレンダーと同期")
        self.sync_button.clicked.connect(self.sync_google_calendar)
        button_layout.addWidget(self.sync_button)

        form_panel_layout.addLayout(button_layout)
        form_panel_layout.addStretch()

        main_layout.addLayout(form_panel_layout, 1)

        # --- 右側: 予定一覧表示と詳細表示 ---
        schedule_list_panel_layout = QVBoxLayout()
        schedule_list_panel_layout.setSpacing(10)

        list_header_label = QLabel("🗓️ 登録済みの予定")
        list_header_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 15px; color: #333;")
        schedule_list_panel_layout.addWidget(list_header_label)

        self.schedule_list_widget = QListWidget()
        self.schedule_list_widget.itemClicked.connect(self._show_schedule_detail)
        schedule_list_panel_layout.addWidget(self.schedule_list_widget)

        # 予定詳細表示エリア
        self.detail_area = QWidget()
        detail_layout = QVBoxLayout()
        
        self.detail_title = QLabel("選択された予定")
        self.detail_title.setStyleSheet("font-size: 18px; font-weight: bold; color:#0056b3;")
        detail_layout.addWidget(self.detail_title)

        self.detail_start_end = QLabel("")
        self.detail_location = QLabel("")
        self.detail_category = QLabel("")
        
        detail_layout.addWidget(self.detail_start_end)
        detail_layout.addWidget(self.detail_location)
        detail_layout.addWidget(self.detail_category)

        # 詳細説明表示用のQLabel
        detail_layout.addWidget(QLabel("<b>詳細内容:</b>"))
        self.detail_description_label = QLabel("") # QLabelとして追加
        self.detail_description_label.setWordWrap(True) # 長文対応
        detail_layout.addWidget(self.detail_description_label) # レイアウトに追加

        # タスクリスト表示用のウィジェット
        task_list_label = QLabel("<b>タスク:</b>")
        detail_layout.addWidget(task_list_label)

        self.task_list_container = QVBoxLayout()
        self.task_scroll_area = QScrollArea()
        self.task_scroll_area.setWidgetResizable(True)
        self.task_scroll_area.setMinimumHeight(200)  # 最小高さを200pxに設定
        self.task_scroll_area.setMaximumHeight(400)  # 最大高さを400pxに設定（スクロール可能）
        self.task_scroll_content = QWidget()
        self.task_scroll_content.setLayout(self.task_list_container)
        self.task_scroll_area.setWidget(self.task_scroll_content)
        
        detail_layout.addWidget(self.task_scroll_area)

        # 編集ボタンを追加
        edit_button_layout = QHBoxLayout()
        self.edit_schedule_button = QPushButton("この予定を編集")
        self.edit_schedule_button.clicked.connect(self._edit_current_schedule)
        self.edit_schedule_button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px;")
        edit_button_layout.addWidget(self.edit_schedule_button)
        edit_button_layout.addStretch()
        detail_layout.addLayout(edit_button_layout)

        detail_layout.addStretch()
        self.detail_area.setLayout(detail_layout)
        self.detail_area.hide()

        schedule_list_panel_layout.addWidget(self.detail_area)
        schedule_list_panel_layout.addStretch()

        main_layout.addLayout(schedule_list_panel_layout, 2)

        self.setLayout(main_layout)

    def save_schedule(self):
        title = self.title_input.text().strip()
        start_dt = self.start_datetime_input.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        end_dt = self.end_datetime_input.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        category = self.category_input.currentText()
        location = self.location_input.text().strip()
        detailed_description = self.details_content_input.toPlainText().strip()
        task_input_text = self.task_input.toPlainText().strip()

        if not title or not start_dt or not end_dt:
            QMessageBox.warning(self, "入力エラー", "タイトル、開始日時、終了日時は必須です。")
            return

        start_qdatetime = self.start_datetime_input.dateTime()
        end_qdatetime = self.end_datetime_input.dateTime()
        if start_qdatetime >= end_qdatetime:
            QMessageBox.warning(self, "入力エラー", "終了日時は開始日時よりも後に設定してください。")
            return

        if self.is_edit_mode and self.editing_schedule_id:
            # 編集モード: 既存の予定を更新
            success = self.data_manager.update_schedule(
                self.editing_schedule_id, title, start_dt, end_dt, category, location, detailed_description
            )
            if success:
                # タスクも更新（既存のタスクを削除して新しく保存）
                task_lines = [
                    line.strip().lstrip('□✅- ').strip()
                    for line in task_input_text.split('\n') if line.strip()
                ]
                if task_lines:
                    self.data_manager.save_tasks(self.editing_schedule_id, task_lines)

                QMessageBox.information(self, "更新完了", f"予定 '{title}' を更新しました。")
                self._cancel_edit_mode()  # 編集モードを終了
                self._load_schedules_to_list()
            else:
                QMessageBox.critical(self, "更新失敗", "予定の更新中にエラーが発生しました。")
        else:
            # 新規作成モード
            schedule_id = self.data_manager.save_schedule(
                title, start_dt, end_dt, category, location, detailed_description
            )

            if schedule_id:
                # タスクを保存
                task_lines = [
                    line.strip().lstrip('□- ').strip()
                    for line in task_input_text.split('\n') if line.strip()
                ]
                if task_lines:
                    self.data_manager.save_tasks(schedule_id, task_lines)

                QMessageBox.information(self, "保存完了", f"予定 '{title}' をデータベースに保存しました。")
                self._clear_form()
                self._load_schedules_to_list()
            else:
                QMessageBox.critical(self, "保存失敗", "予定の保存中にエラーが発生しました。")


    def _clear_form(self):
        # ... (既存の _clear_form メソッドはそのまま) ...
        self.title_input.clear()
        self.start_datetime_input.setDateTime(QDateTime.currentDateTime())
        self.end_datetime_input.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.category_input.setCurrentIndex(0)
        self.location_input.clear()
        self.details_content_input.clear() # 新しい詳細内容フィールドをクリア
        self.task_input.clear()            # 新しいタスク入力フィールドをクリア

    def _load_schedules_to_list(self):
        self.schedule_list_widget.clear()
        schedules = self.data_manager.get_all_schedules()
        
        self.schedules_data = {s[0]: s for s in schedules}

        for schedule in schedules:
            schedule_id = schedule[0]
            title = schedule[1]
            start_dt = QDateTime.fromString(schedule[2], "yyyy-MM-dd HH:mm:ss").toString("MM/dd HH:mm")
            
            item_text = f"{start_dt} - {title}"
            list_item = QListWidgetItem(item_text)
            
            list_item.setData(Qt.UserRole, schedule_id) 
            self.schedule_list_widget.addItem(list_item)
        
        if schedules:
            self.schedule_list_widget.setCurrentRow(0)
            self._show_schedule_detail(self.schedule_list_widget.currentItem())

    def _show_schedule_detail(self, item):
        """リストで選択された予定の詳細を表示し、タスクをチェックボックスで表示します。"""
        if not item:
            self.detail_area.hide()
            return
            
        schedule_id = item.data(Qt.UserRole)
        self.current_selected_schedule_id = schedule_id
        schedule_data = self.schedules_data.get(schedule_id)

        if schedule_data:
            self.detail_title.setText(f"{schedule_data[1]}")
            self.detail_start_end.setText(f"<b>開始-終了:</b> {QDateTime.fromString(schedule_data[2], 'yyyy-MM-dd HH:mm:ss').toString('yyyy/MM/dd HH:mm')} - {QDateTime.fromString(schedule_data[3], 'yyyy-MM-dd HH:mm:ss').toString('yyyy/MM/dd HH:mm')}")
            self.detail_location.setText(f"<b>場所:</b> {schedule_data[4] or '未設定'}")
            self.detail_category.setText(f"<b>区分:</b> {schedule_data[5] or '未設定'}")
            
            # 詳細内容を表示
            self.detail_description_label.setText(schedule_data[6] or "なし") # descriptionカラムから詳細内容を表示

            # 既存のタスクチェックボックスを全てクリア
            for i in reversed(range(self.task_list_container.count())):
                widget = self.task_list_container.itemAt(i).widget()
                if widget is not None:
                    widget.deleteLater()
            
            # タスク情報を取得してチェックボックスとして表示
            tasks = self.data_manager.get_tasks_for_schedule(schedule_id)
            if not tasks:
                self.task_list_container.addWidget(QLabel("<i>タスクはありません</i>"))
            else:
                for task in tasks:
                    task_id, task_desc, is_completed = task
                    checkbox = QCheckBox(task_desc)
                    checkbox.setChecked(bool(is_completed))
                    checkbox.task_id = task_id
                    checkbox.stateChanged.connect(self._on_task_checkbox_changed)
                    self.task_list_container.addWidget(checkbox)
            
            # スクロールエリア内のウィジェットを更新したらレイアウトも更新
            self.task_scroll_content.setLayout(self.task_list_container)
            self.detail_area.show()
        else:
            self.detail_area.hide()

    def _on_task_checkbox_changed(self, state):
        checkbox = self.sender()
        if checkbox:
            task_id = getattr(checkbox, 'task_id', None)
            if task_id:
                is_completed = bool(state == 2)  # 2 = Qt.CheckState.Checked
                self.data_manager.update_task_completion(task_id, is_completed)
                print(f"タスク '{checkbox.text()}' の状態を更新: {'完了' if is_completed else '未完了'}")

    def _edit_current_schedule(self):
        """選択された予定を編集モードで開く"""
        if hasattr(self, 'current_selected_schedule_id') and self.current_selected_schedule_id:
            self.editing_schedule_id = self.current_selected_schedule_id
            self.is_edit_mode = True
            self._load_schedule_for_editing()
            self._update_ui_for_edit_mode()

    def _load_schedule_for_editing(self):
        """編集対象の予定データをフォームに読み込む"""
        schedule_data = self.schedules_data.get(self.editing_schedule_id)
        if schedule_data:
            # フォームに既存データを設定
            self.title_input.setText(schedule_data[1])  # タイトル
            self.start_datetime_input.setDateTime(QDateTime.fromString(schedule_data[2], "yyyy-MM-dd HH:mm:ss"))
            self.end_datetime_input.setDateTime(QDateTime.fromString(schedule_data[3], "yyyy-MM-dd HH:mm:ss"))
            
            # 区分（category）を設定
            category_index = self.category_input.findText(schedule_data[5])
            if category_index != -1:
                self.category_input.setCurrentIndex(category_index)
                
            self.location_input.setText(schedule_data[4] or "")  # 場所
            self.details_content_input.setText(schedule_data[6] or "")  # 詳細内容
            
            # タスクデータを取得してタスク入力欄に設定
            tasks = self.data_manager.get_tasks_for_schedule(self.editing_schedule_id)
            task_text = ""
            for task in tasks:
                task_id, task_desc, is_completed = task
                task_text += f"{'✅' if is_completed else '□'} {task_desc}\n"
            self.task_input.setText(task_text.strip())

    def _update_ui_for_edit_mode(self):
        """UIを編集モード用に更新"""
        self.header_label.setText("📝 予定の編集")
        self.save_button.setText("変更を保存")
        self.save_button.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px;")
        
        # キャンセルボタンを追加
        if not hasattr(self, 'cancel_button'):
            self.cancel_button = QPushButton("編集をキャンセル")
            self.cancel_button.clicked.connect(self._cancel_edit_mode)
            self.cancel_button.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px;")
            # 保存ボタンの隣にキャンセルボタンを追加
            button_layout = self.save_button.parent().layout()
            button_layout.addWidget(self.cancel_button)

    def _cancel_edit_mode(self):
        """編集モードをキャンセルして新規作成モードに戻る"""
        self.is_edit_mode = False
        self.editing_schedule_id = None
        self._clear_form()
        self._update_ui_for_create_mode()

    def _update_ui_for_create_mode(self):
        """UIを新規作成モード用に更新"""
        self.header_label.setText("📅 新しい予定の登録")
        self.save_button.setText("予定を保存")
        self.save_button.setStyleSheet("")  # デフォルトスタイルに戻す
        
        # キャンセルボタンを非表示
        if hasattr(self, 'cancel_button'):
            self.cancel_button.hide()

    def sync_google_calendar(self):
        QMessageBox.information(self, "同期", "Googleカレンダーとの同期機能を呼び出します。")

    def closeEvent(self, event):
        self.data_manager.close()
        event.accept()
        
def run_gui():
    app = QApplication(sys.argv)
    window = ScheduleApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_gui()