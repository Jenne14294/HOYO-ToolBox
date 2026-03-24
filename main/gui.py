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

CACHE_DIR = "./assets/data"
GENSHIN_LOC_PATH = os.path.join(CACHE_DIR, "gs_loc.json")
GENSHIN_LOC_ETAG = os.path.join(CACHE_DIR, "gs_loc.etag")

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

def get_with_cache_check(url, local_path, etag_path, session):
    """檢查遠端是否有更新，若無更新則回傳本地內容路徑"""
    headers = {}
    
    # 如果本地有 ETag 紀錄，就發送給伺服器比對
    if os.path.exists(local_path) and os.path.exists(etag_path):
        with open(etag_path, "r") as f:
            headers["If-None-Match"] = f.read().strip()

    try:
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code == 304:
            print(f"📦 {os.path.basename(local_path)} 無變動，使用本地快取。")
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        elif response.status_code == 200:
            print(f"📥 {os.path.basename(local_path)} 有更新，正在下載...")
            data = response.json()
            # 存入本地
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            # 存入新 ETag
            if "ETag" in response.headers:
                with open(etag_path, "w") as f:
                    f.write(response.headers["ETag"])
            return data
            
    except Exception as e:
        print(f"⚠️ 快取檢查失敗: {e}")
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
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

class PityItem(QFrame):
    """專門用來顯示『已墊抽數』的卡片"""
    def __init__(self, pity):
        super().__init__()
        self.pity = pity
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedSize(480, 100) # 維持跟角色卡片一樣的大小
        self.setToolTip("距離下一次出高星級的墊池抽數")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 5, 30, 5) # 因為沒有頭像，邊距稍微拉大一點讓視覺置中

        # --- 左側標題 ---
        title_label = QLabel("✨ 目前已墊")
        title_label.setObjectName("pityTitle")
        layout.addWidget(title_label)

        layout.addStretch() 

        # --- 右側抽數 ---
        count_label = QLabel(f"{self.pity} 抽")
        count_label.setObjectName("pityCount")
        layout.addWidget(count_label)

        # 顏色邏輯 (墊越多越接近保底，顏色越紅)
        if self.pity < 40: color = "#8BC34A" 
        elif self.pity <= 69: color = "#FF9800" 
        else: color = "#F44336" 

        # 💡 特殊樣式：加上半透明虛線邊框，讓它看起來像「狀態卡」而不是「角色卡」
        self.setStyleSheet(f"""
            PityItem {{ 
                background-color: {color}; 
                border-radius: 12px; 
                border: 3px dashed rgba(255, 255, 255, 0.4); 
            }}
            
            QLabel#pityTitle {{ 
                font-size: 35px;  
                font-weight: bold;
                color: white;
                background: transparent;
            }}
            
            QLabel#pityCount {{
                font-size: 35px;
                font-weight: bold;
                color: white;
                background: transparent;
            }}
        """)

