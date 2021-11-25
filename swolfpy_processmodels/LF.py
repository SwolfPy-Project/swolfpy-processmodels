# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 11:07:56 2019

@author: msardar2
"""
import numpy as np
import pandas as pd
from .ProcessModel import ProcessModel
from swolfpy_inputdata import LF_Input
from copy import deepcopy


class LF(ProcessModel):
    Process_Type = 'Treatment'
    def __init__(self, process_name='LF', input_data_path=None, CommonDataObjct=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData = LF_Input(input_data_path,
                                 process_name=self.process_name,
                                 CommonDataObjct=CommonDataObjct)

        self.process_data = self.InputData.process_data

        self.gas_emission_factor = self.InputData.gas_emission_factor

        self.lcht_Qlty = self.InputData.lcht_Qlty

        self.GasColPlan = self.InputData.GasColPlan

        self.timescale = 301

    # Landfill Gas Collection Efficiency
    def _Cal_LFG_Col_Ox(self):
        self._n = int(self.InputData.LF_Op['optime']['amount'])

        self._plan = {0: 'Typical',
                      1: 'Best Case',
                      2: 'Worst Case',
                      3: 'California'}[self.InputData.LFG_param['LFG_col_plan']['amount']]

        # Parameters for LF operation (timing for LFG collection)
        index_n = np.arange(self._n)
        index_t = np.arange(self.timescale)
        self._param1 = pd.DataFrame(index=index_n)

        # Parameters for LF operation (timing for LFG collection)
        t = (self.GasColPlan.loc['initColTime', self._plan]
             - np.mod(index_n, self.GasColPlan.loc['cellFillTime', self._plan]))
        t[t < 0] = 0
        self._param1['Time to initial collection'] = t

        self._param1['Time to interim cover'] = (
            self.GasColPlan.loc['cellFillTime', self._plan]
            - np.mod(index_n, self.GasColPlan.loc['cellFillTime', self._plan]))

        self._param1['Time to long term cover'] = (
            self.GasColPlan.loc['incColTime', self._plan]
            - np.mod(index_n, self.GasColPlan.loc['cellFillTime', self._plan]))

        self.LFG_Coll_Eff = np.zeros((self.timescale, self._n))

        xx, yy = np.mgrid[0:self.timescale, 0:self._n]
        filter_FCover = xx + yy >= self.GasColPlan.loc['timeToFinCover', self._plan] + self.InputData.LF_Op['optime']['amount']
        filter_IncCover = xx >= self._param1['Time to long term cover'].values
        filter_IntCover = xx >= self._param1['Time to interim cover'].values
        filter_InitCover = xx >= self._param1['Time to initial collection'].values

        self.LFG_Coll_Eff[filter_InitCover] = self.InputData.LFG_param['initColEff']['amount']
        self.LFG_Coll_Eff[filter_IntCover] = self.InputData.LFG_param['intColEff']['amount']
        self.LFG_Coll_Eff[filter_IncCover] = self.InputData.LFG_param['incColEff']['amount']
        self.LFG_Coll_Eff[filter_FCover] = self.InputData.LFG_param['finColEff']['amount']

        self._potential_LFG = pd.DataFrame(index=index_t)
        self._potential_LFG['Average Collection Eff'] = self.LFG_Coll_Eff.mean(axis=1)

        k = self.InputData.LFG_param['actk']['amount']

        decay_rate = (self.InputData.LFG_param['base_L0']['amount']
            * (np.e**(-k * index_t)
               - np.e**(-k * np.arange(1, self.timescale + 1))))

        dumped_waste = np.concatenate((np.full(self._n - 1, self.InputData.LF_Op['annWaste']['amount']),
                                       np.full(self.timescale - self._n + 1, 0)))

        methane_gen = []
        methane_col = []

        for i in index_t:
            methane_gen.append(sum(dumped_waste[i::-1] * decay_rate[0:i+1]))
            methane_col.append(
                sum(dumped_waste[i::-1]
                * decay_rate[0:i+1]
                * self._potential_LFG['Average Collection Eff'].values[0:i+1] / 100))

        lfg_cfm = (methane_col
                   / self.InputData.LFG_param['ch4prop']['amount']
                   / 365 / 24 / 60  # yr to min
                   * 35.3147)  # m3 to ft3

        NMOC_CutOn = (methane_gen
                      / self.InputData.LFG_param['ch4prop']['amount']
                      * 10**3  # m3 --> L
                      * self.InputData.Flare['NMOC_Conc']['amount'] / 10**6  # ppmv
                      / 0.08206  # L.atm --> K.mol
                      / (273.15 + self.InputData.Flare['Temp']['amount'])
                      * self.InputData.Flare['NMOC_MW']['amount']
                      / 10**6)  # g --> Mg

        NMOC_CutOff = (methane_col
                      / self.InputData.LFG_param['ch4prop']['amount']
                      * 10**3  # m3 --> L
                      * self.InputData.Flare['NMOC_Conc_actual']['amount'] / 10**6  # ppmv
                      / 0.08206  # L.atm --> K.mol
                      / (273.15 + self.InputData.Flare['Temp']['amount'])
                      * self.InputData.Flare['NMOC_MW']['amount']
                      / 10**6)  # g --> Mg

        self.GasColPlan.loc['enrgOn', self._plan] = 10000
        self.GasColPlan.loc['enrgOff', self._plan] = 0
        if self.InputData.Energy_Rec['enrgRecovered']['amount'] == 1:
            lfg_ok = np.where(lfg_cfm >= self.InputData.Energy_Rec['MinFowRec']['amount'])[0]
            if len(lfg_ok):
                self.GasColPlan.loc['enrgOn', self._plan] = (
                        lfg_ok[0] + self.InputData.Energy_Rec['RecInstallTime']['amount'])
                lfg_low = np.where(lfg_cfm[lfg_ok[0]:] <= self.InputData.Energy_Rec['MinFowRec']['amount'])[0]
                if len(lfg_low):
                    if lfg_ok[0] + lfg_low[0] > (self.GasColPlan.loc['enrgOn', self._plan]
                                                 + self.InputData.Energy_Rec['MinYrRec']['amount']):
                        self.GasColPlan.loc['enrgOff', self._plan] = lfg_ok[0] + lfg_low[0]
                    else:
                        self.GasColPlan.loc['enrgOff', self._plan] = (
                            self.GasColPlan.loc['enrgOn', self._plan]
                            + self.InputData.Energy_Rec['MinYrRec']['amount']
                            + 1)
                else:
                   self.GasColPlan.loc['enrgOff', self._plan] = self.timescale

        self.GasColPlan.loc['flareOn', self._plan] = 10000
        self.GasColPlan.loc['flareOff', self._plan] = (self.InputData.LF_Op['optime']['amount']
                                                       + self.InputData.Flare['TimeReq']['amount'])

        NMOC_high = np.where(NMOC_CutOn >= self.InputData.Flare['NMOC_Cufoff']['amount'])[0]
        if len(NMOC_high):
            self.GasColPlan.loc['flareOn', self._plan] = NMOC_high[0]
            self.GasColPlan.loc['flareOff', self._plan] = NMOC_high[0] + self.InputData.Flare['MinYr']['amount']
            if self.GasColPlan.loc['flareOff', self._plan] < (self.InputData.LF_Op['optime']['amount']
                                                              + self.InputData.Flare['TimeReq']['amount']):
                self.GasColPlan.loc['flareOff', self._plan] = (
                    self.InputData.LF_Op['optime']['amount']
                    + self.InputData.Flare['TimeReq']['amount'])


        if NMOC_CutOff[int(self.GasColPlan.loc['flareOff', self._plan])] > self.InputData.Flare['NMOC_Cufoff']['amount']:
            NMOC_low = np.where(NMOC_CutOff[int(self.GasColPlan.loc['flareOff', self._plan] + 1):] <= self.InputData.Flare['NMOC_Cufoff']['amount'])[0]
            if len(NMOC_low):
                self.GasColPlan.loc['flareOff', self._plan] +=  1 + NMOC_low[0]
            else:
                self.GasColPlan.loc['flareOff', self._plan] = self.timescale

        if self.InputData.Flare['Flow_cutoff']['amount']:
            if lfg_cfm[int(self.GasColPlan.loc['flareOff', self._plan])] > self.InputData.Flare['Flow_req']['amount']:
                NMOC_flow_low = np.where(lfg_cfm[int(self.GasColPlan.loc['flareOff', self._plan] + 1):] < self.InputData.Flare['Flow_req']['amount'])[0]
                if len(NMOC_flow_low):
                    self.GasColPlan.loc['flareOff', self._plan] += 1 + NMOC_flow_low[0]
                else:
                    self.GasColPlan.loc['flareOff', self._plan] = self.timescale

        # Report in DF
        self._potential_LFG['waste Mg/year'] = dumped_waste
        self._potential_LFG['Methane Generated m3/year'] = methane_gen
        self._potential_LFG['Methane Collected m3/year'] = methane_col
        self._potential_LFG['LFG Collected cfm'] = lfg_cfm
        self._potential_LFG['NMOC CutOn Mg/yr'] = NMOC_CutOn
        self._potential_LFG['NMOC CutOff Mg/yr'] = NMOC_CutOff

        # Collection efficiency
        filter_Off = xx + yy >= max(self.GasColPlan.loc['enrgOff', self._plan], self.GasColPlan.loc['flareOff', self._plan])
        self.LFG_Coll_Eff[filter_Off] = 0

        # Oxidation
        self._LFG_Ox_Eff = np.full((int(self.timescale), int(self._n)), self.InputData.Ox['ox_nocol']['amount'])

        self.filter_ox_1 = xx + yy >= max(self.GasColPlan.loc['enrgOff', self._plan], self.GasColPlan.loc['flareOff', self._plan])
        self.filter_ox_2 = self.LFG_Coll_Eff >= self.InputData.LFG_param['incColEff']['amount']

        self._LFG_Ox_Eff[self.filter_ox_2] = self.InputData.Ox['ox_col']['amount']
        self._LFG_Ox_Eff[self.filter_ox_1] = self.InputData.Ox['ox_fincov']['amount']

        # calculating average collection and oxdiation
        self.Average_Collection = pd.Series(self.LFG_Coll_Eff.mean(axis=1), index=index_t)
        self.Average_Oxidation = pd.Series(self._LFG_Ox_Eff.mean(axis=1), index=index_t)

    # Landfill Gas
    def _Cal_LFG(self):
        self.LCI = LCI(self.Index)
        self._param2 = pd.DataFrame(index=self.Index) # LFG generation parameter
        self.LFG = pd.DataFrame(index=self.Index)
        n_waste_fracs = len(self.Index)

        # LFG generation parameter
        self._param2['k'] = (self.Material_Properties['Lab Decay Rate'].values / 156
                             * self.InputData.LFG_param['actk']['amount'] / 0.04)

        # Methane Yield (m3/dry Mg)
        self.Material_Properties['Methane Yield'] = (
            self.Material_Properties['Biogenic Carbon Content'].values / 100
            * self.Material_Properties['Ultimate Biogenic C Converted to Biogas'].values / 100
            * self.CommonData.STP['mole_to_L']['amount']
            / self.CommonData.MW['C']['amount']
            * self.InputData.LFG_param['ch4prop']['amount']
            * 1000)

        self._param2['L0'] = self.Material_Properties['Methane Yield'].values

        self._param2['solid Content'] = 1 - self.Material_Properties['Moisture Content'].values / 100

        # Methane generation
        self._Methan_gen_by_year = (
            self._param2['L0'].values.reshape(n_waste_fracs, 1)
            * self._param2['solid Content'].values.reshape(n_waste_fracs, 1)
            * (np.e**(-self._param2['k'].values.reshape(n_waste_fracs, 1) * np.arange(self.timescale))
               - np.e**(-self._param2['k'].values.reshape(n_waste_fracs, 1) * np.arange(1, self.timescale + 1))))

        self.LFG['Total generated Methane'] = self._Methan_gen_by_year.sum(axis=1)

        self.LFG['Fraction of L0 Generated'] = np.divide(
            self.LFG['Total generated Methane'].values,
            self._param2['L0'].values * self._param2['solid Content'].values,
            out=np.zeros(n_waste_fracs),
            where=self._param2['L0'].values>0.0)

        # Methane collected
        self.LFG['Total Methane collected'] = np.multiply(self._Methan_gen_by_year,
                                                          self.Average_Collection.values / 100).sum(axis=1)

        self.LFG['Collection Eff'] = np.divide(
            self.LFG['Total Methane collected'].values,
            self.LFG['Total generated Methane'].values,
            out=np.zeros(n_waste_fracs),
            where=self.LFG['Total generated Methane'].values>0.0)

        # Blower electricity use
        self.LFG['Blower electricity use'] = (
            (self.LFG['Total Methane collected'].values / self.InputData.LF_gas['blwrPRRm3']['amount'])
            * (self.InputData.LF_gas['blwrPerLoad']['amount'] / 100)
            * (100 / self.InputData.LF_gas['blwrEff']['amount'])
            * 24 * 356.25)

        # Adding Blower electricity use to LCI
        self.LCI.add('Electricity_consumption', self.LFG['Blower electricity use'].values)

        # Methane combustion for Energy
        frac_cob = np.zeros(self.timescale)
        ii = np.mgrid[:self.timescale]
        if self.InputData.Energy_Rec['enrgRecovered']['amount'] == 1:
            fltr = np.logical_and(
                ii <= self.GasColPlan.loc['enrgOff', self._plan],
                ii > self.GasColPlan.loc['enrgOn', self._plan])
            frac_cob[fltr] = 1 - self.InputData.Energy_Rec['EnrgRecDownTime']['amount'] / 100

        # Percent of generation that combusted
        comb_col = np.multiply(frac_cob, self.Average_Collection.values / 100)
        self.LFG['Total Methane combusted'] = np.multiply(self._Methan_gen_by_year, comb_col).sum(axis=1)

        self.LFG['Percent of Generated used for Energy'] = np.divide(
            self.LFG['Total Methane combusted'].values,
            self.LFG['Total generated Methane'].values,
            out=np.zeros(n_waste_fracs),
            where=self.LFG['Total generated Methane'].values>0.0) * 100

        self.LFG['Percent of Collected used for Energy'] = np.divide(
            self.LFG['Total Methane combusted'].values,
            self.LFG['Total Methane collected'].values,
            out=np.zeros(n_waste_fracs),
            where=self.LFG['Total Methane collected'].values>0.0) * 100

        # Electricity generated
        self.LFG['Electricity generated'] = (
            self.LFG['Total Methane combusted'].values
            * self.InputData.Energy_Rec['convEff']['amount']
            * self.CommonData.LHV['CH4']['amount']
            / 3.6)

        # Adding the generated electricity to LCI
        self.LCI.add('Electricity_production', self.LFG['Electricity generated'].values)

        # Methane Sent to Flare  (Includes downtime but not methane destruction efficiency)
        self.LFG['Total Methane flared'] = (
            self.LFG['Total Methane collected'].values
            - self.LFG['Total Methane combusted'].values)

        # Methane Oxidized
        # Percent of generated that oxidized
        oxd_colec = np.multiply(1 - self.Average_Collection.values / 100,
                                self.Average_Oxidation.values / 100)

        self.LFG['Total Methane oxidized'] = np.multiply(self._Methan_gen_by_year, oxd_colec).sum(axis=1)

        # Methane Emitted
        self.LFG['Total Methane Emitted'] = (
            self.LFG['Total generated Methane'].values
            - self.LFG['Total Methane combusted'].values
            * self.InputData.Energy_Rec['EngineCombEff']['amount'] / 100
            - self.LFG['Total Methane flared'].values
            * self.InputData.Flare['FlareCombEff']['amount'] / 100
            - self.LFG['Total Methane oxidized'].values)

        self.LFG['Percent of Generated Methane Emitted'] = np.divide(
            self.LFG['Total Methane Emitted'].values,
            self.LFG['Total generated Methane'].values,
            out=np.zeros(n_waste_fracs),
            where=self.LFG['Total generated Methane'].values>0.0) * 100

        # Mass of methane in uncollected biogas used to calculated the emissions
        self.LFG['Total methane in uncollected biogas'] = (
            self.LFG['Total generated Methane'].values
            - self.LFG['Total Methane collected'].values)

        # Emission factor: Emission to the air from venting, flaring and combustion of biogas
        Biogas_factor = (self.gas_emission_factor['Concentration_ppmv'].values
                         / (self.InputData.LFG_param['ch4prop']['amount'] * 10**6))

        Vent_factor = (Biogas_factor
                       * (1 - self.gas_emission_factor['Destruction_Eff_Vent'].values / 100)
                       * (1 / self.CommonData.STP['mole_to_L']['amount'])
                       * self.gas_emission_factor['MW'].values)

        Flare_factor = (Biogas_factor
                        * (1 - self.gas_emission_factor['Destruction_Eff_Flare'].values / 100)
                        * (1 / self.CommonData.STP['mole_to_L']['amount'])
                        * self.gas_emission_factor['MW'].values)

        Comb_factor = (Biogas_factor
                       * (1 - self.gas_emission_factor['Destruction_Eff_User_Defined'].values / 100)
                       * (1 / self.CommonData.STP['mole_to_L']['amount'])
                       * self.gas_emission_factor['MW'].values)

        self.emission_to_air = (self.LFG['Total methane in uncollected biogas'].apply(lambda x: x * Vent_factor).values
                                + self.LFG['Total Methane flared'].apply(lambda x: x * Flare_factor).values
                                + self.LFG['Total Methane combusted'].apply(lambda x: x * Comb_factor).values)

        self.emission_to_air = np.array([list(self.emission_to_air[i]) for i in range(len(self.emission_to_air))])

        self.emission_to_air = pd.DataFrame(self.emission_to_air,
                                            index=self.Index,
                                            columns=(self.gas_emission_factor['Exchange'].values
                                                     + ' to '
                                                     + self.gas_emission_factor['Subcompartment'].values))

        key1 = zip(self.emission_to_air.columns, self.gas_emission_factor['Biosphere_key'].values)
        self._key1 = dict(key1)

        # Direct CO2 and Methane emissions, Calculated in the model
        self.LFG['Mass of emitted methane'] = (
            self.LFG['Total Methane Emitted'].values
            * self.CommonData.STP['m3CH4_to_kg']['amount'])

        self.LFG['Mass of CO2 generated with methane'] = (
            self.LFG['Total generated Methane'].values
            * (1 / self.InputData.LFG_param['ch4prop']['amount'])
            * (1 - self.InputData.LFG_param['ch4prop']['amount'])
            * self.CommonData.STP['m3CO2_to_kg']['amount'])

        self.LFG['Mass of CO2 generated with methane combustion'] = (
            (self.LFG['Total Methane combusted'].values
             * self.InputData.Energy_Rec['EngineCombEff']['amount'] / 100
             + self.LFG['Total Methane flared'].values
             * self.InputData.Flare['FlareCombEff']['amount'] / 100)
            * 1000
            * (1 / self.CommonData.STP['mole_to_L']['amount'])
            * self.CommonData.MW['CO2']['amount'] / 1000)

        self.LFG['Mass of CO2 generated with methane oxidation'] = (
            self.LFG['Total Methane oxidized'].values * 1000
            * (1 / self.CommonData.STP['mole_to_L']['amount'])
            * self.CommonData.MW['CO2']['amount'] / 1000)

        self.LFG['Mass of CO2 storage'] = (
            - (1 - self.Material_Properties['Moisture Content'].values / 100)
            * self.Material_Properties['Carbon Storage Factor'].values
            * self.CommonData.MW['CO2']['amount']
            / self.CommonData.MW['C']['amount'])

        # Adding the CO2 emissions to 'emission_to_air' dict
        if 'Carbon dioxide, non-fossil to unspecified' in self.emission_to_air.columns:
            self.emission_to_air['Carbon dioxide, non-fossil to unspecified'] += (
                self.LFG['Mass of CO2 generated with methane'].values
                + self.LFG['Mass of CO2 generated with methane combustion'].values
                + self.LFG['Mass of CO2 generated with methane oxidation'].values)
        else:
            self.emission_to_air['Carbon dioxide, non-fossil to unspecified'] = (
                self.LFG['Mass of CO2 generated with methane'].values
                + self.LFG['Mass of CO2 generated with methane combustion'].values
                + self.LFG['Mass of CO2 generated with methane oxidation'].values)

            self._key1['Carbon dioxide, non-fossil to unspecified'] = ('biosphere3', 'eba59fd6-f37e-41dc-9ca3-c7ea22d602c7')

        # Adding the CO2 storage to 'emission_to_air' dict
        if 'Carbon dioxide, from soil or biomass stock to unspecified' in self.emission_to_air.columns:
            self.emission_to_air['Carbon dioxide, from soil or biomass stock to unspecified'] += self.LFG['Mass of CO2 storage'].values
        else:
            self.emission_to_air['Carbon dioxide, from soil or biomass stock to unspecified'] = self.LFG['Mass of CO2 storage'].values
            self._key1['Carbon dioxide, from soil or biomass stock to unspecified'] = ('biosphere3', 'e4e9febc-07c1-403d-8d3a-6707bb4d96e6')

        # Adding the Methane emissions to 'emission_to_air' dict
        if 'Methane, non-fossil to unspecified' in self.emission_to_air.columns:
            self.emission_to_air['Methane, non-fossil to unspecified'] += self.LFG['Mass of emitted methane'].values
        else:
            self.emission_to_air['Methane, non-fossil to unspecified'] = self.LFG['Mass of emitted methane'].values
            self._key1['Methane, non-fossil to unspecified'] = ('biosphere3', 'da1157e2-7593-4dfd-80dd-a3449b37a4d8')


    def _Leachate(self):
        """
        Calculates the leachate flow and concentraions
        """
        self._n_lcht = 100
        # LEACHATE GENERATION, QUANTITY AND CONSTITUENTS
        self._param3 = pd.DataFrame(index=np.arange(self._n_lcht), dtype=float)
        self._param3['year'] = np.arange(1, 101)

        self._param3['Time to initial cover placement'] = (
            self.GasColPlan.loc['cellFillTime', self._plan]
            - np.mod(np.arange(self._n_lcht), self.GasColPlan.loc['cellFillTime', self._plan]))

        k = self.InputData.LFG_param['actk']['amount']
        if k <= 0.03:
            self._param3['Annual Precipitation (mm)'] = self.InputData.Leachate['precip_arid']['amount']
        elif k <= 0.6:
            self._param3['Annual Precipitation (mm)'] = self.InputData.Leachate['precip_mod']['amount']
        elif k > 0.06:
            self._param3['Annual Precipitation (mm)'] = self.InputData.Leachate['precip_wet']['amount']

        if self.InputData.Leachate['is_bioreactor']['amount']:
            self._param3['Annual Precipitation (mm)'] = self.InputData.Leachate['precip_bio']['amount']

        self.LeachColEff = np.full((self._n_lcht, self._n), self.InputData.Leachate['prep_leach_init']['amount'])
        xx, yy = np.mgrid[0:self._n_lcht, 0:self._n]
        filter_FCover = xx + yy >= self.GasColPlan.loc['timeToFinCover', self._plan] + self.InputData.LF_Op['optime']['amount']
        filter_IntCover = (xx.reshape(self._n, self._n_lcht) >= self._param3['Time to initial cover placement'].values).reshape(self._n_lcht, self._n)
        self.LeachColEff[filter_IntCover] = self.InputData.Leachate['prep_leach_red']['amount']
        self.LeachColEff[filter_FCover] = self.InputData.Leachate['prep_leach_f']['amount']

        self._param3['Frac Precip to Leachate'] = self.LeachColEff.mean(axis=1)

        if self.InputData.Leachate['is_bioreactor']['amount']:
            Circulate = np.zeros(self._n_lcht)
            fltr_cir = self._param3['year'].values < self.InputData.Leachate['LF_time2']['amount']
            fltr_cir_off = self._param3['year'].values < self.InputData.Leachate['LF_time1']['amount']
            Circulate[fltr_cir] = self.InputData.Leachate['frac_recirc']['amount']
            Circulate[fltr_cir_off] = 0.0
            self._param3['frac Col Leach Recirculated'] = Circulate
        else:
            self._param3['frac Col Leach Recirculated'] =  0.0

        self._param3['frac Col Leach to WWTP'] = 1.0 - self._param3['frac Col Leach Recirculated'].values

        leach_col_eff = np.zeros(self._n_lcht)
        fltr_1 = self._param3['year'].values < self.InputData.Leachate['LF_time3']['amount']
        fltr_2 = self._param3['year'].values < self.InputData.Leachate['LF_time1']['amount']
        leach_col_eff[fltr_1] = self.InputData.Leachate['Lcht_Col_Ef']['amount']
        leach_col_eff[fltr_2] = 0.0
        self._param3['Leach Col Eff'] = leach_col_eff

        """
        Annual Waste to landfill:
            <200000 Mg/y small landfill: 1500 lb/yd3 (890 kg/m3);
            >=200000 Mg/yr large landfill: 1800 lb/yds (1068 kg/m3)
        Equation are from regression in the landfill paper (Wang et. al. 2021)
        """
        if self.InputData.LF_Op['annWaste']['amount'] < 200000:
            self._LF_msw_ha = (
                29806
                * np.log(self.InputData.LF_Op['annWaste']['amount']
                         * self.InputData.LF_Op['optime']['amount'])
                - 263324)
        else:
            self._LF_msw_ha = (
                73172
                * np.log(self.InputData.LF_Op['annWaste']['amount']
                         * self.InputData.LF_Op['optime']['amount'])
                - 837452)

        # Mass balance of Leachate
        self._param3['Generated Leachate (m3/Mg MSW)'] = (
            (self._param3['Annual Precipitation (mm)'].values / 1000)  # mm to m
            * (self._param3['Frac Precip to Leachate'].values)
            * (10000 / self._LF_msw_ha))  # Ha to m2

        self._param3['Collected Leachate (m3/Mg MSW)'] = (
            self._param3['Generated Leachate (m3/Mg MSW)'].values
            * self._param3['Leach Col Eff'].values)

        self._param3['Recirculated Leachate (m3/Mg MSW)'] = (
            self._param3['Generated Leachate (m3/Mg MSW)'].values
            * self._param3['frac Col Leach Recirculated'].values)
        self._param3['Treated Leachate (m3/Mg MSW)'] = (
            self._param3['Collected Leachate (m3/Mg MSW)'].values
            * self._param3['frac Col Leach to WWTP'].values)
        self._param3['Fugitive Leachate  (m3/Mg MSW)'] = (
            self._param3['Generated Leachate (m3/Mg MSW)'].values
            - self._param3['Treated Leachate (m3/Mg MSW)'].values
            - self._param3['Recirculated Leachate (m3/Mg MSW)'].values)

        # Concentration of other effluents in leachate  (kg/L)
        self.lcht_conc = np.zeros((self._n_lcht, self.lcht_Qlty.shape[0]))
        self.lcht_conc[:2, :] = self.lcht_Qlty['Stage 1 (0-2 years, mg/L)'].values
        self.lcht_conc[2:10, :] = self.lcht_Qlty['Stage 2 (3-10 years, mg/L)'].values
        self.lcht_conc[10:40, :] = self.lcht_Qlty['Stage 3 (11-40 years, mg/L)'].values
        self.lcht_conc[40:100, :] = self.lcht_Qlty['Stage 4 (41-100 years, mg/L)'].values
        self.lcht_conc /= 10**6  # mg/L -> kg/L

        self.lcht_conc = pd.DataFrame(
            self.lcht_conc,
            columns=self.lcht_Qlty['Emission'].values)

        # Fugitive Leachate Emissions (leaks through liner) (kg/Mg MSW)
        self._Fugitive_Leachate = pd.Series(
            (self.lcht_conc.values.T
             * self._param3['Fugitive Leachate  (m3/Mg MSW)'].values).sum(axis=1)
            * 1000,  # m3 -> L
            index=self.lcht_Qlty['Emission'].values)

        # Post-treatment effluent emissions (kg/Mg MSW)
        self._Effluent = pd.Series(
            np.multiply(
                np.multiply(
                    self.lcht_conc.values.T,
                    self._param3['Treated Leachate (m3/Mg MSW)'].values).sum(axis=1),
                1 - self.lcht_Qlty['Removal Efficiency (%)'].values / 100) * 1000,
            index=self.lcht_Qlty['Emission'].values)



        self.lcht_Alloc = np.zeros((len(self.Index), self.lcht_Qlty.shape[0]))
        comp = self.process_data['Assumed_Comp'].values
        sld_cont = (1 - self.Material_Properties['Moisture Content'] / 100)
        sld_msw = (comp * sld_cont).sum()
        sld_alloc = sld_cont / sld_msw
        for i, j in enumerate(self.lcht_Qlty['Allocation_base'].values):
            if j == 'Solid Content':
                self.lcht_Alloc[:, i] = sld_alloc
            elif j == 'Nitrogen Content' or j == 'Phosphorus Content':
                m = self.Material_Properties[j].values * sld_cont * self.process_data['Degrades'].values
                self.lcht_Alloc[:, i] = m / (m * comp).sum()
            else:
                m = self.Material_Properties[j].values * sld_cont
                self.lcht_Alloc[:, i] = m / (m * comp).sum()

        self.lcht_Alloc = pd.DataFrame(self.lcht_Alloc,
                                       columns=self.lcht_Qlty['Emission'].values,
                                       index=self.Index)

        self.Surface_water_emission = pd.DataFrame(
            self.lcht_Alloc.values * self._Effluent.values,
            index=self.Index,
            columns=self.lcht_Qlty['Emission'].values + "_ to SW")

        self._key2 = dict(zip(self.Surface_water_emission.columns, self.lcht_Qlty['Surface_water'].values))

        self.Ground_water_emission = pd.DataFrame(
            self.lcht_Alloc.values * self._Fugitive_Leachate.values,
            index=self.Index,
            columns=self.lcht_Qlty['Emission'].values + "_ to GW")

        self._key3 = dict(zip(self.Ground_water_emission.columns, self.lcht_Qlty['Ground_water'].values))

        # Electricity Consumption for Leachate Treatment
        BOD_removed = (sum(self.lcht_conc['BOD5, Biological Oxygen Demand'].values
                           * self._param3['Treated Leachate (m3/Mg MSW)'].values)
                       * 1000
                       - self._Effluent['BOD5, Biological Oxygen Demand'])

        BOD_elec = BOD_removed * self.InputData.BOD['LF_lcht_ec']['amount']

        Pump_elec_per_litr = (
            self.InputData.lcht_pump['leachAirPerLeach']['amount']
            * (1 / self.InputData.lcht_pump['leachCompPowReq']['amount'])
            * (1 / 28.32)
            * (1 / (60 * 24 * 365.25))
            * (self.InputData.lcht_pump['leachCompLoad']['amount'] / 100)
            * (100 / self.InputData.lcht_pump['leachEff']['amount'])
            * 8766 / 1.341)

        Pump_elec = sum(self._param3['Collected Leachate (m3/Mg MSW)'].values
                        * 1000 * Pump_elec_per_litr)

        Leachate_elec = (self.lcht_Alloc['BOD5, Biological Oxygen Demand']
                         * BOD_elec
                         + Pump_elec)

        # Adding leachate collection electricity use to LCI
        self.LCI.add('Electricity_consumption', Leachate_elec.values)

        # List of metals in Leachate
        metals = ['Arsenic, ion', 'Barium', 'Cadmium, ion', 'Chromium, ion',
                  'Lead','Mercury', 'Selenium', 'Silver, ion']

        # Calculating Slude generation and transport
        LF_sldg_BOD = self.InputData.BOD['LF_sldg_per_BOD']['amount'] * BOD_removed

        LF_sldg_PO4 = (
            self._Effluent['Phosphate']
            * (self.InputData.Leachate['LF_eff_PO4']['amount'] / 100)
            / (1 - self.InputData.Leachate['LF_eff_PO4']['amount'] / 100))

        LF_sldg_mtls = (self._Effluent[metals].sum()
                        * (self.InputData.Leachate['LF_eff_mtls']['amount'] / 100)
                        / (1 - self.InputData.Leachate['LF_eff_mtls']['amount'] / 100))

        LF_sldg_tss = (self._Effluent['TSS']
                       * (self.InputData.Leachate['LF_eff_TSS']['amount'] / 100)
                       / (1 - self.InputData.Leachate['LF_eff_TSS']['amount'] / 100))

        # Generated sludge from Leachate treatment
        self.sludge = pd.DataFrame(index=self.Index)
        self.sludge['sludge generated from BOD removal'] = (
            self.lcht_Alloc['BOD5, Biological Oxygen Demand'].values
            * LF_sldg_BOD)

        self.sludge['sludge generated from phosphate removal'] = (
            self.lcht_Alloc['Phosphate'].values
            * LF_sldg_PO4)

        self.sludge['sludge generated from metals removal'] = (
            self.lcht_Alloc[metals].values
            * LF_sldg_mtls).sum(axis=1)

        self.sludge['sludge generated from suspended solids removal'] = (
            self.lcht_Alloc['TSS'].values
            * LF_sldg_tss)

        self.sludge['total sludge generated'] = (
            self.sludge['sludge generated from BOD removal'].values
            + self.sludge['sludge generated from phosphate removal'].values
            + self.sludge['sludge generated from metals removal'].values
            + self.sludge['sludge generated from suspended solids removal'].values)

        self.sludge['Medium-Heavy Duty Transportation'] = (
            self.sludge['total sludge generated'].values / 1000
            * self.InputData.Leachate['dis_POTW']['amount'])

        self.LCI.add('Internal_Process_Transportation_Medium_Duty_Diesel_Truck',
                     self.sludge['Medium-Heavy Duty Transportation'].values * 1000)

    # Life-Cycle Costs
    def _Add_cost(self):
        self.cost_DF = pd.DataFrame(index=self.Index)
        self.cost_DF[('biosphere3', 'Operational_Cost')] = [
            self.InputData.Operational_Cost[y]['amount'] for y in self.Index]

    # Life-Cycle Inventory
    def _Material_energy_use(self):
        # Electricity used for office and maitenance buildings
        bld_elec = 0.081  # kWh/Mg
        self.LCI.add('Electricity_consumption', bld_elec)

        """
        Diesel use include:
        1. Fuel used for heavy equipment during construction
        2. Fuel used for heavy equipment during closure
        3. Fuel used for heavy equipment during operation
        4. Fuel used for heavy equipment during closure
        """
        diesel = 1.628  # L/Mg
        self.LCI.add('Equipment_Diesel', diesel)

        # Material Use
        """
        HDPE include:
        1. Mass of HDPE liner for construction
        2. Mass of HDPE Final Cover & Closure System
        3. Mass of HDPE replaced on a yearly basis for Post-Closure Care
        """
        HDPE_Liner = 0.074  # kg/Mg
        self.LCI.add('HDPE_Liner', HDPE_Liner)

        """
        HDPE Pipe include:
        1. HDPE pipe for construction
        2. HDPE pipe for final cover& Closure system
        """
        HDPE_Pipe = 0.0022  # m/Mg
        self.LCI.add('HDPE_Pipe', HDPE_Pipe)

        """
        PVC pipe for final cover and closure system
        """
        PVC_Pipe = 0.0011  # m/Mg
        self.LCI.add('PVC_Pipe', PVC_Pipe)

        """
        Steal
        """
        Steel = 0.2382  # kg/Mg
        self.LCI.add('Steel', Steel)

        """
        Concrete
        """
        Concrete = 0.0071  # kg/Mg
        self.LCI.add('Concrete', Concrete)

        """
        Asphalt
        """
        Asphalt = 0.0850  # kg/Mg
        self.LCI.add('Asphalt', Asphalt)


        """
        Sand
        """
        Sand = 33.751  # kg/Mg
        self.LCI.add('Sand', Sand)

        """
        Gravel
        """
        Gravel = 2.320  # kg/Mg
        self.LCI.add('Gravel', Gravel)

        """
        Clay
        """
        Clay = 57.115  # kg/Mg
        self.LCI.add('Clay', Clay)

        """
        Building
        """
        Building = 2.29E-05  # m2/Mg
        self.LCI.add('Building', Building)

        # Transportation
        # Heavy duty truck transportation required
        HD_trans = 542.98    # kgkm/Mg
        self.LCI.add('Internal_Process_Transportation_Heavy_Duty_Diesel_Truck', HD_trans)
        # Medium duty transportation required
        MD_trans = 1611.18  # kgkm/Mg
        self.LCI.add('Internal_Process_Transportation_Medium_Duty_Diesel_Truck', MD_trans)
        # Heavy duty truck transportation required
        HD_trans_empty  = 0.018  # vkm/Mg
        self.LCI.add('Empty_Return_Heavy_Duty_Diesel_Truck', HD_trans_empty)
        # Medium duty transportation required
        MD_trans_empty = 0.067  # vkm/Mg
        self.LCI.add('Empty_Return_Medium_Duty_Diesel_Truck', MD_trans_empty)

        self._key4 = {
            'Electricity_production': ('Technosphere', 'Electricity_production'),
            'Electricity_consumption': ('Technosphere', 'Electricity_consumption'),
            'Equipment_Diesel': ('Technosphere', 'Equipment_Diesel'),
            'Internal_Process_Transportation_Heavy_Duty_Diesel_Truck': ('Technosphere', 'Internal_Process_Transportation_Heavy_Duty_Diesel_Truck'),
            'Internal_Process_Transportation_Medium_Duty_Diesel_Truck': ('Technosphere', 'Internal_Process_Transportation_Medium_Duty_Diesel_Truck'),
            'Empty_Return_Heavy_Duty_Diesel_Truck': ('Technosphere', 'Empty_Return_Heavy_Duty_Diesel_Truck'),
            'Empty_Return_Medium_Duty_Diesel_Truck': ('Technosphere', 'Empty_Return_Medium_Duty_Diesel_Truck'),
            'HDPE_Liner': ('Technosphere', 'HDPE_Liner'),
            'HDPE_Pipe': ('Technosphere', 'HDPE_Pipe'),
            'PVC_Pipe': ('Technosphere', 'PVC_Pipe'),
            'Steel': ('Technosphere', 'Steel'),
            'Concrete': ('Technosphere', 'Concrete'),
            'Asphalt': ('Technosphere', 'Asphalt'),
            'Sand': ('Technosphere', 'Sand'),
            'Gravel': ('Technosphere', 'Gravel'),
            'Clay': ('Technosphere', 'Clay'),
            'Building': ('Technosphere', 'Building'),}

    # Calc function _ Do all the calculations
    def calc(self):
        self._Cal_LFG_Col_Ox()
        self._Cal_LFG()
        self._Leachate()
        self._Material_energy_use()
        self._Add_cost()

    # setup for Monte Carlo simulation
    def setup_MC(self, seed=None):
        self.InputData.setup_MC(seed)

    # Calculate based on the generated numbers
    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        self.calc()
        return input_list

    # Report
    def report(self):
        ### Output
        self.LF = {}
        Waste = {}
        Technosphere = {}
        self.LF["process name"] = (self.process_name, self.Process_Type, self.__class__)
        self.LF["Waste"] = Waste
        self.LF["Technosphere"] = Technosphere

        for x in [Waste, Technosphere]:
            for y in self.Index:
                x[y] = {}

        ### Output Biosphere Database
        LCI_DF = self.LCI.report()

        # Check the electricity production
        if LCI_DF['Electricity_production'].values.sum() > 0:
            LCI_DF['Electricity_production'] = (
                LCI_DF['Electricity_production'].values
                - LCI_DF['Electricity_consumption'].values)
            LCI_DF['Electricity_consumption'] = 0
        else:
            LCI_DF['Electricity_consumption'] = (
                LCI_DF['Electricity_consumption'].values
                - LCI_DF['Electricity_production'].values)
            LCI_DF['Electricity_production'] = 0

        for y in self.Index:
            # Technosphere
            for x in self._key4:
                Technosphere[y][self._key4[x]] = LCI_DF[x][y]

        self.bio_rename_dict = dict(self._key1, **self._key2)
        self.bio_rename_dict = dict(self.bio_rename_dict, **self._key3)
        self.bio_rename_dict[('biosphere3', 'Operational_Cost')] = ('biosphere3', 'Operational_Cost')

        self.LCI_bio = pd.concat([self.emission_to_air,
                                  self.Surface_water_emission,
                                  self.Ground_water_emission], axis=1)

        self.LCI_bio = self.LCI_bio.rename(columns=self.bio_rename_dict)
        self.LCI_bio_index = True
        keys = list(self.bio_rename_dict.keys())
        for x in keys:
            if "biosphere3" not in str(self.bio_rename_dict[x]):
                self.bio_rename_dict.pop(x)
        self.LCI_bio[('biosphere3','Operational_Cost')] = self.cost_DF[('biosphere3','Operational_Cost')].values
        self.Biosphere = self.LCI_bio[self.bio_rename_dict.values()].transpose().to_dict()
        self.LF["Biosphere"] = self.Biosphere
        return self.LF


# LCI class
class LCI():
    """
    This class store the LCI data in numpy.ndarray instead of pandas for speedup.
    Report function create pandas DataFrame and return it
    Column names are stored in self.ColDict
    """
    def __init__(self, Index):
        self.Index = Index
        self.LCI = np.zeros((len(Index), 20))
        self.ColDict = {}
        self.ColNumber = 0

    def add(self, name, flow):
        if name not in self.ColDict:
            self.ColDict[name] = self.ColNumber
            self.ColNumber += 1
        self.LCI[:, self.ColDict[name]] += flow

    def report(self):
        LCI = deepcopy(self.LCI)
        return pd.DataFrame(LCI[:, :len(self.ColDict)],
                            columns=list(self.ColDict.keys()),
                            index=self.Index)

    def report_T(self):
        LCI = deepcopy(self.LCI)
        return pd.DataFrame(LCI[:, :len(self.ColDict)].transpose(),
                            index=list(self.ColDict.keys()),
                            columns=self.Index)
