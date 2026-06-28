import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from modules.logger import setup_logging
setup_logging(logging.INFO)

from modules.feedback_checker import check_feedback

if __name__ == "__main__":
    count: int = check_feedback()
    if count:
        print(f"已更新 {count} 条反馈评分")
    else:
        print("未发现新的反馈回复")
