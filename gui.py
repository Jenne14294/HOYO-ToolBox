import os
import json
import tkinter as tk
import threading
import textwrap
import functions
import webview
from tkinter import messagebox, filedialog


local_folder_path = os.environ.get("LOCALAPPDATA")
data_path = os.path.join(local_folder_path, "HoYo ToolBox") # pyright: ignore[reportCallIssue, reportArgumentType]

# 創建主視窗
root = tk.Tk()
root.title("抽卡紀錄與HOYO工具箱")
root.geometry("1200x500")

selected_game = tk.StringVar(value="原神")  # 預設選擇原神
selected_category = tk.StringVar(value="角色")  # 預設選擇角色
selected_game_path = tk.StringVar()

def change_account(account):
    selected_account.set(account)
    show_record_options()

def get_options():
    account_options = []
    folder_path = f"{data_path}/user_data"

    for file in os.listdir(folder_path):
        start_index = file.find("_", 10)
        end_index = file.find(".json")

        if selected_game.get() == "原神":
            if file.startswith("GenshinImpact"):
                account_options.append(file[start_index + 1:end_index])

        elif selected_game.get() == "崩鐵":
            if file.startswith("Honkai_StarRail"):
                account_options.append(file[start_index + 1:end_index])
                
        elif selected_game.get() == "絕區零":
            if file.startswith("ZenlessZoneZero"):
                account_options.append(file[start_index + 1:end_index])
                
    return account_options


selected_account = tk.StringVar(value=get_options()[0]) if len(get_options()) > 0 else tk.StringVar()

# 定義 input_frame 和 message_label 為全局變量
input_frame = tk.Frame(root)
message_label = tk.Label(root, text="", font=("Arial", 14))

def add_line_spacing(text, width, line_spacing=1):
    wrapped_lines = textwrap.wrap(text, width=width)  # 分行
    spaced_text = ("\n" * line_spacing).join(wrapped_lines)  # 插入空行
    return spaced_text

def fetch_data_in_thread():
    def thread_target():
        try:
            game = selected_game.get()

            if game == "原神":
                message_label.config(text="正在讀取原神歷史紀錄，請稍等...")
                functions.get_GSdata_by_api()

            elif game == "崩鐵":
                message_label.config(text="正在讀取崩鐵歷史紀錄，請稍等...")
                functions.get_HSRdata_by_api()

            elif game == "絕區零":
                message_label.config(text="正在讀取絕區零歷史紀錄，請稍等...")
                functions.get_HSRdata_by_api()

            message_label.config(text="抽卡紀錄已讀取")

        except Exception as e:
            root.after(0, messagebox.showerror, "Error", f"無法讀取歷史紀錄，請先在遊戲裡開啟")
            print(e)

    thread = threading.Thread(target=thread_target)
    thread.start()

    root.after(0, show_game_options(selected_game.get()))

# 顯示記錄選項的函數
def show_record_options():
    # 清除 option_frame 和 game_frame 內的所有子元件
    for widget in option_frame.winfo_children():
        widget.destroy()
    for widget in game_frame.winfo_children():
        widget.destroy()

    # 遊戲選擇標籤
    tk.Label(option_frame, text="選擇遊戲:").pack(anchor=tk.W)

    # 遊戲選擇的單選按鈕
    radio_frame = tk.Frame(option_frame)
    radio_frame.pack(anchor=tk.W, padx=10)
    
    tk.Radiobutton(radio_frame, text="絕區零", variable=selected_game, value="絕區零", command=show_record_options).pack(side=tk.BOTTOM)
    tk.Radiobutton(radio_frame, text="崩鐵", variable=selected_game, value="崩鐵", command=show_record_options).pack(side=tk.BOTTOM)
    tk.Radiobutton(radio_frame, text="原神", variable=selected_game, value="原神", command=show_record_options).pack(side=tk.BOTTOM)

    # 帳號選擇標籤
    tk.Label(option_frame, text="選擇帳號:").pack(anchor=tk.W, padx=10, pady=5)

    # 獲取帳號選項
    account_options = get_options()
    # 帳號選項下拉選單
    if len(account_options) > 0:
        # 如果當前選擇的帳號不在選項中，重置為第一個選項
        if selected_account.get() not in account_options:
            selected_account.set(account_options[0])

        # 創建下拉選單並綁定到 selected_account
        account_option_menu = tk.OptionMenu(option_frame, selected_account, *account_options, command=change_account)
        account_option_menu.pack(anchor=tk.W, padx=10)

    # 信息標籤，顯示在按鈕上方並居中
    message_label.pack(anchor=tk.CENTER, pady=10)

    # 顯示當前選中的遊戲選項
    show_game_options(selected_game.get())


