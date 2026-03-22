import os
import json
import configparser
import asyncio
import requests
import sys
import subprocess
import time
import concurrent.futures

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

IMAGE_PATH_MAP = { "原神": {}, "崩鐵": {}, "絕區零": {} }
IMAGE_BYTES_CACHE = {}

LOC_CACHE_PATH = "./assets/data/loc_genshin.json"
ETAG_CACHE_PATH = "./assets/data/loc_genshin.etag"

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


def get_avatar_bytes_dynamically(game, item_id, name):
    """瞬間查表並下載圖片 (不存硬碟)"""
    search_key = name if game == "原神" else str(item_id)
    icon_suffix = IMAGE_PATH_MAP.get(game, {}).get(search_key)
    
    if not icon_suffix: return None

    img_url = f"https://enka.network{icon_suffix}"
    if img_url in IMAGE_BYTES_CACHE: return IMAGE_BYTES_CACHE[img_url]
    return None

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
    def __init__(self, name, pity, time_str, is_wry=False, image_bytes=None):
        super().__init__()
        self.name = name
        self.pity = pity
        self.time_str = time_str
        self.is_wry = is_wry
        self.image_bytes = image_bytes # 接收傳進來的圖片資料
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        
        # 💡 修正 1：把寬度從 240 加寬到 340，才放得下你放大後的字體和頭像！
        self.setFixedSize(480, 100) 
        self.setToolTip(f"抽取時間：\n{self.time_str}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(10) # 加上元件間距，才不會黏在一起

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(50, 50)
        
        # 【關鍵】：把收到的 Bytes 畫出來！
        if self.image_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(self.image_bytes) 
            scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(scaled_pixmap)
        else:
            self.avatar_label.setStyleSheet("background-color: #555; border-radius: 5px;")
            
        self.avatar_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.avatar_label)

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
            # 💡 修正 2：大小為 40x40，border-radius 要設為一半 (20px) 才會是圓形
            self.wry_label.setStyleSheet("background-color: #D32F2F; color: white; border-radius: 20px; font-weight: bold; font-size: 20px;")
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

    def set_avatar(self, image_bytes):
        if image_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(image_bytes) 
            scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(scaled_pixmap)
            self.avatar_label.setStyleSheet("background: transparent;") # 圖片載入後，把灰底去掉

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

class AvatarFetchThread(QThread):
    # 定義一個訊號：當圖片抓好時，把「卡片編號」和「圖片資料」送回給主畫面
    avatar_fetched = pyqtSignal(int, bytes)

    def __init__(self, fetch_tasks):
        super().__init__()
        self.fetch_tasks = fetch_tasks 
        self.is_running = True

    def run(self):
        for task in self.fetch_tasks:
            if not self.is_running:
                break 
                
            card_id = task['id']
            game = task['game']
            item_id = task['item_id']
            name = task['name']

            # 💡 把 banner_name 拿掉，直接傳這三個就好
            image_bytes = get_avatar_bytes_dynamically(game, item_id, name)
            
            if image_bytes and self.is_running:
                self.avatar_fetched.emit(card_id, image_bytes)

    def stop(self):
        self.is_running = False

