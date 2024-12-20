import os
import json
import configparser
import asyncio
import GenshinAPI
import functions
import sys
import isodate
import subprocess
import time

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup, QLabel, QComboBox, QWidget, QFrame, QPushButton, QScrollArea, QFileDialog, QMessageBox, QDialog, QTextEdit, QStackedWidget, QProgressBar
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl, Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QFontDatabase, QIcon, QPixmap, QBrush, QColor
from PyQt5.QtChart import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis

from datetime import datetime, timedelta
from genshin.errors import AccountNotFound, GenshinException

local_folder_path = os.environ.get("LOCALAPPDATA")
data_path = os.path.join(local_folder_path, "HoYo ToolBox") # pyright: ignore[reportCallIssue, reportArgumentType]
config = configparser.ConfigParser()
language_dict = {
    "zh-TW":"繁體中文(台灣)",
    "zh-CN":"简体中文(中国)",
    "en-US":"English",
    "ja-JP":"日本語"
}

os.makedirs(f"{data_path}/user_data",exist_ok=True)
os.makedirs(f"{data_path}/diary",exist_ok=True)

if not os.path.exists("./config.ini"):
    config.add_section('General')
    config.set('General', 'Author', 'Jenne14294')
    config.set('General', 'AppName', 'HOYO ToolBox')
    config.set('General', 'version', '1.13')

    config.add_section('Settings')
    config.set('Settings', 'Language', 'en-US')

    with open('config.ini', 'w') as configfile:
        config.write(configfile)

game = "原神"

def check_version():
        status = functions.check_version()
        if status:
            update_ans = ask_update()

            if update_ans:
                window.close()
                program_path = ".\\updater\\updater.exe"  # 修改為目標程式的路徑
                subprocess.Popen([program_path], shell=True)

        else:
            info_dialog = QMessageBox()
            info_dialog.setIcon(QMessageBox.Information)  # 設置為信息類型
            info_dialog.setWindowTitle("HOYO ToolBox")
            info_dialog.setText("沒有發現新版本！")
            info_dialog.setStandardButtons(QMessageBox.Ok)  # 添加「確定」按鈕

            info_dialog.exec_()

