from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dateutil import parser
from dateutil import tz
import time
import json
import random
import re
import jieba.analyse


# 檢查貼文：至少有60％中文 
def is_mostly_chinese(text, threshold=0.6):
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    return len(chinese_chars) / max(len(text), 1) >= threshold


# 檢查貼文：至少30個字 中文字 
def count_chinese_chars(text):
    return len(re.findall(r"[\u4e00-\u9fff]", text))

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

# 主程式
def scrape_threads_posts():
    start_time = datetime.now()
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.threads.com/")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//div[@data-pressable-container='true']"))
    )

    # ----------- 設定參數 ------------
    MAX_TARGET = 5
    MAX_SCROLLS = 40
    MAX_NO_NEW_SCROLLS = 2

    all_posts_data = []
    post_index = 0
    scroll_round = 0
    no_new_scrolls = 0

    while len(all_posts_data) < MAX_TARGET and scroll_round < MAX_SCROLLS:
        scroll_round += 1
        print(f"\n🔄 滾動第 {scroll_round} 次...")

        prev_posts_len = len(driver.find_elements(By.XPATH, "//div[@data-pressable-container='true']"))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 4))

        posts = driver.find_elements(By.XPATH, "//div[@data-pressable-container='true']")

        if len(posts) == prev_posts_len:
            no_new_scrolls += 1
            print("⚠️ 此輪未載入新貼文")
            if no_new_scrolls >= MAX_NO_NEW_SCROLLS:
                print("🛑 已連續多次無新增貼文，結束。")
                break
        else:
            no_new_scrolls = 0

        while post_index < len(posts):
            post = posts[post_index]
            post_index += 1
            print(f"\n📝 正在處理第 {post_index} 筆貼文")

            try:
                author = post.find_element(By.XPATH, ".//span[contains(@class, 'x1lliihq') and ancestor::a[contains(@href, '/@')]]").text.strip()
            except:
                author = "N/A"

            try:
                link_elem = post.find_element(By.XPATH, ".//a[@role='link'][time]")
                href = link_elem.get_attribute("href")
                post_link = "https://www.threads.com" + href if href.startswith("/") else href
            except:
                post_link = "N/A"

            try:
                time_str = post.find_element(By.XPATH, ".//time").get_attribute("datetime")
                utc_time = parser.parse(time_str)
                taipei_time = utc_time.astimezone(tz.gettz("Asia/Taipei"))
                post_time = taipei_time.strftime("%Y-%m-%d %H:%M:%S")
            except:
                post_time = "N/A"

            try:
                spans = post.find_elements(By.XPATH, ".//div[contains(@class, 'x1a6qonq')]//span[contains(@class, 'x1lliihq')]//span")
                parts = [s.text.strip() for s in spans if s.text.strip()]
                post_text = "\n".join(sorted(set(parts), key=parts.index))
                post_title = generate_title_with_keywords(post_text)

            except:
                post_text = "N/A"

            # has_image = bool(post.find_elements(By.XPATH, ".//img"))
            # has_video = bool(post.find_elements(By.XPATH, ".//video"))

            chinese_count = count_chinese_chars(post_text)
            if not is_mostly_chinese(post_text):
                print("❌ 非中文主體，跳過。")
                continue
            if chinese_count < 30:
                print("❌ 中文字 < 30，跳過。")
                continue

            comments = []
            if post_link != "N/A":
                try:
                    driver.execute_script("window.open(arguments[0]);", post_link)
                    time.sleep(3)
                    new_tab = [w for w in driver.window_handles if w != driver.current_window_handle][-1]
                    driver.switch_to.window(new_tab)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                    for _ in range(3):
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)

                    wrapper = driver.find_element(
                        By.XPATH,
                        "//div[contains(@class, 'xb57i2i') and contains(@class, 'x1q594ok') and contains(@class, 'x5lxg6s') and contains(@class, 'x78zum5') and contains(@class, 'xdt5ytf') and contains(@class, 'x1ja2u2z') and contains(@class, 'x1pq812k') and contains(@class, 'x1rohswg') and contains(@class, 'xfk6m8') and contains(@class, 'x1yqm8si') and contains(@class, 'xjx87ck') and contains(@class, 'xx8ngbg') and contains(@class, 'xwo3gff') and contains(@class, 'x1n2onr6') and contains(@class, 'x1oyok0e') and contains(@class, 'x1e4zzel') and contains(@class, 'x1plvlek') and contains(@class, 'xryxfnj')]"
                    )

                    blocks = wrapper.find_elements(By.XPATH, ".//div[contains(@class, 'x1a6qonq')]")[1:]

                    for block in blocks:
                        spans = block.find_elements(By.XPATH, ".//span[@dir='auto']/span")
                        text = "\n".join([s.text.strip() for s in spans if s.text.strip()])
                        if text:
                            comments.append(text)
                        if len(comments) >= 10:
                            break

                    print(f"💬 擷取留言數：{len(comments)}")
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                except Exception as e:
                    print("留言抓取錯誤:", e)
                    try:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    except:
                        pass

            all_posts_data.append({
                "author": author,
                "link": post_link,
                "content": post_text,
                "title": post_title,
                # "has_image": has_image,
                # "has_video": has_video,
                "post_time": post_time,
                "comments": comments
            })
            print(f"✅ 收錄第 {len(all_posts_data)} 篇貼文")

            if len(all_posts_data) >= MAX_TARGET:
                break
            time.sleep(random.uniform(1, 2))

    # 儲存 JSON
    end_time = datetime.now()
    elapsed = end_time - start_time

    output = {
        "summary": {
            "total_posts": len(all_posts_data),
            "elapsed_time": f"{elapsed.seconds // 60} 分 {elapsed.seconds % 60} 秒"
        },
        "posts": all_posts_data
    }

    with open("threads_posts.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 已儲存 threads_posts.json（共 {len(all_posts_data)} 篇）")
    print(f"⌛ 總耗時：{elapsed.seconds // 60} 分 {elapsed.seconds % 60} 秒")
    driver.quit()

if __name__ == "__main__":
    scrape_threads_posts()
