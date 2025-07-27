from analyzer.utils import get_tvbs_news, fetch_article_stats, get_top_hot_articles_by_stats

# 1. 先抓幾篇新聞
articles = get_tvbs_news("台灣", max_pages=1)

# 2. 單篇內頁補抓驗證
for art in articles[:3]:
    v, s = fetch_article_stats(art)
    print(f"{art['title']}\n  URL: {art['news_url']}\n  view_count: {v}, share_count: {s}\n")

# 3. 補抓並列出 Top10 熱門
hot = get_top_hot_articles_by_stats(articles, top_n=10, weight_share=5, fetch_stats=True)
print("----- 熱門 Top10 -----")
for idx, art in enumerate(hot, 1):
    print(f"{idx}. {art['title']}  ({art['view_count']} 點閱, {art['share_count']} 分享) → 分數 {art['hot_score']}")
