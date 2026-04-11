import os
import json
import requests
import time
import re
import zipfile
import shutil
import configparser
import logging
import concurrent.futures
from datetime import datetime

local_folder_path = os.environ.get("LOCALAPPDATA")
data_path = os.path.join(local_folder_path, "HoYo ToolBox")  # pyright: ignore[reportCallIssue, reportArgumentType]

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("gacha_export.log", encoding="utf-8"), 
        logging.StreamHandler()                                    
    ]
)

class HistoryURLNotFound(Exception):
    pass

def get_warp_url_from_cache(game):
    """直接解析本地遊戲快取來獲取抽卡網址，耗時 < 0.1秒"""
    user_profile = os.environ.get("USERPROFILE")
    if not user_profile: return None

    # 1. 根據遊戲設定 Log 檔案路徑與特徵
    if game == "原神":
        log_path = os.path.join(user_profile, r"AppData\LocalLow\miHoYo\Genshin Impact\output_log.txt")
        data_folder_name = "GenshinImpact_Data"
    elif game == "崩鐵":
        log_path = os.path.join(user_profile, r"AppData\LocalLow\Cognosphere\Star Rail\Player.log")
        data_folder_name = "StarRail_Data"
    elif game == "絕區零":
        log_path = os.path.join(user_profile, r"AppData\LocalLow\Cognosphere\ZenlessZoneZero\Player.log")
        if not os.path.exists(log_path): # 雙重檢查
            log_path = os.path.join(user_profile, r"AppData\LocalLow\miHoYo\ZenlessZoneZero\Player.log")
        data_folder_name = "ZenlessZoneZero_Data"
    else:
        return None

    if not os.path.exists(log_path):
        logging.error(f"找不到 {game} 的本地日誌檔，請確認是否在此電腦開啟過遊戲。")
        return None

    # 2. 從 Log 中找出遊戲安裝目錄
    game_data_path = ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            log_content = f.read()
            # 尋找類似 D:/Games/Star Rail/Games/StarRail_Data 的路徑
            match = re.search(r"([A-Z]:[\\/].*?[\\/]" + data_folder_name + r")", log_content, re.IGNORECASE)
            if match:
                game_data_path = match.group(1).replace("/", "\\")
    except Exception as e:
        logging.error(f"讀取日誌失敗: {e}")
        return None

    if not game_data_path or not os.path.exists(game_data_path):
        logging.error(f"無法從日誌中定位 {game} 的遊戲資料夾路徑。")
        return None

    # 3. 掃描 webCaches 資料夾，找出最新的 data_2 快取檔
    web_caches_dir = os.path.join(game_data_path, "webCaches")
    actual_cache_file = None
    
    if os.path.exists(web_caches_dir):
        for root, dirs, files in os.walk(web_caches_dir):
            if "data_2" in files:
                temp_path = os.path.join(root, "data_2")
                # 找出最後修改時間最新的 data_2
                if actual_cache_file is None or os.path.getmtime(temp_path) > os.path.getmtime(actual_cache_file):
                    actual_cache_file = temp_path

    if not actual_cache_file:
        logging.error(f"找不到 {game} 的網頁快取檔，請先在遊戲內打開抽卡紀錄！")
        return None

    # 4. 讀取二進位快取檔，精準挖出 AuthKey 網址
    try:
        with open(actual_cache_file, "r", encoding="utf-8", errors="ignore") as f:
            cache_content = f.read()
            # 正則表達式：抓取從 https 開始，包含 authkey= 的完整網址 (過濾掉不需要的字元)
            urls = re.findall(r"https://[^\s\0\"'<]+authkey=[^\s\0\"'<#]+", cache_content)
            if urls:
                # 永遠回傳最後一個找到的網址 (因為它是最新的)
                return urls[-1]
    except Exception as e:
        logging.error(f"解析快取網址失敗: {e}")
        return None

    return None

# ==========================================
# 定義全局常駐名單 (供 gui.py 判斷歪不歪使用)
# ==========================================
STANDARD_CHAR = {
    "原神": ["莫娜", "琴", "迪盧克", "迪希雅", "七七", "提納里", "刻晴", "夢見月瑞希"],
    "崩鐵": ["瓦爾特", "姬子", "彥卿", "布洛妮婭", "克拉拉", "白露", "傑帕德"],
    "絕區零": ["貓又", "「11號」", "珂蕾妲", "萊卡恩", "格莉絲", "麗娜"]
}

STANDARD_WEAPON = {
    "原神": ["阿莫斯之弓", "天空之翼", "和璞鳶", "天空之脊", "四風原典", "天空之卷", "狼的末路", "天空之傲", "風鷹劍", "天空之刃"],
    "崩鐵": ["但戰鬥還未結束", "如泥酣眠", "以世界之名", "無可取代的東西", "銀河鐵道之夜", "時節不居", "制勝的瞬間"],
    "絕區零": ["鋼鐵肉墊", "燃獄齒輪", "拘縛者", "硫磺石", "嵌合編譯器", "啜泣搖籃"]
}