def ask_update():
    # 彈出訊息框詢問是否更新
    reply = QMessageBox.question(QWidget(), "HOYO ToolBox", "發現新版本，是否要更新到最新版本？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

    if reply == QMessageBox.Yes:
        return True
    
    return False

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("HOYO ToolBox")
        self.setGeometry(0, 0, 720, 480)
        self.now_function = "抽卡紀錄"
        self.web_button_function = ""
        self.update_signal = pyqtSignal(str)
        self.app_font = "Arial"
        self.drawing_enabled = False

        try:
            self.font_path = "./assets/font.ttf"
            self.font_id = QFontDatabase.addApplicationFont(self.font_path)
            self.font_family = QFontDatabase.applicationFontFamilies(self.font_id)[0]

            self.app_font = self.font_family
            self.setFont(QFont(self.app_font))

        except:
            pass

        # 主水平布局，左右比例 1:9
        main_layout = QHBoxLayout()

        # 左邊垂直區塊
        self.left_frame = QFrame()
        self.left_frame.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout()

        # 添加遊戲選項 RadioButtons
        self.game_label = QLabel("選擇遊戲：")
        self.radio_1 = QRadioButton("原神")
        self.radio_1.setIcon(QIcon(QPixmap("./assets/icons/GI.jpeg")))
        self.radio_1.setIconSize(QSize(64, 64))
        self.radio_1.setStyleSheet("""
            QRadioButton {
                color: transparent;
                background-color: #2E2E2E; /* 深灰色背景 */
                QRadioButton::indicator { width: 0; height: 0; }
            }
        """)

        self.radio_2 = QRadioButton("崩鐵")
        self.radio_2.setIcon(QIcon(QPixmap("./assets/icons/hsr.png")))
        self.radio_2.setIconSize(QSize(64, 64))
        self.radio_2.setStyleSheet("""
            QRadioButton {
                color: transparent;
                background-color: #2E2E2E; /* 深灰色背景 */
                QRadioButton::indicator { width: 0; height: 0; }
            }
        """)

        self.radio_3 = QRadioButton("絕區零")
        self.radio_3.setIcon(QIcon(QPixmap("./assets/icons/zzz.png")))
        self.radio_3.setIconSize(QSize(64, 64))
        self.radio_3.setStyleSheet("""
            QRadioButton {
                color: transparent;
                background-color: #2E2E2E; /* 深灰色背景 */
                QRadioButton::indicator { width: 0; height: 0; }
            }
        """)

        self.radio_1.setChecked(True)

        # RadioButton 群組
        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.radio_1)
        self.button_group.addButton(self.radio_2)
        self.button_group.addButton(self.radio_3)

        # 添加到左邊布局
        left_layout.addWidget(self.game_label)
        left_layout.addWidget(self.radio_1)
        left_layout.addWidget(self.radio_2)
        left_layout.addWidget(self.radio_3)

        self.radio_1.toggled.connect(self.change_game)
        self.radio_2.toggled.connect(self.change_game)
        self.radio_3.toggled.connect(self.change_game)

        # 添加紀錄帳號選單
        self.account_combo = QComboBox()
        self.account_label = QLabel("選擇紀錄帳號：")
        accounts = self.get_accounts()
        self.account_combo.addItems(accounts)
        self.account_combo.setCurrentIndex(0)  # 預設選擇 "帳號1"
        self.account_combo.currentTextChanged.connect(self.update_account_display)
        left_layout.addWidget(self.account_label)
        left_layout.addWidget(self.account_combo)

        # 添加hoyolab帳號選單
        self.hoyolab_account_combo = QComboBox()
        self.hoyolab_account_label = QLabel("選擇Hoyolab帳號：")

        hoyolab_accounts = self.get_hoyolab_accounts()
        for account_id, account_name in hoyolab_accounts:
            self.hoyolab_account_combo.addItem(account_name, account_id)

        self.hoyolab_account_combo.setCurrentIndex(0)  # 預設選擇 "帳號1"
        self.hoyolab_account_combo.currentTextChanged.connect(self.update_hoyolab_account_display)
        self.hoyolab_account_combo.hide()
        self.hoyolab_account_label.hide()

        # 添加遊戲帳號選單
        self.game_account_combo = QComboBox()
        self.game_account_label = QLabel("選擇遊戲帳號：")
        game_accounts = self.get_game_accounts()
        self.game_account_combo.addItems(game_accounts)
        self.game_account_combo.setCurrentIndex(0)  # 預設選擇 "帳號1"
        self.game_account_combo.currentTextChanged.connect(self.update_game_account_display)
        self.game_account_combo.hide()
        self.game_account_label.hide()


        left_layout.addWidget(self.game_account_label)
        left_layout.addWidget(self.game_account_combo)

        left_layout.addWidget(self.hoyolab_account_label)
        left_layout.addWidget(self.hoyolab_account_combo)

        # 按鈕 - 獲取月曆
        self.login_website = QPushButton("網頁登入")
        self.login_website.hide()
        self.login_website.clicked.connect(self.open_website)  # 註冊事件
        left_layout.addWidget(self.login_website)

        # 填充剩餘空間
        left_layout.addStretch()

        # 新增功能區塊 (底部)
        self.bottom_layout = QVBoxLayout()

        # 按鈕 - 獲取月曆
        self.btn_diary = QPushButton("獲取月曆資料")
        self.btn_diary.hide()
        self.btn_diary.clicked.connect(self.get_diary)  # 註冊事件
        self.bottom_layout.addWidget(self.btn_diary)

        btn_read_history = QPushButton("讀取歷史紀錄")
        btn_read_history.clicked.connect(self.fetch_data)
        self.bottom_layout.addWidget(btn_read_history)

        # 外部輸入選單 (導入 JSON 或 手動輸入)
        self.input_combo = QComboBox()
        self.input_label = QLabel("外部輸入：")
        self.input_combo.addItems(["選擇方式", "導入 JSON", "手動輸入"])
        self.input_combo.currentTextChanged.connect(self.external_input)
        self.bottom_layout.addWidget(self.input_label)
        self.bottom_layout.addWidget(self.input_combo)

        # 導出紀錄按鈕
        btn_export = QPushButton("導出紀錄")
        btn_export.clicked.connect(self.export_data)
        self.bottom_layout.addWidget(btn_export)

        

        #變更語言
        # 外部輸入選單 (導入 JSON 或 手動輸入)
        # self.language_combo = QComboBox()
        # self.language_label = QLabel("變更語言")

        # self.language_combo.addItems(list(language_dict.values()))
        # #self.language_combo.currentTextChanged.connect(self.change_language)
        # #self.language_combo.setCurrentIndex(0)
        # self.bottom_layout.addWidget(self.language_label)
        # self.bottom_layout.addWidget(self.language_combo)

        # 按鈕 - 更新檢查
        self.btn_update = QPushButton("檢查更新")
        self.btn_update.setIcon(QIcon("./assets/icons/update.png"))
        self.btn_update.clicked.connect(check_version)  # 註冊事件
        self.bottom_layout.addWidget(self.btn_update)

        # 將底部功能區塊設置為左邊的底部區域
        left_layout.addLayout(self.bottom_layout)

        self.left_frame.setLayout(left_layout)

        # 右邊主區塊，比例 8:1:1
        self.right_frame = QFrame()
        self.right_frame.setFrameShape(QFrame.StyledPanel)
        self.right_layout = QVBoxLayout()
        
        keys_length = ""
        try:
            file_path = os.path.join(user_path, f"GenshinImpact_{self.account_combo.currentText()}.json")

            if file_path:
                with open(file_path, "r", encoding="utf8") as file:
                    data = json.load(file)

                keys_length = len(list(data.keys())) - 1
        except:
            pass

        keys_length = keys_length if keys_length else 5
        self.group_boxes = []

        # 創建外層滾動區域
        self.outer_scroll_area = QScrollArea()
        self.outer_scroll_area.setFixedSize(1600, 200)  # 外部滾動區域大小
        self.outer_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 僅在需要時顯示水平滾動條
        self.outer_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用垂直滾動條

        # 創建容器和佈局作為外層滾動區域的內容
        self.outer_container = QWidget()
        self.outer_layout = QHBoxLayout()

        # 創建多個水平排列的小區塊
        for i in range(keys_length):  # 創建多個小區塊
            # 標題
            title = QLabel("")
            title.setStyleSheet("""
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 10px;
                background-color: #4CAF50; /* 綠色背景 */
                border-radius: 5px;
                margin: 5px 0;
            """)
            font = self.app_font if self.app_font else "Arial"
            title.setFont(QFont(font))

            # 滾動區域
            scroll_area = QScrollArea()
            scroll_area.setFixedHeight(725)  # 每個小滾動區域的大小

            # 禁用水平滾動條
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            # 垂直滾動條僅在需要時顯示
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            # 創建 Label 內容
            content = "_" * 50 + "\n"  # 測試用文字內容
            label = QLabel(content * 50)  # 測試文字，顯示多行
            label.setWordWrap(True)  # 啟用換行
            label.setMaximumWidth(260)
            label.setFont(QFont(font))

            # 創建一個 widget 作為 QScrollArea 的容器
            container_widget = QWidget()
            container_layout = QVBoxLayout()
            container_layout.setAlignment(Qt.AlignTop)  # 讓文字從頂部開始
            container_layout.addWidget(label)  # 把 label 放到容器中
            container_widget.setLayout(container_layout)

            # 設置 QScrollArea 的 widget
            scroll_area.setWidget(container_widget)

            # 創建一個垂直區塊包裹標題和滾動區域
            group_widget = QWidget()
            group_layout = QVBoxLayout()
            group_layout.setSpacing(10)  # 增加間距讓區塊更有呼吸感
            group_layout.addWidget(title)
            group_layout.addWidget(scroll_area)
            group_widget.setLayout(group_layout)

            # 設置外框樣式
            group_widget.setStyleSheet("""
                background-color: #333;  /* 深色背景 */
                border-radius: 10px;
                padding: 10px;
            """)

            # 將整個區塊添加到外層水平佈局
            self.outer_layout.addWidget(group_widget)
            self.group_boxes.append((title, label, scroll_area))

        # 設置外層滾動區域內容
        self.outer_container.setLayout(self.outer_layout)
        self.outer_scroll_area.setWidget(self.outer_container)
        self.outer_scroll_area.setFixedSize(1675, 600)

        # 把外層區塊添加到主佈局
        self.right_layout.addWidget(self.outer_scroll_area, 6)

        # 顯示抽數資訊
        self.gacha_info = QWidget()
        self.gacha_info_layout = QHBoxLayout()
        self.gacha_info_layout.setSpacing(0)
        self.gacha_info_list = []

        # 測試用文字內容
        content = "_" * 100 + "\n"
        gacha_label = QLabel(content * 5)  # 測試文字，顯示多行
        gacha_label.setWordWrap(True)  # 啟用換行
        gacha_label.setMaximumWidth(1650)
        self.gacha_info_list.append(gacha_label)

        # 添加 label 到佈局
        self.gacha_info_layout.addWidget(gacha_label)

        # 設置佈局到 gacha_info
        self.gacha_info.setLayout(self.gacha_info_layout)
        self.gacha_info.setFixedSize(1675, 200)

        # 把外層區塊添加到主佈局
        self.right_layout.addWidget(self.gacha_info, 6)

        # 合併後的按鈕區塊，放在右邊區塊的底部
        self.bottom_frame = QFrame()
        bottom_layout = QHBoxLayout()

        # 按鈕 - 抽卡紀錄
        btn_gacha = QPushButton("抽卡紀錄")
        btn_gacha.clicked.connect(self.on_gacha_click)  # 註冊事件
        bottom_layout.addWidget(btn_gacha)

        # 按鈕 - HOYO工具箱
        btn_toolbox = QPushButton("HOYO工具箱")
        btn_toolbox.clicked.connect(self.on_toolbox_click)  # 註冊事件
        bottom_layout.addWidget(btn_toolbox)

        # 按鈕 - 遊戲功能
        # btn_game_features = QPushButton("遊戲功能")
        # btn_game_features.clicked.connect(self.on_game_function_click)
        # bottom_layout.addWidget(btn_game_features)

        #堆疊區塊
        self.stacked_widget = QStackedWidget()
        self.right_layout.addWidget(self.stacked_widget)

        # 顯示網頁區域
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background-color: lightgray;")

        #網頁按鈕
        self.bottom_frame.setLayout(bottom_layout)
        self.right_layout.addWidget(self.bottom_frame, 1)  # 底部按鈕區佔比例 1

        self.web_bottom_frame = QFrame()
        bottom_layout = QHBoxLayout()
        self.web_button_list = []

        btn_notes = QPushButton("即時便籤")
        btn_notes.clicked.connect(self.show_notes)  # 註冊事件
        bottom_layout.addWidget(btn_notes)
        self.web_button_list.append(btn_notes)

        btn_calander = QPushButton("收入月曆")
        btn_calander.clicked.connect(self.show_now_income_calander)  # 註冊事件
        bottom_layout.addWidget(btn_calander)
        self.web_button_list.append(btn_calander)

        btn_caculator = QPushButton("傷害計算")
        btn_caculator.clicked.connect(self.show_caculator)  # 註冊事件
        bottom_layout.addWidget(btn_caculator)
        btn_caculator.hide()
        self.web_button_list.append(btn_caculator)

        btn_record = QPushButton("查看戰績")
        btn_record.clicked.connect(self.view_record)  # 註冊事件
        bottom_layout.addWidget(btn_record)
        self.web_button_list.append(btn_record)

        btn_daily = QPushButton("每日簽到")
        btn_daily.clicked.connect(self.daily_function)  # 註冊事件
        bottom_layout.addWidget(btn_daily)
        self.web_button_list.append(btn_daily)

        btn_redeem = QPushButton("兌換碼")
        btn_redeem.clicked.connect(self.redeem_code)  # 註冊事件
        bottom_layout.addWidget(btn_redeem)
        self.web_button_list.append(btn_redeem)

        btn_map = QPushButton("互動地圖")
        btn_map.clicked.connect(self.interact_map)  # 註冊事件
        bottom_layout.addWidget(btn_map)
        self.web_button_list.append(btn_map)

        self.web_bottom_frame.setLayout(bottom_layout)
        self.right_layout.insertWidget(0, self.web_bottom_frame, 1)  # 底部按鈕區佔比例 1
        self.web_bottom_frame.setFixedSize(0,0)

        self.stacked_widget.addWidget(self.web_view)

        #收入月曆區塊
        self.income_calander = QWidget()
        custom_layout = QVBoxLayout()

        self.month_data = []
        # 添加多個顯示文字的 QLabel
        
        # 顯示標題
        title = QLabel("")
        self.month_data.append(title)
        title.setMinimumHeight(50)
        title.setMaximumHeight(50)
        custom_layout.addWidget(title)

        # 使用 QHBoxLayout 把這個月和過去月並排顯示
        month_layout = QHBoxLayout()

        # 左邊滾動區塊
        scroll_area_left = QScrollArea()
        scroll_area_left.setFixedWidth(150)
        scroll_area_left.setWidgetResizable(True)
        self.left_content = QWidget()
        self.left_content_layout = QVBoxLayout()

        self.left_content.setLayout(self.left_content_layout)
        scroll_area_left.setWidget(self.left_content)

        # 創建 this_month 和 past_month 兩個區塊
        this_month_layout = QVBoxLayout()

        this_month = QLabel("")
        self.month_data.append(this_month)
        this_month.setMaximumHeight(100)

        this_month_content = QLabel("")
        this_month_content.setMaximumSize(800, 150)
        this_month_content.setWordWrap(True)
        self.month_data.append(this_month_content)

        this_month_graph = QChartView(QChart())
        this_month_graph.setMaximumSize(800, 400)
        self.month_data.append(this_month_graph)

        this_month_layout.addWidget(this_month)
        this_month_layout.addWidget(this_month_content)
        this_month_layout.addWidget(this_month_graph)

        past_month_layout = QVBoxLayout()

        past_month = QLabel("")
        self.month_data.append(past_month)
        past_month.setMaximumHeight(100)

        past_month_content = QLabel("")
        past_month_content.setMaximumSize(800, 150)
        past_month_content.setWordWrap(True)
        self.month_data.append(past_month_content)

        past_month_graph = QChartView(QChart())
        past_month_graph.setMaximumSize(800, 400)
        self.month_data.append(past_month_graph)

        past_month_layout.addWidget(past_month)
        past_month_layout.addWidget(past_month_content)
        past_month_layout.addWidget(past_month_graph)

        # 將滾動區塊放在左邊，這個月區塊和過去月區塊放在右邊
        month_layout.addWidget(scroll_area_left)  # 左邊的滾動區塊
        month_layout.addLayout(this_month_layout)  # 這個月
        month_layout.addLayout(past_month_layout)  # 過去月

        # 將 QHBoxLayout 加入到 custom_layout
        custom_layout.addLayout(month_layout)

        # 設定佈局到 income_calander
        self.income_calander = QWidget()
        self.income_calander.setLayout(custom_layout)

        # 添加到 QStackedWidget
        self.stacked_widget.addWidget(self.income_calander)
        self.stacked_widget.setFixedSize(0,0)



        #及時便籤區塊
        self.realtime_notes = QWidget()
        custom_layout = QVBoxLayout()

        self.notes_data = []
        # 添加多個顯示文字的 QLabel
        
        layout = QHBoxLayout()

        # 創建標題 QLabel
        title = QLabel("")
        title.setMinimumHeight(75)
        title.setMaximumHeight(75)
        layout.addWidget(title)
        self.notes_data.append(title)

        custom_layout.addLayout(layout)

        # 使用 QHBoxLayout 把這個月和過去月並排顯示
        notes_layout = QHBoxLayout()

        notes_data = QLabel("")
        self.notes_data.append(notes_data)
        notes_data.setMaximumHeight(600)
        custom_layout.addWidget(notes_data)

        # 將 QHBoxLayout 加入到 custom_layout
        custom_layout.addLayout(notes_layout)

        # 設定佈局到 income_calander
        self.realtime_notes = QWidget()
        self.realtime_notes.setLayout(custom_layout)

        self.stacked_widget.addWidget(self.realtime_notes)

        
        # #遊戲功能區塊
        # self.game_container = GameBlock()
        # # self.game_container.setFixedSize(0,0)
        
        # try:
        #     # 定義遊戲背景圖片的映射
        #     game_backgrounds = {
        #         "原神": "./bg/GI.png",
        #         "崩鐵": "./bg/HSR.png",
        #         "絕區零": "./bg/ZZZ.png"
        #     }

        #     # 設置背景
        #     if game in game_backgrounds:
        #         self.game_container.setStyleSheet(f"""
        #         QWidget {{
        #             background-image: url("{game_backgrounds[game]}");
        #             background-repeat: no-repeat;
        #             background-position: center;
        #         }}
        #         """)
        # except:
        #     pass


        # self.right_layout.insertWidget(0, self.game_container)
        
        # 添加 QSS 樣式表來增強界面外觀
        self.setStyleSheet("""
        QMainWindow {
            background-color: #2E2E2E; /* 深灰色背景 */
        }

        QLabel {
            color: white; /* 白色字體 */
            font-size: 25px; /* 字體大小 */
        }

        QPushButton {
            background-color: #4CAF50; /* 綠色背景 */
            color: white; /* 白色字體 */
            border-radius: 5px; /* 圓角 */
            padding: 10px; /* 內距 */
            font-size: 16px; /* 字體大小 */
            margin: 5px; /* 外邊距 */
            border: 2px solid #4CAF50; /* 添加邊框 */
        }

        QPushButton:hover {
            background-color: #45a049; /* 懸停顏色 */
        }

        QPushButton:pressed {
            background-color: #388E3C; /* 按下時顏色 */
            border: 2px solid #388E3C; /* 改變邊框顏色 */
        }

        QRadioButton {
            color: white; /* 白色字體 */
            background-color: #2E2E2E; /* 深灰色背景 */         
            font-size: 14px; /* 字體大小 */
        }

        QComboBox {
            background-color: #333; /* 深色背景 */
            color: white; /* 白色字體 */
            border-radius: 5px; /* 圓角 */
            padding: 5px; /* 內距 */
            border: 1px solid #4CAF50; /* 綠色邊框 */
        }

        QComboBox::drop-down {
            border: none; /* 隱藏下拉框邊框 */
        }

        QComboBox QAbstractItemView {
            background-color: #292A3A; /* 下拉選單背景 */
            color: white; /* 白色文字 */
            border-radius: 5px;
        }

        QWidget {
            background-color: #333; /* 深色背景 */
        }

        QScrollArea {
            background-color: #333; /* 深色背景 */
            border-radius: 10px; /* 圓角 */
        }

        QFrame {
            background-color: #444; /* 更深的背景色 */
            border-radius: 10px; /* 圓角 */
        }

        QVBoxLayout, QHBoxLayout {
            spacing: 10px; /* 元素間距 */
        }

        QScrollBar:vertical, QScrollBar:horizontal {
            background: #2B2C3C; /* 滾動條背景顏色 */
            border-radius: 10px; /* 滾動條圓角 */
            width: 12px; /* 設定滾動條寬度 */
            height: 12px; /* 設定滾動條高度 */
        }

        QScrollBar::handle {
            background: #4CAF50; /* 滾動條手柄顏色 */
            border-radius: 8px; /* 手柄圓角 */
            min-height: 50px; /* 最小高度 */
            min-width: 10px; /* 最小寬度 */
        }

        QScrollBar::handle:hover {
            background: #45A049; /* 懸停時的手柄顏色 */
        }

        QScrollBar::handle:pressed {
            background: #388E3C; /* 按下時的手柄顏色 */
        }

        /* 隱藏上下箭頭 */
        QScrollBar::add-line, QScrollBar::sub-line {
            background: none;
        }

        /* 滾動條的上下箭頭的樣式（已隱藏，但為了完整性保留） */
        QScrollBar::up-arrow, QScrollBar::down-arrow {
            background: none;
        }

        QScrollBar::add-page, QScrollBar::sub-page {
            background: none;
        }
        """)

        # 右邊內容填充
        self.right_frame.setLayout(self.right_layout)

        # 加入左右框架到主佈局，左右區塊比例為 1:9
        main_layout.addWidget(self.left_frame, 1)  # 左邊區塊占用 1 份寬度
        main_layout.addWidget(self.right_frame, 9)  # 右邊區塊占用 9 份寬度


        self.setLayout(main_layout)
        self.show_game_options()
        

    def on_toolbox_click(self):
        self.outer_scroll_area.setFixedSize(0, 0)
        # self.game_container.setFixedSize(0, 0)
        self.gacha_info.setFixedSize(0, 0)
        self.stacked_widget.setFixedSize(1675, 700)

        self.web_bottom_frame.setVisible(True)
        self.web_bottom_frame.setFixedSize(1675,100)

        self.account_combo.hide()
        self.account_label.hide()

        self.game_account_combo.show()
        self.game_account_label.show()
        


        self.hoyolab_account_combo.clear()
        hoyolab_accounts = self.get_hoyolab_accounts()

        for account_id, account_name in hoyolab_accounts:
            self.hoyolab_account_combo.addItem(account_name, account_id)

        self.hoyolab_account_combo.setCurrentIndex(0)

        self.hoyolab_account_combo.show()
        self.hoyolab_account_label.show()
        


        self.login_website.show()
        
        for i in range(self.bottom_layout.count() - 1):
            widget = self.bottom_layout.itemAt(i).widget()
            if widget:
                widget.hide()

        self.now_function = "HOYO工具箱"


        
    def on_gacha_click(self):
        self.now_function = "抽卡紀錄"

        self.account_combo.show()
        self.account_label.show()

        self.game_account_combo.hide()
        self.game_account_label.hide()
        self.hoyolab_account_combo.hide()
        self.hoyolab_account_label.hide()
        self.btn_diary.hide()
        self.login_website.hide()
        
        self.web_bottom_frame.setFixedSize(0, 0)
        # self.game_container.setFixedSize(0, 0)
        self.stacked_widget.setFixedSize(0, 0)

        for i in range(1, self.bottom_layout.count() - 2):
            widget = self.bottom_layout.itemAt(i).widget()
            if widget:
                widget.show()

        # 恢復原本的顯示區域
        self.outer_scroll_area.setFixedSize(1675, 600)
        self.gacha_info.setFixedSize(1675, 200)

    # def on_game_function_click(self):
    #     self.now_function = "遊戲功能"

    #     self.outer_scroll_area.setFixedSize(0, 0)
    #     self.gacha_info.setFixedSize(0, 0)
    #     self.stacked_widget.setFixedSize(0, 0)
    #     self.web_bottom_frame.setVisible(False)
    #     self.web_bottom_frame.setFixedSize(0, 0)
    #     self.account_combo.hide()
    #     self.account_label.hide()
    #     self.btn_diary.hide()
    #     self.login_website.hide()
    #     self.game_account_combo.hide()
    #     self.game_account_label.hide()

    #     for i in range(self.bottom_layout.count() - 1):
    #         widget = self.bottom_layout.itemAt(i).widget()
    #         if widget:
    #             widget.hide()

    #     # self.game_container.setFixedSize(1675,800)

    def show_web_view(self):
        """顯示 QWebEngineView 頁面"""
        self.stacked_widget.setCurrentWidget(self.web_view)
        self.web_view.setPage(CustomWebEnginePage(self.web_view))


    def view_record(self):
        self.web_button_function = "查看戰績"
        self.btn_diary.hide()
        self.show_web_view()
        selected_game = self.button_group.checkedButton().text()

        game_urls = {
            "原神": "https://act.hoyolab.com/app/community-game-records-sea/index.html?bbs_presentation_style=fullscreen&bbs_auth_required=true&v=104&gid=2&utm_source=hoyolab&utm_medium=tools&bbs_theme=dark&bbs_theme_device=1#/ys",
            "崩鐵": "https://act.hoyolab.com/app/community-game-records-sea/rpg/index.html?bbs_presentation_style=fullscreen&gid=6&utm_campaign=battlechronicle&utm_id=6&utm_medium=tools&utm_source=hoyolab&v=101&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/hsr",
            "絕區零": "https://act.hoyolab.com/app/zzz-game-record/index.html?hyl_presentation_style=fullscreen&utm_campaign=battlechronicle&utm_id=8&utm_medium=tools&utm_source=hoyolab&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/zzz"
        }
        url = game_urls.get(selected_game)
        self.web_view.setUrl(QUrl(url))

    def daily_function(self):
        self.web_button_function = "每日簽到"
        self.btn_diary.hide()
        self.show_web_view()
        selected_game = self.button_group.checkedButton().text()
        
        game_urls = {
            "原神": "https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481",
            "崩鐵": "https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311",
            "絕區零": "https://act.hoyolab.com/bbs/event/signin/zzz/e202406031448091.html?act_id=e202406031448091"
        }
        url = game_urls.get(selected_game)
        self.web_view.setUrl(QUrl(url))

    def redeem_code(self):
        self.web_button_function = "兌換碼"
        self.btn_diary.hide()
        self.show_web_view()
        selected_game = self.button_group.checkedButton().text()
        
        game_urls = {
            "原神": "https://genshin.hoyoverse.com/zh-tw/gift",
            "崩鐵": "https://hsr.hoyoverse.com/gift",
            "絕區零": "https://zenless.hoyoverse.com/redemption?lang=zh-tw"
        }

        url = game_urls.get(selected_game)
        self.web_view.setUrl(QUrl(url))

    def interact_map(self):
        self.web_button_function = "互動地圖"
        self.btn_diary.hide()
        self.show_web_view()
        selected_game = self.button_group.checkedButton().text()
        
        game_urls = {

        "原神": "https://act.hoyolab.com/ys/app/interactive-map/index.html?bbs_presentation_style=no_header&utm_source=hoyolab&utm_medium=tools&lang=zh-tw&bbs_theme=dark&bbs_theme_device=1#/map/2?shown_types=3,154,212",
        "崩鐵": "https://act.hoyolab.com/sr/app/interactive-map/index.html?hyl_presentation_style=fullscreen&utm_source=hoyolab&utm_medium=tools&utm_campaign=map&utm_id=6&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/map/38?shown_types=24,49,306,2,3,4,5,6,7,8,9,10,11,12,134,135,195,196"
        }
        
        url = game_urls.get(selected_game)
        self.web_view.setUrl(QUrl(url))
    
    def get_hoyolab_accounts(self):
        try:
            account_options = GenshinAPI.get_hoyolab_account()  
        except:
            account_options = []

        return account_options
       

    # 更新右側帳號顯示
    def update_account_display(self, account_name):
        if account_name == "":
            return
        
        if self.now_function == "抽卡紀錄":
            self.show_game_options()

    def update_game_account_display(self, account_name):
        pass

    def update_hoyolab_account_display(self):
        selected_index = self.hoyolab_account_combo.currentIndex()
        self.hoyolab_account_combo.setCurrentIndex(selected_index)

        game_accounts = self.get_game_accounts()      
        self.game_account_combo.clear()
        self.game_account_combo.addItems(game_accounts)
        
    def change_game(self):    
        game = self.button_group.checkedButton().text()

        if self.now_function == "HOYO工具箱":
            self.on_toolbox_click()
            self.web_button_list[3].show()

            game_accounts = self.get_game_accounts()      
            self.game_account_combo.clear()
            self.game_account_combo.addItems(game_accounts)

            if game == "絕區零":
                self.web_button_list[3].hide()


        elif self.now_function == "抽卡紀錄":
            accounts = self.get_accounts()
            self.account_combo.clear()
            self.account_combo.addItems(accounts)

            self.show_game_options()
            self.input_combo.setCurrentIndex(0)

        # elif self.now_function == "遊戲功能":
        #     try:
        #         game_backgrounds = {
        #             "原神": "./bg/GI.png",
        #             "崩鐵": "./bg/HSR.png",
        #             "絕區零": "./bg/ZZZ.png"
        #         }

        #         # 設置背景
        #         if game in game_backgrounds:
        #             self.game_container.setStyleSheet(f"""
        #             QWidget {{
        #                 background-image: url("{game_backgrounds[game]}");
        #                 background-repeat: no-repeat;
        #                 background-position: center;
        #             }}
        #             """)

        #     except:
        #         pass

    def get_accounts(self):
        account_options = []
        folder_path = f"{data_path}/user_data"
        selected_game = self.button_group.checkedButton().text()

        if not os.path.exists(folder_path):
            return account_options

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
    
    def get_game_accounts(self):
        selected_id = self.hoyolab_account_combo.currentData()
        selected_game = self.button_group.checkedButton().text()
        
        account_options = []
        API_function = GenshinAPI.API_function()
        gameText = "GENSHIN" if selected_game == "原神" else "STARRAIL" if selected_game == "崩鐵" else "ZZZ"

        try:
            account_options = API_function.get_game_accounts(selected_id, gameText)

        except:
            pass
            
        return account_options

    def change_language(self, language_name):
        pass

    def show_notes(self):
        self.web_button_function = "即時便籤"
        self.btn_diary.hide()
        self.stacked_widget.setCurrentWidget(self.realtime_notes)

        selected_game = self.selected_game = self.button_group.checkedButton().text()
        accountID = self.game_account_combo.currentText()
        
        data = None

        try:

            API_function = GenshinAPI.API_function()
            current_time = datetime.now()

            if selected_game == "原神":
                data = asyncio.run(API_function.get_genshin_notes(accountID))

            if selected_game == "崩鐵":
                data = asyncio.run(API_function.get_starrail_notes(accountID))

            if selected_game == "絕區零":
                data = asyncio.run(API_function.get_zzz_notes(accountID))

        except Exception as e:
            print(e)

            if isinstance(e, AccountNotFound):
                error_dialog = QMessageBox(self)
                error_dialog.setIcon(QMessageBox.Critical)  # 設置為錯誤類型
                error_dialog.setWindowTitle("錯誤")
                error_dialog.setInformativeText("帳號不存在")
                error_dialog.setStandardButtons(QMessageBox.Ok)  # 添加「確定」按鈕
                error_dialog.exec_()
                return
            

        if not data:
            self.notes_data[0].setText("")
            self.notes_data[1].setText("")
            return

        title = f"名稱：{data['info']['nickname']} | 等級：{data['info']['level']}"

        self.notes_data[0].setText(title)
        self.notes_data[0].setAlignment(Qt.AlignCenter)

        try:
            if selected_game == "原神":
                resin_time = isodate.parse_duration(data['remaining_resin_recovery_time'])
                resin_recover_time = (current_time + resin_time)
                resin_formatted_time = "體力已滿！" if resin_time == timedelta(0) else resin_recover_time.strftime("%H:%M:%S")
                resin_day = resin_recover_time.day - current_time.day
                resin_day_label = "" if resin_time == timedelta(0) else "今天" if resin_day == 0 else "明天" if resin_day == 1 else "後天" if resin_day == 2 else f"{resin_day} 天後"


                currency_time = isodate.parse_duration(data['remaining_realm_currency_recovery_time'])

                currency_recover_time = "" if currency_time == timedelta(0) else (current_time + currency_time)
                currency_formatted_time = "寶錢已滿！" if currency_time == timedelta(0) else currency_recover_time.strftime("%H:%M:%S")
                currency_day = "" if currency_time == timedelta(0) else currency_recover_time.day - current_time.day
                currency_day_label = "" if currency_time == timedelta(0) else "今天" if currency_day == 0 else "明天" if currency_day == 1 else "後天" if currency_day == 2 else f"{currency_day} 天後"

                claim_commission = "已領取！" if data['claimed_commission_reward'] else "未領取！"
                
                transformer_time = None if data['remaining_transformer_recovery_time'] == None else isodate.parse_duration(data['remaining_transformer_recovery_time'])
                transformer_recover_time = "" if transformer_time == timedelta(0) else "" if transformer_time == None else  (current_time + transformer_time)
                transformer_formatted_time = "冷卻結束！" if transformer_time == timedelta(0) else "" if transformer_time == None else transformer_recover_time.strftime("%H:%M:%S")
                transformer_day = "" if not isinstance(transformer_recover_time, datetime) else transformer_recover_time.day - current_time.day
                transformer_day_label = "" if transformer_day == "" else "今天" if transformer_day == 0 else "明天" if transformer_day == 1 else "後天" if transformer_day == 2 else f"{transformer_day} 天後"

                content = f"原粹樹脂：{data['current_resin']} / {data['max_resin']} | 完全恢復時間：{resin_day_label} {resin_formatted_time}\n\n洞天寶錢：{data['current_realm_currency']} / {data['max_realm_currency']} | 到達上限時間：{currency_day_label} {currency_formatted_time}\n\n每日委託：{data['completed_commissions']} / {data['max_commissions']} | 委託獎勵：{claim_commission}\n\n周本減免：{data['remaining_resin_discounts']} / {data['max_resin_discounts']}\n\n質變儀冷卻：{transformer_day_label} {transformer_formatted_time}\n委託派遣：\n\n"

                for info in data['expeditions']:
                    status = "派遣中" if info['status'] == "Ongoing" else "已完成！"
                    remain_time = current_time + isodate.parse_duration(info['remaining_time'])
                    formatted_remain_time = remain_time.strftime("%H:%M:%S")
                    remain_time_label = f"- 完成時間：{formatted_remain_time}" if info['status'] == "Ongoing" else ""
                    content += f"   {status} {remain_time_label}\n\n"

            if selected_game == "崩鐵":
                resin_time = isodate.parse_duration(data['stamina_recover_time'])
                resin_recover_time = (current_time + resin_time)
                resin_formatted_time = "體力已滿！" if resin_time == timedelta(0) else resin_recover_time.strftime("%H:%M:%S")
                resin_day = resin_recover_time.day - current_time.day
                resin_day_label = "" if resin_time == timedelta(0) else "今天" if resin_day == 0 else "明天" if resin_day == 1 else "後天" if resin_day == 2 else f"{resin_day} 天後"

                claim_commission = "已領取！" if data['current_train_score'] == data['max_train_score'] else "未領取！"
                

                content = f"開拓力：{data['current_stamina']} / {data['max_stamina']} | 完全恢復時間：{resin_day_label} {resin_formatted_time} | 後備開拓力：{data['current_reserve_stamina']} / 2400 \n\n每日委託：{data['current_train_score']} / {data['max_train_score']}\n\n周本減免：{data['remaining_weekly_discounts']} / {data['max_weekly_discounts']}\n\n委託派遣：\n\n"

                for info in data['expeditions']:
                    status = "派遣中" if info['status'] == "Ongoing" else "已完成！"
                    remain_time = current_time + isodate.parse_duration(info['remaining_time'])
                    formatted_remain_time = remain_time.strftime("%H:%M:%S")
                    remain_time_label = f"- 完成時間：{formatted_remain_time}" if info['status'] == "Ongoing" else ""
                    content += f"   {status} {remain_time_label}\n\n"

                content += f"模擬宇宙分數：{data['current_rogue_score']} / {data['max_rogue_score']}"
                
                if data['have_bonus_synchronicity_points']:
                    content += f"\n\n本週擬合值：{data['current_bonus_synchronicity_points']} / {data['max_bonus_synchronicity_points']}\n\n"

            if selected_game == "絕區零":
                resin_time = timedelta(seconds=data['battery_charge']['seconds_till_full'])
                resin_recover_time = (current_time + resin_time)
                resin_formatted_time = "體力已滿！" if resin_time == timedelta(0) else resin_recover_time.strftime("%H:%M:%S")
                resin_day = resin_recover_time.day - current_time.day
                resin_day_label = "" if resin_time == timedelta(0) else "今天" if resin_day == 0 else "明天" if resin_day == 1 else "後天" if resin_day == 2 else f"{resin_day} 天後"

                scratch_card = "已完成" if data['scratch_card_completed'] else "未完成"
                video_store_state = "經營中" if data['video_store_state'] == "SaleStateDoing" else "未經營"

                content = f"電量：{data['battery_charge']['current']} / {data['battery_charge']['max']} | 完全恢復時間：{resin_day_label} {resin_formatted_time}\n\n每日委託：{data['engagement']['current']} / {data['engagement']['max']}\n\n刮刮樂：{scratch_card} | 錄影帶店經營：{video_store_state}\n\n零號空洞：\n\n  調查點數 - {data['hollow_zero']['investigation_point']['num']} / {data['hollow_zero']['investigation_point']['total']}"

        except:
            content = ""


        self.notes_data[1].setText(content)
        self.notes_data[1].setAlignment(Qt.AlignCenter)

    def show_now_income_calander(self):
        self.web_button_function = "收入月曆"
        self.btn_diary.show()
        self.stacked_widget.setCurrentWidget(self.income_calander)

        selected_game = self.button_group.checkedButton().text()
        accountID = self.game_account_combo.currentText()

        game = "GenshinImpact" if selected_game == "原神" else "HonkaiStarRail" if selected_game == "崩鐵" else "ZenlessZoneZero"
        data_list = [file[:-5] for file in os.listdir(os.path.join(data_path, "diary")) if accountID in file and game in file]

        for i in reversed(range(self.left_content.layout().count())):
            self.left_content.layout().itemAt(i).widget().deleteLater()

        if len(data_list) == 0 or accountID == "":
            self.month_data[0].setText("")
            self.month_data[1].setText("")
            self.month_data[2].setText("")
            self.month_data[3].setChart(QChart())
            self.show_other_income_calander(-1)
            return
        
        files_sorted = sorted(
            data_list, 
            key=lambda x: datetime.strptime(x.split('_')[2] + '_' + x.split('_')[3], '%m_%Y'), 
            reverse=True
        )

        self.buttons = {}

        for i in range(len(files_sorted)):
            time = files_sorted[i].split("_")[3] + "-" + files_sorted[i].split("_")[2]
            button = QPushButton(time)
            self.buttons[time] = button
            button.clicked.connect(lambda _, index=i: self.show_other_income_calander(index))
            self.left_content_layout.addWidget(button)
            self.left_content_layout.setAlignment(Qt.AlignTop)

        latest_path = os.path.join(data_path, f"diary/{files_sorted[0]}.json")
        
        with open(latest_path, "r", encoding="utf8") as file:
            data = json.load(file)

        self.month_data[0].setText(f"UID：{data['uid']} | 伺服器：{data['server']} | 名稱：{data['nickname']}")
        self.month_data[0].setAlignment(Qt.AlignCenter)

        self.month_data[1].setText(f"當前月份：{files_sorted[0].split('_')[3] + '-' + files_sorted[0].split('_')[2]}")
        self.month_data[1].setAlignment(Qt.AlignCenter)

        if selected_game == "原神":
            data_text = f"""
            本日原石數：{data['day_data']['current_primogems']} | 本日摩拉數：{data['day_data']['current_mora']}\n
            本月原石數：{data['data']['current_primogems']} | 本月摩拉數：{data['data']['current_mora']}\n
            原石增減率：{data['data']['primogems_rate']} % | 摩拉增減率：{data['data']['mora_rate']} %
            """

        if selected_game == "崩鐵":
            data_text = f"""
            本日星瓊數：{data['day_data']['current_hcoin']} | 本日票券數：{data['day_data']['current_rails_pass']}\n
            本月星瓊數：{data['data']['current_hcoin']} | 本月票券數：{data['data']['current_rails_pass']}\n
            星瓊增減率：{data['data']['hcoin_rate']} % | 票券增減率：{data['data']['rails_rate']} %
            """

        if selected_game == "絕區零":
            data_text = f"本月菲林：{data['income']['currencies'][0]['num']} | 本月加密&原裝母帶：{data['income']['currencies'][1]['num']} | 本月邦布券：{data['income']['currencies'][2]['num']}"

        self.month_data[2].setText(data_text)

        if selected_game != "絕區零":
            # 創建 QBarSeries 和 QBarSet
            bar_series = QBarSeries()
            bar_series.setLabelsVisible(True)

            # 創建 QBarSet 並將數據添加到其中
            bar_set = QBarSet("")
            for entry in data['data']['categories']:
                bar_set.append(entry['amount'])

            # 將 QBarSet 添加到 QBarSeries
            bar_series.append(bar_set)

            # 創建 QChart 並設置標題
            chart = QChart()
            chart.addSeries(bar_series)
            chart.setTitle("各類別數據分佈")
            chart.setAnimationOptions(QChart.SeriesAnimations)
            chart.setBackgroundBrush(QBrush(QColor(90, 90, 90)))
            # 設置字體顏色為白色
            chart.setTitleFont(QFont(self.app_font, 16, QFont.Bold))
            chart.setTitleBrush(QBrush(QColor(255, 255, 255)))  # 白色

            # 設置 X 軸分類
            categories = [entry['name'] for entry in data['data']['categories']]
            axis_x = QBarCategoryAxis()
            axis_x.setLabelsBrush(QBrush(QColor(255, 255, 255)))  # X 軸標籤為白色
            axis_x.append(categories)
            chart.addAxis(axis_x, Qt.AlignBottom)
            bar_series.attachAxis(axis_x)

            # 創建 QChartView 並設置為圖表顯示
            self.month_data[3].setChart(chart)

    def show_other_income_calander(self, buttonIndex):
        if buttonIndex == -1:
            self.month_data[4].setText("")
            self.month_data[5].setText("")
            self.month_data[6].setChart(QChart())
            return
        
        self.stacked_widget.setCurrentWidget(self.income_calander)

        selected_game = self.button_group.checkedButton().text()
        accountID = self.game_account_combo.currentText()
        game = "GenshinImpact" if selected_game == "原神" else "HonkaiStarRail" if selected_game == "崩鐵" else "ZenlessZoneZero"

        data_list = [file[:-5] for file in os.listdir(os.path.join(data_path, "diary")) if accountID in file and game in file]

        if len(data_list) == 0:
            return
        
        files_sorted = sorted(
            data_list, 
            key=lambda x: datetime.strptime(x.split('_')[2] + '_' + x.split('_')[3], '%m_%Y'), 
            reverse=True
        )

        latest_path = os.path.join(data_path, f"diary/{files_sorted[buttonIndex]}.json")
        
        with open(latest_path, "r", encoding="utf8") as file:
            data = json.load(file)

        self.month_data[0].setText(f"UID：{data['uid']} | 伺服器：{data['server']} | 名稱：{data['nickname']}")
        self.month_data[0].setAlignment(Qt.AlignCenter)

        self.month_data[4].setText(f"歷史月份：{files_sorted[buttonIndex].split('_')[3] + '-' + files_sorted[buttonIndex].split('_')[2]}")
        self.month_data[4].setAlignment(Qt.AlignCenter)

        if selected_game == "原神":
            data_text = f"""
            本月原石數：{data['data']['current_primogems']} | 本月摩拉數：{data['data']['current_mora']}
            """

        if selected_game == "崩鐵":
            data_text = f"""
            本月星瓊數：{data['data']['current_hcoin']} | 本月票券數：{data['data']['current_rails_pass']}
            """

        if selected_game == "絕區零":
            data_text = f"本月菲林：{data['income']['currencies'][0]['num']} | 本月加密&原裝母帶：{data['income']['currencies'][1]['num']} | 本月邦布券：{data['income']['currencies'][2]['num']}"
        
        
        self.month_data[5].setText(data_text)

        if selected_game != "絕區零":
            # 創建 QBarSeries 和 QBarSet
            bar_series = QBarSeries()
            bar_series.setLabelsVisible(True)

            # 創建 QBarSet 並將數據添加到其中
            bar_set = QBarSet("")
            for entry in data['data']['categories']:
                bar_set.append(entry['amount'])

            # 將 QBarSet 添加到 QBarSeries
            bar_series.append(bar_set)

            # 創建 QChart 並設置標題
            chart = QChart()
            chart.addSeries(bar_series)
            chart.setTitle("各類別數據分佈")
            chart.setAnimationOptions(QChart.SeriesAnimations)
            chart.setBackgroundBrush(QBrush(QColor(90, 90, 90)))
            # 設置字體顏色為白色
            chart.setTitleFont(QFont(self.app_font, 16, QFont.Bold))
            chart.setTitleBrush(QBrush(QColor(255, 255, 255)))  # 白色

            # 設置 X 軸分類
            categories = [entry['name'] for entry in data['data']['categories']]
            axis_x = QBarCategoryAxis()
            axis_x.setLabelsBrush(QBrush(QColor(255, 255, 255)))  # X 軸標籤為白色
            axis_x.append(categories)
            chart.addAxis(axis_x, Qt.AlignBottom)
            bar_series.attachAxis(axis_x)

            # 創建 QChartView 並設置為圖表顯示
            self.month_data[6].setChart(chart)
        
    def show_caculator(self):
        self.btn_diary.hide()

    def show_game_options(self):
        options = []
        selected_game = self.button_group.checkedButton().text()

        gameText = "GenshinImpact" if selected_game == "原神" else "Honkai_StarRail" if selected_game == "崩鐵" else "ZenlessZoneZero"
        accountID = self.account_combo.currentText() if self.account_combo.currentText() != "" else [file for file in os.listdir(f"{data_path}/user_data") if gameText in file][0].split("_")[-1][:-5] if len(os.listdir(f"{data_path}/user_data")) >= 1 else ""

        # 根據遊戲選擇設定選項和資料檔案
        if selected_game == "原神":
            options = ["資訊", "新手", "常駐", "角色", "武器", "集錄"]
            path = f"{data_path}/user_data/GenshinImpact_{accountID}.json"

        elif selected_game == "崩鐵":
            options = ["資訊", "新手", "常駐", "角色", "光錐"]
            path = f"{data_path}/user_data/Honkai_StarRail_{accountID}.json"

        elif selected_game == "絕區零":
            options = ["資訊", "常駐", "代理人", "音擎", "邦布"]
            path = f"{data_path}/user_data/ZenlessZoneZero_{accountID}.json"

        # 如果資料檔案存在，讀取資料
        if os.path.exists(path):
            with open(path, "r", encoding="utf8") as file:
                data = json.load(file)

            for i, option in enumerate(options):
                
                if option == "資訊":
                    continue

                counter = 0
                text = ""
                keys = list(data.keys())

                self.group_boxes[i - 1][0].setText(option)
                self.group_boxes[i - 1][2].show()

                if keys[i] == "info":
                    continue

                reversed_data = data[keys[i]][::-1]
                if reversed_data == []:
                    self.group_boxes[i - 1][1].setText("")
                    continue

                for items in reversed_data:
                    counter += 1

                    if selected_game != "絕區零" and items['rank_type'] == '5':
                        text += f"{items['name']} [{counter}] "
                        counter = 0

                    elif selected_game == "絕區零" and items['rank_type'] == "4":
                        text += f"{items['name']} [{counter}] "
                        counter = 0

                self.group_boxes[i - 1][1].setText(text)

            if selected_game != "原神":
                self.group_boxes[4][0].setText("")
                self.group_boxes[4][1].setText("")
                self.group_boxes[4][2].hide()

            input_data = functions.get_average(path, selected_game, "")
            self.gacha_info_list[0].setText(input_data)
            self.gacha_info_list[0].setAlignment(Qt.AlignLeft | Qt.AlignTop)

    def export_data(self):
        """讓用戶選擇資料夾並輸出檔案。"""
        folder_path = QFileDialog.getExistingDirectory(self, "選擇資料夾", "")
        if folder_path:
            try:
                # 載入當前帳號的資料
                accountID = self.account_combo.currentText()
                selected_game = self.button_group.checkedButton().text()

                if selected_game == "原神":
                    file_path = f"{data_path}/user_data/GenshinImpact_{accountID}.json"
                    export_file_name = f"GenshinImpact_{accountID}_export.json"

                elif selected_game == "崩鐵":
                    file_path = f"{data_path}/user_data/Honkai_StarRail_{accountID}.json"
                    export_file_name = f"Honkai_StarRail_{accountID}_export.json"

                elif selected_game == "絕區零":
                    file_path = f"{data_path}/user_data/ZenlessZoneZero_{accountID}.json"
                    export_file_name = f"ZenlessZoneZero_{accountID}_export.json"

                # 確保來源檔案存在
                if not os.path.exists(file_path):
                    error_dialog = QMessageBox(self)
                    error_dialog.setIcon(QMessageBox.Critical)  # 設置為錯誤類型
                    error_dialog.setWindowTitle("錯誤")
                    error_dialog.setInformativeText("檔案不存在!")
                    error_dialog.setStandardButtons(QMessageBox.Ok)  # 添加「確定」按鈕
                    error_dialog.exec_()
                    return

                export_path = os.path.join(folder_path, export_file_name)
                functions.export_json(file_path, export_path, selected_game)

                info_dialog = QMessageBox(self)
                info_dialog.setIcon(QMessageBox.Information)  # 設置為信息類型
                info_dialog.setWindowTitle("提示")
                info_dialog.setText("操作成功！")
                info_dialog.setInformativeText("歷史紀錄已導出")
                info_dialog.setStandardButtons(QMessageBox.Ok)  # 添加「確定」按鈕

                info_dialog.exec_()

            except Exception as e:
                error_dialog = QMessageBox(self)
                error_dialog.setIcon(QMessageBox.Critical)  # 設置為錯誤類型
                error_dialog.setWindowTitle("錯誤")
                error_dialog.setInformativeText(f"歷史紀錄導出失敗")
                error_dialog.setStandardButtons(QMessageBox.Ok)  # 添加「確定」按鈕

                error_dialog.exec_()

    def fetch_data(self):
        selected_game = self.button_group.checkedButton().text()

        # 創建線程實例並連接信號
        self.thread = FetchDataThread(selected_game)
        self.thread.update_signal.connect(self.update_gacha_info)  # 連接信號到更新方法
        self.thread.finished_signal.connect(self.on_thread_finished)
        self.thread.start()  # 啟動線程

    def update_gacha_info(self, text):
        # 更新 GUI 上的 gacha_info_list
        self.gacha_info_list[0].setText(text)

    def on_thread_finished(self):
        self.show_game_options()

    def external_input(self, input_name):
        if input_name == "手動輸入":
            self.manual_input()
        
        if input_name == "導入 JSON":
            self.import_json()

    def caculate_average_manual(self, text):
        selected_game = self.button_group.checkedButton().text()
        result = functions.get_average("", selected_game, text)
        return result

    def manual_input(self):
        dialog = InputDialog()
        if dialog.exec_() == QDialog.Accepted:
            text = dialog.get_input_text()

            result = self.caculate_average_manual(text)
            self.gacha_info_list[0].setText(result)

            self.input_combo.setCurrentIndex(0)

    def import_json(self):
        file_path = QFileDialog.getOpenFileName(self, "打開檔案", "", "JSON 檔案 (*.json)")
        selected_game = self.button_group.checkedButton().text()

        system_path = (f"{data_path}/user_data/GenshinImpact.json"
                    if selected_game == "原神"
                    else f"{data_path}/user_data/Honkai_StarRail.json"
                    if selected_game == "崩鐵"
                    else f"{data_path}/user_data/ZenlessZoneZero.json")
        
        file_path = file_path[0]

        if file_path:
            extracted_data = functions.extract_data(selected_game, file_path)

            if extracted_data == "錯誤的遊戲資料":
                error_dialog = QMessageBox(self)
                error_dialog.setIcon(QMessageBox.Critical)  # 設置為錯誤類型
                error_dialog.setWindowTitle("錯誤")
                error_dialog.setInformativeText(f"錯誤或無法解析的歷史紀錄")
                error_dialog.setStandardButtons(QMessageBox.Ok)  # 添加「確定」按鈕

                error_dialog.exec_()
                return

            account = extracted_data['info']['uid']
            system_path = system_path[:-5] + f"_{account}.json"

            if os.path.exists(system_path):
                extracted_data = functions.compare_input_data(system_path, extracted_data, selected_game)

            with open(system_path, "w", encoding="utf8") as file:
                json.dump(extracted_data, file, indent=4, ensure_ascii=False)

            accounts = self.get_accounts()
            self.account_combo.clear()
            self.account_combo.addItems(accounts)
            index = accounts.index(account)
            self.account_combo.setCurrentIndex(index)
            self.input_combo.setCurrentIndex(0)

            self.show_game_options()

    def open_website(self):

        self.web_window = WebWindow()
        self.web_window.show()
            
    def get_diary(self):
        selected_game = self.button_group.checkedButton().text()
        accountId = self.game_account_combo.currentText()
        
        try:
            API_function = GenshinAPI.API_function()

            
            if selected_game == "原神":
                asyncio.run(API_function.get_genshin_diary(accountId))
                

            elif selected_game == "崩鐵":
                asyncio.run(API_function.get_starrail_diary(accountId))

            elif selected_game == "絕區零":
                asyncio.run(API_function.get_zzz_diary(accountId))
            
            self.show_now_income_calander()
            return

        except GenshinException as e:
            text = "等級不足，無法開啟月曆" if "-501101" in str(e) else "帳號不存在，請先登入"
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Critical)  # 設置為錯誤類型
            error_dialog.setWindowTitle("錯誤")
            error_dialog.setInformativeText(text)
            error_dialog.setStandardButtons(QMessageBox.Ok)  # 添加「確定」按鈕

            error_dialog.exec_()

