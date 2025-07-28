import os
from collections import Counter
from django.shortcuts import render
from django.conf import settings

from .utils import (
    work,
    get_latest_articles_by_source,
    compute_source_ranking,
    get_top_hot_articles_by_stats,
    get_top_hot_comments_by_reactions
)

def index(request):
    context = {}
    if request.method == 'POST':
        keyword = request.POST.get('keyword','').strip()
        data    = work(keyword)

        # 只顯示每個來源最新 5 筆
        display_list = get_latest_articles_by_source(data['articles'], top_n=5)

        # 熱門貼文 TOP10
        hot_posts = get_top_hot_articles_by_stats(
            data['articles'], top_n=10, weight_share=5, fetch_stats=True
        )
        hot_site_types = sorted({p['site_type'] for p in hot_posts})
        hot_topics     = sorted({p['discussion'] for p in hot_posts})

        # 熱門留言 TOP10
        hot_comments = get_top_hot_comments_by_reactions(data['articles'], top_n=10, per_article=5)
        comment_regions    = sorted({c['region'] for c in hot_comments})
        comment_categories = sorted({c['source_category'] for c in hot_comments})

        # 討論來源排行榜
        ranking_df = compute_source_ranking({keyword: data['articles']})
        ranking    = ranking_df.to_dict(orient='records')
        site_types = sorted({row['網站類型'] for row in ranking})
        topics     = sorted({row['討論面向'] for row in ranking})

        # 前 5 個關鍵字
        top_keywords = data.get('top_keywords', [])

        # 組 tag_image 的完整 URL
        tag_image_url = None
        if data.get('tag_image'):
            fname = os.path.basename(data['tag_image'])
            tag_image_url = settings.STATIC_URL + f"clouds/{fname}"

        context = {
            'keyword':         keyword,
            'articles':        display_list,
            'positive_count':  int(data['sentiment_count']['正面']),
            'negative_count':  int(data['sentiment_count']['負面']),
            'neutral_count':   int(data['sentiment_count']['中立']),
            'cate_count':      data['category_stats'],
            'tag_image_url':   tag_image_url,
            'top_word':        data['top_word'],
            'trend_labels':    data['trend_labels'],
            'trend_values':    data['trend_values'],
            'report':          data['AIreport'],
            'source_ranking':  ranking,
            'site_types':      site_types,
            'topics':          topics,
            'hot_posts':       hot_posts,
            'hot_site_types':  hot_site_types,
            'hot_topics':      hot_topics,
            'hot_comments':    hot_comments,
            'comment_regions': comment_regions,
            'comment_categories': comment_categories,
            'top_keywords':    top_keywords,
        }

    return render(request, 'index.html', context)
