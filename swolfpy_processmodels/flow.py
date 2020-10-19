# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 09:41:44 2019

@author: msardar2
"""
import pandas as pd


### Flow
class flow:
    def __init__(self, Material_Properties):
        self.prop = Material_Properties 
        self.data = pd.DataFrame(index=self.prop.index,
                                 columns=['mass', 'sol_cont', 'moist_cont', 'vs_cont', 'ash_cont'])
### Update flow        
    def update(self, assumed_comp): 
        self.flow = sum(self.data['mass'].values * assumed_comp.values)
        self.water = sum(self.data['moist_cont'].values * assumed_comp.values)
        self.moist_cont = self.water / self.flow
        self.ash = sum(self.data['ash_cont'].values * assumed_comp.values)
        self.solid = sum(self.data['sol_cont'].values * assumed_comp.values)

### Create new flow
    def init_flow(self, massflows):
        self.data['mass'] = massflows
        self.data['sol_cont'] = self.data['mass'].values * (1 - self.prop['Moisture Content'].values / 100)
        self.data['moist_cont'] = self.data['mass'].values * (self.prop['Moisture Content'].values / 100)
        self.data['vs_cont'] = self.data['sol_cont'].values * self.prop['Volatile Solids'].values / 100
        self.data['ash_cont'] = self.data['sol_cont'].values * self.prop['Ash Content'].values / 100