class GameBlock(QWidget):
    def __init__(self):
        super().__init__()
        # 創建遊戲功能區塊的布局
        self.game_layout = QHBoxLayout(self)

        # 創建遊戲區塊
        self.game_container = QWidget(self)
        self.game_container.setLayout(self.game_layout)
        # self.game_container.setFixedSize(1675, 800)  # 設定區塊大小


        self.setLayout(self.game_layout)

class InputDialog(QDialog):
    def __init__(self):
        super().__init__()

        # 設置對話框標題和大小
        self.setWindowTitle("輸入框")
        self.setFixedSize(800, 600)

        # 創建總佈局
        main_layout = QVBoxLayout()

        # 添加提示標籤
        self.label = QLabel("請輸入五星角色/武器和抽數\n每行只能填一個角色或武器\n格式：<角色/武器><抽數>")
        main_layout.addWidget(self.label)

        # 創建多行文本框
        self.text_input = QTextEdit(self)
        self.text_input.setPlaceholderText("")
        main_layout.addWidget(self.text_input)

        # 創建選擇框 (角色 / 武器)
        radio_layout = QHBoxLayout()
        self.role_radio = QRadioButton("角色", self)
        self.weapon_radio = QRadioButton("武器", self)

        # 預設選擇 "角色"
        self.role_radio.setChecked(True)

        # 把選擇框放入佈局
        radio_layout.addWidget(self.role_radio)
        radio_layout.addWidget(self.weapon_radio)

        main_layout.addLayout(radio_layout)

        # 添加確認按鈕
        self.ok_button = QPushButton("開始計算", self)
        self.ok_button.clicked.connect(self.accept)
        main_layout.addWidget(self.ok_button)

        self.setStyleSheet("""
                /* 主視窗背景 */
        QMainWindow {
            background-color: #1F1F2F; /* 深色主背景 */
        }

        /* 標籤 */
        QLabel {
            color: #D8D8D8; /* 柔和的灰白色字體 */
            font-size: 20px;
            font-weight: 600; /* 加粗字體 */
            margin: 5px 0; /* 增加上下邊距 */
            padding: 5px;
        }

        /* 按鈕 */
        QPushButton {
            background-color: #388E3C; /* 綠色背景 */
            color: #FFFFFF; /* 白色字體 */
            border: 1px solid #2E7D32; /* 按鈕邊框 */
            border-radius: 12px; /* 圓角 */
            padding: 12px 20px; /* 增加內距 */
            font-size: 16px;
            margin: 10px;
        }

        QPushButton:hover {
            background-color: #2E7D32; /* 懸停效果 */
        }

        QPushButton:pressed {
            background-color: #1B5E20; /* 按下效果 */
        }

        /* 單選框 */
        QRadioButton {
            color: #EAEAEA;
            font-size: 14px;
            margin: 5px;
            padding-left: 5px; /* 增加左邊距離 */
        }

        /* 下拉選單 */
        QComboBox {
            background-color: #333545; /* 深色背景 */
            color: #EAEAEA; /* 白色字體 */
            border: 1px solid #4CAF50; /* 綠色邊框 */
            border-radius: 6px; /* 圓角 */
            padding: 5px 10px;
            font-size: 14px;
        }

        QComboBox:focus {
            border-color: #81C784; /* 聚焦時綠色邊框 */
        }

        /* 下拉選單視圖 */
        QComboBox QAbstractItemView {
            background-color: #2B2D3A; /* 下拉選單的背景色 */
            color: #FFFFFF; /* 文字顏色 */
            border-radius: 6px;
        }

        /* 基本小部件背景 */
        QWidget {
            background-color: #2C2D3A; /* 深色背景 */
        }

        /* 滾動區域 */
        QScrollArea {
            background-color: #333545; /* 深色背景 */
            border-radius: 8px;
            border: 1px solid #4CAF50; /* 綠色邊框 */
        }

        /* 框架 */
        QFrame {
            background-color: #1C1F2A; /* 黑灰色背景 */
            border-radius: 10px;
            border: 2px solid #4CAF50; /* 綠色邊框 */
            padding: 15px; /* 增加內邊距 */
        }

        /* 垂直和水平布局 */
        QVBoxLayout, QHBoxLayout {
            spacing: 12px; /* 元素間隔 */
        }

        /* 網頁視圖 */
        QWebEngineView {
            border: 3px solid #4CAF50; /* 加粗邊框 */
            border-radius: 20px; /* 圓角 */
            background-color: #FFFFFF; /* 白色背景 */
        }

        /* 滾動條 */
        QScrollBar:vertical, QScrollBar:horizontal {
            background: #2B2C3A; /* 滾動條背景色 */
            border-radius: 8px;
            width: 12px;
            margin: 0 5px; /* 讓滾動條不靠邊 */
        }

        QScrollBar::handle {
            background: #4CAF50; /* 滾動條手柄顏色 */
            border-radius: 8px;
            min-height: 30px; /* 設置手柄最小高度 */
        }

        QScrollBar::handle:hover {
            background: #66BB6A; /* 滾動條手柄懸停效果 */
        }

        QScrollBar::add-line, QScrollBar::sub-line {
            background: none; /* 隱藏箭頭 */
        }


        """)

        # 設置對話框的佈局
        self.setLayout(main_layout)

    def get_input_text(self):
        # 返回用戶輸入的段落文本
        return self.text_input.toPlainText()

    def get_selected_category(self):
        # 返回選擇的類別（角色 / 武器）
        if self.role_radio.isChecked():
            return "角色"
        
        elif self.weapon_radio.isChecked():
            return "武器"
      
