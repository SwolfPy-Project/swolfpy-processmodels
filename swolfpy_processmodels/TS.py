# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 11:51:31 2021

@author: msardar2
"""
import numpy as np
import numpy_financial as npf
from swolfpy_inputdata import TS_Input
from .TS_subprocess import LCI, Electricity, Rolling_Stock
from .ProcessModel import ProcessModel


class TS(ProcessModel):
    Process_Type = 'Transfer_Station'
    def __init__(self,process_name='TS', input_data_path=None, CommonDataObjct=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData= TS_Input(input_data_path, process_name=self.process_name, CommonDataObjct=CommonDataObjct)

        self._Extened_Index = []
        for i in ['ORG', 'DryRes', 'REC', 'WetRes']:
            for j in self.Index:
                self._Extened_Index.append(i + '_' + j)

#%% Calc Function
    def calc(self):
        n = len(self._Extened_Index)
        self.LCI_Waste = LCI(self._Extened_Index)
        self.LCI = LCI(self._Extened_Index)

        ### Initial mass
        self._Input = np.array([1/n] * n)

        ### Rolling_Stock
        Rolling_Stock(self._Input, self.InputData, self.LCI)

        self._organics = np.zeros(n)
        self._residuals = np.zeros(n)
        self._recyclables = np.zeros(n)
        for i, j in enumerate(self._Extened_Index):
            if 'DryRes' == j[0:6] or 'WetRes' == j[0:6]:
                self._residuals[i] = 1 / n
            elif 'ORG'==j[0:3]:
                self._organics[i] = 1 / n
            elif 'REC'==j[0:3]:
                self._recyclables[i] = 1 / n

        self.LCI_Waste.add('Other_Residual', self._residuals)
        self.LCI_Waste.add('Separated_Organics', self._organics)
        self.LCI_Waste.add('Separated_Recyclables', self._recyclables)

        ### General Electricity
        Electricity(self._Input, self.InputData, self.LCI)

        ### Capital Cost
        Land_req =  self.InputData.Electricity['Area_rate']['amount'] * self.InputData.Constr_cost['Land_req_factor']['amount']
        Land_cost = Land_req * self.InputData.Constr_cost['Land_rate']['amount'] / 4046.86  # 1acr = 4046.86 m2
        Constr_cost =  Land_req * (self.InputData.Constr_cost['Paving_rate']['amount'] +
                                   self.InputData.Constr_cost['Grading_rate']['amount']) / 10000  # 1ha = 10000m2
        Constr_cost += (self.InputData.Electricity['Area_rate']['amount'] * self.InputData.Constr_cost['Constr_rate']['amount'] / 0.0929)  # 1ft2 = 0.0929 m2
        Constr_cost *= (1 + self.InputData.Constr_cost['Eng_rate']['amount'])

        # Add Miscellaneous Costs based on the average size TS: 1000 tpd
        Miscellaneous_Costs = (self.InputData.Constr_cost['Weigh_Station']['amount'] +
                               self.InputData.Constr_cost['Utility_Connections']['amount']) / 1000  # Assume capacity of 1000 tpd
        Miscellaneous_Costs += (self.InputData.Constr_cost['Landscaping_rate']['amount'] / 10000 * Land_req) # 1 ha = 10000m2
        # Assumes fenc along three sides of square
        Miscellaneous_Costs += np.sqrt(Land_req * 1000) * 3 * self.InputData.Constr_cost['Fencing_Rate']['amount'] / 1000

        # Total capital cost
        Unit_capital_cost = Land_cost + Constr_cost +  Miscellaneous_Costs  # $/tpd
        Unit_capital_cost /= self.InputData.Labor['Day_year']['amount']  # $/t.yr
        capital_cost = -npf.pmt(rate=self.InputData.Constr_cost['Inerest_rate']['amount'],
                        nper=self.InputData.Constr_cost['lifetime']['amount'],
                        pv=Unit_capital_cost)
        self.LCI.add(('biosphere3', 'Capital_Cost'), capital_cost * self._Input)


#%% Report
    ### Report
    def report(self):
        ### Output
        self.SS_MRF = {}
        self.SS_MRF["process name"] = (self.process_name, self.Process_Type, self.__class__)

        # Waste
        #self.waste_DF = self.LCI_Waste.report(self._Input)
        #self.SS_MRF["Waste"] = self.waste_DF.transpose().to_dict()
        self.SS_MRF["Waste"] = self.LCI_Waste.report_T(self._Input).to_dict()

        # Technosphere
        tech_index = [x for x in self.LCI.ColDict.keys() if 'biosphere3' not in x]
        self.SS_MRF["Technosphere"] = self.LCI.report_T(self._Input).loc[tech_index,:].to_dict()


        # Biosphere
        bio_index = [x for x in self.LCI.ColDict.keys() if 'biosphere3' in x]
        self.SS_MRF["Biosphere"] = self.LCI.report_T(self._Input).loc[bio_index,:].to_dict()
        return(self.SS_MRF)

#%% Monte Carlo
    ### setup for Monte Carlo simulation
    def setup_MC(self,seed=None):
        self.InputData.setup_MC(seed)

    ### Calculate based on the generated numbers
    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        self.calc()
        return(input_list)
