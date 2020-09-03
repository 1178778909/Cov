import json
import time
import requests
import pymysql
import traceback # 追踪异常
from selenium.webdriver import Chrome,ChromeOptions

def get_tencent_data():
    '''
    return: 返回历史数据和当日详细数据
    '''
    url_main = "https://view.inews.qq.com/g2/getOnsInfo?name=disease_h5"
    url_other = 'https://view.inews.qq.com/g2/getOnsInfo?name=disease_other'
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36 Edg/84.0.522.63'
    }
    r_main = requests.get(url_main, headers)
    r_other = requests.get(url_other, headers)

    res_main = json.loads(r_main.text)
    res_other = json.loads(r_other.text)

    data_main_all = json.loads(res_main['data'])
    data_other_all = json.loads(res_other['data'])
    
    history = {} # 历史数据
    
    for i in data_other_all['chinaDayList']:
        ds = "2020." + i["date"]
        tup = time.strptime(ds, "%Y.%m.%d")
        ds = time.strftime("%Y-%m-%d", tup)
        confirm = i['confirm']
        suspect = i['suspect']
        heal = i['heal']
        dead = i['dead']
        history[ds] = {"confirm": confirm, "suspect": suspect, "heal": heal, "dead": dead}
    for i in data_other_all['chinaDayAddList']:
        ds = "2020." + i["date"]
        tup = time.strptime(ds, "%Y.%m.%d")
        ds = time.strftime("%Y-%m-%d", tup)
        confirm = i['confirm']
        suspect = i['suspect']
        heal = i['heal']
        dead = i['dead']
        history[ds].update({"confirm_add": confirm, "suspect_add": suspect, "head_add": heal, "dead_add": dead})
        
    details = [] # 当日详细数据

    update_time = data_main_all['lastUpdateTime']
    data_country = data_main_all['areaTree']  # list 25个国家
    data_province = data_country[0]['children']  # 中国各省
    for pro_infos in data_province:
        province = pro_infos['name']  # 省名
        for city_infos in pro_infos['children']:
            city = city_infos['name']
            confirm = city_infos['total']['confirm']
            confirm_add = city_infos['today']['confirm']
            heal = city_infos['total']['heal']
            dead = city_infos['total']['dead']
            details.append([update_time, '中国', province, city, confirm, confirm_add, heal, dead])

    return history, details

def get_conn():
    # 建立连接
    conn = pymysql.connect(host="127.0.0.1", user="xilingf", password="117877", db="cov", charset="utf8")
    # 创建游标
    cursor = conn.cursor()
    return conn, cursor

def close_conn(conn, cursor):
    if cursor:
        cursor.close()
    if conn:
        conn.close()

# 定义更新细节函数(插入数据到detail表)
def update_details():
    cursor = None
    conn = None
    try:
        li = get_tencent_data()[1] # 1代表最新数据
        conn, cursor = get_conn()
        sql = "insert into details(update_time,country,province,city,confirm,confirm_add,heal,dead) values(%s,%s,%s,%s,%s,%s,%s,%s)"
        sql_query = 'select %s=(select update_time from details order by id desc limit 1)'
        # 对比当前最大时间戳
        cursor.execute(sql_query, li[0][0])
        if not cursor.fetchone()[0]:
            print(f"{time.asctime()}开始更新数据")
            for item in li:
                cursor.execute(sql,item)
            conn.commit()
            print(f"{time.asctime()}更新到最新数据")
        else:
            print(f"{time.asctime()}已是最新数据！")
    except:
        traceback.print_exc()
    finally:
        close_conn(conn, cursor)


# 插入历史数据
def insert_history():
    cursor = None
    conn = None
    try:
        dic = get_tencent_data()[0] # 0代表取出返回数据的第一位数据
        print(f"{time.asctime()}开始更新历史数据")
        conn, cursor = get_conn()
        sql = "insert into history values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        for k,v in dic.items():
            cursor.execute(sql, [k, v.get("confirm"), v.get("confirm_add"), v.get("suspect"), v.get("suspect_add"), v.get("heal"), v.get("heal_add"), v.get("dead"), v.get("dead_add")])
        conn.commit()
        print(f"{time.asctime()}历史数据更新完毕")
    except:
        traceback.print_exc()
    finally:
        close_conn(conn, cursor)


# 更新历史数据
def update_history():
    cursor = None
    conn = None
    try:
        dic = get_tencent_data()[0]#0代表历史数据字典
        print(f"{time.asctime()}开始更新历史数据")
        conn,cursor = get_conn()
        sql = "insert into history values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        sql_query = "select confirm from history where ds=%s"
        for k,v in dic.items():
            if not cursor.execute(sql_query,k):
                cursor.execute(sql,[k, v.get("confirm"),v.get("confirm_add"),v.get("suspect"),
                               v.get("suspect_add"),v.get("heal"),v.get("heal_add"),
                               v.get("dead"),v.get("dead_add")])
        conn.commit()
        print(f"{time.asctime()}历史数据更新完毕")
    except:
        traceback.print_exc()
    finally:
        close_conn(conn,cursor)

# 查找百度热评数据
def get_baidu_hot():
    option = ChromeOptions()
    option.add_argument('--headless')   # 隐藏浏览器
    option.add_argument('--no--sandbox')
    browser = Chrome(options = option, executable_path="chromedriver.exe")

    url = "https://voice.baidu.com/act/virussearch/virussearch?from=osari_map&tab=0&infomore=1"
    browser.get(url)
    but = browser.find_element_by_css_selector('#ptab-0 > div > div.VirusHot_1-5-6_32AY4F.VirusHot_1-5-6_2RnRvg > section > div')  # 点击加载更多按钮
    but.click()
    time.sleep(1)
    c = browser.find_elements_by_xpath('//*[@id="ptab-0"]/div/div[1]/section/a/div/span[2]')
    print(len(c))
    context = [i.text for i in c]
    browser.close()
    return context

# 更新百度热评数据
def update_hotsearch():
    cursor = None
    conn = None
    try:
        context = get_baidu_hot()
        print(f"{time.asctime()}开始更新数据")
        conn, cursor = get_conn()
        sql = "insert into hotsearch(dt, content) values(%s,%s)"
        ts = time.strftime("%Y-%m-%d %X")
        for i in context:
            cursor.execute(sql, (ts, i))
        conn.commit()
        print(f"{time.asctime()}数据更新完毕")
    except:
        traceback.print_exc()
    finally:
        close_conn(conn, cursor)

if __name__ == "__main__":
    get_baidu_hot()