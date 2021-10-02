# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 21:31:49 2020

@author: msmsa
"""
from abc import ABC, abstractmethod
from swolfpy_inputdata import CommonData


class ProcessModel(ABC):
    def __init__(self, process_name, CommonDataObjct):
        if CommonDataObjct:
            self.CommonData = CommonDataObjct
        else:
            self.CommonData = CommonData()
        self.process_name = process_name

        # Read Material properties
        self.Material_Properties = self.CommonData.Material_Properties


        self.Index = self.CommonData.Index

    @property
    @abstractmethod
    def Process_Type(self):
        pass

    @abstractmethod
    def calc(self):
        pass

    @abstractmethod
    def setup_MC(self, seed=None):
        pass

    @abstractmethod
    def MC_calc(self):
        pass

    @abstractmethod
    def report(self):
        pass
