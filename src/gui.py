# src/gui.py

import sys
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QDateTimeEdit, QMessageBox, QCheckBox, QSpinBox,
    QListWidget, QListWidgetItem, QStackedWidget, QScrollArea, # リスト表示用に追加
    QSystemTrayIcon, QStyle # システムトレイアイコン用
)
from PySide6.QtCore import QDateTime, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtMultimedia import QSoundEffect

from src.data_manager import DataManager

class NotificationManager:
    """予定の通知を管理するクラス"""
    def __init__(self, parent):
        self.parent = parent
        self.data_manager = parent.data_manager
        self.timer = QTimer(parent)
        self.timer.timeout.connect(self.check_notifications)
        self.timer.start(60000)  # 1分ごとにチェック
        
        # システムトレイアイコンの設定
        self.tray_icon = QSystemTrayIcon(parent)
        # スタイルアイコンを直接指定
        app_icon = parent.style().standardIcon(QStyle.SP_MessageBoxInformation)
        self.tray_icon.setIcon(app_icon)
        self.tray_icon.setToolTip("My Schedule Manager")
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
        # 通知音の設定
        self.sound = QSoundEffect(parent)
        sound_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "notification.wav")
        if os.path.exists(sound_file):
            self.sound.setSource(QUrl.fromLocalFile(sound_file))
            self.sound.setVolume(0.5)
        
        # 最後に通知した時間を記録する辞書（schedule_id: last_notification_time）
        self.last_notifications = {}
        
        # スケジュール開始タスクのチェック状態を記録する辞書（schedule_id: is_checked）
        self.schedule_start_checked = {}
        
        # 通知を繰り返す予定のリスト
        self.repeat_notification_schedules = set()
    
    def check_notifications(self):
        """通知が必要な予定をチェックする"""
        current_time = datetime.now()
        
        # 現在および未来の予定を取得
        schedules = self.data_manager.get_current_schedules()
        
        for schedule in schedules:
            schedule_id = schedule[0]
            title = schedule[1]
            start_time_str = schedule[2]
            
            # 開始時間をdatetimeオブジェクトに変換
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            
            # 1. 通知設定による通知
            notification_minutes = None
            try:
                notification_minutes = schedule[9]  # notification_minutes カラムは9番目
            except IndexError:
                pass
            
            if notification_minutes is not None:
                # 通知時間を計算（開始時間の何分前に通知するか）
                notification_time = start_time - timedelta(minutes=notification_minutes)
                
                # 現在時刻が通知時間を過ぎているかつ、まだ通知していないか、前回の通知から24時間以上経過している場合
                last_notified = self.last_notifications.get(f"{schedule_id}_scheduled")
                if (current_time >= notification_time and 
                    (last_notified is None or (current_time - last_notified).total_seconds() > 86400)):
                    
                    # 通知を表示
                    self.show_notification(title, start_time_str, schedule_id, "scheduled")
                    
                    # 最後に通知した時間を記録
                    self.last_notifications[f"{schedule_id}_scheduled"] = current_time
            
            # 2. 開始時間から5分後の強制通知
            five_min_after_start = start_time + timedelta(minutes=5)
            
            # 「スケジュールの開始」タスクのチェック状態を取得
            start_task_checked = self.schedule_start_checked.get(schedule_id, False)
            
            # 現在時刻が開始時間から5分後を過ぎていて、まだ通知していない場合
            last_notified = self.last_notifications.get(f"{schedule_id}_5min")
            if (current_time >= five_min_after_start and not start_task_checked and
                (last_notified is None or (current_time - last_notified).total_seconds() > 300)):  # 5分ごとに繰り返し
                
                # 「スケジュールの開始」タスクのチェック状態を確認
                tasks = self.data_manager.get_tasks_for_schedule(schedule_id)
                for task in tasks:
                    task_id, task_desc, is_completed = task
                    if task_desc == "スケジュールの開始":
                        if is_completed:
                            start_task_checked = True
                            self.schedule_start_checked[schedule_id] = True
                            # チェックされていれば繰り返し通知リストから削除
                            if schedule_id in self.repeat_notification_schedules:
                                self.repeat_notification_schedules.remove(schedule_id)
                        else:
                            # チェックされていなければ繰り返し通知リストに追加
                            self.repeat_notification_schedules.add(schedule_id)
                        break
                
                # チェックされていなければ通知
                if not start_task_checked:
                    self.show_notification(
                        title, 
                        start_time_str, 
                        schedule_id, 
                        "start_reminder",
                        "スケジュールの開始時間から5分が経過しました。「スケジュールの開始」にチェックを入れてください。"
                    )
                    
                    # 最後に通知した時間を記録
                    self.last_notifications[f"{schedule_id}_5min"] = current_time
    
    def show_notification(self, title, start_time, schedule_id, notification_type, custom_message=None):
        """通知を表示する"""
        # 開始時間を読みやすい形式に変換
        readable_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").strftime("%Y/%m/%d %H:%M")
        
        # 通知メッセージを設定
        if custom_message:
            message = custom_message
        else:
            message = f"予定「{title}」が {readable_time} から始まります。"
        
        # システムトレイ通知を表示
        self.tray_icon.showMessage(
            "予定の通知",
            message,
            QSystemTrayIcon.Information,
            5000  # 5秒間表示
        )
        
        # 通知音を再生
        if self.sound.isLoaded():
            self.sound.play()
        
        # ポップアップメッセージボックスを表示（最前面に表示）
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle("予定の通知")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)  # 最前面に表示
        msg_box.exec()
    
    def tray_icon_activated(self, reason):
        """システムトレイアイコンがクリックされたときの処理"""
        if reason == QSystemTrayIcon.Trigger:
            # シングルクリックでウィンドウを表示
            self.parent.showNormal()
            self.parent.activateWindow()
            
    def update_task_check_status(self, schedule_id, task_desc, is_checked):
        """タスクのチェック状態を更新する"""
        if task_desc == "スケジュールの開始":
            self.schedule_start_checked[schedule_id] = is_checked
            # チェックされていれば繰り返し通知リストから削除
            if is_checked and schedule_id in self.repeat_notification_schedules:
                self.repeat_notification_schedules.remove(schedule_id)

class ScheduleApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Schedule Manager")
        self.setGeometry(100, 100, 1000, 700) # ウィンドウサイズを少し広げました
        self.data_manager = DataManager()
        self.editing_schedule_id = None  # 編集中の予定ID
        self.is_edit_mode = False  # 編集モードフラグ
        self.show_past_schedules = False  # 過去の予定表示フラグ（デフォルトは非表示）
        self.init_ui()
        self._load_schedules_to_list() # アプリ起動時に予定を読み込む
        
        # 通知マネージャーを初期化（UI初期化後に行う）
        self.notification_manager = NotificationManager(self)

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
        # 開始日時が変更されたときに終了日時も自動的に更新する
        self.start_datetime_input.dateTimeChanged.connect(self._update_end_datetime)
        form_panel_layout.addWidget(self.start_datetime_input)

        form_panel_layout.addWidget(QLabel("終了日時:"))
        self.end_datetime_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.end_datetime_input.setCalendarPopup(True)
        self.end_datetime_input.setDisplayFormat("yyyy/MM/dd HH:mm")
        # 終了日時が変更されたときに開始日時との関係をチェック
        self.end_datetime_input.dateTimeChanged.connect(self._validate_end_datetime)
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
        
        # 通知設定用のUI
        notification_layout = QVBoxLayout()
        notification_layout.setSpacing(5)
        
        # スケジュール通知設定
        schedule_notification_layout = QHBoxLayout()
        schedule_notification_layout.addWidget(QLabel("スケジュール通知:"))
        
        # 通知を有効にするチェックボックス
        self.notification_enabled_checkbox = QCheckBox("開始時刻の")
        self.notification_enabled_checkbox.stateChanged.connect(self._toggle_notification_settings)
        schedule_notification_layout.addWidget(self.notification_enabled_checkbox)
        
        # 通知時間（分前）を設定するスピンボックス
        self.notification_minutes_spinbox = QSpinBox()
        self.notification_minutes_spinbox.setRange(0, 1440)  # 0分〜24時間（1440分）
        self.notification_minutes_spinbox.setValue(30)  # デフォルトは30分前
        self.notification_minutes_spinbox.setSuffix(" 分前")
        self.notification_minutes_spinbox.setEnabled(False)  # デフォルトは無効
        schedule_notification_layout.addWidget(self.notification_minutes_spinbox)
        
        schedule_notification_layout.addWidget(QLabel("に通知する"))
        schedule_notification_layout.addStretch()
        notification_layout.addLayout(schedule_notification_layout)
        
        # タスク通知設定
        task_notification_layout = QHBoxLayout()
        task_notification_layout.addWidget(QLabel("タスク通知:"))
        
        # タスク通知を有効にするチェックボックス
        self.task_notification_enabled_checkbox = QCheckBox("前のタスク完了から")
        self.task_notification_enabled_checkbox.stateChanged.connect(self._toggle_task_notification_settings)
        task_notification_layout.addWidget(self.task_notification_enabled_checkbox)
        
        # タスク通知時間（分後）を設定するスピンボックス
        self.task_notification_minutes_spinbox = QSpinBox()
        self.task_notification_minutes_spinbox.setRange(1, 120)  # 1分〜2時間（120分）
        self.task_notification_minutes_spinbox.setValue(15)  # デフォルトは15分後
        self.task_notification_minutes_spinbox.setSuffix(" 分後")
        self.task_notification_minutes_spinbox.setEnabled(False)  # デフォルトは無効
        task_notification_layout.addWidget(self.task_notification_minutes_spinbox)
        
        task_notification_layout.addWidget(QLabel("に次のタスクを確認"))
        task_notification_layout.addStretch()
        notification_layout.addLayout(task_notification_layout)
        
        form_panel_layout.addLayout(notification_layout)
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

        # ヘッダーと表示切り替えボタンを横に並べるレイアウト
        header_layout = QHBoxLayout()
        
        self.list_header_label = QLabel("🗓️ 登録済みの予定")
        self.list_header_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 15px; color: #333;")
        header_layout.addWidget(self.list_header_label)
        
        header_layout.addStretch()  # 右寄せにするためのスペーサー
        
        schedule_list_panel_layout.addLayout(header_layout)

        self.schedule_list_widget = QListWidget()
        self.schedule_list_widget.itemClicked.connect(self._show_schedule_detail)
        schedule_list_panel_layout.addWidget(self.schedule_list_widget)
        
        # 過去の予定表示切り替えボタンを右下に配置
        past_schedule_button_layout = QHBoxLayout()
        past_schedule_button_layout.addStretch()  # 右寄せにするためのスペーサー
        
        self.toggle_past_schedule_button = QPushButton("過去の予定")
        self.toggle_past_schedule_button.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold; padding: 8px;")
        self.toggle_past_schedule_button.clicked.connect(self._toggle_past_schedules)
        past_schedule_button_layout.addWidget(self.toggle_past_schedule_button)
        
        schedule_list_panel_layout.addLayout(past_schedule_button_layout)

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

        # 編集、ロック/解除、削除ボタンを追加
        action_button_layout = QHBoxLayout()
        
        # 編集ボタン
        self.edit_schedule_button = QPushButton("この予定を編集")
        self.edit_schedule_button.clicked.connect(self._edit_current_schedule)
        self.edit_schedule_button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px;")
        action_button_layout.addWidget(self.edit_schedule_button)
        
        # ロック/解除ボタン
        self.toggle_lock_button = QPushButton("ロック/解除")
        self.toggle_lock_button.clicked.connect(self._toggle_schedule_lock)
        self.toggle_lock_button.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px;")
        action_button_layout.addWidget(self.toggle_lock_button)
        
        # 削除ボタン
        self.delete_schedule_button = QPushButton("削除")
        self.delete_schedule_button.clicked.connect(self._delete_current_schedule)
        self.delete_schedule_button.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 8px;")
        action_button_layout.addWidget(self.delete_schedule_button)
        
        action_button_layout.addStretch()
        detail_layout.addLayout(action_button_layout)

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
        
        # 通知設定を取得
        notification_minutes = None
        if self.notification_enabled_checkbox.isChecked():
            notification_minutes = self.notification_minutes_spinbox.value()
            
        # タスク通知設定を取得
        task_notification_minutes = None
        if self.task_notification_enabled_checkbox.isChecked():
            task_notification_minutes = self.task_notification_minutes_spinbox.value()

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
                self.editing_schedule_id, title, start_dt, end_dt, category, location, detailed_description, 
                notification_minutes, task_notification_minutes
            )
            if success:
                # タスクも更新（既存のタスクを削除して新しく保存）
                # 自動タスクと入力タスクを結合
                auto_tasks = ["スケジュールの開始"]
                
                # ユーザーが入力したタスクを取得（自動タスクを除外）
                user_tasks = []
                for line in task_input_text.split('\n'):
                    task_text = line.strip().lstrip('□✅- ').strip()
                    if task_text and task_text not in ["スケジュールの開始", "スケジュールの終了"]:
                        user_tasks.append(task_text)
                
                # 最後に「スケジュールの終了」タスクを追加
                all_tasks = auto_tasks + user_tasks + ["スケジュールの終了"]
                
                # タスクを保存
                if all_tasks:
                    self.data_manager.save_tasks(self.editing_schedule_id, all_tasks)

                QMessageBox.information(self, "更新完了", f"予定 '{title}' を更新しました。")
                self._cancel_edit_mode()  # 編集モードを終了
                self._load_schedules_to_list()
            else:
                QMessageBox.critical(self, "更新失敗", "予定の更新中にエラーが発生しました。")
        else:
            # 新規作成モード
            schedule_id = self.data_manager.save_schedule(
                title, start_dt, end_dt, category, location, detailed_description, 0, 
                notification_minutes, task_notification_minutes
            )

            if schedule_id:
                # 自動タスクと入力タスクを結合
                auto_tasks = ["スケジュールの開始"]
                
                # ユーザーが入力したタスクを取得
                user_tasks = [
                    line.strip().lstrip('□- ').strip()
                    for line in task_input_text.split('\n') if line.strip()
                ]
                
                # 最後に「スケジュールの終了」タスクを追加
                all_tasks = auto_tasks + user_tasks + ["スケジュールの終了"]
                
                # タスクを保存
                if all_tasks:
                    self.data_manager.save_tasks(schedule_id, all_tasks)

                QMessageBox.information(self, "保存完了", f"予定 '{title}' をデータベースに保存しました。")
                self._clear_form()
                self._load_schedules_to_list()
            else:
                QMessageBox.critical(self, "保存失敗", "予定の保存中にエラーが発生しました。")


    def _clear_form(self):
        """フォームの内容をクリアして初期状態に戻す"""
        self.title_input.clear()
        
        # 開始日時を現在時刻に設定（シグナルをブロックして終了日時の自動更新を防止）
        current_datetime = QDateTime.currentDateTime()
        self.start_datetime_input.blockSignals(True)
        self.start_datetime_input.setDateTime(current_datetime)
        self.start_datetime_input.blockSignals(False)
        
        # 終了日時を1時間後に設定
        self.end_datetime_input.setDateTime(current_datetime.addSecs(3600))
        
        self.category_input.setCurrentIndex(0)
        self.location_input.clear()
        self.details_content_input.clear() # 新しい詳細内容フィールドをクリア
        self.task_input.clear()            # 新しいタスク入力フィールドをクリア
        
        # 通知設定をリセット
        self.notification_enabled_checkbox.setChecked(False)
        self.notification_minutes_spinbox.setValue(30)
        self.notification_minutes_spinbox.setEnabled(False)
        
        # タスク通知設定をリセット
        self.task_notification_enabled_checkbox.setChecked(False)
        self.task_notification_minutes_spinbox.setValue(15)
        self.task_notification_minutes_spinbox.setEnabled(False)

    def _load_schedules_to_list(self):
        self.schedule_list_widget.clear()
        
        # 表示モードに応じて予定を取得
        if self.show_past_schedules:
            schedules = self.data_manager.get_past_schedules()
            self.list_header_label.setText("🗓️ 過去の予定")
            self.toggle_past_schedule_button.setText("現在の予定")
            self.toggle_past_schedule_button.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 8px;")
        else:
            schedules = self.data_manager.get_current_schedules()
            self.list_header_label.setText("🗓️ 登録済みの予定")
            self.toggle_past_schedule_button.setText("過去の予定")
            self.toggle_past_schedule_button.setStyleSheet("background-color: #6c757d; color: white; font-weight: bold; padding: 8px;")
        
        self.schedules_data = {s[0]: s for s in schedules}

        for schedule in schedules:
            schedule_id = schedule[0]
            title = schedule[1]
            start_dt = QDateTime.fromString(schedule[2], "yyyy-MM-dd HH:mm:ss").toString("MM/dd HH:mm")
            
            item_text = f"{start_dt} - {title}"
            list_item = QListWidgetItem(item_text)
            
            # ロックされている場合は表示を変える
            # is_locked カラムは8番目だが、存在しない可能性もあるのでインデックスエラーを防止
            is_locked = False
            try:
                is_locked = schedule[8] == 1
            except IndexError:
                # 古いレコードの場合はロックされていないとみなす
                pass
                
            # 完了状態を確認
            is_completed = False
            try:
                is_completed = schedule[10] == 1  # is_completed カラムは10番目
            except IndexError:
                # 古いレコードの場合は完了していないとみなす
                pass
                
            if is_locked:
                list_item.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
                list_item.setText(f"{item_text} 🔒")
                
            if is_completed:
                # グレーアウト表示
                list_item.setForeground(Qt.gray)
                list_item.setText(f"{item_text} ✓")
            
            list_item.setData(Qt.UserRole, schedule_id) 
            self.schedule_list_widget.addItem(list_item)
        
        if schedules:
            self.schedule_list_widget.setCurrentRow(0)
            self._show_schedule_detail(self.schedule_list_widget.currentItem())
        else:
            # 予定がない場合は詳細表示をクリア
            self.detail_area.hide()

    def _show_schedule_detail(self, item):
        """リストで選択された予定の詳細を表示し、タスクをチェックボックスで表示します。"""
        if not item:
            self.detail_area.hide()
            return
            
        schedule_id = item.data(Qt.UserRole)
        self.current_selected_schedule_id = schedule_id
        schedule_data = self.schedules_data.get(schedule_id)

        if schedule_data:
            # is_locked カラムは8番目だが、存在しない可能性もあるのでインデックスエラーを防止
            is_locked = False
            try:
                is_locked = schedule_data[8] == 1
            except IndexError:
                # 古いレコードの場合はロックされていないとみなす
                pass
            
            self.detail_title.setText(f"{schedule_data[1]}")
            self.detail_start_end.setText(f"<b>開始-終了:</b> {QDateTime.fromString(schedule_data[2], 'yyyy-MM-dd HH:mm:ss').toString('yyyy/MM/dd HH:mm')} - {QDateTime.fromString(schedule_data[3], 'yyyy-MM-dd HH:mm:ss').toString('yyyy/MM/dd HH:mm')}")
            self.detail_location.setText(f"<b>場所:</b> {schedule_data[4] or '未設定'}")
            self.detail_category.setText(f"<b>区分:</b> {schedule_data[5] or '未設定'}")
            
            # 通知設定を表示
            notification_minutes = None
            try:
                notification_minutes = schedule_data[9]  # notification_minutes カラムは9番目
            except IndexError:
                # 古いレコードの場合は通知設定なし
                pass
                
            if notification_minutes is not None:
                self.detail_category.setText(f"{self.detail_category.text()} <b>🔔 {notification_minutes}分前に通知</b>")
                
            # タスク通知設定を表示
            task_notification_minutes = None
            try:
                task_notification_minutes = schedule_data[12]  # task_notification_minutes カラムは12番目
            except IndexError:
                # 古いレコードの場合はタスク通知設定なし
                pass
                
            if task_notification_minutes is not None:
                self.detail_category.setText(f"{self.detail_category.text()} <b>⏱️ タスク完了{task_notification_minutes}分後に確認</b>")
            
            # ロック状態を表示
            if is_locked:
                self.detail_category.setText(f"{self.detail_category.text()} <b>🔒 ロック中</b>")
                
            # 完了状態を確認
            is_completed = False
            try:
                is_completed = schedule_data[10] == 1  # is_completed カラムは10番目
            except IndexError:
                # 古いレコードの場合は完了していないとみなす
                pass
                
            if is_completed:
                self.detail_category.setText(f"{self.detail_category.text()} <b>✓ 完了済み</b>")
            
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
                    checkbox.setEnabled(not is_locked)  # ロック中はチェックボックスを無効化
                    self.task_list_container.addWidget(checkbox)
            
            # スクロールエリア内のウィジェットを更新したらレイアウトも更新
            self.task_scroll_content.setLayout(self.task_list_container)
            
            # ロック状態に応じてボタンの状態を更新
            self.edit_schedule_button.setEnabled(not is_locked)
            self.delete_schedule_button.setEnabled(not is_locked)
            
            if is_locked:
                self.toggle_lock_button.setText("ロック解除")
                self.toggle_lock_button.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 8px;")
            else:
                self.toggle_lock_button.setText("ロック")
                self.toggle_lock_button.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 8px;")
            
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
                
                schedule_id = self.current_selected_schedule_id
                if schedule_id:
                    # 「スケジュールの開始」タスクのチェック状態を通知マネージャーに通知
                    if checkbox.text() == "スケジュールの開始":
                        self.notification_manager.update_task_check_status(schedule_id, "スケジュールの開始", is_completed)
                    
                    # 「スケジュールの終了」タスクがチェックされた場合、予定を完了状態にする
                    if is_completed and checkbox.text() == "スケジュールの終了":
                        self.data_manager.update_schedule_completion(schedule_id, True)
                        self._load_schedules_to_list()  # 一覧を更新して完了状態を反映
                            
                    # 「スケジュールの終了」タスクのチェックが外された場合、予定の完了状態を解除
                    elif not is_completed and checkbox.text() == "スケジュールの終了":
                        self.data_manager.update_schedule_completion(schedule_id, False)
                        self._load_schedules_to_list()  # 一覧を更新して完了状態を反映

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
            
            # 開始日時と終了日時を設定（シグナルをブロックして自動更新を防止）
            self.start_datetime_input.blockSignals(True)
            self.start_datetime_input.setDateTime(QDateTime.fromString(schedule_data[2], "yyyy-MM-dd HH:mm:ss"))
            self.start_datetime_input.blockSignals(False)
            
            self.end_datetime_input.setDateTime(QDateTime.fromString(schedule_data[3], "yyyy-MM-dd HH:mm:ss"))
            
            # 区分（category）を設定
            category_index = self.category_input.findText(schedule_data[5])
            if category_index != -1:
                self.category_input.setCurrentIndex(category_index)
                
            self.location_input.setText(schedule_data[4] or "")  # 場所
            self.details_content_input.setText(schedule_data[6] or "")  # 詳細内容
            
            # 通知設定を読み込む
            notification_minutes = None
            try:
                notification_minutes = schedule_data[9]  # notification_minutes カラムは9番目
            except IndexError:
                # 古いレコードの場合は通知設定なし
                pass
                
            if notification_minutes is not None:
                self.notification_enabled_checkbox.setChecked(True)
                self.notification_minutes_spinbox.setValue(notification_minutes)
                self.notification_minutes_spinbox.setEnabled(True)
            else:
                self.notification_enabled_checkbox.setChecked(False)
                self.notification_minutes_spinbox.setValue(30)
                self.notification_minutes_spinbox.setEnabled(False)
                
            # タスク通知設定を読み込む
            task_notification_minutes = None
            try:
                task_notification_minutes = schedule_data[12]  # task_notification_minutes カラムは12番目
            except IndexError:
                # 古いレコードの場合はタスク通知設定なし
                pass
                
            if task_notification_minutes is not None:
                self.task_notification_enabled_checkbox.setChecked(True)
                self.task_notification_minutes_spinbox.setValue(task_notification_minutes)
                self.task_notification_minutes_spinbox.setEnabled(True)
            else:
                self.task_notification_enabled_checkbox.setChecked(False)
                self.task_notification_minutes_spinbox.setValue(15)
                self.task_notification_minutes_spinbox.setEnabled(False)
            
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

    def _toggle_past_schedules(self):
        """過去の予定表示と現在の予定表示を切り替えます。"""
        self.show_past_schedules = not self.show_past_schedules
        self._load_schedules_to_list()
    
    def _toggle_schedule_lock(self):
        """選択中の予定のロック状態を切り替えます。"""
        if hasattr(self, 'current_selected_schedule_id') and self.current_selected_schedule_id:
            success = self.data_manager.toggle_schedule_lock(self.current_selected_schedule_id)
            if success:
                # 予定リストを再読み込み
                self._load_schedules_to_list()
                # 現在選択中の予定を再選択
                for i in range(self.schedule_list_widget.count()):
                    item = self.schedule_list_widget.item(i)
                    if item.data(Qt.UserRole) == self.current_selected_schedule_id:
                        self.schedule_list_widget.setCurrentItem(item)
                        break
            else:
                QMessageBox.warning(self, "操作失敗", "予定のロック状態を変更できませんでした。")
    
    def _delete_current_schedule(self):
        """選択中の予定を削除します。"""
        if hasattr(self, 'current_selected_schedule_id') and self.current_selected_schedule_id:
            schedule_data = self.schedules_data.get(self.current_selected_schedule_id)
            if schedule_data:
                title = schedule_data[1]
                reply = QMessageBox.question(
                    self, 
                    "削除確認", 
                    f"予定「{title}」を削除しますか？\nこの操作は元に戻せません。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    success = self.data_manager.delete_schedule(self.current_selected_schedule_id)
                    if success:
                        QMessageBox.information(self, "削除完了", f"予定「{title}」を削除しました。")
                        self._load_schedules_to_list()
                    else:
                        QMessageBox.warning(self, "削除失敗", "予定を削除できませんでした。ロックされている可能性があります。")

    def sync_google_calendar(self):
        QMessageBox.information(self, "同期", "Googleカレンダーとの同期機能を呼び出します。")

    def _update_end_datetime(self, start_datetime):
        """開始日時が変更されたときに終了日時を自動的に1時間後に設定する"""
        # 現在の終了日時を取得
        current_end_datetime = self.end_datetime_input.dateTime()
        
        # 新しい開始日時から1時間後の日時を計算
        new_end_datetime = start_datetime.addSecs(3600)
        
        # 終了日時を更新（シグナルをブロックして無限ループを防止）
        self.end_datetime_input.setDateTime(new_end_datetime)
        
        # 終了日時が開始日時より前になっていないか確認
        if self.end_datetime_input.dateTime() <= start_datetime:
            self.end_datetime_input.setDateTime(start_datetime.addSecs(3600))
    
    def _toggle_notification_settings(self, state):
        """スケジュール通知設定の有効/無効を切り替える"""
        is_enabled = state == 2  # Qt.CheckState.Checked = 2
        self.notification_minutes_spinbox.setEnabled(is_enabled)
        
    def _toggle_task_notification_settings(self, state):
        """タスク通知設定の有効/無効を切り替える"""
        is_enabled = state == 2  # Qt.CheckState.Checked = 2
        self.task_notification_minutes_spinbox.setEnabled(is_enabled)
    
    def _validate_end_datetime(self, end_datetime):
        """終了日時が開始日時より前にならないようにチェック"""
        start_datetime = self.start_datetime_input.dateTime()
        
        # 終了日時が開始日時より前の場合
        if end_datetime < start_datetime:
            # 終了日時を開始日時の1時間後に設定
            self.end_datetime_input.blockSignals(True)  # シグナルをブロックして無限ループを防止
            self.end_datetime_input.setDateTime(start_datetime.addSecs(3600))
            self.end_datetime_input.blockSignals(False)
            
            # ユーザーに通知
            QMessageBox.warning(self, "入力エラー", "終了日時は開始日時よりも後に設定してください。\n自動的に開始時刻の1時間後に設定しました。")
    
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