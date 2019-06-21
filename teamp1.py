#!/usr/bin/python
#-*- coding: utf-8 -*-
import sys
import re
import requests
import argparse
import commands
import operator
import timeit
import numpy
import math
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, render_template
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from elasticsearch import Elasticsearch
reload(sys)
sys.setdefaultencoding('utf-8')

def clean_text(text):
	cleaned_text=re.sub('[\{\}\[\]\/?.,;:|\)*~`!^\–_+<>@\#$%&\\\=\(\'\"]',
                          '', text)

	return cleaned_text

word_d = {}
sent_list = []
sent_list2 = []
def process_new_sentence(s):
    global sent_list
    sent_list.append(s)
    tokenized = word_tokenize(s)
    for word in tokenized:
        if word not in word_d.keys():
            word_d[word]=0
        word_d[word] += 1
	
def process_new_sentence2(s):
    global sent_list2
    sent_list2.append(s)
    tokenized = word_tokenize(s)
    for word in tokenized:
        if word not in word_d.keys():
            word_d[word]=0
        word_d[word] += 1

def make_vector(i):
    global sent_list
    v = []
    s = sent_list[i]
    tokenized = word_tokenize(s)
    for w in word_d.keys():
        val = 0
        for t in tokenized:
            if t==w:
                val +=1
        v.append(val)
    return v

def compute_tf(s):
	bow = set()
	wordcount_d = {} # dictionary for words in the given sentence (document)
	tokenized = word_tokenize(s)
	for tok in tokenized:
		if tok not in wordcount_d.keys():
           		wordcount_d[tok]=0
        	wordcount_d[tok] += 1
       		bow.add(tok)
	tf_d = {}
	for t in bow:
		tf_d[t] = wordcount_d[t]/float(sum(wordcount_d.values()))
	return tf_d

def compute_idf():
	global sent_list2
	Dval = len(sent_list2)
	# build set of words
	bow = set()
	for i in range(0,len(sent_list2)):
		tokenized = word_tokenize(sent_list2[i])
	for tok in tokenized:
		bow.add(tok)
    	idf_d = {}
    	for t in bow:
        	cnt = 0
        	for s in sent_list2:
            		if t in word_tokenize(s):
                		cnt += 1
		idf_d[t] = math.log10(Dval/float(cnt))
	return idf_d


app = Flask(__name__)

@app.route('/status',methods=['POST'])
def status():
        if request.method == 'POST':
		url=[]
		ncount=0
		successstatuses=[]
		duplicationstatuses=[]
		reasons=[]
		try:
                	f = request.files['file']
			lines = f.readlines()
			f.close()	
			for i in lines:
				url.append(i)
				url[ncount]=url[ncount].replace("\n","")
				try:
					res = requests.get(url[ncount])
					reasons.append("")
					successstatuses.append("O")
				except:
					reasons.append("URL is not available")
					successstatuses.append("X")
				ncount+=1
		except:
			url.append(request.form['URL'])
			try:
				res = requests.get(url[ncount])
				reasons.append("")
				successstatuses.append("O")
			except:
				reasons.append("URL is not available")
				successstatuses.append("X")
			ncount+=1

		global es
		eslist=[]
		n=0
		try:
			eslist=es.search('url1', ignore=[400,404])
			for i in eslist['hits']['hits']:
				url.append(i['_source']['url'])
				n+=1
		except:
			eslist=[]			
		count=len(url)
                for i in range(0,count):
                        url[i]=url[i].replace("\n","")
		
		for i in range(0,ncount):
			check=0
			for j in range(0,count):
				if(url[i]==url[j] and i!=j):
					check=1
					break
			if(check==1):
				duplicationstatuses.append("O")
			else:
				duplicationstatuses.append("X")	
		
		status=""	
		for i in range(0,ncount):
			status = status + "<tr><td>" + url[i] + "</td><td>" + successstatuses[i] + "</td><td>" + reasons[i] + "</td><td>" + duplicationstatuses[i]  + "</td></tr>"
		
		body=[]
		a={}
		dup=""
		index=[]
		b=0
		for i in range(0,count):
			index.append(0)

		for i in range(0,ncount):
			if(duplicationstatuses[i]=="O"):
				dup=url[i]
				for j in range(i+1,count):
					if(url[j]==dup):
						index[j]=1
		for k in range(0,ncount):
			if(index[k]==1):	
				url.pop(k)
				successstatuses.pop(k)
		 		duplicationstatuses.pop(k)
				reasons.pop(k)
				b+=1
		ncount-=b
		
	
		for i in range(0,ncount):
			a={
				"url":url[i]
			}
			if(n==0):
				if(successstatuses[i]=="O"):
					body.append(a)
				else:
					ncount-=1
			else:
				if(successstatuses[i]=="O" and duplicationstatuses[i]=="X"):
					body.append(a)
				else:
					ncount-=1	
		
		for i in range(0,ncount):
			es.index(index='url1',doc_type='doc',id=n+i,body=body[i])
		return "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>Status text Box</title></head><body><p>Status Text Box</p><table border=1 style=\"border: 1px solid black; text-align:center;\"><th>URL</th><th>SuccessStatus</th><th>Reason</th><th>DuplicationStatus</th>" + status+ "</table><p><form action = \"/result\" method = \"post\"><input type =\"submit\" value = \"OK\"></form></p></body></html>"

