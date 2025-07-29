from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json # 導入 json 模塊
import random # 導入 random 模塊

def scrape_threads_posts():
    # --- WebDriver 設定 ---
    # 設置 Chrome 選項
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # 無頭模式，不顯示瀏覽器介面
    options.add_argument('--disable-gpu') # 禁用GPU，在某些系統上可以避免問題
    options.add_argument('--no-sandbox') # 禁用沙箱模式
    options.add_argument('--disable-dev-shm-usage') # 禁用/dev/shm使用，避免資源不足問題
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36") # 模擬User-Agent

    # 啟動 WebDriver
    print("正在啟動瀏覽器...")
    driver = None # 初始化 driver 變數
    try:
        driver = webdriver.Chrome(options=options)
        print("瀏覽器已啟動。")
    except Exception as e:
        print(f"啟動瀏覽器失敗: {e}")
        return # 啟動失敗則直接退出

    try:
        # --- 目標網址 ---
        target_url = "https://www.threads.com/" # 使用你確認有效的 Threads 首頁URL

        print(f"正在訪問網址: {target_url}")
        driver.get(target_url)

        # --- 等待頁面加載 ---
        print("等待頁面加載...")
        try:
            # 使用 data-pressable-container 來等待貼文容器出現
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-pressable-container='true']"))
            )
            print("頁面主要內容已加載。")
        except Exception as e:
            print(f"等待頁面元素超時或出錯: {e}")
            print("可能需要手動檢查頁面結構或嘗試滾動。")

        # --- 滾動頁面 (可選，但通常是必要的) ---
        # 增加滾動次數，以嘗試獲取更多貼文
        # 每次滾動之間增加隨機延遲
        scroll_count = 10 # 增加滾動次數，嘗試抓取更多貼文
        for i in range(scroll_count):
            print(f"正在滾動頁面 ({i+1}/{scroll_count})...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # 隨機延遲 2 到 5 秒
            time.sleep(random.uniform(2, 5)) 

        # --- 抓取貼文內容 ---
        print("正在抓取貼文內容...")
        # 使用新的 XPath 尋找所有貼文容器 (使用 data-pressable-container)
        posts = driver.find_elements(By.XPATH, "//div[@data-pressable-container='true']")
        print(f"找到 {len(posts)} 篇潛在的貼文容器。")

        if not posts:
            print("未找到任何貼文容器，請檢查 XPath 或頁面加載情況。")
            return # 如果沒有找到貼文，結束函數執行

        all_posts_data = [] # 用於儲存所有貼文的資料

        for i, post in enumerate(posts):
            # 達到 20 筆就停止抓取
            if len(all_posts_data) >= 20:
                print(f"已抓取到 {len(all_posts_data)} 筆貼文，達到目標數量。")
                break 

            print(f"\n--- 貼文 {i+1} ---")

            # --- 抓取作者 ---
            author = "N/A"
            try:
                author_elements = post.find_elements(By.XPATH, ".//span[contains(@class, 'x1lliihq') and ancestor::a[contains(@href, '/@')]]")
                if author_elements:
                    author = author_elements[0].text.strip()
                print(f"作者: {author}")
            except Exception as e:
                print(f"抓取作者失敗: {e}")
                author = "N/A"

            # --- 抓取貼文單獨連結 (Permalink) ---
            post_link = "N/A"
            try:
                permalink_element = post.find_element(By.XPATH, ".//a[@role='link'][time]")
                if permalink_element:
                    relative_link = permalink_element.get_attribute('href')
                    if relative_link and relative_link.startswith('/'):
                        post_link = f"https://www.threads.com{relative_link}"
                    else:
                        post_link = relative_link
                print(f"貼文連結: {post_link}")
            except Exception as e:
                print(f"抓取貼文連結失敗: {e}")
                post_link = "N/A"

            # --- 抓取貼文文字內容 ---
            post_text = "N/A"
            try:
                # 恢復到之前能成功抓取且沒有語法錯誤的版本
                text_elements = post.find_elements(By.XPATH, ".//div[contains(@class, 'x1a6qonq') and contains(@class, 'x6ikm8r')]//span[contains(@class, 'x1lliihq')]//span")
                
                post_text_parts = [elem.text.strip() for elem in text_elements if elem.text.strip() != '']
                post_text = "\n".join(post_text_parts)

                # 移除重複的文本行
                post_text = "\n".join(sorted(list(set(post_text.splitlines())), key=post_text.splitlines().index))
                print(f"內容: {post_text[:300]}...") # 顯示前300字
            except Exception as e:
                print(f"抓取內容失敗: {e}")
                post_text = "N/A"

            # --- 檢查是否有圖片或影片 ---
            has_image = False
            has_video = False
            
            try:
                image_elements = post.find_elements(By.XPATH, ".//img")
                if image_elements:
                    has_image = True
            except:
                pass 

            try:
                video_elements = post.find_elements(By.XPATH, ".//video")
                if video_elements:
                    has_video = True
            except:
                pass 
            
            media_note = []
            if has_image:
                media_note.append("有圖片")
            if has_video:
                media_note.append("有影片")
            
            if media_note:
                print(f"媒體類型: {', '.join(media_note)}")
            else:
                print("媒體類型: 無")

            # 將抓取的數據添加到列表中
            all_posts_data.append({
                "author": author,
                "link": post_link,
                "content": post_text,
                "has_image": has_image,
                "has_video": has_video
            })
            # 每次處理完一篇貼文後，也增加隨機延遲，模擬人類瀏覽行為
            time.sleep(random.uniform(1, 3)) # 隨機延遲 1 到 3 秒

        # --- 數據儲存為 JSON 檔案 ---
        output_filename = "threads_posts.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_posts_data, f, ensure_ascii=False, indent=4)
        print(f"\n所有貼文數據已儲存到 '{output_filename}'")


    except Exception as e:
        print(f"運行過程中發生錯誤: {e}")
        # 如果你啟用了無頭模式，這裡可以考慮保存截圖
        # if driver and '--headless' in options.arguments:
        #     driver.save_screenshot('error_screenshot.png')
        #     print("已在無頭模式下截圖，請檢查 error_screenshot.png")

    finally:
        # --- 關閉瀏覽器 ---
        if driver:
            print("正在關閉瀏覽器...")
            driver.quit()
            print("瀏覽器已關閉。")

# 運行爬蟲
if __name__ == "__main__":
    scrape_threads_posts()