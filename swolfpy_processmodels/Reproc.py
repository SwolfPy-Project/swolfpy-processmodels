# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 21:46:21 2020

@author: msardar2
"""
from .ProcessModel import ProcessModel
from swolfpy_inputdata import Reproc_Input


class Reproc(ProcessModel):
    Process_Type = 'Reprocessing'
    def __init__(self,process_name='Reproc', input_data_path=None, CommonDataObjct=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData= Reproc_Input(input_data_path, process_name=self.process_name, CommonDataObjct=CommonDataObjct)

    def calc(self):
        self.Biosphere = {}
        self.Technosphere = {}
        self.Waste={}

        for act in self.CommonData.Reprocessing_Index:
            self.Biosphere[act] = {}
            self.Technosphere[act] = {}
            self.Waste[act] = {}
            if act in self.InputData.Input_dict.keys():
                for exchange in self.InputData.Input_dict[act].keys():
                    if exchange[0] == 'Technosphere':
                        self.Technosphere[act][exchange]=self.InputData.Input_dict[act][exchange]['amount']
                    elif exchange[0] == 'biosphere3':
                        self.Biosphere[act][exchange]=self.InputData.Input_dict[act][exchange]['amount']

        #self.LCI = self.Reprocessing.read_output_from_SWOLF('ReProc',Path(__file__).parent.parent/"Data/Material_Reprocessing_BW2.csv")

    def setup_MC(self,seed=None):
        self.InputData.setup_MC(seed)

    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        self.calc()
        return(input_list)


    def report(self):
        self.REPROC = {}
        self.REPROC["process name"] = (self.process_name, self.Process_Type, self.__class__)
        self.REPROC["Biosphere"] = self.Biosphere
        self.REPROC["Technosphere"] = self.Technosphere
        self.REPROC["Waste"]= self.Waste
        return(self.REPROC)
