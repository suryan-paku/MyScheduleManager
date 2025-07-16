import sys
import os

# プロジェクトのルートディレクトリをsys.pathに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gui import run_gui

def main():
    print("スケジュールマネージャーを起動します。")
    run_gui()

if __name__ == "__main__":
    main()