def check_is_standard(game, banner_name, item_name):
    """判斷抽到的物品是否為常駐大獎"""
    # 新手池與常駐池沒有歪的概念，直接略過
    if banner_name in ["新手", "常駐"]:
        return False
        
    # 角色相關池
    if banner_name in ["角色", "聯動角色", "代理人", "集錄"]:
        return item_name in STANDARD_CHAR.get(game, [])
        
    # 武器相關池
    elif banner_name in ["武器", "光錐", "聯動武器", "音擎"]:
        return item_name in STANDARD_WEAPON.get(game, [])
        
    return False

# ==========================================
# 下面是你原本寫好的抓取與計算邏輯 (完全保留)
# ==========================================

def fetch_data_by_api(game):
    logging.info(f"開始執行抓取流程，目標遊戲：{game}")
    logging.info("正在透過 Python 解析本地快取以獲取抽卡網址...")
    
    # 🚀 直接呼叫我們剛寫好的秘密武器
    warp_url = get_warp_url_from_cache(game)
    
    if not warp_url:
        logging.error(f"❌ 嚴重錯誤：無法在本地快取中找到 {game} 的抽卡網址！請先在遊戲中開啟抽卡紀錄頁面。")
        return None, None

    logging.info(f"成功擷取網址 (長度 {len(warp_url)}): {warp_url[:100]}...")

    if game == "原神":
        warp_url += "&size=100&gacha_type=301&end_id="
    elif game == "崩鐵" and "size=" not in warp_url:
        warp_url += "&size=100&end_id="
    elif game == "絕區零":
        page_index = warp_url.find("&page")
        if page_index != -1: 
            warp_url = warp_url[:page_index]
        warp_url += "&size=100&real_gacha_type=1&end_id="

    if "api/getLdGachaLog" in warp_url:
        warp_url = warp_url.replace("api/getLdGachaLog", "api/getGachaLog")

    logging.info("正在進行初始連接以獲取帳號資訊...")
    
    try:
        response = requests.get(warp_url, timeout=10) 
        response.raise_for_status() 
        resdict = response.json()
    except Exception as e:
        logging.error(f"❌ 網路請求失敗: {e}", exc_info=True)
        return None, None

    retcode = resdict.get("retcode", -1)
    if retcode != 0:
        logging.error(f"❌ 獲取資料失敗！伺服器回傳錯誤: {resdict.get('message', '未知錯誤')}")
        if retcode == -101:
            logging.error("💡 提示：你的抽卡連結可能已過期，請重新在遊戲內打開紀錄頁面。")
        return None, None

    logging.info("✅ 成功連接並獲取初始資料！")
    return resdict, warp_url

