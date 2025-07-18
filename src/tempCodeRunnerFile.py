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