@app.route('/tfidf', methods=['GET'])
def tfidf():
	global es
	global sent_list2
        es.list=[]
        eslist=es.search('result')
        n=0
        words=[]
        url=[]
        for i in eslist['hits']['hits']:
                words.append(i['_source']['word'])
                url.append(i['_source']['url'])
                n+=1
        if(n<2):
                return "Need More Documents"
        sentence=[]
        for i in range(0,n):
                sentence.append("")
        for i in range(0,n):
                for j in words[i]:
                        sentence[i]+=j+" "
        for i in range(0,n):
                process_new_sentence2(sentence[i])
	
	idf_d = compute_idf()
   	for i in range(0,len(sent_list2)):
        	tf_d = compute_tf(sent_list2[i])
	dic={}
        for word,tfval in tf_d.iteritems():
		dic[word] = tfval*idf_d[word]
	dic = sorted(dic.items(), key = operator.itemgetter(1,0),reverse=True)
	e=""
	for i in range(0,10):
		word=dic[i][0]
		tfidf=dic[i][1]
		e=e+"<tr><td>"+str(word)+"</td><td>"+str(tfidf)+"</td></tr>"
	return "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>TF-IDF Top10</title></head><body><p>TF-IDF Top10</p><table border=1 style=\"border: 1px solid black; text-align:center;\"><th>Word</th><th>TF-IDF</th>" + e + "</table></body></html>"

@app.route('/cosine',methods=['GET'])
def cosine():
	global es
	es.list=[]
	eslist=es.search('result')
	n=0
	words=[]
	url=[]
	for i in eslist['hits']['hits']:
		words.append(i['_source']['word'])
		url.append(i['_source']['url'])
        	n+=1
	if(n<3):
		return "Need More Documents"
	sentence=[]
	for i in range(0,n):
		sentence.append("")
	for i in range(0,n):
		for j in words[i]:
			sentence[i]+=j+" "
	for i in range(0,n):
		process_new_sentence(sentence[i])
        
	dotpro={}
	cossimil={}
	for i in range(0,n):
		for j in range(i+1,n):
			v1=make_vector(i)
			v2=make_vector(j)
			index=str(i)+'-'+str(j)
			dotpro[index] = numpy.dot(v1,v2)
				
		    	cossimil[index] = dotpro[index] / numpy.linalg.norm(v1) * numpy.linalg.norm(v2)
	
	cossimil = sorted(cossimil.items(), key = operator.itemgetter(1,0),reverse=True)
	e=""
	for i in range(0,3):
		key=str(cossimil[i][0])
		value=str(cossimil[i][1])
		keys=key.split('-')
		urltourl="[ " + url[int(keys[0])] + " ] - [ " + url[int(keys[1])] + " ]"  
		e=e+"<tr><td>"+str(i+1)+"</td><td>"+urltourl+"</td><td>"+str(value)+"</td></tr>"
	return "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>Cosine-Similarlity Top3</title></head><body><p>Cosine-Similarlity Top3</p><table border=1 style=\"border: 1px solid black; text-align:center;\"><th>Rank</th><th>URL</th><th>Cosine-Similarlity</th>" + e + "</table></body></html>"


