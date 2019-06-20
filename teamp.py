#!/usr/bin/python
#-*- coding: utf-8 -*-
import sys
import re
import requests
import argparse
import commands
import operator
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

app = Flask(__name__)

@app.route('/status2',methods=['POST'])
def status2():
	if request.method == 'POST':
		Input = request.form['URL']
		url1=Input
		success=1
		
		try:
			res = requests.get(url1)
		except:
			success=0
		
		successstatus="O"
		duplicationstatus="X"
		reason=""
		if(success==0):
			successstatus="X"
			reason="URL is not available"
		
		status = "<tr><td>" + Input + "</td><td>" + successstatus + "</td><td>" + reason + "</td><td>" + duplicationstatus  + "</td></tr>"
		
		return "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>Status text Box</title></head><body><p>Status Text Box</p><table border=1 style=\"border: 1px solid black; text-align:center;\"><th>URL</th><th>SuccessStatus</th><th>Reason</th><th>DuplicationStatus</th>" + status+ "</table><form action = \"/result\" method = \"post\"><input type =\"submit\" value = \"OK\"></form></body></html>"

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
			print "except 들어옴"

		global es
		eslist=[]
		eslist=es.search('*')
		n=0
		for i in eslist['hits']['hits']:
			url.append(i['_source']['url'])
			n+=1
			
		count=len(url)
		print n
		print count
		print ncount
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
			if(successstatuses[i]=="O"):
				body.append(a)
			else:
				ncount-=1

		for i in range(0,ncount):
			es.index(index='team1',doc_type='doc',id=n+i,body=body[i])
		
		return "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>Status text Box</title></head><body><p>Status Text Box</p><table border=1 style=\"border: 1px solid black; text-align:center;\"><th>URL</th><th>SuccessStatus</th><th>Reason</th><th>DuplicationStatus</th>" + status+ "</table><form action = \"/result\" method = \"post\"><input type =\"submit\" value = \"OK\"></form></body></html>"

@app.route('/result2', methods=['POST'])
def file():
	if request.method == 'POST':
		

		return "boy"


@app.route('/result', methods=['POST'])
def URL():
        if request.method == 'POST':
		global url1
		global success
		Input = url1
		res = requests.get(Input)
		soup = BeautifulSoup(res.content, "html.parser")
		a = soup.find_all('div')
		txt=""
		for i in a:
			txt = txt+i.get_text()
		txt = clean_text(txt)
		tokens = word_tokenize(txt)
		
		d = {}
		for word in tokens:
			if word in d:
				d[word] = d[word]+1
			else:
				d[word] = 1
		d = sorted(d.items(), key = operator.itemgetter(1,0),reverse=True)

		e=""
		key=""
		value=""
		for i in range(0,10):
			key=str(d[i][0])
			value=str(d[i][1])
			e=e+"<tr><td>"+key+"</td><td>"+value+"</td></tr>"

		return "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>Post</title></head><body><form action=\"/result\" method=\"post\"><p>Input URL<input type=\"text\" name=\"URL\"></p><input type=\"submit\" value=\"Analyze\"></form>"+"<table><th>Word</th><th>Frequency</th>"+e+"</table></body></html>"

@app.route('/', methods=['GET'])
def homepage():
	upload="<form action = \"/status\" method = \"post\" enctype =\"multipart/form-data\"><input type = \"file\" name = \"file\" /><input type = \"submit\" /></form>"

	return "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><title>Post</title></head><body><form action=\"/status\" method=\"post\"><p>Input URL<input type=\"text\" name=\"URL\"></p><input type=\"submit\" value=\"Analyze\"></form>"+upload+"</body></html>"

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