class RecordItem(QFrame):
    """單筆抽卡紀錄卡片 (支援懸停時間與歪標記)"""
    def __init__(self, name, pity, time_str, is_wry=False, image_bytes=None):
        super().__init__()
        self.name = name
        self.pity = pity
        self.time_str = time_str
        self.is_wry = is_wry
        self.image_bytes = image_bytes
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        # 💡 高度維持 100，寬度 480 足夠放下大字
        self.setFixedSize(480, 100) 
        self.setToolTip(f"抽取時間：\n{self.time_str}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5) # 稍微增加邊距
        layout.setSpacing(15) 

        # --- 頭像部分 (稍微放大到 70x70) ---
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(70, 70) 
        
        if self.image_bytes:
            self.update_pixmap(self.image_bytes)
            
        self.avatar_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.avatar_label)

        # --- 名字部分 (字級加大到 35) ---
        self.name_label = QLabel(self.name)
        # 這裡設定字級為 35，並確保粗體
        font_size = 16
        
        font_id = QFontDatabase.addApplicationFont("./assets/font.ttf")
        if font_id != -1:
            custom_font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.name_label.setFont(QFont(custom_font_family, font_size, QFont.Bold))
        else:
            self.name_label.setFont(QFont("Microsoft JhengHei", font_size, QFont.Bold))
        
        layout.addWidget(self.name_label)

        # --- 歪 標籤 ---
        if self.is_wry:
            self.wry_label = QLabel("歪")
            self.wry_label.setAlignment(Qt.AlignCenter)
            self.wry_label.setFixedSize(45, 45) # 稍微放大標記
            self.wry_label.setStyleSheet("""
                background-color: #D32F2F; 
                color: white; 
                border-radius: 22px; 
                font-weight: bold; 
                font-size: 20px;
                border: 2px solid white;
            """)
            layout.addWidget(self.wry_label)

        layout.addStretch() 

        # --- 抽數部分 ---
        self.pity_label = QLabel(f"{self.pity} 抽")
        self.pity_label.setFont(QFont("Consolas", 20, QFont.Bold)) # 抽數也稍微放大一點點
        layout.addWidget(self.pity_label)

        # 設定背景色邏輯
        if self.pity < 40: color = "#8BC34A" # 綠
        elif self.pity <= 69: color = "#FF9800" # 橘
        else: color = "#F44336" # 紅

        self.setStyleSheet(f"""
                RecordItem {{ 
                    background-color: {color}; 
                    border-radius: 12px; 
                }}
                
                /* 使用 #ID 選擇器，權限會高於全域的 QLabel */
                QLabel#nameLabel {{ 
                    font-size: 35px;  /* 這裡設定你要的大尺寸 */
                    font-weight: bold;
                    color: white;
                    background: transparent;
                }}
                
                QLabel#pityLabel {{
                    font-size: 28px;
                    font-weight: bold;
                    color: white;
                    background: transparent;
                }}
            """)

    def set_avatar(self, image_bytes):
        """外部補傳圖片時呼叫"""
        self.update_pixmap(image_bytes)
        self.avatar_label.setStyleSheet("background: transparent;")

    def update_pixmap(self, image_bytes):
        """統一更新圖片的邏輯"""
        if image_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(image_bytes) 
            # 這裡縮放比例改為 70, 70
            scaled_pixmap = pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(scaled_pixmap)

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
                self.update_signal.emit("🚀 開始連接原神伺服器，請稍等...")
                # 💡 關鍵：把 self.update_signal 當作 log_signal 傳進去
                functions.get_GSdata_by_api(log_signal=self.update_signal)
                
            elif self.selected_game == "崩鐵":
                self.update_signal.emit("🚀 開始連接崩壞：星穹鐵道伺服器，請稍等...")
                functions.get_HSRdata_by_api(log_signal=self.update_signal)
                
            elif self.selected_game == "絕區零":
                self.update_signal.emit("🚀 開始連接絕區零伺服器，請稍等...")
                functions.get_ZZZdata_by_api(log_signal=self.update_signal)
            
            # 因為 data_to_json 跑完會自己發送 "🎉 所有操作完成"，這行也可以作為保險
            self.update_signal.emit(f"✅ {self.selected_game} 抽卡紀錄已讀取完成！")
            
            # 任務成功結束，發送完成訊號去啟動圖片預載小精靈
            self.finished_signal.emit()
            
        except Exception as e:
            # 發生錯誤時，傳送失敗提示，並印出錯誤原因方便你除錯
            print(f"抓取資料發生例外錯誤: {e}")
            self.update_signal.emit("❌ 讀取失敗，請確認是否已在遊戲內打開抽卡紀錄頁面")
            
            # 💡 記得就算失敗也要發送 finished_signal，不然 UI 按鈕會永遠卡在轉圈圈或鎖死狀態
            self.finished_signal.emit()

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
        print("🚀 [背景作業] 1. 正在初始化連線與掃描本地紀錄...")
        
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        
        # --- A. 掃描紀錄：提取所有遊戲已擁有的高星級名單 ---
        pulled_items = set() 
        user_data_dir = f"{data_path}/user_data"
        
        if os.path.exists(user_data_dir):
            for filename in os.listdir(user_data_dir):
                if not filename.endswith(".json"): continue
                game = "原神" if "GenshinImpact" in filename else "崩鐵" if "Honkai_StarRail" in filename else "絕區零" if "ZenlessZoneZero" in filename else ""
                if not game: continue

                try:
                    with open(os.path.join(user_data_dir, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for banner_key, pulls in data.items():
                        if banner_key == "info": continue 
                        for pull in pulls:
                            rank = str(pull.get("rank_type", "3"))
                            # 原神/崩鐵為5星，絕區零為4星(S級)
                            is_high_rank = (game != "絕區零" and rank == '5') or (game == "絕區零" and rank == "4")
                            if is_high_rank:
                                pulled_items.add((game, str(pull.get('item_id', '')), pull.get('name', '')))
                except: pass

        print(f"🎯 分析完畢！共有 {len(pulled_items)} 個高星項目需要處理。")

        # --- B. 平行下載各遊戲的「對照表」JSON (這只是文字，很快) ---
        print("🚀 [背景作業] 2. 正在取得各遊戲對照表...")
        
        # 準備暫存字典
        raw_gs_chars, raw_gs_wpns, raw_gs_loc = {}, {}, {}
        raw_hsr_chars, raw_hsr_wpns = {}, {}
        raw_zzz_chars, raw_zzz_wpns = {}, {}

        def fetch_meta():
            nonlocal raw_gs_chars, raw_gs_wpns, raw_gs_loc, raw_hsr_chars, raw_hsr_wpns, raw_zzz_chars, raw_zzz_wpns
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # 原神
                f1 = executor.submit(lambda: session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/gi/avatars.json").json())
                f2 = executor.submit(lambda: session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/gi/weapons.json").json())
                f3 = executor.submit(lambda: session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/gi/locs.json").json())
                # 崩鐵
                f4 = executor.submit(lambda: session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/hsr/avatars.json").json())
                f5 = executor.submit(lambda: session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/hsr/weapons.json").json())
                # 絕區零
                f6 = executor.submit(lambda: session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/avatars.json").json())
                f7 = executor.submit(lambda: session.get("https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/weapons.json").json())
                
                raw_gs_chars, raw_gs_wpns, raw_gs_loc = f1.result(), f2.result(), f3.result()
                raw_hsr_chars, raw_hsr_wpns = f4.result(), f5.result()
                raw_zzz_chars, raw_zzz_wpns = f6.result(), f7.result()

        fetch_meta()
        zh_tw = raw_gs_loc.get("zh-tw", raw_gs_loc.get("zh-TW", {}))

        # --- C. 建立精確的 IMAGE_PATH_MAP (只存有抽到的) ---
        for game, item_id, name in pulled_items:
            if game == "原神":
                # 原神邏輯：用名字找 Hash，再找路徑
                # 先搜角色
                found = False
                for info in raw_gs_chars.values():
                    if zh_tw.get(str(info.get("NameTextMapHash"))) == name:
                        IMAGE_PATH_MAP["原神"][name] = info.get("SideIconName", "").replace("_Side", "")
                        found = True; break
                if not found: # 再搜武器
                    for info in raw_gs_wpns.values():
                        if zh_tw.get(str(info.get("NameTextMapHash"))) == name:
                            IMAGE_PATH_MAP["原神"][name] = info.get("AwakenIcon", "")
                            break
            
            elif game == "崩鐵":
                path = raw_hsr_chars.get(item_id, {}).get('AvatarSideIconPath') or raw_hsr_wpns.get(item_id, {}).get('ImagePath')
                if path: IMAGE_PATH_MAP["崩鐵"][item_id] = path

            elif game == "絕區零":
                path = raw_zzz_chars.get(item_id, {}).get('CircleIcon') or raw_zzz_wpns.get(item_id, {}).get('ImagePath')
                if path: IMAGE_PATH_MAP["絕區零"][item_id] = path

        # --- D. 最終步驟：平行下載圖片 Bytes 到記憶體 ---
        print("🚀 [背景作業] 3. 開始平行下載專屬五星圖片...")

        def fetch_single_image(item):
            game, item_id, name = item
            key = name if game == "原神" else item_id
            suffix = IMAGE_PATH_MAP.get(game, {}).get(key)
            if not suffix: return

            # 統一網址格式
            if not suffix.startswith("/ui/"):
                if suffix.startswith("/"): suffix = f"/ui{suffix}"
                else: suffix = f"/ui/{suffix}"
            
            img_url = f"https://enka.network{suffix}"
            if not img_url.endswith(".png"): img_url += ".png"

            if img_url not in IMAGE_BYTES_CACHE:
                try:
                    res = session.get(img_url, timeout=5)
                    if res.status_code == 200:
                        IMAGE_BYTES_CACHE[img_url] = res.content
                except: pass
                time.sleep(0.01)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            executor.map(fetch_single_image, pulled_items)

        print("🎉 [背景作業] 所有專屬高星級圖片已平行預載完成！")
        self.preload_finished.emit()

# ==============================
# 主視窗 (UI 結合 邏輯)
# ==============================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HOYO ToolBox")
        self.resize(900, 600)
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
        self.history_title.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 18px; padding: 10px; border-radius: 5px;")
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
        self.change_game()

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
                            if time_str >= "2025-04-26 00:00:00" and name in ["符玄", "刃", "希兒"] and selected_game == "崩鐵":
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
                
                # 💡 新增判斷邏輯：原神/崩鐵的新手池，如果總抽數 >= 50，就不顯示「已墊卡片」
                show_pity_card = True
                if selected_game in ["原神", "崩鐵"] and banner_name == "新手":
                    show_pity_card = False

                # 如果條件允許，才把已墊卡片畫出來
                if show_pity_card and counter > 0:
                    pity_widget = PityItem(counter)
                    self.flow_layout.addWidget(pity_widget)

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
        self.summary_label.setText("正在解析新獲得的角色與圖片，請稍候...")
        
        self.preload_thread = PreloadDictionaryThread()
        # 小精靈抓完圖片後，再真正去重繪畫面 (例如呼叫 change_game 或是你原本畫卡片的函式)
        self.preload_thread.preload_finished.connect(self.on_dictionary_ready) 
        self.preload_thread.start()
        
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
                
                # 取得解析後的資料 (現在會是字典格式：{"原神": {...}, "崩鐵": {...}})
                extracted_data = functions.extract_data(selected_game, file_path)
                
                if extracted_data == "錯誤的遊戲資料":
                    QMessageBox.critical(self, "錯誤", "錯誤或無法解析的歷史紀錄")
                    return

                last_account = ""

                # ========================================================
                # 🚀 關鍵修改：迴圈處理每一個成功解析的遊戲，分別存成不同檔案
                # ========================================================
                for game_name, game_data in extracted_data.items():
                    # 判斷這個資料屬於哪個遊戲
                    gameText = "GenshinImpact" if game_name == "原神" else "Honkai_StarRail" if game_name == "崩鐵" else "ZenlessZoneZero"
                    
                    account = game_data['info']['uid']
                    last_account = account  # 記下帳號，等一下更新選單用
                    
                    system_path = f"{data_path}/user_data/{gameText}_{account}.json"

                    if os.path.exists(system_path):
                        game_data = functions.compare_input_data(system_path, game_data, game_name)

                    # 1. 儲存最新的 JSON 紀錄 (寫入對應的遊戲檔案中)
                    with open(system_path, "w", encoding="utf8") as file:
                        json.dump(game_data, file, indent=4, ensure_ascii=False)

                # 2. 更新 Combo 選單狀態
                if last_account:
                    self.account_combo.setCurrentText(last_account)
                self.external_combo.setCurrentIndex(0)

                # ==========================================
                # 🚀 3. 呼叫小精靈去掃描並下載新圖片！
                # ==========================================
                self.summary_label.setText("正在載入最新圖片，請稍候...") # 加個提示讓體驗更好
                
                self.preload_thread = PreloadDictionaryThread()
                # 將信號連接到更新畫面的函式 (等圖片抓完再刷新畫面，才不會破圖)
                self.preload_thread.preload_finished.connect(self.on_dictionary_ready) 
                self.preload_thread.start()

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
                font-size: 16px;
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
                font-size: 18px;
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
                font-size: 18px;
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