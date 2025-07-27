# analyzer/views.py
from django.shortcuts import render
from .utils import (
    work,
    get_latest_articles_by_source,
    compute_source_ranking,
    get_top_hot_articles_by_stats,
    get_top_hot_comments_by_reactions
)
from collections import Counter

def index(request):
    context = {}
    if request.method == 'POST':
        # 1. 讀取使用者輸入
        keyword = request.POST.get('keyword', '').strip()

        # 2. 執行分析主流程
        data = work(keyword)

        # 3. 每個來源只顯示最新 top_n 筆
        display_list = get_latest_articles_by_source(data['articles'], top_n=5)

        # 取得熱門貼文 TOP 10
        hot_posts = get_top_hot_articles_by_stats(
            data['articles'],
            top_n=10,
            weight_share=5,
            fetch_stats=True
        )

        # 準備下拉篩選用的值
        hot_site_types = sorted({p['site_type'] for p in hot_posts})
        hot_topics     = sorted({p['discussion'] for p in hot_posts})

        # 計算熱門留言
        hot_comments = get_top_hot_comments_by_reactions(data['articles'], top_n=10, per_article=5)
        comment_regions    = sorted({c['region'] for c in hot_comments})
        comment_categories = sorted({c['source_category'] for c in hot_comments})

        # 計算「熱門討論來源排行榜」
        ranking_df = compute_source_ranking({keyword: data['articles']})
        ranking = ranking_df.to_dict(orient='records')
        site_types = sorted({row['網站類型'] for row in ranking})
        topics     = sorted({row['討論面向'] for row in ranking})

        # 計算前 5 個關鍵詞比例
        all_tags = []
        for art in data['articles']:
            tags = art.get('news_tag') or []
            all_tags.extend(tags)
        tag_counts   = Counter(all_tags)
        top_keywords = tag_counts.most_common(5)  # 取得出現最多的 5 個關鍵詞

        # 4. 組裝 template context
        context = {
            'keyword':           keyword,
            'articles':          display_list,
            'positive_count':    int(data['sentiment_count']['正面']),
            'negative_count':    int(data['sentiment_count']['負面']),
            'neutral_count':     int(data['sentiment_count']['中立']),
            'cate_count':        data['category_stats'],
            'tag_image':         data['tag_image'],
            'top_word':          data['top_word'],
            'trend_labels':      data['trend_labels'],
            'trend_values':      data['trend_values'],
            'report':            data['AIreport'],
            'hot_articles':      data.get('hot_articles', []),
            'source_ranking':    ranking,
            'site_types':        site_types,
            'topics':            topics,
            'hot_posts':         hot_posts,
            'hot_site_types':    hot_site_types,
            'hot_topics':        hot_topics,
            'hot_comments':      hot_comments,
            'comment_regions':   comment_regions,
            'comment_categories': comment_categories,
            'top_keywords':      top_keywords,
        }

    # 5. 最後渲染範本
    return render(request, 'index.html', context)
