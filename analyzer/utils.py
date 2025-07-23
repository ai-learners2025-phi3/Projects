import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
import re
import jieba
import jieba.analyse
from collections import Counter, defaultdict

from snownlp import SnowNLP
from wordcloud import WordCloud
import google.generativeai as genai


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        # 發送 GET 請求
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            continue
        html = BeautifulSoup(response.text, "html.parser")

        # 抓取新聞區塊
        article_list = html.find('div', class_='mainBlk').find('div', class_='item-list').find_all('a')
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
            time_tag = article.find('p', class_='time').find('time')
            date = time_tag.text.strip() if time_tag else ''

            # 摘要
            summary_tag = article.find('p', class_='content text-truncate')
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
                'source':'NOWnews',
            })
    return results

def get_ET_news(keyword, max_pages=10):
    results = []

    for page in range(1, max_pages + 1):
        url = f"https://www.ettoday.net/news_search/doSearch.php?keywords={keyword}&idx=1&page={page}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            continue

        html = BeautifulSoup(response.text, "html.parser")

        # 根據實際網頁結構定位文章區塊
        article_list = html.select("div.archive.clearfix")

        for article in article_list:
            a_tag = article.find("a")
            if not a_tag:
                continue

            # 標題
            title_tag = article.find("h2")
            title = title_tag.text.strip() if title_tag else ""

            # 新聞連結
            news_url = a_tag["href"] if a_tag.has_attr("href") else ""

            # 發布時間
            time_tag = article.select_one('.date')
            date = time_tag.text.strip() if time_tag else ''

            # 摘要
            summary_tag = article.find("p")
            summary = summary_tag.text.strip() if summary_tag else ""

            # 標籤
            tags = extract_tags(summary)

            # 類別
            category_tag = article.find('span', class_='date').find('a')
            category = category_tag.text.strip() if category_tag else ''

            results.append({
                "title": title,
                "date": parse_date(date),
                "summary": summary,
                "news_tag": tags,
                "news_url": news_url,
                "category": category,
                "source": "ETtoday新聞雲",
            })

    return results

def search_news(keyword):
    tvbs_news = get_tvbs_news(keyword)
    ET_news = get_ET_news(keyword)
    # chdtv_news = get_chdtv_news(keyword)
    articles = tvbs_news + ET_news
    return articles

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
    stats = defaultdict(lambda: {'positive': 0, 'neutral': 0, 'negative': 0})
    for art in articles:
        cate = art['category']
        if art['sentiment'] == '正面':
            stats[cate]['positive'] += 1
        elif art['sentiment'] == '中立':
            stats[cate]['neutral'] += 1
        elif art['sentiment'] == '負面':
            stats[cate]['negative'] += 1
    return dict(stats)

def generate_wordcloud(tags, save_path):
    font_path = "/System/Library/Fonts/STHeiti Medium.ttc"  # macOS 可用字體
    text = ' '.join(tags)
    wc = WordCloud(
        background_color="white", 
        font_path=font_path, 
        width=1096, 
        height=480,
        max_words=100,
    )
    wc.generate(text)
    wc.to_file(save_path)

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

def call_LLM(prompt):
    api_key = ''
    genai.configure(api_key = api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # gemini-1.5-flash/ gemini-1.5-flash
    response = model.generate_content(prompt)
    return response.text.strip()

def work(keyword):
    start_time = datetime.now().strftime("%Y%m%d_%H%M")
    # 1. 搜尋與情緒分析
    articles = analyze_sentiment(search_news(keyword))
    # 2. 計算正負情緒數量
    sentiment_count = count_sentiment(articles)
    # 3. 趨勢分析（各時間點的新聞數量）
    trend_labels,trend_values = news_counter(articles)
    # 4. 分析詞彙貢獻
    top_word = get_top_words(articles)
    # 5. 分析分類情緒
    category_stats = sentiment_by_category(articles)
    # 6. 統計標籤詞彙製作文字雲圖
    all_tags = []
    for art in articles:
        all_tags.extend(art['news_tag'])
    
    wordcloud_path = os.path.join(BASE_DIR, 'static', 'clouds', f'{keyword}{start_time}.png')
    os.makedirs(os.path.dirname(wordcloud_path), exist_ok=True)
    generate_wordcloud(all_tags, wordcloud_path)
    # 7. 使用 Gemini 生成報告
    prompt = generate_prompt(keyword, sentiment_count, top_word, category_stats)
    try:
        report = call_LLM(prompt)
    except Exception as e:
        report = f"⚠️ Gemini 回應失敗：{e}"

    end_time = datetime.now().strftime("%Y%m%d_%H%M")
    # 回傳結果
    return {
        'articles': articles,
        'sentiment_count': sentiment_count,
        'top_word': top_word,
        'category_stats': category_stats,
        'tag_image': f'./static/clouds/{keyword}{start_time}.png',
        'trend_labels': trend_labels,
        'trend_values': trend_values,
        'AIreport': report,
    }

# source venv/bin/activate
# python manage.py runserver