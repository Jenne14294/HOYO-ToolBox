import functions
import sys
import subprocess
import requests

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QLabel, QWidget, QPushButton, QProgressBar, QHBoxLayout
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt5.QtGui import QIcon

language_dict = {
    "zh-TW":"繁體中文(台灣)",
    "zh-CN":"简体中文(中国)",
    "en-US":"English",
    "ja-JP":"日本語"
}

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, download_data):
        super().__init__()
        self.url = download_data["url"]
        self.save_path = download_data["path"]
        self.total_size = download_data["total_size"]
        self._is_running = True
        self._pause_flag = False
        self._mutex = QMutex()
        self._condition = QWaitCondition()

    def run(self):
        response = requests.get(self.url, stream=True)
        downloaded_size = 0

        with open(self.save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                self._mutex.lock()
                while self._pause_flag:
                    self._condition.wait(self._mutex)
                self._mutex.unlock()

                if not self._is_running:
                    break
                if chunk:
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    progress = int((downloaded_size / self.total_size) * 100)
                    self.progress.emit(progress)

        if self._is_running:
            self.finished.emit()

    def pause(self):
        self._mutex.lock()
        self._pause_flag = True
        self._mutex.unlock()

    def resume(self):
        self._mutex.lock()
        self._pause_flag = False
        self._condition.wakeAll()
        self._mutex.unlock()

    def stop(self):
        self._is_running = False
        self.resume()

class DownloadWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HOYO ToolBox")
        self.setGeometry(300, 300, 400, 150)
        self.setFixedSize(400, 150)

        # 建立元件
        self.label = QLabel("下載進度：", self)
        self.progress_bar = QProgressBar(self)
        self.open_button = QPushButton("完成", self)
        self.pause_button = QPushButton("暫停", self)
        self.resume_button = QPushButton("繼續", self)

        self.open_button.hide()
        self.resume_button.hide()

        # 佈局
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addWidget(self.open_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 模擬下載資料
        self.download_data = functions.download_release()

        # 初始化下載執行緒
        self.download_thread = DownloadThread(self.download_data)
        self.download_thread.progress.connect(self.progress_bar.setValue)
        self.download_thread.finished.connect(self.download_finished)

        self.open_button.clicked.connect(self.open_main_window)
        self.pause_button.clicked.connect(self.pause_download)
        self.resume_button.clicked.connect(self.resume_download)

        # 啟動下載
        self.progress_bar.setValue(0)
        self.download_thread.start()

    def open_main_window(self):
        program_path = "./HOYO ToolBox.exe"  # 修改為目標程式的路徑
        subprocess.Popen([program_path], shell=True)
        sys.exit()

    def download_finished(self):
        data = functions.download_release()
        functions.apply_update(data['path'], data['version'])
        # 模擬更新操作
        self.label.setText("下載完成！")
        self.open_button.show()
        self.pause_button.hide()
        self.resume_button.hide()

    def pause_download(self):
        self.download_thread.pause()
        self.pause_button.hide()
        self.resume_button.show()

    def resume_download(self):
        self.download_thread.resume()
        self.resume_button.hide()
        self.pause_button.show()




# 主函式
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("./assets/icons/icon.png"))
    download_window = DownloadWidget()
    download_window.show()
    sys.exit(app.exec_())
