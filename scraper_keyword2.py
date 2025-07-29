from datetime import datetime
import time, json, random
from dateutil import parser, tz
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import jieba.analyse


# --- 登入 Threads (Instagram)
def login_to_threads(driver):
    IG_USERNAME = "leafwann_"
    IG_PASSWORD = "threads2025"

    driver.get("https://www.threads.net/login")
    try:
        login_button = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//span[text()='使用 Instagram 帳號繼續']"))
        )
        login_button.click()
    except:
        print("❌ 找不到登入按鈕")
        return False

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "username")))
        driver.find_element(By.NAME, "username").send_keys(IG_USERNAME)
        driver.find_element(By.NAME, "password").send_keys(IG_PASSWORD)
        driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-pressable-container='true']"))
        )
        return True
    except Exception as e:
        print("❌ 登入失敗：", e)
        return False

# --- 擷取留言（避開主文、只抓指定留言容器）
def scrape_comments_from_post_page(driver):
    comments = []
    try:
        wrapper = driver.find_element(By.XPATH, "//div[contains(@class,'xb57i2i') and contains(@class,'x1q594ok')]")
        comment_blocks = wrapper.find_elements(By.XPATH, ".//div[contains(@class, 'x1a6qonq')]")[1:]
        for block in comment_blocks:
            spans = block.find_elements(By.XPATH, ".//span[@dir='auto']/span")
            text = "\n".join([s.text.strip() for s in spans if s.text.strip()])
            if text:
                comments.append(text)
            if len(comments) >= 10:
                break
    except Exception as e:
        print("留言擷取錯誤：", e)
    return comments


# 產生主題 title（使用 jieba）
def generate_title_with_keywords(text, topk=3):
    """
    從一段文字中抽取關鍵詞作為主題。
    Args:
        text (str): 貼文內容
        topk (int): 選幾個關鍵詞組成主題
    Returns:
        str: 由關鍵詞組成的主題，例如「沖繩｜推薦｜海」
    """
    keywords = jieba.analyse.extract_tags(text, topK=topk)
    return "｜".join(keywords) if keywords else "無法產生主題"


# --- Threads 貼文爬取主函數（關鍵字模式）
def scrape_threads_by_keyword():
    keyword_to_search = input("請輸入要搜尋的關鍵字：")

    MAX_TARGET = 50
    MAX_SCROLLS = 40
    MAX_NO_NEW_SCROLLS = 2

    start_time = datetime.now()
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(options=options)

    try:
        if not login_to_threads(driver):
            return

        driver.get("https://www.threads.com/search?hl=zh-tw")
        search_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='search' and @placeholder='搜尋']"))
        )
        search_input.send_keys(keyword_to_search)
        search_input.send_keys(Keys.ENTER)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-pressable-container='true']"))
        )

        all_posts_data = []
        post_index = 0
        scroll_round = 0
        no_new_scrolls = 0
        last_post_count = 0
        main_window_handle = driver.current_window_handle

        while len(all_posts_data) < MAX_TARGET and scroll_round < MAX_SCROLLS:
            scroll_round += 1
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 4))

            posts = driver.find_elements(By.XPATH, "//div[@data-pressable-container='true']")
            if len(posts) == last_post_count:
                no_new_scrolls += 1
                if no_new_scrolls >= MAX_NO_NEW_SCROLLS:
                    print("⚠️ 多次滾動無新內容，停止。")
                    break
            else:
                no_new_scrolls = 0
                last_post_count = len(posts)

            while post_index < len(posts) and len(all_posts_data) < MAX_TARGET:
                post = posts[post_index]
                post_index += 1
                print(f"\n📝 正在處理第 {post_index} 篇貼文")

                try:
                    author = post.find_element(By.XPATH, ".//span[contains(@class,'x1lliihq') and ancestor::a[contains(@href, '/@')]]").text.strip()
                except: author = "N/A"

                try:
                    permalink = post.find_element(By.XPATH, ".//a[@role='link'][time]").get_attribute("href")
                    post_link = "https://www.threads.com" + permalink if permalink.startswith("/") else permalink
                except: post_link = "N/A"

                try:
                    raw_time = post.find_element(By.XPATH, ".//time").get_attribute("datetime")
                    taipei_time = parser.parse(raw_time).astimezone(tz.gettz("Asia/Taipei"))
                    post_time = taipei_time.strftime("%Y-%m-%d %H:%M:%S")
                except: post_time = "N/A"

                try:
                    spans = post.find_elements(By.XPATH, ".//div[contains(@class,'x1a6qonq') and contains(@class,'x6ikm8r')]//span[contains(@class,'x1lliihq')]//span")
                    parts = [s.text.strip() for s in spans if s.text.strip()]
                    post_text = "\n".join(sorted(set(parts), key=parts.index))
                    post_title = generate_title_with_keywords(post_text)

                except: post_text = "N/A"

                # has_image = bool(post.find_elements(By.XPATH, ".//img"))
                # has_video = bool(post.find_elements(By.XPATH, ".//video"))

                # 抓留言
                comments_data = []
                if post_link != "N/A":
                    try:
                        driver.execute_script("window.open(arguments[0]);", post_link)
                        time.sleep(2)
                        new_tab = [w for w in driver.window_handles if w != main_window_handle][-1]
                        driver.switch_to.window(new_tab)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        comments_data = scrape_comments_from_post_page(driver)
                        driver.close()
                        driver.switch_to.window(main_window_handle)
                    except Exception as e:
                        print("留言抓取錯誤：", e)
                        if len(driver.window_handles) > 1:
                            driver.close()
                        driver.switch_to.window(main_window_handle)

                all_posts_data.append({
                    "author": author,
                    "link": post_link,
                    "post_time": post_time,
                    "title": post_title,
                    "content": post_text,
                    # "has_image": has_image,
                    # "has_video": has_video,
                    "comments": comments_data
                })

                print(f"✅ 收錄第 {len(all_posts_data)} 篇貼文")
                time.sleep(random.uniform(1, 2))

        elapsed = datetime.now() - start_time
        result = {
            "summary": {
                "total_posts": len(all_posts_data),
                "elapsed_time": f"{elapsed.seconds // 60} 分 {elapsed.seconds % 60} 秒"
            },
            "posts": all_posts_data
        }

        filename = f"threads_posts_{keyword_to_search}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n📁 已儲存為 {filename}")
        print(f"📊 共抓取 {len(all_posts_data)} 筆，耗時 {elapsed.seconds // 60} 分 {elapsed.seconds % 60} 秒")

    finally:
        print("🧹 關閉瀏覽器...")
        driver.quit()
        print("✅ 結束")

# --- 執行
if __name__ == "__main__":
    scrape_threads_by_keyword()
