from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import random

# 直接寫入帳號密碼
IG_USERNAME = "leafwann_"
IG_PASSWORD = "threads2025"

def login_to_threads(driver):
    driver.get("https://www.threads.net/")

    print("等待 Instagram 登入按鈕...")
    try:
        ig_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH,
                "//span[text()='使用 Instagram 帳號繼續'] | "  # 中文
                "//span[text()='Continue with Instagram'] | "  # 英文
                "//button[contains(text(), 'Instagram')]"       # 備用
            ))
        )
        ig_button.click()
        print("已點擊 Instagram 登入")
    except Exception as e:
        print("❌ 找不到 Instagram 登入按鈕")
        print(f"錯誤訊息：{e}")
        return False

    WebDriverWait(driver, 20).until(EC.url_contains("instagram.com"))

    print("輸入帳密...")
    username_input = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.NAME, "username"))
    )
    password_input = driver.find_element(By.NAME, "password")

    username_input.send_keys(IG_USERNAME)
    password_input.send_keys(IG_PASSWORD)

    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()

    # 等待登入完成
    WebDriverWait(driver, 30).until(
        EC.any_of(
            EC.url_contains("threads.net"),
            EC.url_contains("instagram.com/challenge"),
        )
    )

    if "challenge" in driver.current_url:
        input("⚠️ 請手動完成驗證後按 Enter")
        WebDriverWait(driver, 30).until(EC.url_contains("threads.net"))

    print("登入完成")

    # 登入成功後，自動跳轉到搜尋頁
    driver.get("https://www.threads.com/search")
    print("✅ 已跳轉到搜尋頁面")

    return True


def scrape_comments(driver):
    print("嘗試抓留言中...")
    comments = []

    # 滾動幾次
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    # 嘗試抓留言內容
    comment_spans = driver.find_elements(By.XPATH, "//div[@role='main']//span[@dir='auto']")
    for span in comment_spans:
        text = span.text.strip()
        if text and len(text) < 300:
            comments.append(text)
        if len(comments) >= 10:
            break

    print(f"抓到 {len(comments)} 條留言")
    return comments

def scrape_threads(keyword):
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        if not login_to_threads(driver):
            return

        print(f"搜尋關鍵字: {keyword}")
        search_url = f"https://www.threads.net/search?hl=zh-tw"
        driver.get(search_url)
        time.sleep(5)

        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='search']"))
        )
        search_input.send_keys(keyword)
        search_input.send_keys(Keys.ENTER)
        time.sleep(5)

        # 找到貼文
        posts = driver.find_elements(By.XPATH, "//div[@data-pressable-container='true']")
        print(f"找到 {len(posts)} 篇貼文")

        results = []

        for i, post in enumerate(posts[:3]):
            print(f"\n🔹 處理第 {i+1} 篇貼文")
            try:
                # 點開貼文
                link_elem = post.find_element(By.XPATH, ".//a[@role='link']")
                href = link_elem.get_attribute("href")
                driver.execute_script("window.open(arguments[0]);", href)
                time.sleep(2)
                driver.switch_to.window(driver.window_handles[-1])
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                comments = scrape_comments(driver)

                results.append({
                    "link": href,
                    "comments": comments
                })

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                print(f"處理貼文失敗: {e}")
                continue

        with open(f"threads_results_{keyword}.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print("✅ 所有資料已儲存完成！")

    finally:
        driver.quit()

if __name__ == "__main__":
    keyword = input("請輸入搜尋關鍵字: ")
    scrape_threads(keyword)
