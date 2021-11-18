# -*- coding: utf-8 -*-
"""
Created on Wed Nov 10 17:08:02 2021

@author: msardar2
"""
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from time import time
from swolfpy_processmodels import LF

A = LF()
start = time()
for i in range(100):
    A.calc()
    #A._Leachate()
    #A._Cal_LFG_Col_Ox()
print(round(time()-start, 2))



start = time()
for i in range(1000):
    A.LFG['Total Methane Emitted'].values / A.LFG['Total generated Methane'].apply(lambda x: 1 if x <=0 else x).values
print(time()-start)



start = time()
for i in range(1000):
    np.divide(A.LFG['Total Methane Emitted'].values,
                  A.LFG['Total generated Methane'].values,
                  out=np.zeros_like(A.LFG['Total generated Methane'].values),
                  where=A.LFG['Total generated Methane'].values!=0.0)
print(time()-start)



start = time()
for i in range(100):
    c= (A._param2['L0'].values.reshape(44, 1)
    * A._param2['solid Content'].values.reshape(44, 1)
    * (np.e**(-A._param2['k'].values.reshape(44, 1) * np.arange(A.timescale))
       - np.e**(-A._param2['k'].values.reshape(44, 1) * np.arange(1, A.timescale + 1))))
print(time()-start)














start = time()
for i in range(10000):
    A = np.arange(3000)
    flter1 = A >=1000
    flter2 = A > 2000
    A[flter1] = 400
    A[flter2] = 300
print(time()-start)


start = time()
for i in range(10000):
    A = np.arange(3000)
    flter1 = np.logical_and( A >=1000, A <=2000)
    flter2 = A > 2000
    A[flter1] = 400
    A[flter2] = 300
print(time()-start)

































