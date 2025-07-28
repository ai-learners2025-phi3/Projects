from get_ptt_spider import get_ptt_posts

posts = get_ptt_posts()
print(f"取得 {len(posts)} 篇文章")

for i, post in enumerate(posts, 1):
    print(f"\n==== 第 {i} 篇文章 ====")
    for key, value in post.items():
        print(f"{key}:\n{value}\n{'-'*40}")
