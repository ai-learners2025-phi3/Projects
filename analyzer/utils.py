# 📦 系統與環境變數
import os
from django.conf import settings

# 🕒 時間與日期處理
from datetime import datetime, timedelta

# 🌐 網路請求與資料爬取
import requests
from bs4 import BeautifulSoup

# 📊 資料處理與分析
import pandas as pd
from collections import Counter, defaultdict
import pymysql
import json 

# 🧠 自然語言處理（NLP）
import jieba
import jieba.analyse
from snownlp import SnowNLP

# 🖼️ 視覺化與圖形產生
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# 🤖 Google Gemini AI 服務
import google.generativeai as genai

# 🧪 文字處理與正規表示式
import re

from .models import News, Posts, AnalysisResult
from .ptt_crawler import get_ptt_posts,ptt_keyword
from .threads_crawler import scrape_threads_by_keyword



BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _save_single_news_article(news_data_item, history_search_instance=None):
    """
    保存單篇新聞文章到 News 表。
    news_data_item: 字典，包含單篇新聞資訊。
    history_search_instance: HistorySearch 物件，可選，用於 ManyToMany 關聯。
    """
    try:
        date = datetime.strptime(news_data_item.get('date'), "%Y-%m-%d")
    except:
        date = datetime.now
    try:
        news_article, created = News.objects.update_or_create(
            url=news_data_item['news_url'], # 使用 URL 作為唯一標識
            defaults={
                'keyword': news_data_item.get('keyword', '新聞'),
                'source': news_data_item.get('source', ''),
                'title': news_data_item.get('title', ''),
                'publish_date': date,
                'summary': news_data_item.get('summary', ''),
                'tags': news_data_item.get('news_tag', ''),
                'category': news_data_item.get('category', ''),
                'sentiment': news_data_item.get('sentiment', ''),
                'sentiment_score': news_data_item.get('sentiment_score'),
            }
        )
        if history_search_instance:
            news_article.searches.add(history_search_instance)
        print(f"✅ News - {'創建' if created else '更新'}：{news_article.title}")
    except Exception as e:
        print(f"❌ News 儲存失敗 ({news_data_item.get('title', '未知')}): {e}")

def _save_single_post_item(post_data_item, history_search_instance=None):
    """
    保存單篇貼文到 Posts 表。
    post_data_item: 字典，包含單篇貼文資訊。
    history_search_instance: HistorySearch 物件，可選，用於 ManyToMany 關聯。
    """
    try:
        date = datetime.strptime(post_data_item.get('date'), "%Y-%m-%d")
    except:
        date = datetime.now
    try:
        post_item, created = Posts.objects.update_or_create(
            url=post_data_item['post_url'], # 使用 URL 作為唯一標識
            defaults={
                'keyword': post_data_item.get('keyword', 'None'),
                'source': post_data_item.get('source', ''),
                'title': post_data_item.get('title', ''),
                'publish_date': date,
                'summary': post_data_item.get('summary', ''),
                'comments': post_data_item.get('comments', []),
                'sentiment': post_data_item.get('sentiment', ''),
                'sentiment_score': post_data_item.get('sentiment_score'),
            }
        )
        if history_search_instance:
            post_item.searches.add(history_search_instance)
        print(f"✅ Post - {'創建' if created else '更新'}：{post_item.title}")
    except Exception as e:
        print(f"❌ Post 儲存失敗 ({post_data_item.get('title', '未知')}): {e}")

def _save_analysis_result(analysis_n,analysis_p, history_search_instance,current_keyword):
    """
    保存分析結果到 AnalysisResult 表。
    analysis_data: 字典，包含所有分析結果。
    history_search_instance: 相關的 HistorySearch 物件 (可能為 None)。
    current_keyword: 當前分析的關鍵字。
    """
    try:
        # identifier_display 將始終使用 history_search_instance.keyword
        identifier_display = history_search_instance.keyword 

        # 由於 history_search_instance 總會存在，我們直接用它來查找/更新 AnalysisResult
        analysis_result, created = AnalysisResult.objects.update_or_create(
            search=history_search_instance, # 使用有效的 history_search_instance
            defaults={
                'keyword': current_keyword,
                'positive_count': analysis_n.get('positive_count', 0),
                'negative_count': analysis_n.get('negative_count', 0),
                'neutral_count': analysis_n.get('neutral_count', 0),
                'cate_count': analysis_n.get('cate_count', {}),
                'tag_image': analysis_n.get('tag_image', ''),
                'top_word': analysis_n.get('top_word', {}),
                'trend_labels': analysis_n.get('trend_labels', []),
                'trend_values': analysis_n.get('trend_values', []),
                'report': analysis_n.get('report', ''),

                'pos_count': analysis_p.get('pos_count', 0),
                'neg_count': analysis_p.get('neg_count', 0),
                'neu_count': analysis_p.get('neu_count', 0),
                'sour_count': analysis_p.get('sour_count', {}),
                'post_image': analysis_p.get('post_image', ''),
                'post_top_word': analysis_p.get('post_top_word', {}),
                'post_trend_labels': analysis_p.get('post_trend_labels', []),
                'post_trend_values': analysis_p.get('post_trend_values', []),
                'post_report': analysis_p.get('post_report', ''),
            }
        )
        print(f"✅ AnalysisResult - {'創建' if created else '更新'}：{identifier_display} 關鍵字")
        return analysis_result
    except Exception as e:
        # 錯誤日誌也直接使用 history_search_instance.keyword
        print(f"❌ AnalysisResult 儲存失敗 ({history_search_instance.keyword}): {e}")
        return None

