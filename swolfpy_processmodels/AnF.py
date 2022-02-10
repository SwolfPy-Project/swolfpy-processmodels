# -*- coding: utf-8 -*-
"""
Created on Thu Jan  6 12:48:05 2022

@author: msardar2
"""
from .ProcessModel import ProcessModel
from swolfpy_inputdata import AnF_Input
from .Common_subprocess import Flow, LCI
from .MRF_subprocess import Drum_Feeder, Sorting, Shredder, Sterilizer, Dewater, Dryer, Pelletizer
from .MRF_subprocess import Conveyor, Electricity
import numpy_financial as npf
import numpy as np


class AnF(ProcessModel):
    Process_Type = 'Treatment'
    def __init__(self, process_name='Animal Feed', input_data_path=None, CommonDataObjct=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData = AnF_Input(input_data_path=input_data_path,
                                  process_name=self.process_name,
                                  CommonDataObjct=CommonDataObjct)

        self.Assumed_Comp = self.InputData.process_data['Assumed_Comp']

        self.process_data = self.InputData.process_data

        self.flow_init = Flow(self.Material_Properties)

    def calc(self):
        self.LCI = LCI(index=self.Index)

        # Initial mass at tipping floor
        self._Input = np.array(self.Assumed_Comp)

        # Drum Feeder
        self._DF_feed = Drum_Feeder(self._Input, self.InputData, self.LCI)

        # Disk Screen
        self._DS_rmnd, self._DS_rmvd = Sorting(Input=self._DF_feed,
                                               sep_eff=self.process_data['Disk Screen'].values/100,
                                               InputData=self.InputData,
                                               Eqpt_data=self.InputData.Eq_DS,
                                               LCI=self.LCI)

        # Manual Sorting
        self._MS_rmnd, self._MS_rmvd = Sorting(Input=self._DS_rmnd,
                                               sep_eff=self.process_data['Manual Sort (Negative)'].values/100,
                                               InputData=self.InputData,
                                               Eqpt_data=self.InputData.Eq_Neg_Sort,
                                               LCI=self.LCI)

        self.LCI.add('Other_Residual', self._MS_rmvd + self._DS_rmvd)

        # Shredding/Grinding
        self._Shred = Shredder(Input=self._MS_rmnd,
                              InputData=self.InputData,
                              LCI=self.LCI)

        # Sterlizing
        self._Sterilized = Sterilizer(Input=self._Shred,
                                      InputData=self.InputData,
                                      LCI=self.LCI)

        # Dewatering
        self._Dewatered, self._waste_water = Dewater(
            Input=self._Sterilized,
            InputData=self.InputData,
            MaterialProperties=self.Material_Properties,
            LCI=self.LCI)

        if self.InputData.AnF_operation['isDried']['amount']:
            # Pelletizing
            self._Pellet = Pelletizer(Input=self._Dewatered,
                                  InputData=self.InputData,
                                  LCI=self.LCI)

            # Drier
            self._Dried = Dryer(Input=self._Pellet,
                          InputData=self.InputData,
                          LCI=self.LCI)

        # conveyor
        self._Mass_toConveyor = (
            self._DS_rmnd
            + self._MS_rmnd
            + self._Shred
            + self._Sterilized
            + self._Dewatered)

        if self.InputData.AnF_operation['isDried']['amount']:
            self._Mass_toConveyor += (
                self._Pellet
                + self._Dried)
        Conveyor(self._Mass_toConveyor, self.InputData, self.LCI)

        # Solid content of Feed
        if self.InputData.AnF_operation['isDried']['amount']:
            self._Feed_sol = (
                self._Dried
                * (1 - self.InputData.AnF_operation['Dried_moist']['amount']))
        else:
            self._Feed_sol = (
                self._Dewatered
                * (1 - self.InputData.AnF_operation['Dew_moist']['amount']))

        # Calculating avoided feed production

        # Mositure content of avoided maize grain is 14%
        # Source: maize grain, feed production, RoW - Ecoinvent
        self._avoid_feed = (self._Feed_sol / 0.86
                            * self.InputData.AnF_operation['FeedSubFac']['amount'])

        self.LCI.add(('Technosphere', 'Feed_Production'), -self._avoid_feed * 1000)  # Mg to kg

        # Wastewater treatment
        total_BOD = (
            self._waste_water
            * 1000  # 1000L/Mg
            * self.InputData.Wastewater['BOD_conc']['amount']
            / 1000) # kg/1000gr

        BOD_removed = (
            total_BOD
            * self.CommonData.WWT['bod_rem']['amount'] / 100)

        self._BOD_elec = (
            BOD_removed
            * self.InputData.Wastewater['BOD_elec']['amount'])

        self._BOD_CO2 = (
            BOD_removed
            * self.InputData.Wastewater['BOD_CO2']['amount'])

        self.LCI.add(('Technosphere', 'Electricity_consumption'), self._BOD_elec)
        self.LCI.add('Bio-CO2 emissions from wastewater treatment', self._BOD_CO2)

        # General Electricity
        Electricity(self._Input, self.InputData, self.LCI)

        # Capital Cost
        Land_req = self.InputData.Electricity['Area_rate']['amount'] * self.InputData.Constr_cost['Land_req_factor']['amount']
        Land_cost = Land_req * self.InputData.Constr_cost['Land_rate']['amount'] / 4046.86  # 1acr = 4046.86 m2
        Constr_cost =  Land_req * (self.InputData.Constr_cost['Paving_rate']['amount'] +
                                   self.InputData.Constr_cost['Grading_rate']['amount']) / 10000  # 1ha = 10000m2
        Constr_cost += (self.InputData.Electricity['Area_rate']['amount'] * self.InputData.Constr_cost['Constr_rate']['amount'] / 0.0929)  # 1ft2 = 0.0929 m2
        Constr_cost *= (1 + self.InputData.Constr_cost['Eng_rate']['amount'])

        Miscellaneous_Costs = (self.InputData.Constr_cost['Landscaping_rate']['amount'] / 10000 * Land_req) # 1 ha = 10000m2

        # Assumes fenc along three sides of square
        Miscellaneous_Costs += np.sqrt(Land_req * 156) * 3 * self.InputData.Constr_cost['Fencing_Rate']['amount'] / 156

        # Total capital cost
        Unit_capital_cost = Land_cost + Constr_cost +  Miscellaneous_Costs  # $/tpd
        Unit_capital_cost /= self.InputData.Labor['Day_year']['amount']  # $/t.yr
        capital_cost = -npf.pmt(rate=self.InputData.Constr_cost['Inerest_rate']['amount'],
                        nper=self.InputData.Constr_cost['lifetime']['amount'],
                        pv=Unit_capital_cost)
        self.LCI.add(('biosphere3', 'Capital_Cost'), capital_cost * self._Input)

    def setup_MC(self, seed=None):
        self.InputData.setup_MC(seed)

    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        self.calc()
        return(input_list)

    def report(self):
        report = {}
        report["process name"] = (self.process_name, self.Process_Type, self.__class__)
        report["Waste"] = {}
        report["Technosphere"] = {}
        report["Biosphere"] = {}

        for x in ["Waste", "Technosphere", "Biosphere"]:
            for y in self.Index:
                report[x][y] = {}

        lci_report = self.LCI.report(input_mass=self._Input)

        for y in self.Index:
            # Output Technospphere Database
            report["Technosphere"][y][('Technosphere', 'Electricity_consumption')] = lci_report[('Technosphere', 'Electricity_consumption')][y]
            report["Technosphere"][y][('Technosphere', 'Equipment_Diesel')] = lci_report[('Technosphere', 'Equipment_Diesel')][y]
            report["Technosphere"][y][('Technosphere', 'Equipment_LPG')] = lci_report[('Technosphere', 'Equipment_LPG')][y]
            report["Technosphere"][y][('Technosphere', 'Feed_Production')] = lci_report[('Technosphere', 'Feed_Production')][y]

            # Cost
            report["Biosphere"][y][('biosphere3','Operational_Cost')] = lci_report[('biosphere3','Operational_Cost')][y]
            report["Biosphere"][y][('biosphere3', 'Capital_Cost')] = lci_report[('biosphere3', 'Capital_Cost')][y]

            # Emissions
            report["Biosphere"][y][('biosphere3', 'eba59fd6-f37e-41dc-9ca3-c7ea22d602c7')] = (  # Carbon dioxide, non-fossil ('air',)
                lci_report['Bio-CO2 emissions from wastewater treatment'][y])

            # Waste products
            report["Waste"][y]['Other_Residual'] = lci_report['Other_Residual'][y]
        return report