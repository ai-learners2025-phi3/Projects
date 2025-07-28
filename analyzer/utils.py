import time, random, requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import platform
import os
from datetime import datetime, timedelta
import re
import jieba
import jieba.analyse
from collections import Counter, defaultdict
import pandas as pd
from snownlp import SnowNLP
from wordcloud import WordCloud
import google.generativeai as genai
from dotenv import load_dotenv

import pytz

tz = pytz.timezone("Asia/Taipei")


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_latest_articles_by_source(articles, top_n=5):
    """
    將 articles 按 source 分組，各取前 top_n 筆，並維持原順序合併回一個列表。
    :param articles: List[dict]，每筆要有 'source' 欄位
    :param top_n: int，各來源要取的數量
    :return: List[dict]
    """
    grouped = defaultdict(list)
    for art in articles:
        src = art.get('source', 'Unknown')
        grouped[src].append(art)

    # 把每組的前 top_n 筆拼回一個列表
    result = []
    for src, arts in grouped.items():
        result.extend(arts[:top_n])
    return result

def parse_date(date_str):
    date_str = date_str.strip()
    now = datetime.now()

    # 從混亂字串中抽取 YYYY-MM-DD 格式
    match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
    if match:
        return match.group()

    # 支援多種格式解析
    date_formats = [
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y年%m月%d日",
    ]
    for fmt in date_formats:
        try:
            date = datetime.strptime(date_str, fmt)
            return date.strftime("%Y-%m-%d")
        except Exception:
            continue

    # 相對時間處理
    if "剛剛" in date_str or "秒前" in date_str:
        return now.strftime("%Y-%m-%d")
    
    minute_match = re.search(r"(\d+)\s*分鐘前", date_str)
    if minute_match:
        date = now - timedelta(minutes=int(minute_match.group(1)))
        return date.strftime("%Y-%m-%d")
    
    hour_match = re.search(r"(\d+)\s*小時前", date_str)
    if hour_match:
        date = now - timedelta(hours=int(hour_match.group(1)))
        return date.strftime("%Y-%m-%d")

    day_match = re.search(r"(\d+)\s*天前", date_str)
    if day_match:
        date = now - timedelta(days=int(day_match.group(1)))
        return date.strftime("%Y-%m-%d")

    # 無法解析就原樣回傳
    return date_str

def extract_tags(text, top_k=10, use_tfidf=True):
    """
    從一段中文文字中擷取關鍵字詞
    :param text: 輸入的原始文字
    :param top_k: 最多擷取幾個關鍵字（只有在 use_tfidf=True 時生效）
    :param use_tfidf: 是否使用 TF-IDF 權重選字（否則就是純分詞）
    :param stopwords: 停用詞清單（可以客製）
    :return: 字詞標籤的 list
    """
    stopwords = set([
      '的', '了', '是', '我', '你', '他', '她', '它', '我們', '你們', '他們', '這', '那', '和', '與',
      '在', '不', '有', '也', '就', '都', '很', '而', '及', '或', '被', '還', '能', '會',
    ])
    if use_tfidf:
        # 使用 TF-IDF 抽取關鍵詞
        tags = jieba.analyse.extract_tags(text, topK=top_k)
    else:
        # 基本斷詞
        tags = jieba.lcut(text)

    # 過濾標點、空字元、停用詞
    filtered_tags = []
    for word in tags:
        word = word.strip()
        if word and re.match(r'^[\u4e00-\u9fff]+$', word) and word not in stopwords:
            filtered_tags.append(word)

    return filtered_tags

def get_tvbs_news(keyword, max_pages=4):
    results = []

    for page in range(1, max_pages + 1):
        url = f"https://news.tvbs.com.tw/news/searchresult/{keyword}/news/{page}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        # 發送 GET 請求
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            continue
        html = BeautifulSoup(response.text, "html.parser")

        # 抓取新聞區塊
        article_list = html.find('main').find('div', class_='list').find_all('li')
        for article in article_list:
            a_tag = article.find('a')
            if not a_tag:
                continue    
            # 標題
            title_tag = article.find('h2', class_='txt')
            title = title_tag.text.strip() if title_tag else ''

            # 新聞連結
            news_url = a_tag['href'] if a_tag.has_attr('href') else ''

            # 發布時間
            time_tag = article.find('div', class_='time')
            date = time_tag.text.strip() if time_tag else ''

            # 摘要
            summary_tag = article.find('div', class_='summary')
            summary = summary_tag.text.strip() if summary_tag else ''

            # 標籤
            tags_raw = a_tag.get('data-news_tag', '[]')
            # 處理成乾淨的 list（移除 ' 與空格）
            tags = [tag.strip(" '") for tag in tags_raw.strip('[]').split(',')]

            # 類別
            category_tag = article.find('div', class_='type').find('a')
            category = category_tag.text.strip() if category_tag else ''

            # 加入結果
            results.append({
                'title': title,
                'date': parse_date(date),
                'summary': summary,
                'news_tag': tags,
                'news_url': news_url,
                'category': category,
                'source':'TVBS新聞網',
            })
    return results