def _batch_save_news(news_list_data, history_search_instance=None):
    """
    批量保存新聞列表數據。
    news_list_data: 包含多個新聞字典的列表。
    history_search_instance: HistorySearch 物件，可選。
    """
    for item_data in news_list_data:
        _save_single_news_article(item_data, history_search_instance)

def _batch_save_posts(posts_list_data, history_search_instance=None):
    """
    批量保存貼文列表數據。
    posts_list_data: 包含多個貼文字典的列表。
    history_search_instance: HistorySearch 物件，可選。
    """
    for item_data in posts_list_data:
        _save_single_post_item(item_data, history_search_instance)

def parse_date(date_str, as_datetime=False):
    date_str = date_str.strip()
    now = datetime.now()

    # 嘗試從字串中抽出 YYYY-MM-DD 格式
    match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
    if match:
        date = datetime.strptime(match.group(), "%Y-%m-%d")
        return date if as_datetime else date.strftime("%Y-%m-%d")

    # 支援多種常見日期格式
    date_formats = [
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y年%m月%d日",
    ]
    for fmt in date_formats:
        try:
            date = datetime.strptime(date_str, fmt)
            return date if as_datetime else date.strftime("%Y-%m-%d")
        except Exception:
            continue

    # 相對時間處理
    if "剛剛" in date_str or "秒前" in date_str:
        return now if as_datetime else now.strftime("%Y-%m-%d")

    minute_match = re.search(r"(\d+)\s*分鐘前", date_str)
    if minute_match:
        date = now - timedelta(minutes=int(minute_match.group(1)))
        return date if as_datetime else date.strftime("%Y-%m-%d")

    hour_match = re.search(r"(\d+)\s*小時前", date_str)
    if hour_match:
        date = now - timedelta(hours=int(hour_match.group(1)))
        return date if as_datetime else date.strftime("%Y-%m-%d")

    day_match = re.search(r"(\d+)\s*天前", date_str)
    if day_match:
        date = now - timedelta(days=int(day_match.group(1)))
        return date if as_datetime else date.strftime("%Y-%m-%d")

    # 無法解析就回傳現在時間
    if as_datetime:
        return now # 直接回傳 timezone.now() 物件
    else:
        return now.strftime("%Y-%m-%d") # 將 now 物件格式化為字串

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
      '在', '不', '有', '也', '就', '都', '很', '而', '及', '或', '被', '還', '能', '會','核稿','編輯',
      '內容','請見','發布','訂閱','進行','根據','報導','新聞','針對','一名','發現','結果','記得',
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

