import os, sys, requests, uuid, time
import urllib.request
from bs4 import BeautifulSoup
import socket
import threading
from collections import deque
from time import sleep
import pymysql
socket.setdefaulttimeout(15)
p_jclock = threading.Condition() #进程锁调用
p_newPath = deque([]) #最新解析的url链接表
p_stanPath = deque([]) #等待爬取的url链接表
p_existPath = deque([]) #已经爬取过的url链接表
p_errorPath = deque([]) #下载失败的url链接表
title_Path = deque([]) #title池
title_Pathed = deque([])#已下载的title地址池
img_down = deque([]) #img下载池
img_downed = deque([])#已经下载过的Img地址池
p_downNum = 0 #已经下载过的连接数
p_threadNum = 5
url_thread = []
img_thread = []

class pysql:
	def __init__(self):
		self.conn = pymysql.connect(host="localhost", port=3306, user="root", passwd="lw930522", db='qsbk', charset="utf8")#数据库连接字符串
	def connDB(self):
		self.cur = self.conn.cursor()
	def closeDB(self):
		self.cur.close()
		self.conn.close()
	def update(self):
		global uplock
		global p_jclock
		uplock =True
		self.deldate('stanpath_table')
		for url in p_stanPath:
			sql = "INSERT INTO stanpath_table(stanPath)VALUES(\'"+url+"\')"#将url地址池的数据插入数据库
			self.cur.execute(sql)
			self.conn.commit()
		self.deldate('existpath_table')
		for url in p_existPath:
			sql = "INSERT INTO existpath_table(existPath)VALUES(\'"+url+"\')"
			self.cur.execute(sql)
			self.conn.commit()
		self.deldate('qsbktext_table')
		for url in img_down:
			text= str(url.split("&img=")[0])
			img_urlbd = url.split("&img=")[1]
			sql = r"INSERT INTO qsbktext_table(text)VALUES(%s)"
			self.cur.execute(sql,(text))
			self.conn.commit()
	def deldate(self,table):               #删除table中的数据
		sql = "TRUNCATE TABLE "+table
		self.cur.execute(sql)
		self.conn.commit()
class spider:
	def __init__(self,url):
		self.img_downThreadNum = 4
		self.url_threadNum = 2
		p_stanPath.append(url)
	def upup(self):
		for i in range(self.url_threadNum):
			i=superUrl()
			url_thread.append(i)


