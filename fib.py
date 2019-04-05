#!/usr/bin/python

num = int(raw_input("Enter a number for fibonacci: "))
num = num-2

arr = [1, 1]

if num>0:
  for i in range(0,num):
    arr.append(arr[-1] + arr[-2])

print "answer: ", arr[-1]