def data_to_json(resdict, path, categories, game, warp_url, log_signal=None):
    def log_msg(msg):
        logging.info(msg)
        if log_signal:
            log_signal.emit(msg)

    UID = ""
    account = resdict["data"]["list"][0]["uid"]
    log_msg(f"成功獲取 UID: {account}")

    name_map = {
        "novice": "新手",
        "standard": "常駐",
        "characters": "角色",
        "weapons": "光錐" if game == "崩鐵" else "音擎" if game == "絕區零" else "武器",
        "bangboo": "邦布",
        "collection": "集錄",
        "collab_char": "聯動角色",
        "collab_weapon": "聯動武器",
        "collab_Weapon": "聯動武器" 
    }

    data = {}
    path = path[:-5] + f"_{account}" + ".json"

    if os.path.exists(path):
        log_msg(f"偵測到本地歷史紀錄檔案，將進行增量更新...")
        with open(path, "r", encoding="utf8") as file:
            existed_data = json.load(file)
    else:
        log_msg("未偵測到本地歷史紀錄，將建立全新資料檔。")
        existed_data = {key: [] for key in categories.keys()}

    # 初始化 info 區塊
    data["info"] = {
        "export_app": "HOYO ToolBox",
        "timezone": resdict["data"].get("region_time_zone", 0)
    }
    
    # 預先為所有分類建立空陣列，確保匯出時順序正確
    for key in categories.keys():
        data[key] = []

    # ==========================================
    # 🚀 建立獨立的 Pipeline Worker (平行抓取單一卡池)
    # ==========================================
    def fetch_single_pool(key, value):
        zh_name = name_map.get(key, key)
        log_msg(f"正在平行讀取 [{zh_name}] 的資料...")

        latest_id = existed_data[key][0]['id'] if key in existed_data and len(existed_data[key]) >= 1 else ""
        pool_data = []
        pool_info = {} # 用來裝 uid 和 lang 回傳給主執行緒

        if game == "原神":
            url = warp_url.replace("gacha_type=301", f"gacha_type={value}")
        elif game == "崩鐵":
            url = warp_url.replace("gacha_type=11", f"gacha_type={value}")
            if key in ["collab_char", "collab_weapon"]:
                url = url.replace("api/getGachaLog", "api/getLdGachaLog")
        elif game == "絕區零":
            url = warp_url.replace("gacha_type=1", f"gacha_type={value}")

        page_count = 0
        retry_count = 0  # 💡 新增：紀錄連續失敗次數
        
        while True:
            try:
                response = requests.get(url, timeout=10)
                resdict_pool = response.json()
            except Exception as e:
                if retry_count < 3:
                    wait_time = 0.5 * (2 ** retry_count)
                    log_msg(f"⚠️ [{zh_name}] 網路連線異常，動態冷卻 {wait_time} 秒後重試...")
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
                else:
                    log_msg(f"❌ [{zh_name}] 網路異常次數過多，中斷抓取: {e}")
                    break

            data_block = resdict_pool.get("data")
            
            if not data_block:
                err_msg = resdict_pool.get("message", "未知伺服器狀態")
                retcode = resdict_pool.get("retcode", 0)
                
                # 🚀 核心防護機制：如果是「請求頻繁」，我們選擇「等待並重試」，絕不放棄！
                if "frequently" in err_msg or "頻繁" in err_msg or retcode == -110:
                    if retry_count < 5:
                        # 💡 動態計算等待時間：1秒 -> 2秒 -> 4秒 -> 8秒 -> 16秒
                        wait_time = 0.5 * (2 ** retry_count) 
                        
                        log_msg(f"⏳ [{zh_name}] 觸發伺服器防護，動態冷卻 {wait_time} 秒後自動重試...")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue  # 回到迴圈開頭，再發送一次請求
                    else:
                        log_msg(f"❌ [{zh_name}] 連續重試達 5 次上限，強制結束此卡池。")
                        break
                else:
                    # 如果是其他錯誤 (例如登入過期、AuthKey 失效)，才真的中斷
                    log_msg(f"⚠️ [{zh_name}] 伺服器異常 ({err_msg})，結束抓取。")
                    break

            # ✅ 成功拿到資料，將重試次數歸零
            retry_count = 0
                
            api_list = data_block.get("list", [])
            if not api_list:
                break
                
            if "lang" not in pool_info:
                pool_info["lang"] = api_list[0]["lang"]
            if "uid" not in pool_info:
                pool_info["uid"] = api_list[0]["uid"]

            # 只保留比本地最新紀錄 (latest_id) 還新的資料
            new_list = [item for item in api_list if item['id'] > latest_id]

            if not new_list:
                break

            pool_data.extend(new_list)
            page_count += 1

            # 提早中斷邏輯：代表這包資料裡面已經包含舊紀錄了
            if len(new_list) < len(api_list):
                break

            # 準備抓取下一頁
            last_id = new_list[-1]["id"]
            end_id_index = url.find("end_id=")
            url = url[:end_id_index] + f"end_id={last_id}"
            
            # 💡 為了更穩定，我們把換頁的基礎等待時間從 0.3 拉長到 0.5 秒
            time.sleep(0.5)

        log_msg(f"✅ [{zh_name}] 讀取完成! 本次共抓取 {page_count} 頁新資料。")
        return key, pool_data, pool_info

    # ==========================================
    # 🚀 啟動多執行緒 ThreadPool (最高同時 3 條管線)
    # ==========================================
    MAX_WORKERS = 3 
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 將所有卡池的任務派發出去
        future_to_pool = {
            executor.submit(fetch_single_pool, key, value): key 
            for key, value in categories.items()
        }

        # 等待並收集每個管線的回傳結果
        for future in concurrent.futures.as_completed(future_to_pool):
            pool_key = future_to_pool[future]
            try:
                returned_key, pool_data, pool_info = future.result()
                data[returned_key].extend(pool_data)
                
                # 安全地將 uid 和 lang 更新到 info 區塊
                if "lang" not in data["info"] and "lang" in pool_info:
                    data["info"]["lang"] = pool_info["lang"]
                if "uid" not in data["info"] and "uid" in pool_info:
                    data["info"]["uid"] = pool_info["uid"]
                    
            except Exception as exc:
                log_msg(f"❌ 管線 [{name_map.get(pool_key, pool_key)}] 發生嚴重錯誤: {exc}")

    # ==========================================
    # 將抓回來的新資料與本地舊資料合併
    # ==========================================
    for key in categories.keys():
        data[key].extend(existed_data.get(key, []))

    if game != "原神":
        data["info"]["version"] = "v4.0"

    with open(path, "w", encoding="utf8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
        
    log_msg(f"🎉 {game} 所有抽卡紀錄已成功寫入儲存！")

def get_GSdata_by_api(log_signal=None):
    path = f"{data_path}/user_data/GenshinImpact.json"
    categories = {"novice": "100", "standard": "200", "characters": "301", "weapons": "302", "collection": "500"}
    # 這裡拔掉了 command 參數
    resdict, warp_url = fetch_data_by_api(game="原神") 
    if resdict: data_to_json(resdict, path, categories, "原神", warp_url, log_signal=log_signal)

def get_HSRdata_by_api(log_signal=None):
    path = f"{data_path}/user_data/Honkai_StarRail.json"
    categories = {"novice": "2", "standard": "1", "characters": "11", "weapons": "12", "collab_char":"21", "collab_weapon":"22"}
    resdict, warp_url = fetch_data_by_api(game="崩鐵")
    if resdict: data_to_json(resdict, path, categories, "崩鐵", warp_url, log_signal=log_signal)

def get_ZZZdata_by_api(log_signal=None):
    path = f"{data_path}/user_data/ZenlessZoneZero.json"
    categories = {"standard": "1", "characters": "2", "weapons": "3", "bangboo": "5"}
    resdict, warp_url = fetch_data_by_api(game="絕區零")
    if resdict: data_to_json(resdict, path, categories, "絕區零", warp_url, log_signal=log_signal)

def get_average(idx, file_path, game, input_text):
    if game == "絕區零":
        idx += 1

    if not os.path.exists(file_path):
        return "沒有找到遊戲資料，請先導入遊戲資料"
    
    # 這裡直接引用上面定義好的全局變數，程式更簡潔
    standard_char = STANDARD_CHAR["原神"] if game == "原神" else STANDARD_CHAR["崩鐵"] if game == "崩鐵" else STANDARD_CHAR["絕區零"]
    standard_weapon = STANDARD_WEAPON["原神"] if game == "原神" else STANDARD_WEAPON["崩鐵"] if game == "崩鐵" else STANDARD_WEAPON["絕區零"]
    standard_items = standard_char + standard_weapon 

    novice, characters, weapons, standard = [], [], [], []
    limit_char, limit_weapon = [], []
    fivestar_novice, fivestar_standard, fivestar_char, fivestar_weapon = [], [], [], []
    novice_count, standard_count, character_count, weapon_count = [], [], [], []

    category_map = {
        "novice": {"type": "100" if game == "原神" else "2" if game == "崩鐵" else "1", "list": novice, "fivestar_list": fivestar_novice, "count":novice_count},
        "standard": {"type": "200" if game == "原神" else "1" if game == "崩鐵" else "1", "list": standard, "fivestar_list": fivestar_standard, "count":standard_count},
        "characters": {"type": ["301", "400"] if game == "原神" else "11" if game == "崩鐵" else "2", "list": characters, "limit_list": limit_char, "fivestar_list": fivestar_char, "count":character_count},
        "weapons": {"type": "302" if game == "原神" else "12" if game == "崩鐵" else "3", "list": weapons, "limit_list": limit_weapon, "fivestar_list": fivestar_weapon, "count": weapon_count}
    }

    if game == "原神":
        collection, limit_coll, fivestar_coll = [], [], []
        collection_count = []
        category_map["collection"] = {"type": "500", "list": collection, "limit_list": limit_coll, "fivestar_list": fivestar_coll, "count": collection_count}
    elif game == "崩鐵":
        collab_char, fivestar_collab_char, limit_collab_char = [], [], []
        collab_weapon, fivestar_collab_weapon, limit_collab_weapon = [], [], []
        collab_char_count, collab_weapon_count  = [], []
        category_map["collab_char"] = {"type": "21", "list": collab_char, "fivestar_list": fivestar_collab_char, "limit_list":limit_collab_char, "count": collab_char_count}
        category_map["collab_weapon"] = {"type": "22", "list": collab_weapon, "fivestar_list": fivestar_collab_weapon, "limit_list":limit_collab_weapon, "count": collab_weapon_count}
    elif game == "絕區零":
        bangboo, fivestar_bangboo = [], []
        bangboo_count = []
        category_map["bangboo"] = {"type": "5", "list": bangboo, "fivestar_list": fivestar_bangboo, "limit_list":[], "count": bangboo_count}

    def process_item(item, category, standard_items):
        category["list"].append(item) 
        category["count"].append(item) 
        if item["rank_type"] == "5":
            category["fivestar_list"].append(item) 
            if item['name'] not in standard_items and item["gacha_type"] not in ["100", "200", "1", "2"]:
                category["limit_list"].append(item) 
            category["count"] = []

    def process_item_zzz(item, category, standard_items):
        category["list"].append(item)
        category["count"].append(item)
        if item["rank_type"] == "4":
            category["fivestar_list"].append(item)
            if item['name'] not in standard_items and item["gacha_type"] in ["1", "2", "3", "5"]:
                category["limit_list"].append(item)
            category["count"] = []

    if file_path:
        with open(file_path, "r", encoding="utf8") as file:
            data = json.load(file)

        for key in data:
            if key == "info": continue
            if game == "原神" and (len(data[key]) > 1 and data[key][0]['gacha_type'] not in ["100", "200", "301", "302", "400", "500"]):
                return "導入錯誤的遊戲資料"
            elif game == "崩鐵" and (len(data[key]) > 1 and data[key][0]['gacha_type'] not in ["1", "2", "11", "12", "21", "22"]):
                return "導入錯誤的遊戲資料"
            elif game == "絕區零" and (len(data[key]) > 1 and data[key][0]['gacha_type'] not in ["1", "2", "3", "5"]):
                return "導入錯誤的遊戲資料"

        for key, value in data.items():
            if key == "info": continue
            for item in value:
                for category, details in category_map.items():
                    category_type = details["type"]
                    if game != "絕區零":
                        if isinstance(category_type, list):
                            if item["gacha_type"] in category_type: process_item(item, details, standard_items)
                        else:
                            if item["gacha_type"] == category_type: process_item(item, details, standard_items)
                    else:
                        if item["gacha_type"] == category_type: process_item_zzz(item, details, standard_items)

        true_character_count = len(character_count) - 1 if len(fivestar_char) > 0 else len(character_count)
        true_character_count = max(0, true_character_count)
        
        true_weapon_count = len(weapon_count) - 1 if len(fivestar_weapon) > 0 else len(weapon_count)
        true_weapon_count = max(0, true_weapon_count)
        
        # 💡 假設常駐池的五星陣列叫做 fivestar_standard，若你的變數名不同請自行替換
        true_standard_count = len(standard_count) - 1 if len(fivestar_standard) > 0 else len(standard_count)
        true_standard_count = max(0, true_standard_count)
        
        true_novice_count = len(novice_count) - 1 if len(fivestar_novice) > 0 else len(novice_count)
        true_novice_count = max(0, true_novice_count)

        # ==========================================================
        # 2. 計算平均出金（將總抽數扣除「已墊抽數」，只計算已經出金的區間）
        # ==========================================================
        average_limit_character = round((len(characters) - true_character_count) / len(limit_char), 2) if len(limit_char) > 0 else None
        average_character = round((len(characters) - true_character_count) / len(fivestar_char), 2) if len(fivestar_char) > 0 else None

        average_limit_weapon = round((len(weapons) - true_weapon_count) / len(limit_weapon), 2) if len(limit_weapon) > 0 else None
        average_weapon = round((len(weapons) - true_weapon_count) / len(fivestar_weapon), 2) if len(fivestar_weapon) > 0 else None

        average_novice = round((len(novice) - true_novice_count) / len(fivestar_novice), 2) if len(fivestar_novice) > 0 else None

        # 3. 保底不歪率維持原本的計算公式
        char_guarantee_rate = f"{round(((2 * len(limit_char) - len(fivestar_char)) / len(limit_char)) * 100, 2)} %" if len(fivestar_char) > 0 else None
        char_guarantee_rate = None if not char_guarantee_rate else "0.0 %" if "-" in char_guarantee_rate else char_guarantee_rate

        weapon_guarantee_rate = f"{round(((2 * len(limit_weapon) - len(fivestar_weapon)) / len(limit_weapon)) * 100, 2)} %" if len(fivestar_weapon) > 0 else None
        weapon_guarantee_rate = None if not weapon_guarantee_rate else "0.0 %" if "-" in weapon_guarantee_rate else weapon_guarantee_rate

        status_text = ""
        if idx == 2:
            status_text += f"限定池({true_character_count} / 90) - 總抽數：{len(characters)}\n限定角色數：{len(limit_char)}\n平均限定金：{average_limit_character}\n五星角色數：{len(fivestar_char)}\n平均五星金：{average_character}\n保底不歪率：{char_guarantee_rate}\n"
        elif idx == 3:
            status_text += f"武器池({true_weapon_count} / 80) - 總抽數：{len(weapons)}\n限定武器數：{len(limit_weapon)}\n平均限定金：{average_limit_weapon}\n五星武器數：{len(fivestar_weapon)}\n平均五星金：{average_weapon}\n保底不歪率：{weapon_guarantee_rate}\n"

        # ==========================================================
        # 4. 特殊卡池同樣要先精準算出墊池數，再計算平均
        # ==========================================================
        if game == "原神" and idx == 4:
            true_collection_count = len(collection_count) - 1 if len(fivestar_coll) > 0 else len(collection_count)
            true_collection_count = max(0, true_collection_count)
            
            average_limit_collection = round((len(collection) - true_collection_count) / len(limit_coll), 2) if len(limit_coll) > 0 else None
            average_collection = round((len(collection) - true_collection_count) / len(fivestar_coll), 2) if len(fivestar_coll) > 0 else None 
            
            coll_guarantee_rate = f"{round(((2 * (len(limit_coll) - len(fivestar_coll))) / len(limit_coll)), 2) * 100} %" if len(fivestar_coll) > 0 else None
            coll_guarantee_rate = None if not coll_guarantee_rate else "0.0 %" if "-" in coll_guarantee_rate else coll_guarantee_rate
            status_text += f"集錄池({true_collection_count} / 90) - 總抽數：{len(collection)}\n限定數量：{len(limit_coll)}\n平均限定金：{average_limit_collection}\n五星數量：{len(fivestar_coll)}\n平均五星金：{average_collection}\n保底不歪率：{coll_guarantee_rate}\n"

        if idx == 4 and game == "崩鐵":
            true_collab_char_count = len(collab_char_count) - 1 if len(fivestar_collab_char) > 0 else len(collab_char_count)
            true_collab_char_count = max(0, true_collab_char_count)
            
            average_limit_collab_char = round((len(collab_char) - true_collab_char_count) / len(limit_collab_char), 2) if len(limit_collab_char) > 0 else None
            average_collab = round((len(collab_char) - true_collab_char_count) / len(fivestar_collab_char), 2) if len(fivestar_collab_char) > 0 else None
            collab_guarantee_rate = "100 %" if len(limit_collab_char) == len(fivestar_collab_char) else f"{round(((2 * (len(limit_collab_char) - len(fivestar_collab_char))) / len(limit_collab_char)), 2) * 100} %"
            status_text += f"聯動角色({true_collab_char_count} / 90) - 總抽數：{len(collab_char)}\n限定數量：{len(limit_collab_char)}\n平均限定金：{average_limit_collab_char}\n五星數量：{len(fivestar_collab_char)}\n平均五星金：{average_collab}\n保底不歪率：{collab_guarantee_rate}\n"

        if idx == 5 and game == "崩鐵":
            true_collab_weapon_count = len(collab_weapon_count) - 1 if len(fivestar_collab_weapon) > 0 else len(collab_weapon_count)
            true_collab_weapon_count = max(0, true_collab_weapon_count)
            
            average_limit_collab_weapon = round((len(collab_weapon) - true_collab_weapon_count) / len(limit_collab_weapon), 2) if len(limit_collab_weapon) > 0 else None
            average_collab = round((len(collab_weapon) - true_collab_weapon_count) / len(fivestar_collab_weapon), 2) if len(fivestar_collab_weapon) > 0 else None
            collab_guarantee_rate = "100 %" if len(limit_collab_weapon) == len(fivestar_collab_weapon) else f"{round(((2 * (len(limit_collab_weapon) - len(fivestar_collab_weapon))) / len(limit_collab_weapon)), 2) * 100} %"
            status_text += f"聯動武器({true_collab_weapon_count} / 90) - 總抽數：{len(collab_weapon)}\n限定數量：{len(limit_collab_weapon)}\n平均限定金：{average_limit_collab_weapon}\n五星數量：{len(fivestar_collab_weapon)}\n平均五星金：{average_collab}\n保底不歪率：{collab_guarantee_rate}\n"

        if game == "絕區零" and idx == 4:
            true_bangboo_count = len(bangboo_count) - 1 if len(fivestar_bangboo) > 0 else len(bangboo_count)
            true_bangboo_count = max(0, true_bangboo_count)
            
            average_bangboo = round((len(bangboo) - true_bangboo_count) / len(fivestar_bangboo), 2) if len(fivestar_bangboo) > 0 else None
            status_text += f"邦布池({true_bangboo_count} / 80) - 總抽數：{len(bangboo)}\n邦布五星數：{len(fivestar_bangboo)}\n平均五星數：{average_bangboo}\n"

        if game != "絕區零" and idx == 0:
            status_text += f"新手池({true_novice_count} / 50) - 總抽數：{len(novice)}\n新手五星數：{len(fivestar_novice)}\n平均五星數：{average_novice}\n"

        if idx == 1:
            status_text += f"常駐池({true_standard_count} / 90) - 總抽數：{len(standard)}"

        result_text = status_text
        
    else:
        items = input_text.split('\n')
        total = 0
        limit = []
        for item in items: 
            parts = re.findall(r'(\D+)(\d+)', item.strip()) 
            if parts: 
                name, count = parts[0][0], int(parts[0][1]) 
                total += count 
                if name.strip() not in standard_items: 
                    limit.append(name.strip())

        average = round(total / len(limit), 2) if len(limit) > 0 else None
        result_text = f"總抽數：{total}\n限定數：{len(limit)}\n平均限定金：{average}"
        
    return result_text

def compare_input_data(system_path, input_data, game):
    with open(system_path, "r", encoding="utf8") as file:
        system_data = json.load(file)   

    new_data = {}
    new_data["info"] = system_data["info"]
    keys = ["novice", "standard", "characters", "weapons"]

    if game == "原神": keys.append("collection")
    if game == "崩鐵":
        keys.append("collab_char")
        keys.append("collab_weapon")
    if game == "絕區零":
        keys.remove("novice")
        keys.append("bangboo")

    for key in keys:
        # 安全地取得舊資料與新資料的陣列 (如果沒有就給空陣列)
        sys_list = system_data.get(key, [])
        inp_list = input_data.get(key, [])
        
        # 🚀 關鍵絕招：建立一個字典，用 ID 當作 Key 來「去重複」
        merged_dict = {}
        
        # 先把舊資料倒進去
        for item in sys_list:
            merged_dict[item['id']] = item
            
        # 再把新資料倒進去 (如果有重複的 ID，會自然蓋過去，不會多出一筆)
        for item in inp_list:
            merged_dict[item['id']] = item
            
        # 最後把字典裡所有的抽卡紀錄拿出來，依照 ID 從大到小排序 (最新 -> 最舊)
        # 用 int() 包起來排序，確保數字大小絕對精準
        new_data[key] = sorted(merged_dict.values(), key=lambda x: int(x['id']), reverse=True)
                
    return new_data

def extract_data(game, input_path):
    with open(input_path, "r", encoding="utf8") as file:
        input_data = json.load(file)

    # 💡 這裡改成 List (陣列)，這樣同一個遊戲有多個帳號也能裝得下！
    extracted_results = []
    base_info = input_data.get("info", {})

    game_tags = {"hk4e": "原神", "hkrpg": "崩鐵", "nap": "絕區零"}

    def process_single_game(target_game, info_data, data_list):
        if not data_list: return None

        first_gacha = str(data_list[0].get("gacha_type", ""))
        if target_game == "原神" and first_gacha not in ["100", "200", "301", "302", "400", "500"]: return None
        if target_game == "崩鐵" and first_gacha not in ["1", "2", "11", "12", "21", "22"]: return None
        if target_game == "絕區零" and first_gacha not in ["1", "2", "3", "5"]: return None

        novice, standard, character, weapon = [], [], [], []
        new_data = {"info": info_data}

        if target_game == "原神":
            collection = []
            gacha_mapping = {"100": novice, "200": standard, "301": character, "400": character, "302": weapon, "500": collection}
            keys = {"100":"novice", "200":"standard", "301":"characters", "302":"weapons", "500":"collection"}
        elif target_game == "崩鐵":
            collab_char, collab_weapon = [], []
            gacha_mapping = {"1": standard, "2": novice, "11": character, "12": weapon, "21": collab_char, "22": collab_weapon}
            keys = {"2":"novice", "1":"standard", "11":"characters", "12":"weapons", "21":"collab_char", "22":"collab_weapon"}
        elif target_game == "絕區零":
            bangboo = []
            gacha_mapping = {"1": standard, "2": character, "3": weapon, "5": bangboo}
            keys = {"1":"standard", "2":"characters", "3":"weapons", "5":"bangboo"}

        for item in data_list:
            g_list = gacha_mapping.get(str(item.get("gacha_type")))
            if g_list is not None: 
                g_list.append(item)

        for key_id, target_key in keys.items():
            target_list = gacha_mapping.get(key_id)
            if target_list is not None:
                new_data[target_key] = target_list[::-1]

        for key in new_data:
            if key == "info" or new_data[key] == []: continue
            for item in new_data[key]:
                item["uigf_gacha_type"] = "400" if (target_game == "原神" and str(item.get("gacha_type")) == "301") else str(item.get("gacha_type"))

        return new_data

    # ==========================================
    # 1. 處理 UIGF 多遊戲檔案
    # ==========================================
    if any(tag in input_data for tag in game_tags):
        for tag, game_name in game_tags.items():
            if tag in input_data and isinstance(input_data[tag], list):
                # 🚀 關鍵修改：遍歷這個遊戲底下的「每一個帳號」！
                for game_block in input_data[tag]:
                    new_info = base_info.copy()
                    new_info["uid"] = game_block.get("uid", "")
                    new_info["timezone"] = game_block.get("timezone", "")
                    new_info["lang"] = game_block.get("lang", "")
                    
                    parsed_data = process_single_game(game_name, new_info, game_block.get("list", []))
                    if parsed_data:
                        # 塞入陣列中
                        extracted_results.append((game_name, parsed_data))

    # ==========================================
    # 2. 處理單一遊戲舊版檔案
    # ==========================================
    else:
        parsed_data = process_single_game(game, base_info, input_data.get("list", []))
        if parsed_data:
            extracted_results.append((game, parsed_data))

    if not extracted_results:
        return "錯誤的遊戲資料"

    return extracted_results

def export_json(file_path, folder_path, game):
    with open(file_path, "r", encoding="utf8") as file:
        data = json.load(file)
    uid = os.path.basename(file_path).split("_")[-1][:-5]
    new_data = {"info": data["info"]}
    
    if game == "原神":
        new_data["list"] = []
    if game == "崩鐵":
        new_data["info"]["version"] = "v4.0"
        new_data["hkrpg"] = [{"uid": uid, "lang": data["info"]["lang"], "timezone": data["info"]["timezone"], "list": []}]
    if game == "絕區零":
        new_data["info"]["version"] = "v4.0"
        new_data["nap"] = [{"uid": data["info"]["uid"], "lang": data["info"]["lang"], "timezone": data["info"]["timezone"], "list": []}]

    new_data["info"]["export_time"] = datetime.now().strftime("%Y/%m/%d %H：%M：%S")

    for key in data:
        if key == "info": continue
        if game == "原神":
            new_data["list"].extend(data[key])
            new_data['list'].sort(key=lambda x: x['id'])
        if game == "崩鐵":
            new_data["hkrpg"][0]["list"].extend(data[key])
            new_data["hkrpg"][0]['list'].sort(key=lambda x: x['id'])
        if game == "絕區零":
            new_data["nap"][0]["list"].extend(data[key])
            new_data["nap"][0]['list'].sort(key=lambda x: x['id'])

    new_data["info"]["export_app"] = "HOYO ToolBox"
    with open(folder_path, "w", encoding="utf8") as new_file:
        json.dump(new_data, new_file, indent=4, ensure_ascii=False)

def generate_uigf_data(selected_files):
        """將多個本地檔案合併並轉換為 UIGF v4.0 格式"""
        uigf_export = {
            "info": {
                "export_app": "HOYO ToolBox",
                "export_app_version": "1.0.0",
                "version": "v4.0"
            },
            "hk4e": [],
            "hkrpg": [],
            "nap": []
        }

        for file_name in selected_files:
            file_path = f"{data_path}/user_data/{file_name}"
            with open(file_path, "r", encoding="utf8") as f:
                data = json.load(f)

            # 判斷這份檔案屬於哪個遊戲標籤
            if file_name.startswith("GenshinImpact"): tag = "hk4e"
            elif file_name.startswith("Honkai_StarRail"): tag = "hkrpg"
            else: tag = "nap"

            game_list = []
            
            # 把原本分好類的 novice, standard 等陣列，全部倒進同一個大 list
            for key, items in data.items():
                if key != "info" and isinstance(items, list):
                    game_list.extend(items)

            # UIGF 通常要求資料按照抽卡時間/ID 排序 (由小到大，最舊到最新)
            game_list = sorted(game_list, key=lambda x: int(x['id']))

            # 建立單一帳號的資料區塊
            account_block = {
                "uid": data.get("info", {}).get("uid", ""),
                "timezone": data.get("info", {}).get("timezone", 8),
                "lang": data.get("info", {}).get("lang", "zh-tw"),
                "list": game_list
            }
            
            # 塞進對應的遊戲陣列中
            uigf_export[tag].append(account_block)

        # 把沒有資料的空陣列刪掉，讓輸出的 JSON 更乾淨
        if not uigf_export["hk4e"]: del uigf_export["hk4e"]
        if not uigf_export["hkrpg"]: del uigf_export["hkrpg"]
        if not uigf_export["nap"]: del uigf_export["nap"]

        return uigf_export

def check_version():
    config = configparser.ConfigParser()
    config.read('config.ini')
    url = 'https://api.github.com/repos/jenne14294/HOYO-ToolBox/releases/latest'
    response = requests.get(url)
    if response.status_code != 200: return False
    release_data = response.json()
    latest_version = release_data["html_url"][release_data["html_url"].index("tag/") + 5:]
    system_version = config.get('General', 'version')
    return latest_version > system_version
    
def download_release():
    url = 'https://api.github.com/repos/jenne14294/HOYO-ToolBox/releases/latest'
    response = requests.get(url)
    if response.status_code != 200: return False
    release_data = response.json()
    data = {}
    for asset in release_data['assets']:
        name_list = asset['name'].split(".")
        data['url'] = asset['browser_download_url']
        data['version'] = name_list[2][1:] + "." + name_list[3]
        data['name'] = asset['name']
        data['total_size'] = asset['size']
        data['path'] = f"./{asset['name']}"
        temp_path = "./temp"
        if not os.path.exists(temp_path): os.mkdir(temp_path)
        return data

def apply_update(zip_path, version):
    config = configparser.ConfigParser()
    config.read('config.ini')
    if not os.path.exists("./temp"): os.makedirs("./temp")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall("./temp")
    file_path = (f"./temp/HOYO ToolBox v{version}")
    for file in os.listdir(file_path):
        source_path = os.path.join(file_path, file)
        try: shutil.copy(source_path, "./")
        except Exception as e: print(e)
    config.set('General', 'version', version)
    with open('config.ini', 'w') as configfile: config.write(configfile)
    shutil.rmtree("./temp")
    os.remove(zip_path)