# TVBS 新聞爬蟲
def get_tvbs_news(keyword='', max_pages=20, days=7):
    results = []  # 用來儲存所有符合條件的新聞資料    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}   # 模擬瀏覽器，避免被擋爬
    if not keyword.strip():
        keyword = '新聞'  # 若未輸入關鍵字，預設用「新聞」
        if keyword == '新聞':
            days=5
    today = datetime.now()  # 現在的時間
    seven_days_ago = today - timedelta(days=days)  # 幾天前的時間，用來過濾過舊新聞
     
    for page in range(1, max_pages + 1):  # 頁數從 1 到 max_pages
        stop_crawling = False  # 控制是否中斷爬取（遇到太舊的新聞就中斷）
        
        # 構造查詢頁面的 URL
        url = f"https://news.tvbs.com.tw/news/searchresult/{keyword}/news/{page}"
        try:
            # 發送 GET 請求，設定 timeout 避免網路無反應時卡住
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"跳過第 {page} 頁：回應錯誤 {response.status_code}")
                continue  # 若非成功回應，就跳過這頁
        except Exception as e:
            print(f"連線失敗：{e}")
            continue  # 若發生例外也跳過

        # 使用 BeautifulSoup 解析 HTML
        html = BeautifulSoup(response.text, "html.parser")
        
        # 找到新聞清單
        article_list = html.find('main').find('div', class_='list').find_all('li')
        if not article_list:
            break  # 如果沒有新聞條目，就結束爬取

        for article in article_list:
            # 擷取日期字串
            time_tag = article.find('div', class_='time')
            date_str = time_tag.text.strip() if time_tag else ''

            # 將日期字串轉為 datetime 物件，供篩選用
            date_obj = parse_date(date_str, True)
            if not date_obj or date_obj < seven_days_ago:
                stop_crawling = True  # 發現太舊新聞，設停止旗標
                break  # 結束目前頁面的新聞處理

            # 轉換為字串形式，存入結果中
            date = parse_date(date_str)

            # 擷取新聞連結
            a_tag = article.find('a')
            if not a_tag:
                continue  # 若找不到連結則略過

            # 擷取新聞標題
            title_tag = article.find('h2', class_='txt')
            title = title_tag.text.strip() if title_tag else ''

            # 擷取連結 URL
            news_url = a_tag['href'] if a_tag.has_attr('href') else ''
            
            # 擷取摘要內容
            summary_tag = article.find('div', class_='summary')
            summary = summary_tag.text.strip() if summary_tag else ''

            # 擷取標籤列表（原始是字串格式）
            tags_raw = a_tag.get('data-news_tag', '[]')
            tags = [tag.strip(" '") for tag in tags_raw.strip('[]').split(',')]

            # 擷取新聞類別
            category_tag = article.find('div', class_='type').find('a')
            category = category_tag.text.strip() if category_tag else ''

            # 加入結果列表
            results.append({
                'keyword': keyword,
                'title': title,
                'date': date,  
                'summary': summary,
                'news_tag': tags,
                'news_url': news_url,
                'category': category,
                'source': 'TVBS新聞網',
            })

        if stop_crawling:
            break  # 若設定中斷爬取，跳出外層頁數迴圈

    return results  # 回傳所有結果
# 中時新聞爬蟲(被擋)
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
# 自由時報新聞爬蟲
def get_LTN_news(keyword='', max_pages=25, days=7):
    results = []

    if not keyword.strip():
        keyword = '新聞'
        if keyword == '新聞':
            days=5
    stop_crawling = False
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)
    end_time = end_date.strftime('%Y%m%d')
    start_time = start_date.strftime('%Y%m%d')
    for page in range(1, max_pages + 1):
        url = f'https://search.ltn.com.tw/list?keyword={keyword}&start_time={start_time}&end_time={end_time}&sort=date&type=all&page={page}'
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"跳過第 {page} 頁，HTTP 錯誤：{response.status_code}")
                continue
        except Exception as e:
            print(f"連線錯誤：{e}")
            continue
        html = BeautifulSoup(response.text, 'html.parser')
        # print(html)

        # 抓取新聞區塊
        article_list = html.find('section',class_='Searchnews').find('div',class_='page-name').find_all('li')

        for article in article_list:
            # 發布時間
            time_tag = article.find('span', class_='time')
            date_str = time_tag.text.strip() if time_tag else ''
            date_init = parse_date(date_str,True)
            if not date_init or date_init < start_date:
                stop_crawling = True
                break
            date = parse_date(date_str)
            
            a_tag = article.find('a')
            if not a_tag:
                continue    
        
            # 摘要
            summary_tag = article.find('p')
            summary = summary_tag.text.strip() if summary_tag else ''

            # 標籤
            tags = extract_tags(summary)
            if not tags:  
                continue
            # 標題
            title = a_tag['title'] if a_tag.has_attr('title') else ''

            # 新聞連結
            news_url = a_tag['href'] if a_tag.has_attr('href') else ''

            # 類別
            category_tag = article.find('i')
            category = category_tag.text.strip() if category_tag else ''

            # 加入結果
            results.append({
                'keyword': keyword,
                'title': title,
                'date': date,
                'summary': summary,
                'news_tag': tags,
                'news_url': news_url,
                'category': category,
                'source':'自由時報',
            })
        if stop_crawling:
            break
    return results