def show_game_options(selected_game):
    # 清空先前的內容
    for widget in game_frame.winfo_children():
        widget.destroy()

    options = []
    colors = ["#FFC0CB", "#FFD700", "#ADFF2F", "#1E90FF", "#FF69B4"]  # 定義顏色

    accountID = selected_account.get() if selected_account != "" else ""
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

    # 創建選項框架
    option_frame = tk.Frame(game_frame)
    option_frame.pack(pady=20)

    # 創建按鈕框架
    button_frame = tk.Frame(game_frame)
    button_frame.pack(side=tk.BOTTOM, pady=10)
    tk.Button(button_frame, text="讀取抽卡紀錄", command=fetch_data_in_thread).pack(side=tk.LEFT)

    # 下拉選單
    selected_option = tk.StringVar(value="外部資料源")
    dropdown = tk.OptionMenu(button_frame, selected_option, "手動輸入(不會儲存資料)", "導入 JSON(會儲存資料)", command=handle_dropdown_selection)
    dropdown.pack(side=tk.LEFT)

    # 增加輸出按鈕
    if selected_game == "原神":
        if os.path.exists(f"{data_path}/user_data/GenshinImpact_{selected_account.get()}.json"):
            export_button = tk.Button(button_frame, text="導出Json", command=export_to_folder)
            export_button.pack(side=tk.LEFT, padx=5)

    elif selected_game == "崩鐵":
        if os.path.exists(f"{data_path}/user_data/Honkai_StarRail_{selected_account.get()}.json"):
            export_button = tk.Button(button_frame, text="導出Json", command=export_to_folder)
            export_button.pack(side=tk.LEFT, padx=5)

    elif selected_game == "絕區零":
        if os.path.exists(f"{data_path}/user_data/ZenlessZoneZero_{selected_account.get()}.json"):
            export_button = tk.Button(button_frame, text="導出Json", command=export_to_folder)
            export_button.pack(side=tk.LEFT, padx=5)


    # 隱藏並重新顯示 input_frame
    input_frame.pack_forget()
    input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 如果資料檔案存在，讀取資料
    if os.path.exists(path): 
        with open(path, "r", encoding="utf8") as file: 
            data = json.load(file) 

        # 處理每個選項
        for i, option in enumerate(options):
            if option == "資訊":
                continue

            text = ""
            counter = 0

            keys = list(data.keys())

            # 創建 Canvas 和 Scrollbar
            label_canvas = tk.Canvas(option_frame, bg=colors[i % len(colors)], width=250, height=300)  # 設置 Canvas 寬度和高度
            scrollbar = tk.Scrollbar(option_frame, orient="vertical", command=label_canvas.yview)  # 創建垂直滾動條
            scrollable_frame = tk.Frame(label_canvas, bg=colors[i % len(colors)])  # 創建可滾動的框架

            # 綁定scrollregion自動更新
            scrollable_frame.bind(
                "<Configure>",
                lambda e, canvas=label_canvas: canvas.configure(
                    scrollregion=canvas.bbox("all")  # 自動調整 scrollregion
                )
            )

            # 在 Canvas 上創建可滾動的框架
            label_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            label_canvas.configure(yscrollcommand=scrollbar.set)  # 滾動條與 Canvas 綁定

            # 顯示 Canvas 和 滾動條
            label_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            scrollbar.pack(side=tk.LEFT, fill="y")

            # 顯示每個選項標題
            tk.Label(scrollable_frame, text=option, padx=10, pady=5, bg=colors[i % len(colors)], font=("Arial", 16)).pack(anchor=tk.W)
            
            if keys[i] == "info":
                continue

            reversed_data = data[keys[i]][::-1]  # 反向顯示數據

            if reversed_data == []:
                continue

            # 顯示抽卡紀錄
            for items in reversed_data:
                counter += 1
                if selected_game != "絕區零":
                    if items['rank_type'] == '5':  # 顯示五星角色或武器
                        text += f"{items['name']} [{counter}] "
                        counter = 0
                else:
                    if items["rank_type"] == "4":
                        text += f"{items['name']} [{counter}] "
                        counter = 0

            result = add_line_spacing(text, width=22.5, line_spacing=2)
            tk.Label(scrollable_frame, text=result, padx=5, pady=5, bg=colors[i % len(colors)], font=("Arial", 12)).pack(anchor=tk.W)

        # 顯示平均數據
        input_data = functions.get_average(path, selected_game, "", selected_category.get())
        message_label.config(text=input_data)

    else:
        message_label.config(text="")