class FetchDataThread(QThread):
    update_signal = pyqtSignal(str)  # 定義信號，用來傳遞字符串
    finished_signal = pyqtSignal()

    def __init__(self, selected_game):
        super().__init__()
        self.selected_game = selected_game

    def run(self):
        try:
            game = self.selected_game

            if game == "原神":
                self.update_signal.emit("正在讀取原神歷史紀錄，請稍等...")
                functions.get_GSdata_by_api()

            elif game == "崩鐵":
                self.update_signal.emit("正在讀取崩鐵歷史紀錄，請稍等...")
                functions.get_HSRdata_by_api()
                
            elif game == "絕區零":
                self.update_signal.emit("正在讀取絕區零歷史紀錄，請稍等...")
                functions.get_ZZZdata_by_api()

            self.update_signal.emit("抽卡紀錄已讀取")
            self.finished_signal.emit()
            
        except Exception as e:
            self.update_signal.emit("讀取失敗，請先在遊戲裡打開抽卡歷史紀錄")
            print(e)

class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.popup_windows = []  # 用來存儲彈出的視窗引用

    def createWindow(self, webWindowType):
        popup_view = QWebEngineView()
        popup_view.setAttribute(Qt.WA_DeleteOnClose, True)  # 彈窗關閉時自動刪除
        popup_view.setWindowTitle("登入")
        popup_view.resize(800, 600)

        # 儲存 popup_view 的引用，防止被垃圾回收
        self.popup_windows.append(popup_view)

        # 當視窗關閉時，從引用列表中移除
        popup_view.destroyed.connect(lambda: self.popup_windows.remove(popup_view))

        popup_view.show()
        return popup_view.page()
    
class WebWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Hoyoverse 登入')
        self.setGeometry(0, 0, 800, 600)

        # 主視窗的 QWebEngineView
        self.browser = QWebEngineView()

        # 將 CustomWebEnginePage 設為主視窗的頁面處理類
        self.browser.setPage(CustomWebEnginePage(self.browser))
        self.browser.setUrl(QUrl('https://account.hoyoverse.com/'))  # 設置初始 URL

        # 完成按鈕
        self.complete_button = QPushButton('完成')
        self.complete_button.clicked.connect(self.on_complete_button_clicked)

        # 使用 QVBoxLayout 布局
        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        layout.addWidget(self.complete_button)
        self.setLayout(layout)

    def on_complete_button_clicked(self):
        time.sleep(1)
        cookies = GenshinAPI.read_cookies(f"{data_path}/QtWebEngine/Default/Cookies")
        GenshinAPI.write_cookie(cookies['account_id_v2'])
        self.close()



# 主函式
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("./assets/icons/icon.png"))
    download_window = False

    status = functions.check_version()
    if status:
        update_ans = ask_update()

        if update_ans:
            program_path = ".\\updater\\updater.exe"  # 修改為目標程式的路徑
            subprocess.Popen([program_path], shell=True)
            download_window = True
            sys.exit()

    if not download_window:
        window = MainWindow()
        window.show()

    sys.exit(app.exec_())
