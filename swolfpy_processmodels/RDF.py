# -*- coding: utf-8 -*-
"""
Created on Mon Sep 20 14:39:08 2021

@author: msardar2
"""
import numpy as np
import numpy_financial as npf
from swolfpy_inputdata import RDF_Input
from .Common_subprocess import LCI
from .MRF_subprocess import Flail_Mill, Trommel, Sorting, Air_Sep, Shredder, Pelletizer
from .MRF_subprocess import Optical_sorter, Densimetric_Table, Baler, Magnet_RDF
from .MRF_subprocess import ECS_RDF, Rolling_Stock, Conveyor, Electricity
from .ProcessModel import ProcessModel


class RDF(ProcessModel):
    Process_Type = 'Treatment'
    def __init__(self, process_name='RDF', input_data_path=None, CommonDataObjct=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData = RDF_Input(input_data_path, process_name=self.process_name,
                                   CommonDataObjct=CommonDataObjct)
        self.process_data = self.InputData.process_data

#%% Calc Function
    def calc(self):
        self.LCI_Waste = LCI(self.Index)
        self.LCI = LCI(self.Index)

        ### Initial mass
        self._Input = np.array([1/len(self.Index) for _ in range(len(self.Index))])

        ### Flail Mill
        self._FM_feed = Flail_Mill(Input=self._Input,
                                   InputData=self.InputData,
                                   LCI=self.LCI)

        ### Trommel Separating <2"
        self._Trml_rmnd, self._Trml_rmvd = Trommel(Input=self._FM_feed,
                                                   sep_eff=self.process_data['Trommel'].values,
                                                   InputData=self.InputData,
                                                   LCI=self.LCI)

        ### Negative Sort  for separating >24"
        self._NS_rmnd, self._NS_rmvd = Sorting(Input=self._Trml_rmnd,
                                               sep_eff=self.process_data['Negative Sort'].values,
                                               InputData=self.InputData,
                                               Eqpt_data=self.InputData.Eq_Neg_Sort,
                                               LCI=self.LCI)

        ### Air separator for separating Heavy fraction
        self._AS1_rmnd, self._AS1_rmvd = Air_Sep(Input=self._NS_rmnd,
                                                 sep_eff=self.process_data['Air Separator'].values,
                                                 InputData=self.InputData,
                                                 LCI=self.LCI)

        ### Air separator for separating Medium fraction
        self._AS2_rmnd, self._AS2_rmvd = Air_Sep(Input=self._AS1_rmnd,
                                                 sep_eff=self.process_data['Air Separator'].values,
                                                 InputData=self.InputData,
                                                 LCI=self.LCI)

        ### Magnet 1
        self._Magnet1_rmnd, self._Magnet1_rmvd = Magnet_RDF(Input=self._Trml_rmvd,
                                                            sep_eff=self.process_data['Magnet'].values,
                                                            InputData=self.InputData,
                                                            LCI=self.LCI)
        self.LCI_Waste.add('Fe', self._Magnet1_rmvd)

        ### Optical Sort (separating metals)
        self._OptSort_rmnd, self._OptSort_rmvd = Optical_sorter(Input=self._AS2_rmvd,
                                                                sep_eff=self.process_data['Optical Sorter'].values,
                                                                InputData=self.InputData,
                                                                LCI=self.LCI)

        ### Magnet 2
        self._magent_input = self._NS_rmvd +  self._OptSort_rmvd + self._AS1_rmvd
        self._Magnet2_rmnd, self._Magnet2_rmvd = Magnet_RDF(Input=self._magent_input,
                                                            sep_eff=self.process_data['Magnet'].values,
                                                            InputData=self.InputData,
                                                            LCI=self.LCI)
        self.LCI_Waste.add('Fe', self._Magnet2_rmvd)

        ### Positive sort
        self._PS_rmnd, self._PS_rmvd = Sorting(Input=self._Magnet2_rmnd,
                                               sep_eff=self.process_data['Positive Sort'].values,
                                               InputData=self.InputData,
                                               Eqpt_data=self.InputData.Eq_Pos_Sort,
                                               LCI=self.LCI)

        ### ECS
        self._ECS_rmnd, self._ECS_rmvd = ECS_RDF(Input=self._PS_rmnd,
                                                 sep_eff=self.process_data['ECS'].values,
                                                 InputData=self.InputData,
                                                 Eqpt_data=self.InputData.Eq_ECS,
                                                 LCI=self.LCI)
        self.LCI_Waste.add('Al', self._ECS_rmvd)

        ### Densimetric table
        self._DMT_rmnd, self._DMT_rmvd = Densimetric_Table(Input=self._Magnet1_rmnd,
                                                           sep_eff=self.process_data['Densimetric Table'].values,
                                                           InputData=self.InputData,
                                                           LCI=self.LCI)

        ### Organics
        if self.InputData.Products['Sep_org']['amount'] == 0:
            self._Organics = np.zeros(len(self.Index))
            self._Organics_RDF = self._DMT_rmnd
        else:
            self._Organics = self._DMT_rmnd
            self._Organics_RDF = np.zeros(len(self.Index))

        self.LCI_Waste.add('Separated_Organics', self._Organics)

        ### Shredder
        self._shredder_input = self._AS2_rmnd + self._OptSort_rmnd + self._PS_rmvd + self._Organics_RDF
        self._Shredded = Shredder(Input=self._shredder_input,
                                  InputData=self.InputData,
                                  LCI=self.LCI)

        ### Pelletizer
        self._Pelletized = Pelletizer(Input=self._Shredded,
                                      InputData=self.InputData,
                                      LCI=self.LCI)
        self.LCI_Waste.add('RDF', self._Pelletized)

        ### Baler
        self._baler_input = self._ECS_rmvd + self._Magnet1_rmvd + self._Magnet2_rmvd
        self._Baled = Baler(Input=self._baler_input,
                            InputData=self.InputData,
                            LCI=self.LCI)
        #### Residuals
        self._Residuals = self._DMT_rmvd + self._ECS_rmnd
        self.LCI_Waste.add('Other_Residual', self._Residuals)

        ### Conveyor
        # Calculate the mass carried by conveyor
        self._Mass_to_Conveyor = (
            self._Input
            + self._FM_feed
            + self._Trml_rmnd + self._Trml_rmvd
            + self._NS_rmnd + self._NS_rmvd
            + self._AS1_rmnd + self._AS1_rmvd
            + self._AS2_rmnd + self._AS2_rmvd
            + self._Magnet1_rmnd + self._Magnet1_rmvd
            + self._PS_rmnd + self._PS_rmvd
            + self._ECS_rmnd + self._ECS_rmvd
            + self._DMT_rmnd + self._DMT_rmvd
            + self._Organics_RDF + self._Organics
            + self._Shredded
            + self._Pelletized)

        # conveyor
        Conveyor(self._Mass_to_Conveyor, self.InputData, self.LCI)

        ### Rolling_Stock
        Rolling_Stock(self._Input, self.InputData, self.LCI)

        ### General Electricity
        Electricity(self._Input, self.InputData, self.LCI)

        ### Capital Cost
        Land_req = (self.InputData.Electricity['Area_rate']['amount']
                    * self.InputData.Constr_cost['Land_req_factor']['amount'])
        Land_cost = Land_req * self.InputData.Constr_cost['Land_rate']['amount'] / 4046.86  # 1acr = 4046.86 m2
        Constr_cost = Land_req * (self.InputData.Constr_cost['Paving_rate']['amount']
                                  + self.InputData.Constr_cost['Grading_rate']['amount']) / 10000  # 1ha = 10000m2
        Constr_cost += (self.InputData.Electricity['Area_rate']['amount']
                        * self.InputData.Constr_cost['Constr_rate']['amount']
                        / 0.0929)  # 1ft2 = 0.0929 m2
        Constr_cost *= (1 + self.InputData.Constr_cost['Eng_rate']['amount'])

        # Add Miscellaneous Costs based on the average size TS: 156 tpd
        Miscellaneous_Costs = (self.InputData.Constr_cost['Weigh_Station']['amount'] +
                               self.InputData.Constr_cost['Utility_Connections']['amount']) / 156  # Assume capacity of 1000 tpd
        Miscellaneous_Costs += (self.InputData.Constr_cost['Landscaping_rate']['amount']
                                / 10000 * Land_req)  # 1 ha = 10000m2
        # Assumes fenc along three sides of square
        Miscellaneous_Costs += (np.sqrt(Land_req * 156) * 3
                                * self.InputData.Constr_cost['Fencing_Rate']['amount'] / 156)

        # Total capital cost
        Unit_capital_cost = Land_cost + Constr_cost +  Miscellaneous_Costs  # $/tpd
        Unit_capital_cost /= self.InputData.Labor['Day_year']['amount']  # $/t.yr
        capital_cost = -npf.pmt(rate=self.InputData.Constr_cost['Inerest_rate']['amount'],
                                nper=self.InputData.Constr_cost['lifetime']['amount'],
                                pv=Unit_capital_cost)
        self.LCI.add(('biosphere3', 'Capital_Cost'), capital_cost * self._Input)

#%% Check Mass balance
        ### Check mass balance:
        mass_out = self.LCI_Waste.lci.sum(axis=1)
        for i in range(len(self.Index)):
            if abs(mass_out[i] - self._Input[i]) > 0.01:
                raise ValueError('*** Mass Balance Error *** \n Output mass is not equal to input mass!')

#%% Report
    ### Report
    def report(self):
        ### Output
        self.RDF = {}
        self.RDF["process name"] = (self.process_name, self.Process_Type, self.__class__)

        # Waste
        self.RDF["Waste"] = self.LCI_Waste.report(input_mass=self._Input, transpose=True).to_dict()

        # Technosphere
        tech_index = [x for x in self.LCI.col_dict.keys() if 'biosphere3' not in x]
        self.RDF["Technosphere"] = self.LCI.report(input_mass=self._Input, transpose=True).loc[tech_index, :].to_dict()


        # Biosphere
        bio_index = [x for x in self.LCI.col_dict.keys() if 'biosphere3' in x]
        self.RDF["Biosphere"] = self.LCI.report(input_mass=self._Input, transpose=True).loc[bio_index, :].to_dict()
        return self.RDF

#%% Monte Carlo
    ### setup for Monte Carlo simulation
    def setup_MC(self, seed=None):
        self.InputData.setup_MC(seed)

    ### Calculate based on the generated numbers
    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        self.calc()
        return input_list
