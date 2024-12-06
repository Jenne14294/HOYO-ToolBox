import os
import json
import threading
import functions

from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup, QLabel, QComboBox, QWidget, QFrame, QPushButton, QScrollArea, QGroupBox, QFileDialog, QMessageBox, QDialog, QTextEdit
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import sys

local_folder_path = os.environ.get("LOCALAPPDATA")
data_path = os.path.join(local_folder_path, "HoYo ToolBox")  # pyright: ignore[reportCallIssue, reportArgumentType]
user_path = os.path.join(data_path, "user_data")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("HOYO ToolBox")
        self.setGeometry(100, 100, 800, 600)
        self.now_function = "抽卡紀錄"
        self.update_signal = pyqtSignal(str)

        # 主水平布局，左右比例 1:9
        main_layout = QHBoxLayout()

        # 左邊垂直區塊
        self.left_frame = QFrame()
        self.left_frame.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout()

        # 添加遊戲選項 RadioButtons
        self.game_label = QLabel("選擇遊戲：")
        self.radio_1 = QRadioButton("原神")
        self.radio_2 = QRadioButton("崩鐵")
        self.radio_3 = QRadioButton("絕區零")

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

        # 添加帳號選單
        self.account_combo = QComboBox()
        self.account_label = QLabel("選擇帳號：")
        accounts = self.get_accounts()
        self.account_combo.addItems(accounts)
        self.account_combo.setCurrentIndex(0)  # 預設選擇 "帳號1"
        self.account_combo.currentTextChanged.connect(self.update_account_display)
        left_layout.addWidget(self.account_label)
        left_layout.addWidget(self.account_combo)

        # 填充剩餘空間
        left_layout.addStretch()

        # 新增功能區塊 (底部)
        self.bottom_layout = QVBoxLayout()

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

        # 將底部功能區塊設置為左邊的底部區域
        left_layout.addLayout(self.bottom_layout)

        self.left_frame.setLayout(left_layout)

        # 右邊主區塊，比例 8:1:1
        self.right_frame = QFrame()
        self.right_frame.setFrameShape(QFrame.StyledPanel)
        self.right_layout = QVBoxLayout()

        file_path = os.path.join(user_path, f"GenshinImpact_{self.account_combo.currentText()}.json")

        if file_path:
            with open(file_path, "r", encoding="utf8") as file:
                data = json.load(file)

            keys_length = len(list(data.keys())) - 1

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
            title = QLabel(f"Title {i + 1}")
            title.setStyleSheet("font-size: 20px; color: black; text-align:center;")
            
            # 滾動區域
            scroll_area = QScrollArea()
            scroll_area.setFixedSize(300, 725)  # 每個小滾動區域的大小

            # 禁用水平滾動條
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            # 垂直滾動條僅在需要時顯示
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            # 創建 Label 內容
            content = "_" * 50 + "\n"  # 測試用文字內容
            label = QLabel(content * 50)  # 測試文字，顯示多行
            label.setStyleSheet("color:white;")
            label.setWordWrap(True)  # 啟用換行
            label.setMaximumWidth(250)

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
            group_layout.addWidget(title)
            group_layout.addWidget(scroll_area)
            group_widget.setLayout(group_layout)

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
        gacha_label.setStyleSheet("color: white;")
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


        # 顯示網頁區域
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("background-color: lightgray;")
        self.right_layout.insertWidget(0, self.web_view)  # 插入到頂部
        self.web_view.setFixedSize(0,0)

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
        btn_game_features = QPushButton("遊戲功能")
        bottom_layout.addWidget(btn_game_features)

        #網頁按鈕
        self.bottom_frame.setLayout(bottom_layout)
        self.bottom_frame.setStyleSheet("background-color: lightblue; padding: 10px;")
        self.right_layout.addWidget(self.bottom_frame, 1)  # 底部按鈕區佔比例 1

        self.web_bottom_frame = QFrame()
        bottom_layout = QHBoxLayout()

        btn_record = QPushButton("查看戰績")
        btn_record.clicked.connect(self.view_record)  # 註冊事件
        bottom_layout.addWidget(btn_record)

        btn_daily = QPushButton("每日簽到")
        btn_daily.clicked.connect(self.daily_function)  # 註冊事件
        bottom_layout.addWidget(btn_daily)

        btn_redeem = QPushButton("兌換碼")
        btn_redeem.clicked.connect(self.redeem_code)  # 註冊事件
        bottom_layout.addWidget(btn_redeem)

        btn_map = QPushButton("互動地圖")
        btn_map.clicked.connect(self.interact_map)  # 註冊事件
        bottom_layout.addWidget(btn_map)

        self.web_bottom_frame.setLayout(bottom_layout)
        self.web_bottom_frame.setStyleSheet("background-color: lightblue; padding: 10px;")
        self.right_layout.insertWidget(0, self.web_bottom_frame, 1)  # 底部按鈕區佔比例 1
        self.web_bottom_frame.setFixedSize(0,0)

        # 右邊內容填充
        self.right_frame.setLayout(self.right_layout)

        # 加入左右框架到主佈局，左右區塊比例為 1:9
        main_layout.addWidget(self.left_frame, 1)  # 左邊區塊占用 1 份寬度
        main_layout.addWidget(self.right_frame, 9)  # 右邊區塊占用 9 份寬度

        self.setLayout(main_layout)
        self.show_game_options()

    def on_toolbox_click(self):
        self.outer_scroll_area.setFixedSize(0, 0)
        self.gacha_info.setFixedSize(0, 0)
        self.web_view.setFixedSize(1675,710)
        self.web_bottom_frame.setFixedSize(1675,100)
        self.now_function = "HOYO工具箱"

        # 移除左邊區塊底部的按鈕
        for i in range(self.bottom_layout.count()):
            widget = self.bottom_layout.itemAt(i).widget()
            if widget:
                widget.hide()

        selected_game = self.button_group.checkedButton().text()
        
        if selected_game == "原神":
            url = QUrl("https://act.hoyolab.com/app/community-game-records-sea/index.html?bbs_presentation_style=fullscreen&bbs_auth_required=true&v=104&gid=2&utm_source=hoyolab&utm_medium=tools&bbs_theme=dark&bbs_theme_device=1#/ys")

        elif selected_game == "崩鐵":
            url = QUrl("https://act.hoyolab.com/app/community-game-records-sea/rpg/index.html?bbs_presentation_style=fullscreen&gid=6&utm_campaign=battlechronicle&utm_id=6&utm_medium=tools&utm_source=hoyolab&v=101&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/hsr")
        
        elif selected_game == "絕區零":
            url = QUrl("https://act.hoyolab.com/app/zzz-game-record/index.html?hyl_presentation_style=fullscreen&utm_campaign=battlechronicle&utm_id=8&utm_medium=tools&utm_source=hoyolab&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/zzz")
            
        self.web_view.setUrl(url)  # 載入網頁到右側的 QWebEngineView

    def on_gacha_click(self):
        self.now_function = "抽卡紀錄"
        # 縮小網頁顯示區域
        if hasattr(self, 'web_view'):
            self.web_view.setFixedSize(0, 0)
            self.web_bottom_frame.setFixedSize(0, 0)

        for i in range(self.bottom_layout.count()):
            widget = self.bottom_layout.itemAt(i).widget()
            if widget:
                widget.show()

        # 恢復原本的顯示區域
        self.outer_scroll_area.setFixedSize(1675, 600)
        self.gacha_info.setFixedSize(1675, 200)


    def view_record(self):
        selected_game = self.button_group.checkedButton().text()
        
        if selected_game == "原神":
            url = QUrl("https://act.hoyolab.com/app/community-game-records-sea/index.html?bbs_presentation_style=fullscreen&bbs_auth_required=true&v=104&gid=2&utm_source=hoyolab&utm_medium=tools&bbs_theme=dark&bbs_theme_device=1#/ys")

        elif selected_game == "崩鐵":
            url = QUrl("https://act.hoyolab.com/app/community-game-records-sea/rpg/index.html?bbs_presentation_style=fullscreen&gid=6&utm_campaign=battlechronicle&utm_id=6&utm_medium=tools&utm_source=hoyolab&v=101&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/hsr")
        
        elif selected_game == "絕區零":
            url = QUrl("https://act.hoyolab.com/app/zzz-game-record/index.html?hyl_presentation_style=fullscreen&utm_campaign=battlechronicle&utm_id=8&utm_medium=tools&utm_source=hoyolab&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/zzz")
            
        self.web_view.setUrl(url)

    def daily_function(self):
        selected_game = self.button_group.checkedButton().text()
        
        if selected_game == "原神":
            url = QUrl("https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481")

        elif selected_game == "崩鐵":
            url = QUrl("https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311")
        
        elif selected_game == "絕區零":
            url = QUrl("https://act.hoyolab.com/bbs/event/signin/zzz/e202406031448091.html?act_id=e202406031448091")
            
        self.web_view.setUrl(url)

    def redeem_code(self):
        selected_game = self.button_group.checkedButton().text()
        
        if selected_game == "原神":
            url = QUrl("https://genshin.hoyoverse.com/zh-tw/gift")

        elif selected_game == "崩鐵":
            url = QUrl("https://hsr.hoyoverse.com/gift")
        
        elif selected_game == "絕區零":
            url = QUrl("https://zenless.hoyoverse.com/redemption?lang=zh-tw")
            
        self.web_view.setUrl(url)

    def interact_map(self):
        selected_game = self.button_group.checkedButton().text()
        
        if selected_game == "原神":
            url = QUrl("https://act.hoyolab.com/ys/app/interactive-map/index.html?bbs_presentation_style=no_header&utm_source=hoyolab&utm_medium=tools&lang=zh-tw&bbs_theme=dark&bbs_theme_device=1#/map/2?shown_types=3,154,212")

        elif selected_game == "崩鐵":
            url = QUrl("https://act.hoyolab.com/sr/app/interactive-map/index.html?hyl_presentation_style=fullscreen&utm_source=hoyolab&utm_medium=tools&utm_campaign=map&utm_id=6&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/map/38?shown_types=24,49,306,2,3,4,5,6,7,8,9,10,11,12,134,135,195,196")
        
        elif selected_game == "絕區零":
            url = QUrl("https://act.hoyolab.com/app/zzz-game-record/index.html?hyl_presentation_style=fullscreen&utm_campaign=battlechronicle&utm_id=8&utm_medium=tools&utm_source=hoyolab&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/zzz")
            
        self.web_view.setUrl(url)

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

    # 更新右側帳號顯示
    def update_account_display(self, account_name):
        if account_name == "":
            return
        
        if self.now_function == "抽卡紀錄":
            self.show_game_options()

    def change_game(self):
        accounts = self.get_accounts()
        self.account_combo.clear()
        self.account_combo.addItems(accounts)

        if self.now_function == "HOYO工具箱":
            self.on_toolbox_click()

        elif self.now_function == "抽卡紀錄":
            self.show_game_options()
            self.input_combo.setCurrentIndex(0)

    def show_game_options(self):
        options = []
        accountID = self.account_combo.currentText()
        selected_game = self.button_group.checkedButton().text()

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
                self.group_boxes[i - 1][1].setStyleSheet("font-size: 20px; color:black; font-family:arial;")

            if selected_game != "原神":
                self.group_boxes[4][0].setText("")
                self.group_boxes[4][1].setText("")
                self.group_boxes[4][2].hide()

            input_data = functions.get_average(path, selected_game, "")
            self.gacha_info_list[0].setText(input_data)
            self.gacha_info_list[0].setStyleSheet("font-size: 20px; color: black; font-family: Arial; line-height: 1.5; padding: 10px; text-align:center;")
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
                    error_dialog.setText("發生錯誤！")
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
                error_dialog.setText("發生錯誤！")
                error_dialog.setInformativeText(f"歷史紀錄導出失敗, {e}")
                error_dialog.setStandardButtons(QMessageBox.Ok)  # 添加「確定」按鈕

                error_dialog.exec_()

    def fetch_data(self):
        selected_game = self.button_group.checkedButton().text()

        # 創建線程實例並連接信號
        self.thread = FetchDataThread(selected_game)
        self.thread.update_signal.connect(self.update_gacha_info)  # 連接信號到更新方法
        self.thread.start()  # 啟動線程

    def update_gacha_info(self, text):
        # 更新 GUI 上的 gacha_info_list
        self.gacha_info_list[0].setText(text)

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
                error_dialog.setText("發生錯誤！")
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


class InputDialog(QDialog):
    def __init__(self):
        super().__init__()

        # 設置對話框標題和大小
        self.setWindowTitle("輸入框")
        self.setFixedSize(400, 250)

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
        except Exception as e:
            self.update_signal.emit("讀取失敗，請先在遊戲裡打開抽卡歷史紀錄")
            print(e)
        
        
# 主函式
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
