import asyncio
import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag
from datetime import datetime, timedelta
import re
import nest_asyncio


nest_asyncio.apply()


def convert_time_format(time_string):
    """
    將 "Sun Jul 27 13:45:00 2025" 格式的時間字串轉換為 "YYYY-MM-DD" 格式。

    Args:
        time_string (str): 原始時間字串，例如 "Sun Jul 27 13:45:00 2025"。

    Returns:
        str: 轉換後的 "YYYY-MM-DD" 格式時間字串，例如 "2025-07-27"。
    """
    # 定義原始時間字串的格式
    # %a: 星期縮寫 (Sun)
    # %b: 月份縮寫 (Jul)
    # %d: 月份中的日期 (27)
    # %H: 24 小時制小時 (13)
    # %M: 分鐘 (45)
    # %S: 秒 (00)
    # %Y: 四位數年份 (2025)
    original_format = "%a %b %d %H:%M:%S %Y"

    # 將字串解析為 datetime 物件
    dt_object = datetime.strptime(time_string, original_format)

    # 將 datetime 物件格式化為目標字串格式
    target_format = "%Y-%m-%d"
    return dt_object.strftime(target_format)

# ========= 可依需求修改的參數 =========
PTT_URL = 'https://www.ptt.cc'
PAGES_TO_CHECK = 10         # 最多往前翻查的頁數
PUSH_LIMIT = 20            # 推文數門檻（爆 or ≥ 數字）
DAYS_LIMIT = 7              # 只抓最近 N 天的文章
SLEEP_SECONDS = 0.1         # 每頁抓完後延遲秒數
MAX_POSTS_PER_BOARD = 5    # 每個看板最多抓幾篇文章
PTT_BOARDS = ["Gossiping", "Military", "PublicIssue",
    "Stock", "Finance", "Bank_Service", "Tech_Job", 
    "Soft_Job", "Salary","Boy-Girl", "WomenTalk", 
    "LGBT_SEX", "MobileGame", "movie", "TW_Entertain",
    "MobileComm", "PC_Shopping", "nb-shopping", "HardwareSale",
    "home-sale", "NBA", "Baseball", "FITNESS", "Japan_Travel"
    ]  
"""
PTT_BOARDS = ["Gossiping", "Military", "PublicIssue",
    "Stock", "Finance", "Lifeismoney", "Bank_Service",
    "Tech_Job", "Soft_Job", "CV_help", "Salary",
    "Boy-Girl", "WomenTalk", "marriage", "LGBT_SEX",
    "C_Chat", "LoL", "MobileGame", "Steam", "ToS",
    "movie", "KoreaDrama", "Japandrama", "TW_Entertain",
    "MobileComm", "PC_Shopping", "nb-shopping", "HardwareSale",
    "home-sale", "Rent_tao", "home-appliance", "furnishing",
    "NBA", "Baseball", "SportLottery", "FITNESS",
    "car", "biker", "Railway", "Japan_Travel"
    ]  # 預設要爬的看板清單
"""
headers = {"User-Agent": "Mozilla/5.0"}
DATE_LIMIT = datetime.today() - timedelta(days=DAYS_LIMIT)

# ========= 清洗文章內容 =========
def clean_content(raw_text: str) -> str:
    raw_text = raw_text.split('※ 發信站:')[0]
    lines = raw_text.splitlines()
    cleaned = []
    for line in lines:
        if re.match(r'^(作者|看板|標題|時間)\s*:', line.strip()):
            continue
        cleaned.append(line)
    return re.sub(r'\n{3,}', '\n\n', "\n".join(cleaned)).strip()

