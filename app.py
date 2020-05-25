from flask import Flask,render_template, url_for, request, redirect,send_file,jsonify
import requests
import os
import bson
from bson import json_util
from bson.objectid import ObjectId
import json
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
import pymongo
from pymongo import MongoClient
from selenium import webdriver
import time
from selenium.common.exceptions import NoSuchElementException


app = Flask(__name__)
#авторизуемся в MongoDB
cluster = MongoClient\
    ("mongodb+srv://***:***@cluster0-ftcef.mongodb.net/test?retryWrites=true&w=majority",
     connect=False)
#используем браузер без графического интерфейса

opts = Options()
opts.set_headless()
assert opts.headless

def post_dict(messages):
    """Функция публикует файл в MongoDB и возращает
     guid"""
    db = cluster['test']
    collection = db['test']
    _id = collection.insert_one(messages)
    return _id.inserted_id

def first_finder(poisk):
    """Функция производит первичный поиск
    с формированием списка найденных организаций"""
    #driver = webdriver.Firefox(executable_path=os.path.join(os.getcwd(), "geckodriver"), options=opts)
    driver = webdriver.Firefox(executable_path="./geckodriver",options=opts)
    driver.get('https://****/')
    search = driver.find_element_by_xpath('/html/body/fedresurs-app/home/quick-search/div/div/form/input')
    search.send_keys(poisk)
    search.send_keys(Keys.ENTER)
    url = driver.current_url
    driver.get(url)
    links = []
    try:
        while True:
            driver.find_element_by_xpath('/html/body/fedresurs-app/search/\
            div/div/div/entity-search/div[2]/entity-search-result/loader/\
            div[1]/div/div[1]/company-search-result/loader/div[2]/div/button').click()
            time.sleep(5)
    except NoSuchElementException:
        company = driver.find_elements_by_class_name ('td_company_name')
        if company is None:
            return links
        for el in company:
            link = el.get_attribute('href')
            links.append(link)
    driver.close()
    return links

def second_finder(links):
    """Функция формирует список организаций содержащих сведения ,
    и в дальнейщем производит парсинг всех сообщений
    """
    need_link = []
    messages = {}
    for urls in links:
        driver = webdriver.Firefox(executable_path=os.path.join(os.getcwd(), "geckodriver"), options=opts)
        driver.get(urls)
        try:
            find = driver.find_element_by_tag_name("***")
            need_link.append(urls)
            driver.close()
        except NoSuchElementException:
            driver.close()
            continue
        time.sleep(6)
    for eli in need_link:
        driver = webdriver.Firefox\
            (executable_path=os.path.join(os.getcwd(), "geckodriver"),
             options=opts)
        driver.get(eli)
        driver.implicitly_wait(3)
        try:
            while True:
                driver.find_element_by_xpath(
                '/html/body/***/company-card/div/\
                ***/div/div[2]/loader/div[2]/div/button').click()
                time.sleep(6)
        except NoSuchElementException:
            driver.implicitly_wait(3)
            sp=driver.find_elements_by_class_name("msg_item")
            for i in range(1,len(sp)+1):
                time.sleep(2)
                xpath = '/html/body/***/company-card/div/\
                ***/div/div[2]/loader/div[1]/\
                publication-list/div['+str(i)+']/div[2]/h4[1]/a'
                time.sleep(2)
                driver.find_element_by_xpath(xpath).click()
                time.sleep(5)
                newWindowsSet = driver.window_handles
                driver.switch_to_window(newWindowsSet[1])
                if driver.current_url[29] == 'W':
                    messages[str(i)]={'Идентификатор':driver.find_element_by_xpath\
                    ('/html/body/form/table/tbody/tr[3]/td/table/tbody/tr/td/span\
                    /div/table[1]/tbody/tr[1]/td[2]').text.split('\n'),
                    'Текст':driver.find_element_by_class_name('msg').text.split('\n'),
                    'Дата_публикации':driver.find_element_by_xpath\
                    ('/html/body/form/table/tbody/tr[3]/td/table/tbody/tr[1]/td/\
                    span/div/table[1]/tbody/tr[2]/td[2]').text.split('\n'),
                    'URL':driver.current_url}
                driver.close()
                driver.switch_to_window(newWindowsSet[0])
            driver.close()
    return messages

@app.route('/',methods=['POST','GET'])
@app.route('/finder',methods=['POST','GET'])
def finder():
    if request.method == 'POST':
        poisk = request.form['company_name']
        html = requests.get('https://***.ru/')
        if html.status_code == 200:
            links = first_finder(poisk)
            len_link = 'Найдено '+ str(len(links))
            not_bank = 'По указанному названию организации \
            не найдено сведений'
            messages = second_finder(links)
            if len(messages) != 0:
                id_element = post_dict(messages)
                return render_template("finder.html", id_element=id_element)
            return render_template("finder.html", not_bank=not_bank)
        else:
            not_work = 'Сайт недоступен, попробуйте позже'
            return render_template("finder.html", not_work=not_work)
    else:
        return render_template("finder.html")

@app.route('/returner',methods=['POST','GET'])
def returner():
    if request.method == 'POST':
        post_id = request.form['company_name']
        db = cluster['test']
        collection = db['test']
        try:
            results = collection.find_one({"_id": ObjectId(str(post_id))})
            with open("data_file.json", "w") as write_file:
                json.dump(results,write_file,default=json_util.default,ensure_ascii=False)
            return send_file("data_file.json",mimetype='json',as_attachment=True)
        except bson.errors.InvalidId:
            res = 'Неверно указан id'
            return render_template("returner.html",res=res)


    else:
        return render_template("returner.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080,debug=False)
