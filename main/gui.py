import os
import json
import configparser
import asyncio
import sys
import subprocess
import time

import functions # 引入我們的大腦！
import GenshinAPI
import isodate

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QComboBox, QFrame, QPushButton, QScrollArea, 
                             QSizePolicy, QRadioButton, QButtonGroup, QLayout, QStyle,
                             QFileDialog, QMessageBox, QDialog, QTextEdit)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QFontDatabase

# ==============================
# 全局變數與設定初始化
# ==============================
local_folder_path = os.environ.get("LOCALAPPDATA")
data_path = os.path.join(local_folder_path, "HoYo ToolBox")  # pyright: ignore[reportArgumentType, reportCallIssue]
config = configparser.ConfigParser()

os.makedirs(f"{data_path}/user_data",exist_ok=True)
os.makedirs(f"{data_path}/diary",exist_ok=True)

if not os.path.exists("./config.ini"):
    config.add_section('General')
    config.set('General', 'Author', 'Jenne14294')
    config.set('General', 'AppName', 'HOYO ToolBox')
    config.set('General', 'version', '1.17')
    config.add_section('Settings')
    config.set('Settings', 'Language', 'zh-TW')
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

config.read('config.ini')
version = config['General']['version']

def check_version():
    status = functions.check_version()
    if status:
        if ask_update():
            program_path = ".\\updater\\updater.exe"
            subprocess.Popen([program_path], shell=True)
            sys.exit()
    else:
        info_dialog = QMessageBox()
        info_dialog.setIcon(QMessageBox.Information)
        info_dialog.setWindowTitle("HOYO ToolBox")
        info_dialog.setText("沒有發現新版本！")
        info_dialog.setStandardButtons(QMessageBox.Ok)
        info_dialog.exec_()