def get_chdtv_news(keyword, max_pages=3):
    results = []
    for page in range(1, max_pages + 1):
        url = f"https://www.chinatimes.com/search/{keyword}?page={page}&chdtv"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        # 發送 GET 請求
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            continue
        html = BeautifulSoup(response.text, "html.parser")

        # 抓取新聞區塊
        article_list = html.find('div', class_='wrapper').find('ul', class_='vertical-list list-style-none').find_all('li')
        for article in article_list:
            a_tag = article.find('a')
            if not a_tag:
                continue    
            # 標題
            title_tag = article.find('h3', class_='title')
            title = title_tag.text.strip() if title_tag else ''

            # 新聞連結
            news_url = a_tag['href'] if a_tag.has_attr('href') else ''

            # 發布時間
            time_tag = article.find('span', class_='date')
            date = time_tag.text.strip() if time_tag else ''

            # 摘要
            summary_tag = article.find('p', class_='intro')
            summary = summary_tag.text.strip() if summary_tag else ''

            # 標籤
            tags = extract_tags(summary)

            # 加入結果
            results.append({
                'title': title,
                'date': parse_date(date),
                'summary': summary,
                'news_tag': tags,
                'news_url': news_url,
                'source':'中時新聞網',
            })
    return results

def get_now_news(keyword, max_pages=5):
    results = []
    for page in range(1, max_pages + 1):
        url = f"https://www.nownews.com/search?q={keyword}&page={page}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            continue

        html = BeautifulSoup(resp.text, "html.parser")

        main_blk = html.find('div', class_='mainBlk')
        if not main_blk:
            continue

        item_list = main_blk.find('div', class_='item-list')
        if not item_list:
            continue

        article_list = item_list.find_all('a')
        if not article_list:
            continue

        for article in article_list:
            title_tag = article.find('h3', class_='title')
            title = title_tag.get_text(strip=True) if title_tag else ''

            news_url = article.get('href', '')

            time_el = article.find('p', class_='time')
            date = time_el.find('time').get_text(strip=True) if time_el and time_el.find('time') else ''

            # 正確匹配同時含有 content 與 text-truncate 的 <p>
            summary_el = article.select_one('p.content.text-truncate')
            summary = summary_el.get_text(strip=True) if summary_el else ''

            if not title and not summary:
                continue

            tags = extract_tags(summary)

            results.append({
                'title': title,
                'date': parse_date(date),
                'summary': summary,
                'news_tag': tags,
                'news_url': news_url,
                'source':'NOWnews',
            })
    return results


def get_ettoday_news(keyword, start_date=None, end_date=None, max_pages=5):
    results = []
    
    for page in range(1, max_pages+1):
        url = f"https://www.ettoday.net/news_search/doSearch.php?keywords={keyword}&idx=1&page={page}"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for art in soup.select("div.archive.clearfix"):
            # 動態匯入，避免循環依賴
            from analyzer.utils import parse_date

            link    = art.find("a")
            title   = art.find("h2").get_text(strip=True)
            href    = link["href"]
            date    = art.select_one(".date").get_text(strip=True)
            summary = art.find("p").get_text(strip=True)

            # 解析並篩選日期
            dt = parse_date(date)
            if start_date and dt < start_date:   continue
            if end_date   and dt > end_date:     continue

            results.append({
                "title": title,
                "date": dt,
                "summary": summary,
                "news_url": href,
                "source": "ETtoday新聞雲",
            })
        time.sleep(1)
    return results