@app.route('/result', methods=['POST'])
def URL():
        if request.method == 'POST':
		global es
		eslist=[]
		start=[]
		stop=[]
		time=[]
		eslist=es.search('url1')
		n=0
		url=[]
		for i in eslist['hits']['hits']:
			url.append(i['_source']['url'])
			n+=1
		btxt=[]
		o=0
		for i in url:
			start.append(timeit.default_timer())
			res = requests.get(i)
			soup = BeautifulSoup(res.content, "html.parser")
			a = soup.find_all('div')
			btxt.append(a)
			stop.append(timeit.default_timer())
			time.append(stop[o]-start[o])
			o+=1
		txt=[]
		o=0
		for i in btxt:
			start[o]=timeit.default_timer()
			txt.append("")
			stop[o]=timeit.default_timer()
			time[o]+=stop[o]-start[o]
			o+=1
		count=0
		o=0
		for i in btxt:
			start[o]=timeit.default_timer()
			for j in i:
				txt[count] = txt[count]+j.get_text()
			count+=1
			stop[o]=timeit.default_timer()
                        time[o]+=stop[o]-start[o]
			o+=1
		o=0
		for i in range(0,len(txt)):
			start[o]=timeit.default_timer()
			txt[i] = re.sub('[–\{\}\[\]\/?.,;:|\)*~`!^\–_+<>@\#$%&\\\=\(\'\"]','', txt[i])
			txt[i] = txt[i].replace('–',"")
			stop[o]=timeit.default_timer()
                        time[o]+=stop[o]-start[o]		
			o+=1
		tokens=[]
		o=0
		swlist = []
		for sw in stopwords.words("english"):
			swlist.append(sw)

		for i in txt:
			start[o]=timeit.default_timer()
			tokens.append(word_tokenize(i))
			stop[o]=timeit.default_timer()
                        time[o]+=stop[o]-start[o]
                        o+=1
		o=0
		for i in range(0,len(tokens)):
			start[o]=timeit.default_timer()	
			for j in tokens[i]:
				if(j.lower() in swlist):
					tokens[i].remove(j)
			stop[o]=timeit.default_timer()
                        time[o]+=stop[o]-start[o]
                        o+=1
		o=0
		for i in range(0,len(tokens)):
			start[o]=timeit.default_timer()
			for j in tokens[i]:
				if(j.lower() in swlist):
					tokens[i].remove(j)
			stop[o]=timeit.default_timer()
                        time[o]+=stop[o]-start[o]
                        o+=1
		o=0
		d = []
		for i in range(0,count):
			d.append({})
		for i in range(0,count):
			start[o]=timeit.default_timer()  
			for word in tokens[i]:
				if word in d[i]:
					d[i][word] = d[i][word]+1
				else:
					d[i][word] = 1
			stop[o]=timeit.default_timer()
                        time[o]+=stop[o]-start[o]
                        o+=1

		a={}
		body=[]
		numberofwords=[]
		o=0
		for i in range(0,count):
			start[o]=timeit.default_timer()
			sumw=0
			words=d[i].keys()
			frequencies=d[i].values()
			for num in frequencies:
				sumw+=num
			a={
				"url":url[i],	
				"word":words,
				"frequency":frequencies,
				"wholewords":sumw
			}
			numberofwords.append(sumw)
			body.append(a)
			stop[o]=timeit.default_timer()
                        time[o]+=stop[o]-start[o]
                        o+=1
		o=0
		for i in range(0,count):
			start[o]=timeit.default_timer()
			es.index(index='result', doc_type='doc', id=i, body=body[i])
			stop[o]=timeit.default_timer()
                        time[o]+=stop[o]-start[o]
                        o+=1
		e=""
		for i in range(0,count):
			e=e+"<tr><td>"+url[i]+"</td><td>"+str(numberofwords[i])+"</td><td>"+str(time[i])+"</td></tr>"

		return "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>WebSite Analyze Result Table</title></head><body><table border=1 style=\"border: 1px solid black; text-align:center;\"><th>URL</th><th>Number of Words</th><th>ProcessTime(s)</th>"+e+"</table><p><a href=\"/tfidf\" target=\"_blank\"><input type=\"submit\" value=\"TF-IDF\"></a></p><p><a href=\"/cosine\" target=\"_blank\"><input type=\"submit\" value=\"Cosine-Similarity\"></a></p><p><a href=\"/\" target=\"\"><input type =\"submit\" value = \"Go Home\"></a></form></p></body></html>"

@app.route('/', methods=['GET'])
def homepage():
	upload="<form action = \"/status\" method = \"post\" enctype =\"multipart/form-data\"><input type = \"file\" name = \"file\" /><input type = \"submit\" /></form>"

	return "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>Home</title></head><body><form action=\"/status\" method=\"post\"><p>Input URL<input type=\"text\" name=\"URL\"></p><input type=\"submit\" value=\"Analyze\"></form><p>"+upload+"</p></body></html>"

if __name__ == '__main__':
    es = Elasticsearch([{'host':"127.0.0.1", 'port':"9200"}],timeout=30)
    try:
        parser = argparse.ArgumentParser(description="")
        parser.add_argument('--listen-port',  type=str, required=True, help='REST service listen port')
        args = parser.parse_args()
        listen_port = args.listen_port
    except Exception, e:
        print('Error: %s' % str(e))

    ipaddr=commands.getoutput("hostname -I").split()[0]
    print "Starting the service with ip_addr="+ipaddr
    app.run(debug=False,host=ipaddr,port=int(listen_port))