def handle_dropdown_selection(selection):
    if "手動輸入" in selection:
        show_entry()
        
    elif "導入 JSON" in selection:
        import_json()

def show_entry():
    input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    for widget in input_frame.winfo_children():
        widget.destroy()

    # 創建一個框架來包含Radio Button和文本框
    entry_frame = tk.Frame(input_frame)
    entry_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # 左側Radio Button框架
    radio_frame = tk.Frame(entry_frame)
    radio_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
    
    tk.Radiobutton(radio_frame, text="角色", variable=selected_category, value="角色").pack(anchor=tk.W)
    tk.Radiobutton(radio_frame, text="武器", variable=selected_category, value="武器").pack(anchor=tk.W)
    
    # 右側文本框
    text_box = tk.Text(entry_frame)
    text_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    # 添加開始計算按鈕到 entry_frame
    start_button = tk.Button(radio_frame, text="開始計算", command=lambda:caculate_average_manual(text_box))
    start_button.pack(anchor=tk.CENTER, pady=10)

def caculate_average_manual(text_box):
    result = functions.get_average("", selected_game.get(), text_box.get("1.0", tk.END).strip(), selected_category.get())
    message_label.config(text=result)


def import_json():
    input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    for widget in input_frame.winfo_children():
        widget.destroy()

    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    system_path = f"{data_path}/user_data/GenshinImpact.json" if selected_game.get() == "原神" else f"{data_path}/user_data/Honkai_StarRail.json" if selected_game.get() == "崩鐵" else f"{data_path}/user_data/ZenlessZoneZero.json"

    if file_path:      
        extracted_data = functions.extract_data(selected_game.get(), file_path)
        
        if extracted_data == "錯誤的遊戲資料":
            messagebox.showerror("error", "導入錯誤或無法解析的資料")
            return
        
        account = extracted_data['info']['uid']
        system_path = system_path[:-5] + f"_{account}.json"

    if os.path.exists(system_path):
        extracted_data = functions.compare_input_data(system_path, extracted_data, selected_game.get())

    with open(system_path, "w", encoding="utf8") as file:
        json.dump(extracted_data, file, indent=4 ,ensure_ascii=False)

    selected_account.set(account)

    root.after(0, show_game_options, selected_game.get())
    root.after(0, show_record_options)

def export_to_folder():
    """讓用戶選擇資料夾並輸出檔案。"""
    folder_path = filedialog.askdirectory()  # 開啟選擇資料夾對話框
    if folder_path:
        try:
            # 載入當前帳號的資料
            accountID = selected_account.get()

            if selected_game.get() == "原神":
                file_path = f"{data_path}/user_data/GenshinImpact_{accountID}.json"
                export_file_name = f"GenshinImpact_{accountID}_export.json"

            elif selected_game.get() == "崩鐵":
                file_path = f"{data_path}/user_data/Honkai_StarRail_{accountID}.json"
                export_file_name = f"Honkai_StarRail_{accountID}_export.json"

            elif selected_game.get() == "絕區零":
                file_path = f"{data_path}/user_data/ZenlessZoneZero_{accountID}.json"
                export_file_name = f"ZenlessZoneZero_{accountID}_export.json"

            # 確保來源檔案存在
            if not os.path.exists(file_path):
                messagebox.showerror("錯誤", "無法找到要導出的檔案！")
                return

            export_path = os.path.join(folder_path, export_file_name)
            functions.export_json(file_path, export_path)

            messagebox.showinfo("成功", f"檔案已成功輸出至：\n{export_path}")

        except Exception as e:
            messagebox.showerror("錯誤", f"檔案輸出失敗：{e}")

def create_webview():
    if selected_game.get() == "原神":
        url = "https://act.hoyolab.com/app/community-game-records-sea/index.html?bbs_presentation_style=fullscreen&v=350&gid=2&utm_source=hoyolab&utm_medium=tools&bbs_theme=dark&bbs_theme_device=0#/ys"

    elif selected_game.get() == "崩鐵":
        url = "https://act.hoyolab.com/app/community-game-records-sea/rpg/index.html?bbs_presentation_style=fullscreen&gid=6&utm_campaign=battlechronicle&utm_id=6&utm_medium=tools&utm_source=hoyolab&v=101&lang=zh-tw&bbs_theme=dark&bbs_theme_device=0#/hsr"
        
    webview.create_window("WebView", url, width=800, height=600)
    webview.start()