def ask_update():
    reply = QMessageBox.question(QWidget(), "HOYO ToolBox", "發現新版本，是否要更新到最新版本？",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    return reply == QMessageBox.Yes

# ==============================
# UI 輔助類別 (流式佈局與卡片)
# ==============================
class FlowLayout(QLayout):
    """自動換行的流式佈局"""
    def __init__(self, parent=None, margin=-1, hSpacing=-1, vSpacing=-1):
        super().__init__(parent)
        self._item_list = []
        if margin >= 0: self.setContentsMargins(margin, margin, margin, margin)
        self._h_space = hSpacing
        self._v_space = vSpacing

    def __del__(self):
        item = self.takeAt(0)
        while item: item = self.takeAt(0)

    def addItem(self, item): self._item_list.append(item)
    def horizontalSpacing(self): return self._h_space if self._h_space >= 0 else self.smartSpacing(QStyle.PM_LayoutHorizontalSpacing)
    def verticalSpacing(self): return self._v_space if self._v_space >= 0 else self.smartSpacing(QStyle.PM_LayoutVerticalSpacing)
    def count(self): return len(self._item_list)
    def itemAt(self, index): return self._item_list[index] if 0 <= index < len(self._item_list) else None
    def takeAt(self, index): return self._item_list.pop(index) if 0 <= index < len(self._item_list) else None
    def expandingDirections(self): return Qt.Orientations(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self.doLayout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self._item_list: size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size
    def smartSpacing(self, pm):
        parent = self.parent()
        if not parent: return -1
        elif parent.isWidgetType(): return parent.style().pixelMetric(pm, None, parent)
        else: return parent.spacing()
    def doLayout(self, rect, testOnly):
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self._item_list:
            wid = item.widget()
            spaceX = self.horizontalSpacing()
            if spaceX == -1: spaceX = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = self.verticalSpacing()
            if spaceY == -1: spaceY = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                line_height = 0
            if not testOnly: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = nextX
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y()

class RecordItem(QFrame):
    """單筆抽卡紀錄卡片 (支援懸停時間與歪標記)"""
    def __init__(self, name, pity, time_str, is_wry=False):
        super().__init__()
        self.name = name
        self.pity = pity
        self.time_str = time_str
        self.is_wry = is_wry
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedSize(240, 70) 
        self.setToolTip(f"抽取時間：\n{self.time_str}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)

        self.name_label = QLabel(self.name)
        font_id = QFontDatabase.addApplicationFont("./assets/font.ttf")
        if font_id != -1:
            custom_font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.name_label.setFont(QFont(custom_font_family, 25, QFont.Bold))
        else:
            self.name_label.setFont(QFont("Microsoft JhengHei", 25, QFont.Bold))
        layout.addWidget(self.name_label)

        if self.is_wry:
            self.wry_label = QLabel("歪")
            self.wry_label.setAlignment(Qt.AlignCenter)
            self.wry_label.setFixedSize(40, 40)
            self.wry_label.setStyleSheet("background-color: #D32F2F; color: white; border-radius: 14px; font-weight: bold; font-size: 20px;")
            layout.addWidget(self.wry_label)

        layout.addStretch() 

        self.pity_label = QLabel(f"{self.pity} 抽")
        self.pity_label.setFont(QFont("Consolas", 25, QFont.Bold))
        layout.addWidget(self.pity_label)

        if self.pity < 40: color = "#8BC34A" # 綠
        elif self.pity <= 69: color = "#FF9800" # 橘
        else: color = "#F44336" # 紅

        self.setStyleSheet(f"""
            RecordItem {{ border: 2px solid #222; border-radius: 8px; background-color: {color}; }}
            QLabel {{ color: white; border: none; background: transparent; }}
        """)

class InputDialog(QDialog):
    """手動輸入對話框"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("輸入框")
        main_layout = QVBoxLayout()
        self.label = QLabel("請輸入五星角色/武器和抽數\n每行只能填一個角色或武器\n格式：<角色/武器><抽數>")
        main_layout.addWidget(self.label)
        self.text_input = QTextEdit(self)
        main_layout.addWidget(self.text_input)
        radio_layout = QHBoxLayout()
        self.role_radio = QRadioButton("角色", self)
        self.weapon_radio = QRadioButton("武器", self)
        self.role_radio.setChecked(True)
        radio_layout.addWidget(self.role_radio)
        radio_layout.addWidget(self.weapon_radio)
        main_layout.addLayout(radio_layout)
        self.ok_button = QPushButton("開始計算", self)
        self.ok_button.clicked.connect(self.accept)
        main_layout.addWidget(self.ok_button)
        self.setLayout(main_layout)
        self.setStyleSheet("QWidget { background-color: #2b2b2b; color: white; } QPushButton { background-color: #4CAF50; padding: 10px; border-radius: 5px; }")

    def get_input_text(self): return self.text_input.toPlainText()

class FetchDataThread(QThread):
    update_signal = pyqtSignal(str) 
    finished_signal = pyqtSignal()
    def __init__(self, selected_game):
        super().__init__()
        self.selected_game = selected_game
    def run(self):
        try:
            if self.selected_game == "原神":
                self.update_signal.emit("正在讀取原神歷史紀錄，請稍等...")
                functions.get_GSdata_by_api()
            elif self.selected_game == "崩鐵":
                self.update_signal.emit("正在讀取崩鐵歷史紀錄，請稍等...")
                functions.get_HSRdata_by_api()
            elif self.selected_game == "絕區零":
                self.update_signal.emit("正在讀取絕區零歷史紀錄，請稍等...")
                functions.get_ZZZdata_by_api()
            self.update_signal.emit("抽卡紀錄已讀取")
            self.finished_signal.emit()
        except Exception as e:
            self.update_signal.emit(f"讀取失敗，請先在遊戲裡打開抽卡歷史紀錄")

# ==============================
# 主視窗 (UI 結合 邏輯)
# ==============================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HOYO ToolBox")
        self.resize(1000, 750)
        self.init_ui()
        self.apply_global_style()
        self.change_game()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ----------------- 左側面板 -----------------
        self.left_panel = QFrame()
        self.left_panel.setObjectName("Panel")
        self.left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(15)

        left_layout.addWidget(QLabel("選擇遊戲："))
        self.GameIconGroup = QButtonGroup(self)
        games = [("原神", "./assets/icons/GI.jpeg"), ("崩鐵", "./assets/icons/hsr.png"), ("絕區零", "./assets/icons/zzz.png")]
        
        for name, icon_path in games:
            btn = QRadioButton(name)
            btn.setIcon(QIcon(QPixmap(icon_path)))
            btn.setIconSize(QSize(64, 64))
            self.GameIconGroup.addButton(btn)
            left_layout.addWidget(btn)
        self.GameIconGroup.buttons()[0].setChecked(True)
        for btn in self.GameIconGroup.buttons():
            btn.toggled.connect(self.change_game)

        left_layout.addWidget(QLabel("選擇紀錄帳號："))
        self.account_combo = QComboBox()
        self.account_combo.setStyleSheet("font-size: 24px; padding: 5px;")
        self.account_combo.currentTextChanged.connect(self.update_account_display)
        left_layout.addWidget(self.account_combo)

        self.btn_read = QPushButton("讀取歷史紀錄")
        self.btn_read.setObjectName("OutlineBtn")
        self.btn_read.clicked.connect(self.fetch_data)
        left_layout.addWidget(self.btn_read)

        left_layout.addWidget(QLabel("外部輸入："))
        self.external_combo = QComboBox()
        self.external_combo.addItems(["==選擇方式==", "導入 JSON", "手動輸入"])
        self.external_combo.setStyleSheet("font-size: 14px; padding: 5px;")
        self.external_combo.currentTextChanged.connect(self.external_data)
        left_layout.addWidget(self.external_combo)

        self.btn_export = QPushButton("導出紀錄")
        self.btn_export.setObjectName("OutlineBtn")
        self.btn_export.clicked.connect(self.export_data)
        left_layout.addWidget(self.btn_export)

        self.btn_update = QPushButton("檢查更新")
        self.btn_update.setObjectName("OutlineBtn")
        self.btn_update.clicked.connect(check_version)
        left_layout.addWidget(self.btn_update)

        left_layout.addStretch()
        self.version_label = QLabel(f"v {version}")
        self.version_label.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        left_layout.addWidget(self.version_label)

        # ----------------- 右側面板 -----------------
        self.right_panel = QFrame()
        self.right_panel.setObjectName("Panel")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)

        self.banner_layout = QHBoxLayout()
        self.GachaTypeButtonList = []
        for i in range(6): 
            btn = QPushButton(f"按鈕 {i + 1}")
            btn.setObjectName("OutlineBtn")
            btn.clicked.connect(lambda checked, idx=i: self.show_game_options(idx))
            self.banner_layout.addWidget(btn)
            self.GachaTypeButtonList.append(btn)
        right_layout.addLayout(self.banner_layout)

        self.history_title = QLabel("新手")
        self.history_title.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 16px; padding: 10px; border-radius: 5px;")
        right_layout.addWidget(self.history_title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: transparent;")
        
        self.flow_container = QWidget()
        self.flow_layout = FlowLayout(self.flow_container, margin=5, hSpacing=15, vSpacing=15)
        self.flow_container.setLayout(self.flow_layout)
        self.scroll_area.setWidget(self.flow_container)
        right_layout.addWidget(self.scroll_area, stretch=1)

        self.summary_label = QLabel("正在讀取資料...")
        self.summary_label.setObjectName("SummaryBox")
        self.summary_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        right_layout.addWidget(self.summary_label)

        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(self.right_panel, stretch=1)

    # ----------------------------------------
    # 核心邏輯區
    # ----------------------------------------

    def change_game(self):
        sender = self.sender()
        if sender and hasattr(sender, 'isChecked') and not sender.isChecked():
            return

        accounts = self.get_accounts()
        self.account_combo.blockSignals(True) 
        self.account_combo.clear()
        self.account_combo.addItems(accounts)
        self.account_combo.blockSignals(False)
        self.external_combo.setCurrentIndex(0)
        self.show_game_options(0) 

    def update_account_display(self, account_name):
        if account_name:
            self.show_game_options(0)

    def get_accounts(self):
        account_options = []
        folder_path = f"{data_path}/user_data"
        selected_game = self.GameIconGroup.checkedButton().text()
        if not os.path.exists(folder_path): return account_options
        for file in os.listdir(folder_path):
            start_index = file.find("_", 10)
            end_index = file.find(".json")
            if selected_game == "原神" and file.startswith("GenshinImpact"):
                account_options.append(file[start_index + 1:end_index])
            elif selected_game == "崩鐵" and file.startswith("Honkai_StarRail"):
                account_options.append(file[start_index + 1:end_index])
            elif selected_game == "絕區零" and file.startswith("ZenlessZoneZero"):
                account_options.append(file[start_index + 1:end_index])
        return account_options

    def show_game_options(self, idx=None):
        idx = 0 if not idx else idx
        selected_game = self.GameIconGroup.checkedButton().text()
        
        if selected_game == "原神":
            options = ["資訊", "新手", "常駐", "角色", "武器", "集錄"]
            gameText = "GenshinImpact"
        elif selected_game == "崩鐵":
            options = ["資訊", "新手", "常駐", "角色", "光錐", "聯動角色", "聯動武器"]
            gameText = "Honkai_StarRail"
        else:
            options = ["資訊", "常駐", "代理人", "音擎", "邦布"]
            gameText = "ZenlessZoneZero"

        for i in range(6):
            if i < len(options) - 1:
                self.GachaTypeButtonList[i].setText(options[i + 1])
                self.GachaTypeButtonList[i].show()
            else:
                self.GachaTypeButtonList[i].hide()

        accountID = self.account_combo.currentText()
        if not accountID:
            self.summary_label.setText("找不到帳號資料，請先讀取歷史紀錄")
            self.history_title.setText(options[idx + 1] if idx + 1 < len(options) else "")
            self.clear_flow_layout()
            return

        path = f"{data_path}/user_data/{gameText}_{accountID}.json"
        self.clear_flow_layout()
        banner_name = options[idx + 1]
        self.history_title.setText(banner_name)

        if os.path.exists(path):
            with open(path, "r", encoding="utf8") as file:
                data = json.load(file)

            keys = list(data.keys())
            if "info" in keys: keys.remove("info")
            if idx < len(keys):
                
                cards_to_show = []
                counter = 0
                last_was_standard = False 

                old_to_new_data = data[keys[idx]][::-1]

                for items in old_to_new_data:
                    counter += 1
                    rank_type = str(items.get('rank_type', '3'))
                    name = items.get('name', '未知')
                    time_str = items.get('time', '未知時間')
                    
                    is_high_rank = (selected_game != "絕區零" and rank_type == '5') or (selected_game == "絕區零" and rank_type == "4")
                    
                    if is_high_rank:
                        # 呼叫 functions.py 來判斷這是不是常駐大獎
                        is_standard = functions.check_is_standard(selected_game, banner_name, name)
                        
                        # 如果上一隻是常駐，且這池不是新手/常駐池，這隻就是「歪」的大保底
                        is_wry = last_was_standard if banner_name not in ["新手", "常駐"] else False

                        item_widget = RecordItem(name, counter, time_str, is_wry)
                        cards_to_show.append(item_widget)

                        # 更新記憶狀態給下一隻用
                        last_was_standard = is_standard if banner_name not in ["新手", "常駐"] else False
                        counter = 0

                for widget in reversed(cards_to_show):
                    self.flow_layout.addWidget(widget)

            try:
                input_data = functions.get_average(idx, path, selected_game, "")
                self.summary_label.setText(input_data)
            except:
                self.summary_label.setText("無法計算平均數據")

    def clear_flow_layout(self):
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def fetch_data(self):
        selected_game = self.GameIconGroup.checkedButton().text()
        self.thread = FetchDataThread(selected_game)
        self.thread.update_signal.connect(lambda text: self.summary_label.setText(text))
        self.thread.finished_signal.connect(self.on_thread_finished)
        self.thread.start()

    def on_thread_finished(self):
        self.change_game() 

    def export_data(self):
        folder_path = QFileDialog.getExistingDirectory(self, "選擇資料夾", "")
        if folder_path:
            try:
                accountID = self.account_combo.currentText()
                selected_game = self.GameIconGroup.checkedButton().text()
                gameText = "GenshinImpact" if selected_game == "原神" else "Honkai_StarRail" if selected_game == "崩鐵" else "ZenlessZoneZero"
                file_path = f"{data_path}/user_data/{gameText}_{accountID}.json"
                
                if not os.path.exists(file_path):
                    QMessageBox.critical(self, "錯誤", "檔案不存在!")
                    return

                export_path = os.path.join(folder_path, f"{gameText}_{accountID}_export.json")
                functions.export_json(file_path, export_path, selected_game)
                QMessageBox.information(self, "提示", "歷史紀錄已導出！")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"導出失敗\n{e}")

    def external_data(self, input_name):
        if input_name == "手動輸入":
            dialog = InputDialog()
            if dialog.exec_() == QDialog.Accepted:
                text = dialog.get_input_text()
                selected_game = self.GameIconGroup.checkedButton().text()
                result = functions.get_average("", selected_game, text)
                self.summary_label.setText(result)
            self.external_combo.setCurrentIndex(0)
        
        elif input_name == "導入 JSON":
            file_path, _ = QFileDialog.getOpenFileName(self, "打開檔案", "", "JSON 檔案 (*.json)")
            if file_path:
                selected_game = self.GameIconGroup.checkedButton().text()
                gameText = "GenshinImpact" if selected_game == "原神" else "Honkai_StarRail" if selected_game == "崩鐵" else "ZenlessZoneZero"
                system_path = f"{data_path}/user_data/{gameText}.json"
                
                extracted_data = functions.extract_data(selected_game, file_path)
                if extracted_data == "錯誤的遊戲資料":
                    QMessageBox.critical(self, "錯誤", "錯誤或無法解析的歷史紀錄")
                    return

                account = extracted_data['info']['uid']
                system_path = system_path[:-5] + f"_{account}.json"

                if os.path.exists(system_path):
                    extracted_data = functions.compare_input_data(system_path, extracted_data, selected_game)

                with open(system_path, "w", encoding="utf8") as file:
                    json.dump(extracted_data, file, indent=4, ensure_ascii=False)

                self.change_game()
                self.account_combo.setCurrentText(account)
            self.external_combo.setCurrentIndex(0)

    # ----------------------------------------
    # QSS 全局設計樣式
    # ----------------------------------------
    def apply_global_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
                font-family: "Microsoft JhengHei";
            }
            QFrame#Panel {
                background-color: #383838; 
                border-radius: 10px;
            }
            QLabel { font-size: 16px; }
            
            QRadioButton {
                color: white; 
                background-color: transparent;
                spacing: 10px; 
            }
            
            QPushButton#OutlineBtn {
                background-color: transparent;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton#OutlineBtn:hover {
                background-color: rgba(76, 175, 80, 0.2);
            }
            QPushButton#OutlineBtn:pressed {
                background-color: #4CAF50;
            }
            QComboBox {
                background-color: transparent;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                color: white;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #383838;
                border: 1px solid #4CAF50;
            }
            QLabel#SummaryBox {
                background-color: #444444;
                border-radius: 5px;
                padding: 10px;
                font-size: 16px;
                min-height: 80px;
            }
            QScrollBar:vertical {
                background: #2B2C3C; 
                border-radius: 5px; width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #4CAF50; border-radius: 5px; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { background: none; }
            
            QToolTip {
                background-color: #383838;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
            }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("./assets/icons/icon.png"))
    
    status = functions.check_version()
    if status:
        if ask_update():
            program_path = ".\\updater\\updater.exe"
            subprocess.Popen([program_path], shell=True)
            sys.exit()

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())