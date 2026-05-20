"""
Arkanalyzer Knowledge Graph System - File Watcher
====================================================
基于第一性原理：文件系统的本质是「事件的流」，
监听器捕获变化事件并触发增量更新。
"""

import os
import time
import threading
import logging
from datetime import datetime

from system_configuration import FILE_WATCH_INTERVAL_SECONDS, SUPPORTED_SOURCE_EXTENSIONS

logger = logging.getLogger(__name__)


class FileChangeWatcher:
    """文件变化监听器"""

    def __init__(self, watch_directory, callback=None):
        self.watch_directory = watch_directory
        self.callback = callback
        self.file_snapshot = {}
        self.running = False
        self.watch_thread = None
        self.change_count = 0

    def _scan_files(self):
        """扫描目录获取文件快照"""
        current_files = {}
        for root_dir, sub_dirs, file_names in os.walk(self.watch_directory):
            sub_dirs[:] = [d for d in sub_dirs if not d.startswith((".", "__"))]
            for file_name in file_names:
                extension = os.path.splitext(file_name)[1].lower()
                if extension in SUPPORTED_SOURCE_EXTENSIONS:
                    full_path = os.path.join(root_dir, file_name)
                    try:
                        modification_time = os.path.getmtime(full_path)
                        current_files[full_path] = modification_time
                    except OSError:
                        continue
        return current_files

    def _detect_changes(self):
        """检测文件变化"""
        current_snapshot = self._scan_files()
        changed_files = []
        new_files = []
        deleted_files = []

        # 检测修改和新增文件
        for file_path, mod_time in current_snapshot.items():
            if file_path not in self.file_snapshot:
                new_files.append(file_path)
            elif mod_time > self.file_snapshot[file_path]:
                changed_files.append(file_path)

        # 检测删除文件
        for file_path in self.file_snapshot:
            if file_path not in current_snapshot:
                deleted_files.append(file_path)

        self.file_snapshot = current_snapshot
        return changed_files, new_files, deleted_files

    def _watch_loop(self):
        """监听循环"""
        logger.info(f"开始监听目录: {self.watch_directory}")
        self.file_snapshot = self._scan_files()

        while self.running:
            time.sleep(FILE_WATCH_INTERVAL_SECONDS)
            if not self.running:
                break

            changed, new, deleted = self._detect_changes()
            all_changes = changed + new

            if all_changes or deleted:
                self.change_count += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(
                    f"[{timestamp}] 检测到变化: "
                    f"修改={len(changed)}, 新增={len(new)}, 删除={len(deleted)}"
                )

                if self.callback:
                    try:
                        self.callback(all_changes, deleted, self.change_count)
                    except Exception as exception:
                        logger.error(f"回调执行失败: {exception}")

    def start_watching(self):
        """启动文件监听"""
        if self.running:
            return
        self.running = True
        self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.watch_thread.start()

    def stop_watching(self):
        """停止文件监听"""
        self.running = False
        if self.watch_thread:
            self.watch_thread.join(timeout=5)
        logger.info("文件监听已停止")

    def get_status(self):
        """获取监听状态"""
        return {
            "running": self.running,
            "watchDirectory": self.watch_directory,
            "trackedFiles": len(self.file_snapshot),
            "totalChanges": self.change_count
        }
