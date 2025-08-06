from datetime import datetime, timedelta
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
from selenium.common.exceptions import StaleElementReferenceException


def login_to_threads(driver):
    IG_USERNAME = "leafwann_"
    IG_PASSWORD = "threads2025"

    driver.get("https://www.threads.net/login")

    try:
        # 尋找並等待「使用 Instagram 帳號繼續」按鈕變得可點擊
        login_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='使用 Instagram 帳號繼續']"))
        )
        print("✅ 找到登入按鈕，點擊中...")
        login_button.click()
    except TimeoutException:
        print("❌ 找不到登入按鈕，等待超時。")
        return False
    except Exception as e:
        print(f"❌ 登入按鈕點擊失敗，可能是被其他元素阻擋: {e}")
        # 在這裡加入等待阻擋元素消失的邏輯
        try:
            print("⏳ 偵測到阻擋元素，正在等待其消失...")
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.XPATH, "//div[@role='alert']"))
            )
            # 如果彈出視窗消失，重新嘗試點擊登入按鈕
            login_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='使用 Instagram 帳號繼續']"))
            )
            login_button.click()
            print("✅ 重新點擊登入按鈕成功！")
        except:
            print("❌ 無法處理阻擋元素，登入流程失敗。")
            return False

    try:
        # 等待使用者名稱輸入框出現
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "username")))
        print("✅ 成功進入 IG 登入頁面，輸入帳密中...")
        driver.find_element(By.NAME, "username").send_keys(IG_USERNAME)
        driver.find_element(By.NAME, "password").send_keys(IG_PASSWORD)
        driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
        
        # 等待登入成功後的頁面元素
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-pressable-container='true']"))
        )
        print("✅ 成功登入 Threads。")
        return True
    except TimeoutException:
        print("❌ 登入流程超時，登入失敗。")
        return False
    except Exception as e:
        print(f"❌ 登入失敗：{e}")
        return False


# --- 登入 Threads (Instagram)
# def login_to_threads(driver):
#     IG_USERNAME = "leafwann_"
#     IG_PASSWORD = "threads2025"

#     driver.get("https://www.threads.net/login")
#     try:
#         login_button = WebDriverWait(driver, 15).until(
#             EC.presence_of_element_located((By.XPATH, "//span[text()='使用 Instagram 帳號繼續']"))
#         )
#         login_button.click()
#     except:
#         print("❌ 找不到登入按鈕")
#         return False

#     try:
#         WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "username")))
#         driver.find_element(By.NAME, "username").send_keys(IG_USERNAME)
#         driver.find_element(By.NAME, "password").send_keys(IG_PASSWORD)
#         driver.find_element(By.NAME, "password").send_keys(Keys.ENTER)
#         WebDriverWait(driver, 20).until(
#             EC.presence_of_element_located((By.XPATH, "//div[@data-pressable-container='true']"))
#         )
#         return True
#     except Exception as e:
#         print("❌ 登入失敗：", e)
#         return False

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

def count_chinese_chars(text):
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def is_mostly_chinese(text, threshold=0.6):
    chinese_chars = count_chinese_chars(text)
    return (chinese_chars / max(len(text), 1)) >= threshold

