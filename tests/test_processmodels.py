# -*- coding: utf-8 -*-
"""
Created on Sat May  9 17:43:11 2020

@author: Mojtaba Sardarmehni

Tests for `swolfpy_processmodels` package
"""
import pytest
from swolfpy_processmodels import *
from swolfpy_inputdata import CommonData
from pathlib import Path
import pandas as pd
    
def LCA_model_helper(model):
    commondata = CommonData()
    Index = set(commondata.Index)
    Reprocessing_Index = set(commondata.Reprocessing_Index)
    
    model.calc()
    report = model.report() 
    
    assert isinstance(report,dict)
    assert 'process name' in report.keys()
    
    assert 'Waste' in report.keys()
    assert 'Technosphere' in report.keys()
    assert 'Biosphere' in report.keys()
    
    if model.Process_Type == 'Reprocessing':
        assert Reprocessing_Index.issubset(report['Waste'])    
        assert len(Reprocessing_Index) == len(report['Waste'])
        
        assert Reprocessing_Index.issubset(report['Technosphere'])
        assert len(Reprocessing_Index) == len(report['Technosphere'])
        
        assert Reprocessing_Index.issubset(report['Biosphere'])
        assert len(Reprocessing_Index) == len(report['Biosphere'])
        
    else:
        assert Index.issubset(report['Waste'])
        assert len(Index) == len(report['Waste'])
        
        assert Index.issubset(report['Technosphere'])
        assert len(Index) == len(report['Technosphere'])
        
        assert Index.issubset(report['Biosphere'])
        assert len(Index) == len(report['Biosphere'])
    
    model.setup_MC()
    model.MC_calc()
    report=model.report()
    report1=model.report()
    assert report == report1

def test_LF():
    assert LF.Process_Type == 'Treatment'
    LCA_model_helper(LF())
    
def test_WTE():
    assert WTE.Process_Type == 'Treatment'
    LCA_model_helper(WTE())
    
def test_Composting():
    assert Comp.Process_Type == 'Treatment'
    LCA_model_helper(Comp())

def test_AD():
    assert AD.Process_Type == 'Treatment'
    LCA_model_helper(AD())

def test_SS_MRF():
    assert SS_MRF.Process_Type == 'Treatment'
    LCA_model_helper(SS_MRF())
    
def test_Reproc():
    assert Reproc.Process_Type == 'Reprocessing'
    LCA_model_helper(Reproc())
    
def test_SF_Col():
    assert SF_Col.Process_Type == 'Collection'
    col_scheme=SF_Col.scheme()
    col_scheme['RWC']['Contribution']=1
    col_scheme['RWC']['separate_col']['SSR']=1
    col_scheme['RWC']['separate_col']['SSYW']=1
    LCA_model_helper(SF_Col('SF_test',Collection_scheme=col_scheme))
    
def test_Distance():
    # Using csv as input
    dist = Distance(path=Path(__file__).parent/'Distance.csv')
    assert dist.Distance[('P1','P2')] == 20
    assert dist.Distance[('P3','P1')] == 30
    assert dist.Distance[('P2','P3')] == dist.Distance[('P3','P2')]
    
    # Using pandas Dataframe as input
    Processes = ['LF','WTE','AD']
    Data = pd.DataFrame([[None,20,30],[None,None,10],[None,None,None]],index=Processes,columns=Processes)
    distance = Distance(Data=Data)
    assert distance.Distance[('LF','WTE')] == 20
    
    