class PreloadDictionaryThread(QThread):
    preload_finished = pyqtSignal() 

    def run(self):
        print("🚀 [背景作業] 1. 正在使用多執行緒平行載入 JSON 字典...")
        
        # 建立共用連線池，加速所有 API 請求
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        # ====================================================
        # 將三款遊戲的抓取邏輯拆分成獨立的函式
        # ====================================================
        def fetch_hsr():
            try:
                hsr_c = session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/hsr/avatars.json", timeout=10).json()
                for k, v in hsr_c.items(): IMAGE_PATH_MAP["崩鐵"][str(k)] = f"{v.get('AvatarSideIconPath', '')}"
                hsr_w = session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/hsr/weapons.json", timeout=10).json()
                for k, v in hsr_w.items(): IMAGE_PATH_MAP["崩鐵"][str(k)] = f"{v.get('ImagePath', '')}"
            except: pass

        def fetch_zzz():
            try:
                zzz_c = session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/avatars.json", timeout=10).json()
                for k, v in zzz_c.items(): IMAGE_PATH_MAP["絕區零"][str(k)] = f"{v.get('CircleIcon', '')}"
                zzz_w = session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/weapons.json", timeout=10).json()
                for k, v in zzz_w.items(): IMAGE_PATH_MAP["絕區零"][str(k)] = f"{v.get('ImagePath', '')}"
            except: pass

        def fetch_genshin():
            try:
                # 💡 極限優化：直接請求 Amber API 的繁體中文資料，體積極小，直接包含名字與圖片 Key
                
                # 1. 抓取角色 (回傳格式直接就是 名字: 圖片代號)
                gs_c_res = session.get("https://api.allorigins.win/raw?url=https://api.ambr.top/v2/zh-TW/avatar", timeout=10).json()
                for v in gs_c_res.get("data", {}).get("items", {}).values():
                    char_name = v.get("name")
                    if char_name:
                        # 這裡拿到的 icon 是 "UI_AvatarIcon_Furina"，我們把它補上 .png
                        IMAGE_PATH_MAP["原神"][char_name] = f"{v.get('icon')}.png"
                
                # 2. 抓取武器
                gs_w_res = session.get("https://api.allorigins.win/raw?url=https://api.ambr.top/v2/zh-TW/weapon", timeout=10).json()
                for v in gs_w_res.get("data", {}).get("items", {}).values():
                    weapon_name = v.get("name")
                    if weapon_name:
                        IMAGE_PATH_MAP["原神"][weapon_name] = f"{v.get('icon')}.png"
                        
            except Exception as e:
                print(f"❌ 原神字典預載失敗: {e}")

        # ====================================================
        # 💡 召喚 3 個分身，同時執行這三個任務！
        # ====================================================
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 派發任務
            futures = [
                executor.submit(fetch_hsr),
                executor.submit(fetch_zzz),
                executor.submit(fetch_genshin)
            ]
            # 等待這 3 個分身都把工作做完
            concurrent.futures.wait(futures)

        print("✅ [背景作業] 所有 JSON 字典平行載入完成！")

        # ====================================================
        # 💡 關鍵進化：分析本機抽卡紀錄，提取專屬「高星級」名單
        # ====================================================
        print("🚀 [背景作業] 2. 正在分析抽卡紀錄，提取已擁有的高星級名單...")
        pulled_items = set() 
        user_data_dir = f"{data_path}/user_data" # 這裡使用你的資料夾路徑，確保與主程式一致
        
        if os.path.exists(user_data_dir):
            for filename in os.listdir(user_data_dir):
                if not filename.endswith(".json"): continue
                
                game = "原神" if "GenshinImpact" in filename else "崩鐵" if "Honkai_StarRail" in filename else "絕區零" if "ZenlessZoneZero" in filename else ""
                if not game: continue

                filepath = os.path.join(user_data_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                    for banner_key, pulls in data.items():
                        if banner_key == "info": continue 
                        for pull in pulls:
                            rank = str(pull.get("rank_type", "3"))
                            # 原神/崩鐵為5，絕區零為4
                            is_high_rank = (game != "絕區零" and rank == '5') or (game == "絕區零" and rank == "4")
                            if is_high_rank:
                                item_id = str(pull.get('item_id', ''))
                                name = pull.get('name', '')
                                pulled_items.add((game, item_id, name))
                except: pass

        print(f"🎯 [背景作業] 分析完畢！共有 {len(pulled_items)} 個專屬高星級頭像需要下載。")

        # ====================================================
        # 💡 關鍵 3：只針對這個清單下載圖片！
        # ====================================================
        print("🚀 [背景作業] 3. 開始使用多執行緒平行下載圖片...")
        
        # 建立一個 Session 通道，所有請求共用同一個連線，省去握手時間
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        # 定義一個「單張圖片下載」的專屬任務函數
        def fetch_single_image(item):
            game, item_id, name = item
            search_key = name if game == "原神" else str(item_id)
            icon_suffix = IMAGE_PATH_MAP.get(game, {}).get(search_key)
            
            if not icon_suffix: return
                
            if not icon_suffix.startswith("/"): icon_suffix = "/" + icon_suffix
            if not icon_suffix.startswith("/ui/"): icon_suffix = "/ui" + icon_suffix
                
            img_url = f"https://enka.network{icon_suffix}"
            if not img_url.endswith(".png"): img_url += ".png"

            if img_url not in IMAGE_BYTES_CACHE:
                try:
                    # 使用 session.get 取代 requests.get
                    response = session.get(img_url, timeout=5)
                    if response.status_code == 200:
                        IMAGE_BYTES_CACHE[img_url] = response.content
                except:
                    pass
                # 這裡的 sleep 可以縮短到極限 0.01 秒，因為我們有用連線池
                time.sleep(0.01) 

        # 🚀 召喚 5 個分身 (Worker) 同時去執行下載任務！
        # 注意：max_workers 不要設太大 (建議 5~8)，以免被 Enka 防火牆當成惡意攻擊而鎖 IP
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(fetch_single_image, pulled_items)
            
        print("🎉 [背景作業] 專屬高星級圖片已平行快取完畢！")
        
        # 通知主畫面可以放行了！
        self.preload_finished.emit()

# ==============================
# 主視窗 (UI 結合 邏輯)
# ==============================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HOYO ToolBox")
        self.resize(750, 600)
        self.init_ui()
        self.apply_global_style()
        self.change_game()

        self.summary_label.setText("正在背景載入圖片資料庫，請稍候...") # 溫馨提示
        self.preload_thread = PreloadDictionaryThread()
        self.preload_thread.preload_finished.connect(self.on_dictionary_ready)
        self.preload_thread.start()

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

    def on_dictionary_ready(self):
        self.summary_label.setText("圖庫載入完成！可以開始查詢紀錄囉！")

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
                    
                    item_id = str(items.get('item_id', ''))
                    rank_type = str(items.get('rank_type', '3'))
                    name = items.get('name', '未知')
                    time_str = items.get('time', '未知時間')
                    
                    is_high_rank = (selected_game != "絕區零" and rank_type == '5') or (selected_game == "絕區零" and rank_type == "4")
                    
                    if is_high_rank:
                        # --- 歪的判斷邏輯開始 ---
                        is_standard = functions.check_is_standard(selected_game, banner_name, name)
                        
                        # 【新規則】：2025/04/26 以後，特定角色強制視為「歪」
                        # 只在限定池（排除新手、常駐）生效
                        if banner_name not in ["新手", "常駐"]:
                            # 2025/04/26 字串比較在標準 ISO 時間格式下是有效的
                            if time_str >= "2025-04-26 00:00:00" and name in ["符玄", "刃", "希兒"]:
                                is_standard = True
                        
                        # 決定這張卡片要不要顯示「歪」標籤
                        is_wry = last_was_standard if banner_name not in ["新手", "常駐"] else False
                        # --- 歪的判斷邏輯結束 ---

                        image_bytes = get_avatar_bytes_dynamically(selected_game, item_id, name)
                        item_widget = RecordItem(name, counter, time_str, is_wry, image_bytes)
                        cards_to_show.append(item_widget)

                        # 更新「上一抽是否為常駐」的狀態給下一張卡片用
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