def scrape_threads_by_keyword(keyword):
    keyword_to_search = keyword

    MAX_TARGET = 15
    MAX_SCROLLS = 100
    MAX_NO_NEW_SCROLLS = 10
    MAX_DAYS = 7

    time_cutoff = datetime.now(tz=tz.gettz("Asia/Taipei")) - timedelta(days=MAX_DAYS)

    start_time = datetime.now()
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
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

        # ✅ 點選「最近」Tab
        try:
            recent_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='最近']"))
            )
            recent_tab.click()
            print("🕓 已點選『最近』Tab")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ 點選『最近』Tab 失敗：{e}")

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
            new_posts_found = len(posts) > last_post_count
            last_post_count = len(posts)

            post_index = 0  # 每次滾動後從新一輪貼文開始

            while post_index < len(posts) and len(all_posts_data) < MAX_TARGET:
                try:
                    post = posts[post_index]
                except IndexError:
                    break  # 超出貼文列表長度
                post_index += 1

                try:
                    print(f"\n📝 正在處理第 {post_index} 篇貼文")

                    # 發文時間過濾
                    try:
                        raw_time = post.find_element(By.XPATH, ".//time").get_attribute("datetime")
                        taipei_time = parser.parse(raw_time).astimezone(tz.gettz("Asia/Taipei"))
                        if taipei_time < time_cutoff:
                            print(f"📅 發文時間 {taipei_time.strftime('%Y-%m-%d %H:%M:%S')} 超出日期區間，跳過")
                            continue
                        post_time = taipei_time.strftime("%Y-%m-%d")
                    except Exception as e:
                        print(f"⏳ 無法解析時間，跳過（錯誤：{e}）")
                        continue

                    # 內文抓取
                    try:
                        spans = post.find_elements(By.XPATH, ".//div[contains(@class,'x1a6qonq') and contains(@class,'x6ikm8r')]//span[contains(@class,'x1lliihq')]//span")
                        parts = [s.text.strip() for s in spans if s.text.strip()]
                        post_text = "\n".join(sorted(set(parts), key=parts.index))
                    except:
                        print("❌ 抓取貼文內容失敗，跳過")
                        continue

                    if not is_mostly_chinese(post_text):
                        print("🌐 非中文主體貼文，跳過")
                        continue
                    if count_chinese_chars(post_text) < 30:
                        print("🔡 中文字數不足 30，跳過")
                        continue


                    try:
                        permalink = post.find_element(By.XPATH, ".//a[@role='link'][time]").get_attribute("href")
                        post_link = "https://www.threads.com" + permalink if permalink.startswith("/") else permalink
                    except:
                        post_link = "N/A"

                    post_title = generate_title_with_keywords(post_text)

                    comments_data = []
                    if post_link != "N/A":
                        try:
                            driver.execute_script("window.open(arguments[0]);", post_link)
                            time.sleep(2)
                            new_tab = [w for w in driver.window_handles if w != main_window_handle][-1]
                            driver.switch_to.window(new_tab)
                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                            comments_data = scrape_comments_from_post_page(driver)
                            driver.close()
                            driver.switch_to.window(main_window_handle)
                        except Exception as e:
                            print("留言抓取錯誤：", e)
                            if len(driver.window_handles) > 1:
                                driver.close()
                            driver.switch_to.window(main_window_handle)

                    all_posts_data.append({
                        'title': post_title,
                        'date': post_time,
                        'post_url': post_link,
                        'summary': post_text,
                        'comments': comments_data,
                        'source': 'Threads',
                    })

                    print(f"✅ 收錄第 {len(all_posts_data)} 篇貼文")
                    time.sleep(random.uniform(1, 2))

                except StaleElementReferenceException:
                    print(f"⚠️ 第 {post_index} 篇貼文失效（StaleElement），跳過")
                    continue

            if not new_posts_found:
                no_new_scrolls += 1
                if no_new_scrolls >= MAX_NO_NEW_SCROLLS:
                    print("⚠️ 多次滾動無新內容，停止。")
                    break
            else:
                no_new_scrolls = 0


        if len(all_posts_data) < MAX_TARGET:
            print(f"⚠️ 貼文數未達 {MAX_TARGET}，僅收錄 {len(all_posts_data)} 篇")

        elapsed = datetime.now() - start_time

        print(f"📊 共抓取 {len(all_posts_data)} 筆，耗時 {elapsed.seconds // 60} 分 {elapsed.seconds % 60} 秒")
        return all_posts_data

    finally:
        print("🧹 關閉瀏覽器...")
        driver.quit()
        print("✅ 結束")


# # --- 執行

if __name__ == "__main__":
    keyword = ''
    posts = scrape_threads_by_keyword(keyword)
    if posts:
        print(posts[0])