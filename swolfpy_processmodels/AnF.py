# -*- coding: utf-8 -*-
"""
Created on Thu Jan  6 12:48:05 2022

@author: msardar2
"""
from .ProcessModel import ProcessModel
from swolfpy_inputdata import AnF_Input

from .Common_subprocess import Flow, LCI

from .Comp_subprocess import ac_comp, shredding, screen, mix, add_water, vacuum, post_screen, curing

from .MRF_subprocess import Drum_Feeder, Man_Sort1, Vacuum, DS1, DS2, DS3, MS2_DS2, MS2_DS3
from .MRF_subprocess import Baler_1Way, Baler_2Way, GBS, AK, OG, MS3_G, Glass_type, OPET, MS4_Al, MS4_Fe, MS4_HDPE, MS4_PET, MS5
from .MRF_subprocess import HDPE_type, Magnet, ECS, Rolling_Stock, Conveyor, Mixed_paper_separation, Electricity, OHDPE

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

        # Manual Sort 1 (Negative)
        self._MS1_rmnd, self._MS1_rmvd = Man_Sort1(self._DF_feed,
                                                   self.process_data['Manual Sort 1 (Negative)'].values,
                                                   self.InputData,
                                                   self.LCI)

        # Secondary Pre_screen
        self.S2_to_shredding, self.S2_residuls = screen(input_flow=self.S1_overs,
                                                        sep_eff=self.process_data['Pre Screen 2'].values/100,
                                                        Op_param=self.InputData.Screen,
                                                        lci=self.LCI,
                                                        flow_init=self.flow_init)

        # Shredding/Grinding of seconday screen's unders
        self.shred = shredding(self.S2_to_shredding,
                               self.InputData.Shredding,
                               self.LCI,
                               self.flow_init)

# =============================================================================
#         # Mixing the shredded and screened materials
#         self.mixed = mix(self.S1_unders,
#                          self.shred,
#                          self.flow_init)
# 
#         # Adding Water
#         self.mixed.update(self.Assumed_Comp)
#         if self.mixed.moist_cont > self.InputData.Deg_Param['initMC']['amount']:
#             self.water_added = 0
#         else:
#             self.water_added = ((self.InputData.Deg_Param['initMC']['amount']
#                                  * self.mixed.flow - self.mixed.water)
#                                 / (1 - self.InputData.Deg_Param['initMC']['amount']))
# 
#         water_flow = (self.water_added * self.mixed.data['sol_cont'].values
#                       / self.mixed.solid)
# 
#         self.substrate_to_ac = add_water(self.mixed,
#                                          water_flow,
#                                          self.Material_Properties,
#                                          self.process_data,
#                                          self.flow_init)
# 
#         # Active Composting
#         self.substrate_to_ps = ac_comp(self.substrate_to_ac,
#                                        self.CommonData,
#                                        self.process_data,
#                                        self.InputData,
#                                        self.Assumed_Comp,
#                                        self.LCI,
#                                        self.flow_init)
# 
#         # Post screen
#         self.substrate_to_vac, self.ps_res = post_screen(self.substrate_to_ps,
#                                                          self.process_data['Post Screen'].values/100,
#                                                          self.InputData.Screen,
#                                                          self.LCI,
#                                                          self.flow_init)
# 
# =============================================================================
    def setup_MC(self, seed=None):
        self.InputData.setup_MC(seed)

    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        self.calc()
        return(input_list)

    def report(self):
        report = {}
        report["process name"] = (self.process_name, self.Process_Type, self.__class__)
        return report