# ETtoday新聞爬蟲
def get_ET_news(keyword='', max_pages=30, days=7):
    results = []
    if not keyword.strip():
        keyword = '新聞'
        if keyword == '新聞':
            days=5
    stop_crawling = False
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    today = datetime.now()  # 現在的時間
    days_ago = today - timedelta(days=days)  # 幾天前的時間，用來過濾過舊新聞

    for page in range(1, max_pages + 1):
        url = f"https://www.ettoday.net/news_search/doSearch.php?keywords={keyword}&idx=1&page={page}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"跳過第 {page} 頁，HTTP 錯誤：{response.status_code}")
                continue
        except Exception as e:
            print(f"連線錯誤：{e}")
            continue

        html = BeautifulSoup(response.text, "html.parser")

        # 根據實際網頁結構定位文章區塊
        article_list = html.select("div.archive.clearfix")

        for article in article_list:
            # 發布時間
            time_tag = article.select_one('.date')
            date_str = time_tag.text.strip() if time_tag else ''
            date_init = parse_date(date_str,True)
            if not date_init or date_init < days_ago:
                stop_crawling = True
                break
            date = parse_date(date_str)

            a_tag = article.find("a")
            if not a_tag:
                continue

            # 標題
            title_tag = article.find("h2")
            title = title_tag.text.strip() if title_tag else ""

            # 新聞連結
            news_url = a_tag["href"] if a_tag.has_attr("href") else ""

            # 摘要
            summary_tag = article.find("p")
            summary = summary_tag.text.strip() if summary_tag else ""

            # 標籤
            tags = extract_tags(summary)

            # 類別
            category_tag = article.find('span', class_='date').find('a')
            category = category_tag.text.strip() if category_tag else ''

            results.append({
                "keyword": keyword,
                "title": title,
                "date": date,
                "summary": summary,
                "news_tag": tags,
                "news_url": news_url,
                "category": category,
                "source": "ETtoday新聞雲",
            })
        if stop_crawling:
            break
    return results
# 整合新聞文章
def search_news(keyword):
    articles = (
        get_tvbs_news(keyword) +
        get_ET_news(keyword) +
        get_LTN_news(keyword)
    )
    return articles
# 使用 SnowNLP 分析字串情緒
def analyze_sentiment(articles):
    """
    :param articles: 每篇文章為 dict，需包含 summary 和 title
    :return: 回傳原始陣列，每篇文章加入 sentiment_score 及 sentiment 標籤（正面 / 負面 / 中立）
    """
    if not articles:  # 防止 None 或空值
        return []

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
# 計算情緒分類次數
def count_sentiment(articles):
    sentiment_count = {
        '正面': sum(1 for a in articles if a['sentiment'] == '正面'),
        '負面': sum(1 for a in articles if a['sentiment'] == '負面'),
        '中立': sum(1 for a in articles if a['sentiment'] == '中立'),
    }
    return sentiment_count
