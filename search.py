from urllib.request import urlopen
from urllib import error
import re
from bs4 import BeautifulSoup
import argparse
import csv



from flask import Flask
from flask import request, render_template, redirect, url_for, jsonify
app = Flask(__name__)



def parse_links(links, visited, url):
    # убираем ссылки на на js и  css файлы
    timelist = []
    truelinks = []
    copy_links = links.copy()
    for link in copy_links:
        timelist.extend(link.split("/"))
        if ".js" in timelist[len(timelist)-1].lower() or ".css" in timelist[len(timelist)-1].lower():
            links.remove(link)
        elif "." in timelist[len(timelist)-1].lower():
            timelist=timelist[len(timelist) - 1].lower().split(".")
            if "html" not in timelist and "php" not in timelist:
                links.remove(link)
        elif link in visited:
            links.remove(link)
        elif len(re.findall("[.,\-\s\?*\{\}\#]" , timelist[len(timelist)-1].lower())):
            links.remove(link)
        else:
            truelinks.append(link)
    #чистит список от ссылок на левые сайты (почти все)
    copy = truelinks.copy()
    for link in copy:
        if link.startswith("http://") or link.startswith("https://"):
            if not url.split("/")[2] == link.split("/")[2]:
                truelinks.remove(link)
            #и от самого себя
            elif url == link:
                truelinks.remove(link)
            elif not link.startswith(url):
                truelinks.remove(link)
        elif not link.startswith("//ww"):
            truelinks.append(url+link[1:])
            truelinks.remove(link)
        else:
            truelinks.remove(link)
    return truelinks

def get_links(html, url, visited):
    links = [link[0] for link in list(set(re.findall('"((http|ftp)s?://.*?)"', html)))]
    nonfull = list(set(re.findall('href="(.*?)"', html)))

    truelinks = parse_links(links, visited, url)
    truelinks2 = parse_links(nonfull, visited, url)

    truelinks2.extend(truelinks)
    truelinks2 = list(set(truelinks2))

    return truelinks2

def get_text(html):
    soup = BeautifulSoup(html, "lxml")

    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()  # rip it out

    # get all div
    div_saver = []
    for div in soup(["div"]):
        div = div.get_text()
        div_saver.append(div)

    div_saver2 = div_saver.copy()

    for text in div_saver2:
        # get text - если soup.body.get_text() - вернет только боди тд по аналогии
        # text = soup.get_text()

        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text2 = '<br>'.join(chunk for chunk in chunks if chunk)
        div_saver.remove(text)
        div_saver.append(text2)

    return div_saver

def read_url(url):
    with urlopen(url) as data:
        enc = data.info().get_content_charset('utf-8')
        html = data.read().decode(enc)
    return html

def find_words(url, text, words, posts):

    for word in words:
        if word in text:
            if url not in posts:
                posts.append((url, text))
    return posts


def main_alg(url, link, words, posts, visited_links, depth):
    if depth == 0:
        return posts
    try:
    # читаем ссылку и получаем ее html код
        html = read_url(link)
    except error.URLError as err:
        return posts
    # получаем строку с текстом в cсылке
    text_full = list(set(get_text(html)))
    # ищем слова и получаем назад список постов, где они были найдены
    for text in text_full:
        posts = find_words(link, text, words, posts)
        # if fwords and fwords[0] not in posts:
        #     posts.extend([list(set(fwords)-set(posts)), text])
        posts = list(set(posts))
        print("posts are found: {0}".format(len(posts)))
    #for post in posts:
        #print(post)
    # получаем все ссылки ресурса
    links = get_links(html, url, visited_links)

    links2 = []
    count = 0
    if len(links)>10:
        while count < 10:
            links2.append(links[count])
            count+=1
    else:
        links2 = links
    for link in links2:
        try:
            visited_links.append(link)
            posts.extend(main_alg(url, link, words, posts, visited_links, depth - 1))
        except error.HTTPError as e:
               print("bad request")
    return posts


@app.route('/_findwords')
def add_numbers():
    url = request.args.get('url')
    word1 = request.args.get('word1')
    word2 = request.args.get('word2')
    word3 = request.args.get('word3')
    words = [str(word1), str(word2), str(word3)]
    posts = [] # список найденных постов
    depth = 3 # размерность поиска вглубину (кол-во страниц сайта, которые мы просмотрим)
    visited_links = [url] # was here
    if not url.startswith("http://") or not url.startswith("https://"):
        url = 'http://'+url
    print(url)
    print(words)
    posts = set(main_alg(url, url, words, posts, visited_links, depth))
    #print(posts)
    str_to_serv = ''
    for post in posts:
        str_to_serv = str(post) + str_to_serv
    return jsonify(result=str_to_serv)


@app.route('/')
def index():
    return render_template('index.html')



def run(url, words):
    posts = [] # список найденных постов
    depth = 3 # размерность поиска вглубину (кол-во страниц сайта, которые мы просмотрим)
    visited_links = [url] # was here
    print(url)
    print(words)
    posts = set(main_alg(url, url, words, posts, visited_links, depth))
    with open('file.csv', 'w') as csvfile:
        spamwriter = csv.writer(csvfile,  delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL, dialect='excel')
        spamwriter.writerow(posts)
    print(posts)

if __name__ == '__main__':
    # включает веб морду
    app.run()
    # для тестов без веб-морды
    #run('http://toyota-axsel.com', ["price"])