# ========= 抓單篇文章 =========
async def fetch_post(session, href, visited_urls):
    url = PTT_URL + href
    if url in visited_urls:
        return None

    try:
        async with session.get(url, cookies={'over18': '1'}, headers=headers) as resp:
            if resp.status != 200:
                print('PTT,無資料')
                return None

            html = await resp.text()
            soup = BeautifulSoup(html, 'html.parser')
           

            date_str = ''
            for tag, val in zip(soup.select('span.article-meta-tag'), soup.select('span.article-meta-value')):
                if tag.text == '時間':
                    date_str = val.text
                    try:
                        parsed_time = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y")
                        if parsed_time < DATE_LIMIT:
                            return None
                    except:
                        return None
                    break

            main_content = soup.find(id='main-content')
            if not main_content:
                return None

            # 擷取留言
            comments = []
            for push in main_content.find_all("div", class_="push"):
                try:
                    tag = push.find("span", class_="push-tag")
                    user = push.find("span", class_="push-userid")
                    content = push.find("span", class_="push-content")
                    if tag and user and content:
                        comments.append(f"{tag.text.strip()} {user.text.strip()}: {content.text.strip().lstrip(':')}")
                except:
                    continue

            # 移除非留言的 tag
            for tag in main_content.find_all(['div', 'span']):
                if not isinstance(tag, Tag):
                    continue
                try:
                    tag_class = tag.get('class') or []
                    if 'push' not in tag_class:
                        tag.decompose()
                except:
                    continue

            content_raw = main_content.get_text('\n').strip()
            content_cleaned = clean_content(content_raw)

            title_tag = soup.find('title')
            title = title_tag.text.strip() if title_tag else '(無標題)'

            visited_urls.add(url)
            return {
                'title': title,
                'date': convert_time_format(date_str),
                'post_url': url,
                'summary': content_cleaned,
                'comments': comments, # 若要改用「｜」分隔可改成："｜".join(comments)
                'source': 'PTT',
            }

    except:
        return None

# ========= 抓一個看板 =========
async def crawl_board(board_name, visited_urls):
    posts = []
    collected = 0
    page_index = ''

    async with aiohttp.ClientSession() as session:
        for _ in range(PAGES_TO_CHECK):
            page_url = f"{PTT_URL}/bbs/{board_name}/index{page_index}.html" if page_index else f"{PTT_URL}/bbs/{board_name}/index.html"

            try:
                async with session.get(page_url, cookies={'over18': '1'}, headers=headers) as resp:
                    if resp.status != 200:
                        continue
                    html = await resp.text()
            except:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            if not soup:
                print('PTT,board無資料')
                continue
            tasks = []

            for entry in soup.select('div.r-ent'):
                try:
                    push_text = entry.select_one('div.nrec').text.strip()
                    is_hot = (push_text == '爆') or (push_text.isdigit() and int(push_text) >= PUSH_LIMIT)
                    if not is_hot:
                        continue

                    link_tag = entry.select_one('div.title a')
                    if not link_tag:
                        continue

                    href = link_tag['href']
                    tasks.append(fetch_post(session, href, visited_urls))

                    if len(tasks) >= MAX_POSTS_PER_BOARD - collected:
                        break
                except:
                    continue

            results = await asyncio.gather(*tasks)
            for post in results:
                if post:
                    posts.append(post)
                    collected += 1
                    if collected >= MAX_POSTS_PER_BOARD:
                        return posts

            # 下一頁
            prev_btns = soup.find_all('a', class_='btn wide')
            for btn in prev_btns:
                if '上頁' in btn.text:
                    m = re.search(r'index(\d+)\.html', btn['href'])
                    if m:
                        page_index = m.group(1)

            await asyncio.sleep(SLEEP_SECONDS)  # 每頁之間延遲

    return posts

# ========= 主爬蟲流程 =========
async def _main():
    visited_urls = set()
    all_posts = []
    for board in PTT_BOARDS:
        posts = await crawl_board(board, visited_urls)
        all_posts.extend(posts)
    return all_posts

# ========= 外部匯入的主函式 =========
def get_ptt_posts():
    return asyncio.run(_main())
def ptt_keyword(keyword,posts):
    ptt_post = []
    for post in posts:
        if keyword in post['title']:
            ptt_post.append(post)
        elif keyword in post['summary']:
            ptt_post.append(post)
        else:
            for comment in post['comments']:
                if keyword in comment:
                    ptt_post.append(post)
                    break
    return ptt_post

if __name__ == "__main__":
    posts = get_ptt_posts()
    print(f"\n🎯 共獲取 {len(posts)} 篇文章")
    if posts:
        for k, v in posts[0].items():
            print(f"{k}:\n{v}\n{'-'*40}")


