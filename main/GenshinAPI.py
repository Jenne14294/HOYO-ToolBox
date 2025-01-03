import sqlite3
import json
import genshin
import os
import asyncio

from datetime import datetime
from dateutil.relativedelta import relativedelta


local_folder_path = os.environ.get("LOCALAPPDATA")
data_path = os.path.join(local_folder_path, "HoYo ToolBox") # pyright: ignore[reportCallIssue, reportArgumentType]
diary_path = os.path.join(data_path, "diary")
cookie_file_path = os.path.join(data_path, "QtWebEngine/Default/Cookies")

def read_cookies(cookie_file_path):
    if not os.path.exists(cookie_file_path):
        print(f"檔案 {cookie_file_path} 不存在!")
        return None

    conn = sqlite3.connect(cookie_file_path)
    cursor = conn.cursor()

    # 查詢 cookies 表格
    cursor.execute('SELECT name, value FROM cookies')
    cookies = cursor.fetchall()

    cookie_dict = {}
    for cookie in cookies:
        cookie_dict[cookie[0]] = cookie[1]

    conn.close()
    return cookie_dict


def write_cookie(id):
    conn = sqlite3.connect('./HOYO_ToolBox.db')  
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        uid INTEGER PRIMARY KEY,
        nick TEXT,
        game TEXT,
        level INTEGER,
        id INTEGER,
        name TEXT
    )
    ''')
    conn.commit()
    
    functions = API_function()
    user, accounts = asyncio.run(functions.get_accounts(id))

    cursor.execute('SELECT * FROM accounts')
    cookie_account_list = cursor.fetchall()
    cookie_accounts = []

    for cookie_account in cookie_account_list:
        cookie_accounts.append(str(cookie_account[0]))

    for account in accounts:
        if account['uid'] not in cookie_accounts:
            cursor.execute(f"INSERT INTO accounts (uid, nick, game, level, id, name) VALUES (?, ?, ?, ?, ?, ?)", (account['uid'], account['nick'], account['game'], account['level'], user['id'], user['name']))

    conn.commit()
    conn.close()

def get_hoyolab_account():
    # 建立與資料庫的連接
    conn = sqlite3.connect('./HOYO_ToolBox.db')  # 替換成你的資料庫檔案路徑
    cursor = conn.cursor()

    # 執行查詢以獲取不重複的 id
    cursor.execute("SELECT DISTINCT id, name FROM accounts")
    unique_ids = cursor.fetchall()
    accounts = []

    for account in unique_ids:
        accounts.append((str(account[0]), account[1]))  # 每個 uid 是一個 tuple，所以需要用 uid[0] 提取值
        
    # 關閉連接
    conn.close()
    return accounts




class CookieNotFound(Exception):
    pass

class API_function():
    def __init__(self):
        self.cookies = read_cookies(cookie_file_path)

        if not self.cookies:
            raise CookieNotFound("Cookie Not Found！")
        
        self.lang = self.cookies["mi18nLang"]
        self.client = genshin.Client(self.cookies, lang=self.lang)
        self.diary_path = diary_path





    #通用

    async def get_accounts(self, id):
        user = await self.client.get_hoyolab_user(hoyolab_id=id)

        accounts = await self.client.get_game_accounts()
        account_data = [
            {
                "uid": str(account.uid),
                "nick": str(account.nickname),
                "game": str(account.game.name),
                "level": int(account.level)
            } 
            for account in accounts
            ]
        
        user_data = {
            "id":user.hoyolab_id,
            "name":user.nickname
            }

        return user_data, account_data
    
    def get_game_accounts(self, id, game):
        # 建立與資料庫的連接
        conn = sqlite3.connect('./HOYO_ToolBox.db')  # 替換成你的資料庫檔案路徑
        cursor = conn.cursor()

        # 執行查詢以獲取不重複的 id
        cursor.execute("SELECT uid FROM accounts where id = ? and game = ?", (id, game))
        unique_ids = cursor.fetchall()
        accounts = []

        for account in unique_ids:
            accounts.append(str(account[0]))  # 每個 uid 是一個 tuple，所以需要用 uid[0] 提取值
            
        # 關閉連接
        conn.close()
        return accounts


    #原神

    async def get_genshin_diary(self, uid):
        now_info = datetime.now()
        last_info = now_info - relativedelta(months=1)
        last_two_info = now_info - relativedelta(months=2)

        for info in [now_info, last_info, last_two_info]:
            diary = await self.client.get_genshin_diary(uid, month=info.month)
            diary_data = json.loads(diary.model_dump_json())
            uid = diary_data["uid"]
            diary_path = os.path.join(self.diary_path, f"GenshinImpact_{uid}_{str(info.month).zfill(2)}_{info.year}.json")

            with open(diary_path, "w", encoding="utf8") as file:
                json.dump(diary_data, file, indent=4, ensure_ascii=False)

    async def get_genshin_notes(self, uid):
        info = await self.client.get_genshin_user(uid=uid)
        notes = await self.client.get_genshin_notes(uid=uid)

        info_data = json.loads(info.model_dump_json())
        notes_data = json.loads(notes.model_dump_json())

        notes_data["info"] = info_data["info"]
        
        return notes_data




    #崩鐵

    async def get_starrail_diary(self, uid):
        now_info = datetime.now()

        diary = await self.client.get_starrail_diary(uid)
        diary_data = json.loads(diary.model_dump_json())
        uid = diary_data["uid"]
        diary_path = os.path.join(self.diary_path, f"HonkaiStarRail_{uid}_{str(now_info.month).zfill(2)}_{now_info.year}.json")

        with open(diary_path, "w", encoding="utf8") as file:
            json.dump(diary_data, file, indent=4, ensure_ascii=False)

    async def get_starrail_notes(self, uid):
        info = await self.client.get_starrail_user(uid)
        notes = await self.client.get_starrail_notes(uid)

        info_data = json.loads(info.model_dump_json())
        notes_data = json.loads(notes.model_dump_json())

        notes_data["info"] = info_data["info"]
        
        return notes_data

    ##絕區零

    async def get_zzz_diary(self, uid):
        now_info = datetime.now()

        diary = await self.client.get_zzz_diary(uid, month=now_info.month)
        diary_data = json.loads(diary.model_dump_json())
        uid = diary_data["uid"]
        diary_data['nickname'] = diary_data['player']['nickname']
        diary_data['avatar_url'] = diary_data['player']['avatar_url']
        diary_data['server'] = diary_data['region']

        diary_path = os.path.join(self.diary_path, f"ZenlessZoneZero_{uid}_{str(now_info.month).zfill(2)}_{now_info.year}.json")

        with open(diary_path, "w", encoding="utf8") as file:
            json.dump(diary_data, file, indent=4, ensure_ascii=False)

    async def get_zzz_notes(self, uid):
        notes = await self.client.get_zzz_notes(uid)

        notes_data = json.loads(notes.model_dump_json())

        notes_data["info"] = {}
        notes_data["info"]["nickname"] = ""
        notes_data["info"]["level"] = ""
        
        return notes_data
    
    