def dummy_function():
    messagebox.showinfo("提示", "這是一個尚未實現的功能")

def hoyo_toolbox():
    for widget in option_frame.winfo_children():
        widget.destroy()

    for widget in game_frame.winfo_children():
        widget.destroy()

    create_webview()

def show_selected_path():
    """顯示使用者選擇的遊戲路徑"""
    selected_path = selected_game_path.get()
    if selected_path:
        messagebox.showinfo("選擇的路徑", f"您選擇的遊戲路徑是：\n{selected_path}")
    else:
        messagebox.showwarning("警告", "尚未選擇遊戲路徑")

# 使用者選擇路徑
def select_game_path():
    """讓使用者選擇遊戲路徑"""
    file_path = filedialog.askopenfilename(title="選擇遊戲執行檔", filetypes=[("Executable Files", "*.exe")])
    if file_path:
        selected_game_path.set(file_path)

        # 顯示選擇的路徑
        messagebox.showinfo("遊戲路徑已選擇", f"您選擇的遊戲路徑是：\n{file_path}")
    else:
        messagebox.showwarning("警告", "未選擇任何遊戲路徑")

# 遊戲啟動
def launch_game():
    """檢查路徑並啟動遊戲"""
    game_path = selected_game_path.get()
    if os.path.exists(game_path):
        messagebox.showinfo("啟動遊戲", f"正在啟動遊戲：{game_path}...")
        os.startfile(game_path)  # 啟動遊戲
    else:
        messagebox.showwarning("警告", "遊戲路徑無效，請重新選擇正確的路徑。")


def game_function():
    """顯示遊戲功能的選項介面。"""
    for widget in option_frame.winfo_children():
        widget.destroy()
    for widget in game_frame.winfo_children():
        widget.destroy()

    message_label.config(text="")  # 清空之前的訊息

    # 標題
    tk.Label(game_frame, text="遊戲功能", font=("Arial", 16)).pack(pady=10)

    # 遊戲選擇標籤
    tk.Label(game_frame, text="選擇遊戲:").pack(anchor=tk.W, padx=10, pady=5)

        # 按鈕框架
    game_function_frame = tk.Frame(root)
    game_function_frame.pack(pady=20)

    # 遊戲選擇按鈕
    select_button = tk.Button(game_function_frame, text="選擇遊戲路徑", command=select_game_path)
    select_button.pack(pady=10)

    # 顯示選擇的路徑按鈕
    show_path_button = tk.Button(game_function_frame, text="顯示選擇的路徑", command=show_selected_path)
    show_path_button.pack(pady=10)

    # 啟動遊戲按鈕
    launch_button = tk.Button(game_function_frame, text="啟動遊戲", command=launch_game)
    launch_button.pack(pady=10)

    def check_and_launch(game_name, path):
        """檢查路徑並執行遊戲，如果未安裝則提示下載。"""
        if os.path.exists(path):
            messagebox.showinfo("提示", f"正在啟動 {game_name}...")

            os.startfile(path)
        else:
            messagebox.showwarning("下載遊戲", f"{game_name} 尚未安裝，請下載遊戲！")

    # 遊戲執行路徑（更新為真實路徑）
    game_paths = {
        "原神": "C:\\Games\\Genshin Impact\\launcher.exe",
        "崩鐵": "C:\\Games\\Honkai Star Rail\\launcher.exe",
        "絕區零": "C:\\Games\\Zenless Zone Zero\\launcher.exe",
    }

    # 創建按鈕
    for game_name, path in game_paths.items():
        tk.Button(button_frame, text=game_name, font=("Arial", 12),
                  command=lambda g=game_name, p=path: check_and_launch(g, p)).pack(side=tk.LEFT, padx=10)

    # 提示框架
    tk.Label(game_frame, text="提示: 如果遊戲未安裝，請確保路徑正確或前往官網下載。", fg="gray").pack(pady=5)
    

# 創建主框架
option_frame = tk.Frame(root)
option_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

game_frame = tk.Frame(root)
game_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# 主選單保持在畫面底部
button_frame = tk.Frame(root)
button_frame.pack(side=tk.BOTTOM, pady=10)
tk.Button(button_frame, text="抽卡紀錄", command=show_record_options).pack(side=tk.LEFT)
tk.Button(button_frame, text="HOYO工具箱", command=hoyo_toolbox).pack(side=tk.RIGHT)
tk.Button(button_frame, text="遊戲功能", command=game_function).pack(side=tk.RIGHT)

# 運行主循環
root.mainloop()