def get_ltn_news(keyword, max_pages=3):
    base = "https://talk.ltn.com.tw/search"
    results = []
    
    for page in range(1, max_pages+1):
        params = {"keyword":keyword, "page":page}
        r = requests.get(base, params=params, headers={"User-Agent":"Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        for art in soup.select(".searchlistbox .searchlistitem"):
            a = art.find("h3").find("a")
            title = a.get_text(strip=True)
            href  = a["href"]
            date_s = art.select_one(".searchlistinfo").get_text(strip=True)
            # 解析時間
            try:
                dt = datetime.strptime(date_s, "%Y-%m-%d %H:%M").astimezone(tz).strftime("%Y-%m-%d")
            except:
                dt = date_s
            summary = art.find("p").get_text(strip=True) if art.find("p") else ""
            if keyword.lower() not in (title+summary).lower():
                continue
            results.append({
                "title": title,
                "date": dt,
                "summary": summary,
                "news_url": href,
                "source": "自由時報",
            })
        time.sleep(random.uniform(0.5,1.2))
    return results

HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def get_udn_news(keyword, page_num=3):
    results = []
    
    for p in range(1, page_num+1):
        api = f"https://udn.com/api/more?page={p}&channelId=1&cate_id=0&type=breaknews"
        resp = requests.get(api, headers=HEADERS)
        data = resp.json().get("lists", [])
        for item in data:
            title = item.get("title","").strip()
            url   = "https://udn.com" + item.get("url","")
            ts    = item.get("timestamp",0)
            date  = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            snippet = item.get("excerpt","").strip()
            # 關鍵字過濾
            if keyword.lower() not in (title+snippet).lower():
                continue
            results.append({
                "title": title,
                "date": date,
                "summary": snippet,
                "news_url": url,
                "source": "聯合新聞網",
            })
        time.sleep(random.uniform(0.5, 1.5))
    return results

def search_news(keyword):
    tvbs = get_tvbs_news(keyword)
    et   = get_ettoday_news(keyword)
    udn  = get_udn_news(keyword)
    ltn  = get_ltn_news(keyword)
    now  = get_now_news(keyword)
    chd  = get_chdtv_news(keyword)
    # 你也可以合併其它來源
    return tvbs + et + udn + ltn + now + chd

def analyze_sentiment(articles):
    """
    使用 SnowNLP 分析情緒
    :param articles: 每篇文章為 dict，需包含 summary 和 title
    :return: 回傳原始陣列，每篇文章加入 sentiment_score 及 sentiment 標籤（正面 / 負面 / 中立）
    """
    for article in articles:
        # 先使用 summary，若為空則用 title
        text = article['summary'] if article.get('summary') else article.get('title', '')
        
        s = SnowNLP(text)
        score = s.sentiments  # 分數介於 0~1，愈接近 1 越正面，接近 0 越負面
        article['sentiment_score'] = score

        # 加入中立判斷邏輯：0~0.4 負面、0.4~0.6 中立、0.6~1 正面
        if score >= 0.6:
            article['sentiment'] = '正面'   # 正面
        elif score <= 0.4:
            article['sentiment'] = '負面'  # 負面
        else:
            article['sentiment'] = '中立'   # 中立

    return articles

def count_sentiment(articles):
    sentiment_count = {
        '正面': sum(1 for a in articles if a['sentiment'] == '正面'),
        '負面': sum(1 for a in articles if a['sentiment'] == '負面'),
        '中立': sum(1 for a in articles if a['sentiment'] == '中立'),
    }
    return sentiment_count

def get_top_words(articles, top_n=5):
    """
    根據文章情緒標籤，統計正面、負面、中立摘要中的高頻詞。
    
    :param articles: 包含 'summary' 與 'sentiment' 欄位的文章列表
    :param top_n: 每個情緒類別中顯示的前 N 名高頻詞
    :return: dict，包含三類詞彙的 top_n 結果
    """
    pos_words, neg_words, neu_words = [], [], []

    for article in articles:
        words = extract_tags(article['summary'])
        if article['sentiment'] == '正面':
            pos_words.extend(words)
        elif article['sentiment'] == '負面':
            neg_words.extend(words)
        elif article['sentiment'] == '中立':
            neu_words.extend(words)

    return {
        'positive': Counter(pos_words).most_common(top_n),
        'negative': Counter(neg_words).most_common(top_n),
        'neutral': Counter(neu_words).most_common(top_n)
    }

def sentiment_by_category(articles):
    """
    統計各分類（category）下的情緒數量，
    若 article 沒有 category，就改用 source 當分類。
    """
    stats = defaultdict(lambda: {'positive': 0, 'neutral': 0, 'negative': 0})
    for art in articles:
        # 若沒有 category，就拿 source；若連 source 也沒有，就標為「其他」
        cate = art.get('category', art.get('source', '其他'))

        sentiment = art.get('sentiment')
        if sentiment == '正面':
            stats[cate]['positive'] += 1
        elif sentiment == '中立':
            stats[cate]['neutral'] += 1
        elif sentiment == '負面':
            stats[cate]['negative'] += 1
        # 其他或未標記就跳過

    return dict(stats)


def random_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    """自訂文字雲文字顏色調色盤"""
    palette = ["#cceaff", "#7cf8dd", "#faa7a8", "#ffca95", "#dbc2f7", "#ffd9c4"]
    return random.choice(palette)

def generate_wordcloud(frequencies, save_path, max_words=50, min_font_size=20):
    """
    根據 frequencies (字詞: 次數) 產生文字雲並輸出為檔案。
    frequencies: dict, e.g. {'關鍵詞A': 10, '關鍵詞B': 8, ...}
    """
    if not frequencies:
        return  # 沒有任何字詞就跳過

    system = platform.system()
    if system == 'Darwin':
        font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    elif system == 'Windows':
        font_path = r"C:\Windows\Fonts\msjh.ttc"
    else:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    wc = WordCloud(
        background_color="white",
        font_path=font_path,
        width=1096,
        height=480,
        margin=5,
        max_words=max_words,
        min_font_size=min_font_size,
        color_func=random_color_func,
        prefer_horizontal=0.9,
    )
    wc.generate_from_frequencies(frequencies)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    wc.to_file(save_path)

    return

def news_counter(articles):
    # 將資料整理成每日數量 dict
    daily_counts = Counter()
    for article in articles:
        if article['date']:
            daily_counts[article['date']] += 1

    # 轉為排序後的 x, y list
    trend_labels = sorted(daily_counts.keys())
    trend_values = [daily_counts[date] for date in trend_labels]
    return trend_labels,trend_values

def generate_prompt(keyword, sentiment_count, top_words, sentiment_by_cat):
    prompt = f"""
    請根據以下資料，撰寫一篇分析報告，字數約 300 字，以數據分析師的角度去分析，語氣專業清楚：
    
    🔍 主題：{keyword}

    📊 情緒比例：
    正面文章數：{sentiment_count.get('正面', 0)}
    負面文章數：{sentiment_count.get('負面', 0)}
    中立文章數：{sentiment_count.get('中立', 0)}

    📌 類別情緒統計概況：
    {sentiment_by_cat}

    🔥 高頻關鍵詞(每個詞在文章出現的數量):
    {"、".join(top_words.get('all', []))}

    請綜合以上資訊，說明目前熱度趨勢與社群關注重點。
    """
    return prompt

load_dotenv()

def call_LLM(prompt):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("⚠️ GOOGLE_API_KEY 未設定。請確認 .env 檔案存在且有設定金鑰。")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text.strip()

def fetch_article_stats(article, headers=None):
    """
    從文章內頁抓取 view_count 與 share_count。
    回傳 (view_count:int, share_count:int)。
    """
    url = article.get('news_url')
    if not url:
        return 0, 0
    headers = headers or {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            return 0, 0
        dom = BeautifulSoup(resp.text, 'html.parser')
        views_tag = dom.select_one('span.views')
        view_count = int(re.sub(r'\D', '', views_tag.text)) if views_tag else 0
        share_tag = dom.select_one('button.share-count')
        share_count = int(re.sub(r'\D', '', share_tag.text)) if share_tag else 0
        return view_count, share_count
    except Exception:
        return 0, 0

def compute_hot_score_by_stats(article, weight_share=5):
    """
    計算熱門分數：view_count + weight_share * share_count
    """
    views  = article.get('view_count', 0)
    shares = article.get('share_count', 0)
    return views + shares * weight_share

def get_top_hot_articles_by_stats(articles, top_n=10, weight_share=5, fetch_stats=False):
    """
    取出前 top_n 名熱門新聞。
    :param articles: List[dict]，每筆 article 最好有 'news_url'
    :param top_n: 要回傳的筆數
    :param weight_share: 分享數的權重
    :param fetch_stats: 是否先抓內頁統計
    :return: sorted List[dict] 前 top_n 筆，會在每筆 article 裡新增 'hot_score'
    """
    if fetch_stats:
        for art in articles:
            v, s = fetch_article_stats(art)
            art['view_count']  = v
            art['share_count'] = s

    for art in articles:
        art['hot_score'] = compute_hot_score_by_stats(art, weight_share)

    # 依 hot_score 降序
    sorted_list = sorted(articles, key=lambda x: x['hot_score'], reverse=True)
    return sorted_list[:top_n]

# analyzer/utils.py

import os
import platform
import random
from datetime import datetime, timedelta
from collections import Counter, defaultdict

import jieba.analyse
from bs4 import BeautifulSoup
from wordcloud import WordCloud

# 以下省略其他 imports …


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_wordcloud(frequencies, save_path, max_words=100, min_font_size=12):
    """
    根據 frequencies (Counter 或 dict) 產生文字雲並儲存到 save_path。
    """
    # 選字體
    system = platform.system()
    if system == 'Darwin':
        font_path = "/System/Library/Fonts/STHeiti Medium.ttc"
    elif system == 'Windows':
        font_path = r"C:\Windows\Fonts\msjh.ttc"
    else:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    wc = WordCloud(
        background_color="white",
        font_path=font_path,
        width=800,
        height=450,
        max_words=max_words,
        min_font_size=min_font_size,
        random_state=42
    )
    wc.generate_from_frequencies(frequencies)
    wc.to_file(save_path)


def work(keyword):
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    # 1. 搜尋與情緒分析
    articles = analyze_sentiment(search_news(keyword))

    # 2. 熱度貼文
    hot_articles = get_top_hot_articles_by_stats(articles, top_n=10, weight_share=5, fetch_stats=False)

    # 3. 各種統計
    sentiment_count = count_sentiment(articles)
    trend_labels, trend_values = news_counter(articles)
    top_word = get_top_words(articles)
    category_stats = sentiment_by_category(articles)

    # 4. 收集所有 news_tag 作為文字雲的詞彙
    all_tags = []
    for art in articles:
        all_tags.extend(art.get('news_tag', []))

    # 5. 產生文字雲
    wordcloud_dir = os.path.join(BASE_DIR, 'static', 'clouds')
    os.makedirs(wordcloud_dir, exist_ok=True)
    filename  = f"{keyword}_{ts}.png"
    save_path = os.path.join(wordcloud_dir, filename)

    if all_tags:
        freqs = dict(Counter(all_tags).most_common(50))
        generate_wordcloud(freqs, save_path, max_words=50, min_font_size=20)
        tag_image = f"clouds/{filename}"
    else:
        tag_image = None

    # 6. 前 5 名相關關鍵字
    top_keywords = Counter(all_tags).most_common(5)

    # 7. LLM 報告
    prompt = generate_prompt(keyword, sentiment_count, top_word, category_stats)
    try:
        report = call_LLM(prompt)
    except Exception as e:
        report = f"⚠️ Gemini 回應失敗：{e}"

    return {
        'articles':        articles,
        'sentiment_count': sentiment_count,
        'hot_articles':    hot_articles,
        'top_word':        top_word,
        'category_stats':  category_stats,
        'tag_image':       tag_image,
        'trend_labels':    trend_labels,
        'trend_values':    trend_values,
        'top_keywords':    top_keywords,
        'AIreport':        report,
    }

def infer_site_type(source_name):
    """
    根據來源名稱簡單推斷網站類型，
    你可以擴充這個對照表，把各種來源對應到：YT／新聞網／論壇／微博etc.
    """
    if "新聞網" in source_name or "ETtoday" in source_name or "聯合新聞網" in source_name:
        return "News"
    if source_name.upper().endswith("NEWS") or "TVBS" in source_name:
        return "News"
    # 未來再加更多規則
    return "Other"

def compute_source_ranking(articles_by_keyword):
    """
    articles_by_keyword: dict { keyword_str: [article_dict, ...] }
    回傳一個 DataFrame，欄位：
      - 討論面向 (keyword)
      - 網站類型 (site_type)
      - 來源名稱   (source)
      - 貼文數     (count)
    並依 count DESC 排序。
    """
    records = []
    for keyword, articles in articles_by_keyword.items():
        for art in articles:
            src = art.get('source', 'Unknown')
            st  = infer_site_type(src)
            records.append({
                '討論面向': keyword,
                '網站類型': st,
                '來源名稱': src,
            })
    df = pd.DataFrame(records)
    ranking = (
        df
        .groupby(['討論面向', '網站類型', '來源名稱'])
        .size()
        .reset_index(name='貼文數')
        .sort_values('貼文數', ascending=False)
        .reset_index(drop=True)
    )
    return ranking

def work_with_ranking(keyword):
    result = work(keyword)
    ranking = compute_source_ranking({keyword: result['articles']})
    result['source_ranking'] = ranking
    return result


def infer_site_type(source_name):
    if "新聞網" in source_name or "ETtoday" in source_name or "聯合新聞網" in source_name:
        return "News"
    if source_name.upper().endswith("NEWS") or "TVBS" in source_name:
        return "News"
    # 更多規則...
    return "Other"

def fetch_article_stats(article, headers=None):
    url = article.get('news_url')
    if not url:
        return 0, 0
    headers = headers or {"User-Agent":"Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            return 0, 0
        dom = BeautifulSoup(resp.text, 'html.parser')
        # 假設留言數在 <span class="comments">1234</span>
        comments_tag = dom.select_one('span.comments')
        comments = int(re.sub(r'\D','', comments_tag.text)) if comments_tag else 0
        # 假設分享數在 <button class="share-count">56</button>
        share_tag   = dom.select_one('button.share-count')
        shares      = int(re.sub(r'\D','', share_tag.text))   if share_tag   else 0
        return comments, shares
    except:
        return 0, 0

def compute_hot_score_by_stats(article, weight_share=5):
    comments = article.get('comment_count', 0)
    shares   = article.get('share_count', 0)
    # 你也可以調整算法
    return comments + shares * weight_share

def get_top_hot_articles_by_stats(articles, top_n=10, weight_share=5, fetch_stats=False):
    # 選要不要先抓內頁留言／分享數
    if fetch_stats:
        for art in articles:
            c, s = fetch_article_stats(art)
            art['comment_count'] = c
            art['share_count']   = s

    for art in articles:
        art['hot_score'] = compute_hot_score_by_stats(art, weight_share)
        # 加上「討論面向」和「網站類型」方便前端顯示、過濾
        art.setdefault('discussion', art.get('keyword'))  # 假設 article 沒有這欄時，用 keyword
        art['site_type'] = infer_site_type(art.get('source',''))
    # 取前 top_n
    sorted_list = sorted(articles, key=lambda x: x['hot_score'], reverse=True)
    return sorted_list[:top_n]

import re, requests
from bs4 import BeautifulSoup
from collections import defaultdict
# 已有 infer_site_type, parse_date 等函数

def fetch_article_comments(article, max_comments=5):
    """
    從文章內頁抓出評論節點，回傳 list[{
        'timestamp': str,
        'content': str,
        'reaction_count': int
    }]
    """
    comments = []
    url = article.get('news_url')
    if not url:
        return comments

    try:
        resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=5)
        if resp.status_code != 200:
            return comments
        dom = BeautifulSoup(resp.text, 'html.parser')
        # 下面 selector 依實際網站調整：
        nodes = dom.select('.comment-item')[:max_comments]
        for nd in nodes:
            ts = nd.select_one('.comment-time')
            txt = nd.select_one('.comment-text')
            rc = nd.select_one('.comment-reactions')
            timestamp      = ts.get_text(strip=True) if ts else ''
            content        = txt.get_text(strip=True) if txt else ''
            reaction_count = int(re.sub(r'\D','', rc.get_text())) if rc else 0
            comments.append({
                'timestamp': timestamp,
                'content': content,
                'reaction_count': reaction_count
            })
    except Exception:
        pass

    return comments

def get_top_hot_comments_by_reactions(articles, top_n=10, per_article=5):
    """
    抓所有文章的前 per_article 條評論，彙整後依 reaction_count 排序取 top_n
    回傳 list[{
      'region':         str,
      'source_category':str,
      'timestamp':      str,
      'content':        str,
      'reaction_count': int,
    }]
    """
    all_comments = []
    for art in articles:
        region = art.get('category', art.get('source',''))
        site_cat = infer_site_type(art.get('source',''))
        for c in fetch_article_comments(art, max_comments=per_article):
            all_comments.append({
                'region':          region,
                'source_category': site_cat,
                'timestamp':       c['timestamp'],
                'content':         c['content'],
                'reaction_count':  c['reaction_count'],
            })
    # 全部排序並取前 top_n
    sorted_comments = sorted(all_comments,
                             key=lambda x: x['reaction_count'],
                             reverse=True)
    return sorted_comments[:top_n]


# source venv/bin/activate
# python manage.py runserver