# 根據情緒標籤統計正面、負面、中立摘要中的高頻詞
def get_top_words(articles, top_n=5):
    """
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
# 計算情緒出現頻率
def sentiment_feq(data,col):
    stats = defaultdict(lambda: {'positive': 0, 'neutral': 0, 'negative': 0})
    for d in data:
        column = d[col]
        if d['sentiment'] == '正面':
            stats[column]['positive'] += 1
        elif d['sentiment'] == '中立':
            stats[column]['neutral'] += 1
        elif d['sentiment'] == '負面':
            stats[column]['negative'] += 1
    return dict(stats)
# 生成高頻字文字雲
def generate_wordcloud(tags, save_path):
    import platform

    # 根據系統自動選擇字體
    system = platform.system()
    if system == "Windows":
        font_path = "C:/Windows/Fonts/msjh.ttc"  # 微軟正黑體
    elif system == "Darwin":
        font_path = "/System/Library/Fonts/STHeiti Medium.ttc"  # macOS 黑體
    else:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux 常見字體

    if not os.path.exists(font_path):
        raise OSError(f"⚠️ 找不到字體檔案：{font_path}")

    # 製作文字雲
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
# 計算時間序列新聞數量
def news_post_counter(articles):
    # 將資料整理成每日數量 dict
    daily_counts = Counter()
    for article in articles:
        if article['date']:
            daily_counts[article['date']] += 1

    # 轉為排序後的 x, y list
    trend_labels = sorted(daily_counts.keys())
    trend_values = [daily_counts[date] for date in trend_labels]
    return trend_labels,trend_values
# AI分析報告prompt生成
def generate_prompt(keyword, sentiment_count, top_words, sentiment_by_catORsour):
    prompt = f"""
    請根據以下資料(新聞或社群貼文)，撰寫一篇分析報告，字數約 300 字，以數據分析師的角度去分析，語氣專業清楚，
    條列式表達，直接給分析結果就好：
    
    🔍 主題：{keyword}

    📊 情緒比例：
    正面文章數：{sentiment_count.get('正面', 0)}
    負面文章數：{sentiment_count.get('負面', 0)}
    中立文章數：{sentiment_count.get('中立', 0)}

    📌 類別情緒統計概況或貼文來源情緒統計概況(請自行判斷）：
    {sentiment_by_catORsour}

    🔥 高頻關鍵詞(每個詞在文章出現的數量):
    {"、".join(top_words.get('all', []))}

    請綜合以上資訊，說明目前熱度趨勢與社群關注重點。
    """
    return prompt
# 載入大語言模型Gemini
def call_LLM(prompt, api_key):
    genai.configure(api_key = api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # gemini-1.5-pro/ gemini-1.5-flash
    response = model.generate_content(prompt)
    return response.text.strip()
# 執行新聞所有流程
def news_work(keyword, api_key):
    start_time = datetime.now().strftime("%Y%m%d_%H%M")
    # 1. 搜尋與情緒分析
    articles = analyze_sentiment(search_news(keyword))
    # 2. 計算正負情緒數量
    sentiment_count = count_sentiment(articles)
    # 3. 趨勢分析（各時間點的新聞數量）
    trend_labels,trend_values = news_post_counter(articles)
    # 4. 分析詞彙貢獻
    top_word = get_top_words(articles)
    # 5. 分析分類情緒
    category_stats = sentiment_feq(articles,'category')
    # 6. 統計標籤詞彙製作文字雲圖
    all_tags = []
    for art in articles:
        all_tags.extend(art['news_tag'])
    
    wordcloud_path = os.path.join(BASE_DIR, 'static', 'clouds', f'n-{keyword}{start_time}.png')
    os.makedirs(os.path.dirname(wordcloud_path), exist_ok=True)
    generate_wordcloud(all_tags, wordcloud_path)
    # 7. 使用 Gemini 生成報告
    prompt = generate_prompt(keyword, sentiment_count, top_word, category_stats)
    try:
        report = call_LLM(prompt, api_key)
    except Exception as e:
        report = f"⚠️ Gemini 回應失敗：{e}"

    end_time = datetime.now().strftime("%Y%m%d_%H%M")
    # 回傳結果
    analysis = {
        'positive_count': sentiment_count['正面'],
        'negative_count': sentiment_count['負面'],
        'neutral_count': sentiment_count['中立'],
        'cate_count':  category_stats,
        'tag_image': f'./static/clouds/n-{keyword}{start_time}.png',
        'top_word': top_word,
        'trend_labels': trend_labels,
        'trend_values': trend_values,
        'report':report,
    }
    return articles, analysis

def posts_work(keyword, api_key):
    start_time = datetime.now().strftime("%Y%m%d_%H%M")
    ptt_posts = analyze_sentiment(get_ptt_posts())
    threads_posts = analyze_sentiment(scrape_threads_by_keyword(keyword))
    if keyword.strip():
        ptt_posts = ptt_keyword(keyword,ptt_posts)
    posts = ptt_posts + threads_posts
    sentiment_count = count_sentiment(posts)
    trend_labels,trend_values = news_post_counter(posts)
    top_word = get_top_words(posts)
    source_stats = sentiment_feq(posts,'source')
    all_tags = []
    for post in posts:
        all_tags.extend(extract_tags(post['summary']))
    print('tags:',len(all_tags))
    wordcloud_path = os.path.join(BASE_DIR, 'static', 'clouds', f'p-{keyword}{start_time}.png')
    os.makedirs(os.path.dirname(wordcloud_path), exist_ok=True)
    generate_wordcloud(all_tags, wordcloud_path)
    # 7. 使用 Gemini 生成報告
    prompt = generate_prompt(keyword, sentiment_count, top_word, source_stats)
    try:
        report = call_LLM(prompt, api_key)
    except Exception as e:
        report = f"⚠️ Gemini 回應失敗：{e}"
    # 回傳結果
    analysis = {
        'pos_count': sentiment_count['正面'],
        'neg_count': sentiment_count['負面'],
        'neu_count': sentiment_count['中立'],
        'sour_count':  source_stats,
        'post_image': f'./static/clouds/p-{keyword}{start_time}.png',
        'post_top_word': top_word,
        'post_trend_labels': trend_labels,
        'post_trend_values': trend_values,
        'post_report':report,
    }
    return posts, analysis
    

    
# source venv/bin/activate
# python manage.py runserver