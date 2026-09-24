# -*- coding:utf-8 -*-
# feed_discover_parse 的离线用例。不碰网络、不起 scrapy，构造 HtmlResponse 直接调解析器。
#
# 跑法（在仓库根目录）：
#   PYTHONPATH=$(pwd) python hexo_circle_of_friends/test/feed_discover_test.py
#
# 钉住的重点是"什么时候**不该**再发请求"：管道只跟上一轮的快照去重、同一轮内不去重，
# 所以多发一个内容相同的 feed 请求就会让同一篇文章被插入两次。
from scrapy.http import HtmlResponse, Request
from hexo_circle_of_friends.spiders.hexo_circle_of_friends import FriendpageLinkSpider

BASE = "https://ex.com/"
FRIEND = ["X", BASE, "https://ex.com/a.png"]
spider = FriendpageLinkSpider()


def run(html, base=BASE, url=None):
    url = url or base
    req = Request(url, meta={"friend": ["X", base, "https://ex.com/a.png"]})
    resp = HtmlResponse(url, body=html.encode("utf-8"), encoding="utf-8", request=req)
    return [r.url for r in spider.feed_discover_parse(resp)]


def link(href, mime="application/rss+xml", rel="alternate"):
    return f'<html><head><link rel="{rel}" type="{mime}" href="{href}"></head><body></body></html>'


cases = [
    # (说明, html, 期望产生的请求)
    ("固定后缀已经猜过的地址，不再请求", link("https://ex.com/atom.xml",
                                  "application/atom+xml"), []),
    ("相对写法同理", link("/atom.xml", "application/atom+xml"), []),
    ("尾斜杠差异不算新地址（WordPress 声明 /feed/，固定后缀猜 /feed）",
     link("https://ex.com/feed/"), []),
    ("相对的尾斜杠写法同理", link("/feed/"), []),
    ("首页自己不算 feed", link("https://ex.com/"), []),
    ("猜不到的路径才请求（Typecho）", link("/index.php/feed/"),
     ["https://ex.com/index.php/feed/"]),
    ("非 feed 的 alternate（多语言）不要碰", link("/en/", "text/html"), []),
    ("rel 不是 alternate 的不要碰", link("/index.php/feed/", rel="stylesheet"), []),
    ("rel 有多个 token 也认", link("/index.php/feed/", rel="alternate home"),
     ["https://ex.com/index.php/feed/"]),
    ("同时声明 atom/rss/rdf 只取一份，且按 atom 优先",
     '<html><head>'
     '<link rel="alternate" type="application/rss+xml" href="/index.php/feed/">'
     '<link rel="alternate" type="application/atom+xml" href="/index.php/feed/atom/">'
     '<link rel="alternate" type="application/rdf+xml" href="/index.php/feed/rdf/">'
     '</head></html>', ["https://ex.com/index.php/feed/atom/"]),
    ("head 里什么都没声明", "<html><head></head><body>hi</body></html>", []),
]

fails = 0
for desc, html, want in cases:
    got = run(html)
    ok = got == want
    fails += 0 if ok else 1
    print(f"  {'PASS' if ok else 'FAIL'}  {desc}")
    if not ok:
        print(f"        期望 {want}\n        实际 {got}")

# 友链地址带子路径的情形（hexo.io/zh-tw/ 就是这个形状）：声明的 /atom.xml 解析到
# 站点根下，与 base+suffix（.../zh-tw/atom.xml）不同，应当请求。
got = run(link("/atom.xml", "application/atom+xml"), base="https://hexo.io/zh-tw/")
ok = got == ["https://hexo.io/atom.xml"]
fails += 0 if ok else 1
print(f"  {'PASS' if ok else 'FAIL'}  友链地址带子路径时，根下的 /atom.xml 是新地址")
if not ok:
    print(f"        实际 {got}")

# meta 里没有 friend 时不能炸。（不挂 request 的 Response 在 scrapy 里连 .meta
# 都没有、直接抛 AttributeError，而真实链路每个 response 都挂着 request，
# 所以这里要测的是"meta 在、但没有 friend 这一项"。）
got = [r.url for r in spider.feed_discover_parse(
    HtmlResponse(BASE, body=link("/index.php/feed/").encode(), encoding="utf-8",
                 request=Request(BASE)))]
ok = got == []
fails += 0 if ok else 1
print(f"  {'PASS' if ok else 'FAIL'}  meta 里没有 friend 时安静返回")

print(f"\n离线用例：{len(cases) + 2 - fails} 通过 / {fails} 失败")
raise SystemExit(1 if fails else 0)
