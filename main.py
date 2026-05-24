#!/usr/bin/env python3
"""
LiveStream Pro - Stream 24/7 lên YouTube, Facebook, TikTok
"""
import sys
import os

# Đảm bảo thư mục gốc trong PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import LiveStreamApp

if __name__ == "__main__":
    app = LiveStreamApp()
    app.run()