class superUrl(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
	def run(self):
		global p_stanPath
		global p_existPath
		i = 0
		while(len(p_stanPath)!=0):
			try:
				url = p_stanPath.popleft()
				print("正在爬%s i=%s"%(url,i))
				url_obj = requests.get(url,data=None,headers=self.headers(url))
				html = BeautifulSoup(url_obj.text, "html.parser")
				Listpage = html.find("ul",class_="pagination")
				ListUrl_u = Listpage.find_all("a",rel="nofollow")
				for ListUrl in ListUrl_u:
					new_url = r"http://www.qiushibaike.com"+ListUrl.get("href")
					if new_url ==None:
						continue
					if new_url.split(".")[-1]!=r"jpg" and new_url not in p_existPath:
						p_stanPath.append(new_url) #增加新的url给戴爬取的地址池
				try:
					self.img_get(html)
				except  urllib.request.URLError as e:
					print(e)
					sleep(10)
				p_existPath.append(url)
				p_stanPath = deque(set(p_stanPath)-set(p_existPath))
				i+=1
				if i>10:
					pushdata()
					i = 0

			except urllib.request.URLError as e:
				print(e)
				sleep(10)
	def img_get(self, html):
		try:
			img_html = html
			xhhtml = img_html.find('div', id="content-left")
			for imglist in xhhtml.find_all('div', class_="content"):
				new_imgUrl = imglist.text
				# this_imgurl = imglist.find_next_siblings('div', class_="thumb")
				# if this_imgurl ==[]:
				# 	new_url_img = ""
				# else:
				# 	url_img = this_imgurl.find('img')
				# 	new_url_img = url_img.get('src')
				new_url = new_imgUrl + "&img="+ ""#new_url_img
				img_down.append(new_url)
				#print("标题：%s"%title)
				print("添加%s："%new_url)
		except Exception as e:
			print(e)

	def headers(self,url):
		headers = {"Host": "www.qiushibaike.com","User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0","Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3","Accept-Encoding": "gzip, deflate","Referer":url,"Connection":"close"}
		return headers

class downThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.title=""
		self.url=""
		self.name=""
		self.nowFile = os.getcwd()
	def run(self):
		global img_downed
		global img_down
		if (len(title_Path)!=0 and len(img_down)!=0):
			#img_down = deque(set(img_down)-set(img_downed))
			self.name = title_Path.popleft()
			self.url = img_down.popleft()
			self.namePz()
			img_downed.append(self.url)
			imgname = self.imgFileName()
			if not os.path.exists(imgname):
				print("正在爬:"+self.url)
				urllib.request.urlretrieve(self.url, imgname)
			else:
				print(self.url+"这个妹子已经爬过了")
	def namePz(self):
		self.name = self.name.replace(' ','-')
		self.name = self.name.replace('\\','-')
		self.name = self.name.replace('/','-')
		self.name = self.name.replace(':','-')
		self.name = self.name.replace('*','-')
		self.name = self.name.replace('<','-')
		self.name = self.name.replace('>','-')
		self.name = self.name.replace('|','-')
	def generateFileName(self,name):
		return str(uuid.uuid3(uuid.NAMESPACE_URL,name))

	def imgFileName(self):
		folderFile = self.nowFile+"\\"+self.name
		if not os.path.exists(folderFile):
			os.mkdir(folderFile)
		fileName = self.generateFileName(self.url)+'.jpg'
		totalPath = folderFile+"\\"+fileName
		return totalPath
	def headers(self,url):
		headers = {"Host": "www.ugirl.cc","User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0","Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3","Accept-Encoding": "gzip, deflate","Referer":url,"Cookie":"wordpress_logged_in_1659196acd36bd2b798dfa976ded9f1e=%7C1452078328%7C300cdc3567f74a8f71b99d6bfc6bb98b; CNZZDATA1253518311=1277843620-1450516010-%7C1450866964; BDTUJIAID=711e5a906be928a3037ff4af2efce767; PHPSESSID=qlr05lkvjf5n85a4cpvlc8vd55","Connection":"keep-alive"}
		return headers

def pushdata():
	db = pysql()
	global uplock
	try:
		print("开始上传地址池")
		db.connDB()
		db.update()
		db.closeDB()
		uplock = False
		print("上传地址池成功")
		print("解锁所有线程")
	except Exception as e:
		print(e)
		db.closeDB()
		uplock = False
		print("上传地址池失败")


if __name__ == "__main__":
	url = r"http://www.qiushibaike.com/"#input("输入目标网址:\n")
	p_stanPath.append(url)
	for i in range(1):
		imgload = superUrl()
		imgload.start()
		url_thread.append(imgload)
	for u in url_thread:
		u.join()












#headers = {"Host":"www.mzitu.com","User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0","Accept": "image/png,image/*;q=0.8,*/*;q=0.5","Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3","Accept-Encoding": "gzip, deflate","Referer":"www.mzitu.com","Cookie": "BAIDUID=E7640F5E0492BC620C23C0A8B7012A1C:FG=1; HMACCOUNT=5DA7BAB08C224046; BIDUPSID=E7640F5E0492BC620C23C0A8B7012A1C; PSTM=1450504738; H_PS_PSSID=17747_1420_18240_12824_18501_17001_17073_15742_12089","Connection": "keep-alive"}

# def headers(url):
#     headers2 = {"Host": "www.ugirl.cc","User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0","Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3","Accept-Encoding": "gzip, deflate","Referer":url,"Cookie":"JSESSIONID=AB784DB3917A6F98F187B346EC968B46; SUS=SID-2481755897-1450791411-JA-ujy3r-23ab9944a19441d28b2bef649d5ae621; SUE=es%3D5936f89db760aeb2559a5abb7da0f204%26ev%3Dv1%26es2%3Df963fbab1e2cbcb4ad391c3bd532158e%26rs0%3DGG8JjXjmC8aBpzrhRgG%252FF29KoWjHCwiRmcQQS5QCzjavBEPyMuxoGRfdhfgBh9uJv8H2ChWHdDEqxf7lbBxSLrOnBxhdOdZu9poUHvEE9UHP%252FPdUZjJUwfwgR08A6lV9LXaaTZCV4BjD%252FTo7%252BdlOtwZRdH80u6p%252BIbuIbDqalcI%253D%26rv%3D0; SUP=cv%3D1%26bt%3D1450791411%26et%3D1450793211%26d%3Dc909%26i%3D468b%26us%3D1%26vf%3D0%26vt%3D0%26ac%3D2%26st%3D0%26uid%3D2481755897%26name%3Diphone3333%2540126.com%26nick%3D%25E5%25A6%25A5%25E5%25A6%25A5%25E7%259A%2584%25E4%25B9%25A1%25E9%2587%258C%25E4%25BA%25BA%26fmp%3D%26lcp%3D2012-01-13%252019%253A38%253A17; SUB=_2A257fSGjDeTxGeRK41MW9SvEwjuIHXVYCxRrrDV8PUJbuNANLXjQkW9-E0_j8LhvJjn9PUyAofHVDKURGg..; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WFmmZPD4.1bDSzaJCyv1lc05JpX5K2t; SUHB=02M-t-gJWQYvsK","Connection":"keep-alive"}
#     return headers2
# class SuperUrl:
#     def __init__(self,url):
#         self.url = url
#         #self.headers = headers(url)
#         self.img_threadpool = [] #图片进程池
#         self.url_threadpool = [] #url爬取进程池
#         self.url_ThreadNum = 2
#
#     def urlscan(self):
#         global p_stanPath
#         global p_allPath
#         global headers
#         p_stanPath.append(self.url)
#
#         while (len(p_stanPath)!=0):
#             j =0
#             while j<self.url_ThreadNum and j < len(p_stanPath):
#                 print(p_stanPath[j])
#                 urlobj = requests.get(p_stanPath[j],data=None,headers=headers(p_stanPath[j]))
#                 html = BeautifulSoup(urlobj.text, "html.parser")
#                 ListUrl = html.find_all("a")
#                 for my_ListUrl in ListUrl:
#                     new_url = my_ListUrl.get("href")
#                     pd_url = new_url[:7]
#                     if pd_url =="http://":
#                         p_newPath.append(new_url)
#                 urlThread = DownAllImg()
#                 self.url_threadpool.append(urlThread)
#                 urlThread.start()
#                 p_existPath.append(p_stanPath[j])
#                 j+=1
#
#             for urlThread2 in self.url_threadpool:
#                 urlThread2.join()
#             self.url_threadpool = []
#             self.getUrl()
#
#     def getUrl(self):
#             global p_newPath
#             global p_stanPath
#             global p_existPath
#             p_stanPath = list(set(p_newPath)-set(p_existPath))
#             p_newPath = []
#
# class DownAllImg(threading.Thread):
#     def __init__(self):
#         threading.Thread.__init__(self)
#         self.p_threadpool = []
#         self.p_imgPath = []#待爬取的img链表
#         self.p_title = [] #待爬取的title链表
#         self.p_imgThreaNum = 1
#         self.i = 0
#     def run(self):
#         global p_stanPath
#         global headers
#         for Path in p_stanPath:
#             imgobj = requests.get(Path,data=None, headers=headers(Path))
#             html = BeautifulSoup(imgobj.text, "html.parser")
#             girlImg = html.find_all('div', id="gallery-1")
#             if girlImg ==[]:
#                 #print(Path+"没有图片")
#                 continue
#             else:
#                 for imglist in girlImg:
#                  for img_p in imglist.find_all("a"):
#                     url = img_p.get('href')
#                     title = html.title.string
#                     print("添加%s到下载列表："%url)
#                     down = DownThread(url, title)
#                     try:
#                         down.run()
#                     except Exception as e:
#                         print(e)
#                     self.p_imgPath.append(url)
#                     self.p_title.append(title)
#             # j = 0
#         # while j < len(self.p_imgPath):
#         #        # while self.i < self.p_imgThreaNum:
#         #     Path_v = self.p_imgPath[j]
#         #     title_v = self.p_title[j]
#         #     threadpool = DownThread(Path_v, title_v)
#         #     #self.p_threadpool.append(threadpool)
#         #     #print("下载线程数:%d"%self.i)
#         #     self.i += 1
#         #     j += 1
#         #     threadpool.start()
#         # for thread in self.p_threadpool:
#         #     thread.join()
#         # self.i = 0
#         # self.p_imgPath = []
#
#
#
#         #except Exception as e:
#         #    print(e)
#
#
# class DownThread():
#     def __init__(self,url,title):
#         self.url=url
#         self.title=title
#         self.nowFile = os.getcwd()
#     def generateFileName(self,name):
#      return str(uuid.uuid3(uuid.NAMESPACE_URL,name))
#
#     def imgFileName(self):
#         folderFile = self.nowFile+"\\"+self.title
#         if not os.path.exists(folderFile):
#             os.mkdir(folderFile)
#         fileName = self.generateFileName(self.url)+'.jpg'
#         totalPath = folderFile+"\\"+fileName
#         return totalPath
#     def run(self):
#         imgname = self.imgFileName()
#         if not os.path.exists(imgname):
#             print("正在爬:"+self.url)
#             urllib.request.urlretrieve(self.url, imgname)
#         else:
#             print(url+"这个妹子已经爬过了")
#
# if __name__ == "__main__":
#     url = r"http://www.ugirl.cc/corpora"#input("输入目标网址:\n")
#     imgload = SuperUrl(url)
#     imgload.urlscan()

#
#     s= requests.get(url, data=data, headers=headers_value())
#     gs= BeautifulSoup(s.text, "html.parser")
#     i = gs.find_all("span")
#     for c in i:
#         for d in c.find_all("a"):
#             b = d.get("href")
#             print("正在爬%s"%b)
#             j = fanye(b)
#             if j:
#                 continue
#
# class downImg:
#     def __init__(self):
#         self.now
#
#
#
#
# def generateFileName(name):
#     return str(uuid.uuid3(uuid.NAMESPACE_URL,name))
#
#
# # 根据文件名创建文件
# def createFileWithFileName(localPathParam,fileName):
#     totalPath=localPathParam+'\\'+fileName
#     if not os.path.exists(totalPath):
#         file=open(totalPath,'a+')
#         file.close()
#         return totalPath
#
# def meiziImg(url):
#     s = requests.get(url,data=data,headers=headers_value())
#     bs = BeautifulSoup(s.text,"html.parser")
#     girl=bs.find_all('div',class_="postContent")
#     for child in girl:
#         for j in child.find_all('img'):
#             l = j.get('src')
#             #print("慢点慢点")
#             #time.sleep(1)
#             fileName=generateFileName(l)+'.jpg'
#             try:
#                 if os.path.exists(papap+fileName):
#                     print("这个妹子已经扒过了")
#                     continue
#                 else:
#                     urllib.request.urlretrieve(l,createFileWithFileName(targetDir,fileName))
#             except:
#                 print("此图下载失败")
#                 continue
#             print(l)
#     return false
#
# def qzurl(url):
#     s = requests.get(url,data=data,headers=headers_value())
#     bs = BeautifulSoup(s.text,"html.parser")
#     t="http://www.meizitu.com/a/sifang_5_1.html"
#     g = bs.find_all('li', class_="wp-item")
#     for child in g:
#         for m in child.find_all(target="_blank"):
#             l=m.get("href")
#             if t!=l:
#                 print(l)
#                 j= threading.Thread(target = meiziImg, args=l)
#                 j.setDaemon(True)
#                 j.start()
#                 p_threadpool.append(j)
#                 t=l
#     for i in p_threadpool:
#         i.join(30)
#
#
#     return false
# myReferer = ""
# def headers_value():
# <<<<<<< HEAD
#     global myReferer
#     headers = {"Host": "www.meizitu.com","User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0","Accept": "image/png,image/*;q=0.8,*/*;q=0.5","Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3","Accept-Encoding": "gzip, deflate","Referer":myReferer,"Cookie": "BAIDUID=E7640F5E0492BC620C23C0A8B7012A1C:FG=1; HMACCOUNT=5DA7BAB08C224046; BIDUPSID=E7640F5E0492BC620C23C0A8B7012A1C; PSTM=1450504738; H_PS_PSSID=17747_1420_18240_12824_18501_17001_17073_15742_12089","Connection": "keep-alive"}
# =======
#     headers = {"Host": "www.meizitu.com","User-Agent":"Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)"
# ,"Accept": "image/png,image/*;q=0.8,*/*;q=0.5","Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3","Accept-Encoding": "gzip, deflate","Referer":myReferer,"Cookie": "BAIDUID=E7640F5E0492BC620C23C0A8B7012A1C:FG=1; HMACCOUNT=5DA7BAB08C224046; BIDUPSID=E7640F5E0492BC620C23C0A8B7012A1C; PSTM=1450504738; H_PS_PSSID=17747_1420_18240_12824_18501_17001_17073_15742_12089","Connection": "keep-alive"}
# >>>>>>> origin/master
#     return headers
# def fanye(url):
#     g = r"http://www.meizitu.com/a/"
#     global myReferer
#     myReferer= url
#     s = requests.get(url, data=data, headers=headers_value())
#     gs = BeautifulSoup(s.text,"html.parser")
#     i = gs.find_all(id = "wp_page_numbers")
#     for c in i:
#         for d in c.find_all("a"):
#             b = d.get("href")
#             u = g+b
#             print("正在爬"+u)
#             j = qzurl(u)
#             if j:
#                continue
#             p_threadpool = []
#     return false
#
#
# def mulu(url):
#     global myReferer
#     myReferer = url
#     s= requests.get(url, data=data, headers=headers_value())
#     gs= BeautifulSoup(s.text, "html.parser")
#     i = gs.find_all("span")
#     for c in i:
#         for d in c.find_all("a"):
#             b = d.get("href")
#             print("正在爬%s"%b)
#             j = fanye(b)
#             if j:
#                 continue
#
# targetDir =os.getcwd()
# papap=targetDir+"\\"
#
#
# url2 = "http://www.meizitu.com/a/sifang_5_1.html"
# data=None
#
#
#
# false = False
# try:
#
#     mulu(url2)
# except:
#     print ("Unexpected error:", sys.exc_info()) # sys.exc_info()返回出错信息
#     input('press enter key to exit') #这儿放一个等待输入是为了不让程序退出
#


