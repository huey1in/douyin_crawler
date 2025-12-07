#!/usr/bin/env python3
"""
抖音直播间爬虫启动脚本
"""

import sys
import os

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from douyin_live_crawler import main

if __name__ == "__main__":
    main()