import sqlite3
import os
from datetime import datetime

class DataManager:
    def __init__(self, db_name="schedule.db"):
        # プロジェクトのルートにある data ディレクトリ内にDBファイルを配置
        # __file__ は現在のファイル(data_manager.py)のパス
        # os.path.dirname(__file__) は src ディレクトリ
        # os.path.dirname(os.path.dirname(__file__)) は MyScheduleManager ディレクトリ
        # os.path.join(..., "data") で MyScheduleManager/data ディレクトリを指定
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        
        # dataディレクトリが存在しない場合は作成
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"dataディレクトリを作成しました: {data_dir}")
        
        self.db_path = os.path.join(data_dir, db_name)
        self.conn = None #接続オブジェクト
        self.cursor = None #カーソルオブジェクト
        self._connect() #データベースに接続
        self._create_tables() #テーブルを作成

    def _connect(self):
        """データベースに接続"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            print(f"データベースに接続しました: {self.db_path}")
        except sqlite3.Error as e:
            print(f"データベース接続エラー: {e}")
            self.conn = None
            self.cursor = None

    def _create_tables(self):
        """必要なテーブルを作成します（存在しない場合)"""
        if not self.conn:
            print("データベース接続が確率されていないため、テーブルを作成できません")
            return
        
        try:
            #schedulesテーブル: 予定の基本情報
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    start_datatime TEXT NOT NULL,
                    end_datatime TEXT NOT NULL,
                    category TEXT,
                    location TEXT,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            #tasksテーブル: 各予定に紐づくタスク
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id INTEGER NOT NULL,
                    task_description TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0, -- 0:未完了, 1:完了
                    completed_at TEXT,
                    FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
                )
            ''')
            print("データベーステーブルが正常に作成または確認されました。")
        except sqlite3.Error as e:
            print(f"テーブル作成エラー: {e}")
    
    def save_schedule(self, title,start_dt,end_dt,category,location,description):
        """新しい予定をデータベースに保存します。"""
        if not self.conn:
            print("データベース接続が確立されていないため、予定を保存できません。")
            return None
        
        created_at = datetime.now().isoformat()
        try:
            self.cursor.execute('''
                INSERT INTO schedules (title, start_datatime, end_datatime, category, location, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, start_dt, end_dt, category, location, description, created_at,))
            self.conn.commit()
            schedule_id = self.cursor.lastrowid #挿入されたレコードIDを取得
            print(f"予定'{title}'がID{schedule_id}で保存されました。")
            return schedule_id
        except sqlite3.Error as e:
            print(f"予定保存エラー: {e}")
            return None
    
    def save_task(self, schedule_id, tasks_list):
        """指定された予定に紐づくタスクをデータベースに保存します。"""
        if not self.conn:
            print("データベース接続が確立されていないため、タスクを保存できません。")
            return
        
        try:
            #既存のタスクをいったん削除して再挿入する（シンプルにするための実装）
            self.cursor.execute("DELETE FROM tasks WHERE schedule_id = ?", (schedule_id,))

            for task_desc in tasks_list:
                if task_desc in tasks_list:
                    self.cursor.execute('''
                        INSERT INTO tasks (schedule_id, task_description)
                        VALUES (?, ?)
                    ''', (schedule_id, task_desc))
            self.conn.commit()
            print(f"予定ID{schedule_id}に紐づくタスクが保存されました。")
        except sqlite3.Error as e:
            print(f"タスク保存エラー: {e}")

    def get_all_schedules(self):
        """すべての予定を取得します。"""
        if not self.conn:
            print("データベース接続が確立されていないため、予定を取得できません。")
            return []
        
        self.cursor.execute("SELECT * FROM schedules ORDER BY start_datatime ASC")
        #カラム名付きで結果を取得できるように、row_factoryを設定することもできるが、ここではタプルに返す
        return self.cursor.fetchall()
    
    def get_tasks_for_schedule(self, schedule_id):
        """特定の予定に紐づくタスクを取得します。"""
        if not self.conn:
            print("データベース接続が確立されていないため、タスクを取得できません。")
            return []
        
        self.cursor.execute("SELECT id, task_description, is_comleted FROM tasks WHERE schedule_id = ?", (schedule_id,))
        return self.cursor.fetchall()
    
    def update_task_completion(self, task_id, is_completed):
        """タスクの完了状態を更新します。"""
        if not self.conn:
            print("データベース接続が確立されていないため、タスクの状態を更新できません。")
            return

        completed_at = datetime.now().isoformat() if is_completed else None
        try:
            self.cursor.execute('''
                UPDATE tasks SET is_completed = ?, completed_at = ? WHERE id = ?
            ''', (1 if is_completed else 0, completed_at, task_id))
            self.conn.commit()
            print(f"タスクID {task_id} の完了状態を更新しました: {is_completed}")
        except sqlite3.Error as e:
            print(f"タスク状態の更新エラー: {e}")

    def close(self):
        """データベース接続を閉じます。"""
        if self.conn:
            self.conn.close()
            print("データベース接続を閉じました。")

# デバッグ用のテストコード (このファイルが直接実行された場合にのみ実行)
if __name__ == "__main__":
    dm = DataManager()

    # テストデータの保存
    print("\n--- 予定の保存テスト ---")
    schedule_id1 = dm.save_schedule(
        "会議",
        "2025-07-16 10:00:00",
        "2025-07-16 11:00:00",
        "仕事",
        "オンライン",
        "プロジェクト進捗報告"
    )
    if schedule_id1:
        dm.save_tasks(schedule_id1, ["資料作成", "アジェンダ確認"])

    schedule_id2 = dm.save_schedule(
        "病院",
        "2025-07-17 14:00:00",
        "2025-07-17 15:00:00",
        "プライベート",
        "〇〇病院",
        "定期検診"
    )
    if schedule_id2:
        dm.save_tasks(schedule_id2, ["保険証持参", "予約確認電話"])

    # 全ての予定を取得して表示
    print("\n--- 全予定の取得テスト ---")
    schedules = dm.get_all_schedules()
    for sch in schedules:
        print(f"ID: {sch[0]}, タイトル: {sch[1]}, 開始: {sch[2]}")
        tasks = dm.get_tasks_for_schedule(sch[0])
        for task in tasks:
            print(f"  - タスク: {task[1]} (完了: {'はい' if task[2] else 'いいえ'})")
            # タスク完了状態の更新テスト
            if "資料作成" in task[1] and task[2] == 0:
                print(f"    -> タスク '{task[1]}' を完了済みに更新")
                dm.update_task_completion(task[0], True)
    
    print("\n--- 更新後の予定の取得テスト ---")
    schedules = dm.get_all_schedules()
    for sch in schedules:
        print(f"ID: {sch[0]}, タイトル: {sch[1]}, 開始: {sch[2]}")
        tasks = dm.get_tasks_for_schedule(sch[0])
        for task in tasks:
            print(f"  - タスク: {task[1]} (完了: {'はい' if task[2] else 'いいえ'})")


    dm.close() # 最後に接続を閉じる

