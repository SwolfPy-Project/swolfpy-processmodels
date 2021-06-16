# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 11:12:21 2020

@author: msardar2
"""
import pandas as pd
import numpy as np
from copy import deepcopy
import numpy_financial as npf


class LCI():
    """
    This class store the LCI data in numpy.ndarray instead of pandas for speedup.
    Report function create pandas DataFrame and return it
    Column names are stored in self.ColDict
    """
    def __init__(self,Index):
        self.Index = Index
        self.LCI = np.zeros((len(Index),20))
        self.ColDict={}
        self.ColNumber=0

    def add(self,name,flow):
        if name not in self.ColDict:
            self.ColDict[name]=self.ColNumber
            self.ColNumber+=1
        self.LCI[:,self.ColDict[name]]+=flow

    def report(self,InputMass):
        LCI_normal = deepcopy(self.LCI)
        for j in range(len(self.ColDict)):
            LCI_normal[:,j]=self.LCI[:,j]/InputMass
        return(pd.DataFrame(LCI_normal[:,:len(self.ColDict)],columns=list(self.ColDict.keys()),index=self.Index))

    def report_T(self,InputMass):
        LCI_normal = deepcopy(self.LCI)
        for j in range(len(self.ColDict)):
            LCI_normal[:,j]=self.LCI[:,j]/InputMass
        return(pd.DataFrame(LCI_normal[:,:len(self.ColDict)].transpose(),index=list(self.ColDict.keys()),columns=self.Index))

### Resource use calculation for equipments
def calc_resource(total_throughput, remaining, removed, Eq, InputData, LCI):
    #Calculating resource use
    #Elec use = (motor_size*Frac_motor)/(max_input*frac_input)  --> unit: kW/Mg
    elec = Eq['motor']['amount'] * Eq['frac_motor']['amount']/ \
                (Eq['Max_input']['amount']*Eq['frac_MaxInput']['amount'])

    if Eq['Calc_base']['amount']==0: # 0: calculation based on the removed mass
        Aloc = (removed/sum(removed) if sum(removed)>0 else 0)
    elif Eq['Calc_base']['amount']==1: # 1: calculation based on the remaining mass
        Aloc = (remaining/sum(remaining) if sum(remaining)>0 else 0)
    elif Eq['Calc_base']['amount']==2:  # 2: calculation based on the total throughput mass
        Aloc = (total_throughput/sum(total_throughput) if sum(total_throughput)>0 else 0)
    else:
        raise ValueError('Input parameter [Calc_base] is not valid')

    elec_use =  sum(total_throughput) * elec *  Aloc
    dsl_use = sum(total_throughput) * Eq['diesel_use']['amount'] * Aloc
    LPG_use = sum(total_throughput) * Eq['LPG_use']['amount'] * Aloc

    Cap = Eq['Investment_cost']['amount'] + Eq['Installation_cost']['amount']
    Rate = InputData.Constr_cost['Inerest_rate']['amount']
    Lftime = Eq['LifeTime']['amount']
    TotalHour = InputData.Labor['Hr_shift']['amount'] * InputData.Labor['Shift_day']['amount'] * InputData.Labor['Day_year']['amount']
    # Average Cost of Ownership ($/Mg)
    AveCostOwner = (npf.pmt(Rate, Lftime, -Cap) + Eq['O&M']['amount']) / (TotalHour * Eq['Max_input']['amount']*Eq['frac_MaxInput']['amount'])

    #Laborers Required (Sorter*hours/Mg)
    LaborReq = Eq['N_Labor']['amount'] / (Eq['Max_input']['amount'] * Eq['frac_MaxInput']['amount'])
    #Drivers Required (Driver*hours/Mg)
    DriverReq = Eq['N_Driver']['amount'] / (Eq['Max_input']['amount'] * Eq['frac_MaxInput']['amount'])
    #Labor (sorter+Driver) Cost ($/Mg input)
    LaborCost = (LaborReq * InputData.Labor['Labor_rate']['amount'] + DriverReq * InputData.Labor['Driver_rate']['amount'] ) *\
                (1 + InputData.Labor['Fringe_rate']['amount']) * (1 + InputData.Labor['Management_rate']['amount'])

    TotalOMcost = sum(total_throughput) * Aloc * (AveCostOwner + LaborCost)

    # adding the resource use
    LCI.add(('Technosphere', 'Electricity_consumption'), elec_use)
    LCI.add(('Technosphere', 'Equipment_Diesel'), dsl_use)
    LCI.add(('Technosphere', 'Equipment_LPG'), LPG_use)
    LCI.add(('biosphere3', 'Operational_Cost'), TotalOMcost)

### Rolling_Stock
def Rolling_Stock(Input,InputData,LCI):
    #Equipment input
    Eq=InputData.Eq_Rolling_Stock
    #Resource use calculation
    calc_resource(Input,Input,Input,Eq,InputData,LCI)
    return(None)


### General Electricity
def Electricity(Input, InputData, LCI):
    #calculate electricity use in office and floor area
    elec_office = (Input *
                   InputData.Electricity['Area_rate']['amount'] *
                   InputData.Electricity['Frac_office']['amount'] *
                   InputData.Electricity['Elec_office']['amount'])
    elec_floor = (Input *
                  InputData.Electricity['Area_rate']['amount'] *
                  (1 - InputData.Electricity['Frac_office']['amount']) *
                  InputData.Electricity['Elec_floor']['amount'])
    LCI.add(('Technosphere', 'Electricity_consumption'), elec_office + elec_floor)
