# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 11:07:56 2019

@author: msardar2
"""
import numpy as np
import pandas as pd
from .ProcessModel import *
from swolfpy_inputdata import LF_Input
import ast
from pathlib import Path

class LF(ProcessModel):
    Process_Type = 'Treatment'
    def __init__(self, input_data_path=None, CommonDataObjct=None):
        super().__init__(CommonDataObjct)

        self.InputData= LF_Input(input_data_path, CommonDataObjct=CommonDataObjct)

        self.gas_emission_factor=self.InputData.gas_emission_factor

        self.lcht_coef = self.InputData.lcht_coef

        self.lcht_Alloc = self.InputData.lcht_Alloc

        self._n = self.InputData.LF_gas['optime']['amount']+1
        self.timescale = 101

# =============================================================================
#        
### Landfill Gas Collection Efficiency
#
# =============================================================================
    def _Cal_LFG_Col_Ox(self):
        self._param1=pd.DataFrame(index = ['Waste buried in Year '+str(i) for i in np.arange(0,self._n)])  # Parameters for LF operation (timing for LFG collection)

### Parameters for LF operation (timing for LFG collection)
        self._param1['Time to initial collection'] = [max(self.InputData.LF_gas['initColTime']['amount']-np.mod(i,self.InputData.LF_gas['cellFillTime']['amount']),0) \
                                                             for i in np.arange(0,self._n)]
        self._param1['Time to interim cover'] = [self.InputData.LF_gas['cellFillTime']['amount'] - np.mod(i,self.InputData.LF_gas['cellFillTime']['amount']) \
                                                     for i in np.arange(0,self._n)]
        self._param1['Time to long term cover'] = [self.InputData.LF_gas['incColTime']['amount'] - np.mod(i,self.InputData.LF_gas['cellFillTime']['amount']) \
                                             for i in np.arange(0,self._n)]

### How long is energy on
        EnrgOff = self.InputData.LF_gas['enrgOff1']['amount'] if self.InputData.LF_gas['enrgRecovered']['amount']==1 else 0

### Collection efficiency
        self.LFG_Coll_Eff = np.zeros((int(self.timescale),int(self._n)))
        for j in np.arange(0,self.timescale):
            self.LFG_Coll_Eff[j] = [None if i>self.InputData.LF_gas['optime']['amount'] else
                                  0 if(i+j)>=(max(EnrgOff,self.InputData.LF_gas['flareOff']['amount'])) else
                                  self.InputData.LF_gas['finColEff']['amount'] if (i+j)>=(self.InputData.LF_gas['timeToFinCover']['amount']+self.InputData.LF_gas['optime']['amount']) else
                                  self.InputData.LF_gas['incColEff']['amount'] if j>=self._param1['Time to long term cover']['Waste buried in Year '+str(i)] else
                                  self.InputData.LF_gas['intColEff']['amount'] if j>=self._param1['Time to interim cover']['Waste buried in Year '+str(i)] else
                                  self.InputData.LF_gas['initColEff']['amount'] if j>=self._param1['Time to initial collection']['Waste buried in Year '+str(i)] else
                                  0 for i in np.arange(0,self._n)]

### Oxidation
        self._LFG_Ox_Eff = np.zeros((int(self.timescale),int(self._n)))
        for j in np.arange(0,self.timescale):
            self._LFG_Ox_Eff[j] = [ None if i>self.InputData.LF_gas['optime']['amount'] else
                                      self.InputData.Ox['ox_fincov']['amount'] if(i+j)>=(max(EnrgOff,self.InputData.LF_gas['flareOff']['amount'])) else
                                      self.InputData.Ox['ox_nocol']['amount'] if self.LFG_Coll_Eff[int(j)][int(i)] <self.InputData.LF_gas['incColEff']['amount'] else
                                      self.InputData.Ox['ox_col']['amount']  for i in np.arange(0,self._n)]  

### calculating average collection and oxdiation
        self.Average_Collection= pd.Series(self.LFG_Coll_Eff.sum(axis=1)/(self._n),index =['Collection ' + str(j) + ' Years Since Waste Burial' for j in np.arange(0,self.timescale)])
        self.Average_Oxidation= pd.Series(self._LFG_Ox_Eff.sum(axis=1)/(self._n),index = ['Oxidation ' + str(j) + ' Years Since Waste Burial' for j in np.arange(0,self.timescale)])

# =============================================================================
#        
### Landfill Gas
#
# =============================================================================
    def _Cal_LFG(self):
        self.LCI = LCI(self.Index)
        self._param2 = pd.DataFrame(index=self.Index) # LFG generation parameter
        self.LFG = pd.DataFrame(index=self.Index)

### LFG generation parameter
        self._param2['k'] = (self.Material_Properties['Lab Decay Rate'].values/156) * (self.InputData.LF_gas['actk']['amount']/0.04)

        self._param2['L0'] = self.Material_Properties['Methane Yield'].values

        self._param2['solid Content'] = 1 - self.Material_Properties['Moisture Content'].values/100

### Methane generation                
        self._Methan_gen_by_year = self._param2['L0'].values*self._param2['solid Content'].values*self._param2['k'].apply(lambda x:
                                    np.e**(-x*np.arange(0,self.timescale))-np.e**(-x*np.arange(1,self.timescale+1))).values
        self._Methan_gen_by_year= np.array([list(self._Methan_gen_by_year[i]) for i in range(len(self._Methan_gen_by_year))])
        
        self.LFG['Total generated Methane']= self._Methan_gen_by_year.sum(axis=1)                                                    
        
        self.LFG['Fraction of L0 Generated']=  self.LFG['Total generated Methane'].values/(self._param2['L0'].apply(lambda x: 1 if x <=0 else x).values * self._param2['solid Content'].values)
        
### Methane collected            
        self.LFG['Total Methane collected']= np.multiply(self._Methan_gen_by_year,self.Average_Collection.values/100).sum(axis=1)  
        
        self.LFG['Collection Eff']= self.LFG['Total Methane collected'].values/self.LFG['Total generated Methane'].apply(lambda x: 1 if x <=0 else x).values

### Blower electricity use
        self.LFG['Blower electricity use']=(self.LFG['Total Methane collected'].values/self.InputData.LF_gas['blwrPRRm3']['amount']) * (self.InputData.LF_gas['blwrPerLoad']['amount'] /100) * (100/self.InputData.LF_gas['blwrEff']['amount']) * 24 * 356.25
        #Adding Blower electricity use to LCI
        self.LCI.add('Electricity_consumption',self.LFG['Blower electricity use'].values)

### Methane combustion for Energy         
        def comb_frac(j):
            return(0 if not self.InputData.LF_gas['enrgRecovered']['amount']==1 else \
                   0 if j <= self.InputData.LF_gas['enrgOn']['amount'] else \
                   (100-self.InputData.LF_gas['EnrgRecDownTime']['amount'])/100  if j <= self.InputData.LF_gas['enrgOff1']['amount'] else 0)
        
        # fraction of collected that combusted
        frac_cob = pd.Series(np.arange(0,self.timescale)).apply(comb_frac).values
        # Percent of generation that combusted
        comb_col = np.multiply(frac_cob,self.Average_Collection.values/100)
        self.LFG['Total Methane combusted']=  np.multiply(self._Methan_gen_by_year,comb_col).sum(axis=1)
             
        self.LFG['Percent of Generated used for Energy']= self.LFG['Total Methane combusted'].values/self.LFG['Total generated Methane'].apply(lambda x: 1 if x <=0 else x).values  * 100
     
        self.LFG['Percent of Collected used for Energy']= self.LFG['Total Methane combusted'].values/self.LFG['Total Methane collected'].apply(lambda x: 1 if x <=0 else x).values  * 100

### Electricity generated
        self.LFG['Electricity generated'] = self.LFG['Total Methane combusted'].values * self.InputData.LFG_Comb['convEff']['amount']*self.CommonData.LHV['CH4']['amount'] /3.6
        #Adding the generated electricity to LCI
        self.LCI.add('Electricity_production' ,self.LFG['Electricity generated'].values)
    
### Methane Sent to Flare  (Includes downtime but not methane destruction efficiency)        
        self.LFG['Total Methane flared']= self.LFG['Total Methane collected'].values-self.LFG['Total Methane combusted'].values

### Methane Oxidized
        # Percent of generated that oxidized
        oxd_colec = np.multiply(1-self.Average_Collection.values/100,self.Average_Oxidation.values/100)
        self.LFG['Total Methane oxidized'] = np.multiply(self._Methan_gen_by_year,oxd_colec).sum(axis=1) 

### Methane Emitted        
        self.LFG['Total Methane Emitted']=  self.LFG['Total generated Methane'].values - self.LFG['Total Methane combusted'].values * self.InputData.LF_gas['EngineCombEff']['amount']/100 \
                                                        - self.LFG['Total Methane flared'].values *self.InputData.LF_gas['FlareCombEff']['amount']/100 - self.LFG['Total Methane oxidized'].values

        self.LFG['Percent of Generated Methane Emitted']= self.LFG['Total Methane Emitted'].values/self.LFG['Total generated Methane'].apply(lambda x: 1 if x <=0 else x).values  * 100

### Mass of methane in uncollected biogas used to calculated the emissions         
        self.LFG['Total methane in uncollected biogas'] = self.LFG['Total generated Methane'].values - self.LFG['Total Methane collected'].values

### Emission factor: Emission to the air from venting, flaring and combustion of biogas        
        Biogas_factor = self.gas_emission_factor['Concentration_ppmv'].values/(self.InputData.LF_gas['ch4prop']['amount']*10**6)
        Vent_factor = Biogas_factor*(1-self.gas_emission_factor['Destruction_Eff_Vent'].values/100)*(1/self.CommonData.STP['mole_to_L']['amount'])*self.gas_emission_factor['MW'].values
        Flare_factor = Biogas_factor*(1-self.gas_emission_factor['Destruction_Eff_Flare'].values/100)*(1/self.CommonData.STP['mole_to_L']['amount'])*self.gas_emission_factor['MW'].values
        Comb_factor = Biogas_factor*(1-self.gas_emission_factor['Destruction_Eff_User_Defined'].values/100)*(1/self.CommonData.STP['mole_to_L']['amount'])*self.gas_emission_factor['MW'].values
        self.emission_to_air =self.LFG['Total methane in uncollected biogas'].apply(lambda x: x*Vent_factor).values + self.LFG['Total Methane flared'].apply(lambda x: x*Flare_factor).values+self.LFG['Total Methane combusted'].apply(lambda x: x*Comb_factor).values
        self.emission_to_air=np.array([list(self.emission_to_air[i]) for i in range(len(self.emission_to_air))])
        self.emission_to_air=pd.DataFrame(self.emission_to_air,index=self.Index,columns=self.gas_emission_factor['Exchange'].values +' to '+ self.gas_emission_factor['Subcompartment'].values)

        key1 = zip(self.emission_to_air.columns,self.gas_emission_factor['Biosphere_key'].values)
        self._key1=dict(key1) 

### Direct CO2 and Methane emissions, Calculated in the model        
        self.LFG['Mass of emitted methane']=self.LFG['Total Methane Emitted'].values*self.CommonData.STP['m3CH4_to_kg']['amount']

        self.LFG['Mass of CO2 generated with methane']=self.LFG['Total generated Methane'].values*(1/self.InputData.LF_gas['ch4prop']['amount'])*(1-self.InputData.LF_gas['ch4prop']['amount'])*self.CommonData.STP['m3CO2_to_kg']['amount']

        self.LFG['Mass of CO2 generated with methane combustion'] =  (self.LFG['Total Methane combusted'].values*self.InputData.LF_gas['EngineCombEff']['amount']/100 + self.LFG['Total Methane flared'].values*self.InputData.LF_gas['FlareCombEff']['amount']/100) \
                                                                        *1000*(1/self.CommonData.STP['mole_to_L']['amount'])*self.CommonData.MW['CO2']['amount']/1000

        self.LFG['Mass of CO2 generated with methane oxidation'] = self.LFG['Total Methane oxidized'].values*1000*(1/self.CommonData.STP['mole_to_L']['amount'])*self.CommonData.MW['CO2']['amount']/1000

        self.LFG['Mass of CO2 storage'] = -(1-self.Material_Properties['Moisture Content'].values/100)*self.Material_Properties['Carbon Storage Factor'].values*self.CommonData.MW['CO2']['amount']/self.CommonData.MW['C']['amount']

### Adding the CO2 emissions to 'emission_to_air' dict        
        if 'Carbon dioxide, non-fossil to unspecified' in self.emission_to_air.columns:
            self.emission_to_air['Carbon dioxide, non-fossil to unspecified'] += self.LFG['Mass of CO2 generated with methane'].values+self.LFG['Mass of CO2 generated with methane combustion'].values+self.LFG['Mass of CO2 generated with methane oxidation'].values
        else:
            self.emission_to_air['Carbon dioxide, non-fossil to unspecified'] = self.LFG['Mass of CO2 generated with methane'].values+self.LFG['Mass of CO2 generated with methane combustion'].values+self.LFG['Mass of CO2 generated with methane oxidation'].values
            self._key1['Carbon dioxide, non-fossil to unspecified']=('biosphere3', 'eba59fd6-f37e-41dc-9ca3-c7ea22d602c7')

### Adding the CO2 storage to 'emission_to_air' dict  
        if 'Carbon dioxide, from soil or biomass stock to unspecified' in self.emission_to_air.columns:
            self.emission_to_air['Carbon dioxide, from soil or biomass stock to unspecified'] += self.LFG['Mass of CO2 storage'].values
        else:
            self.emission_to_air['Carbon dioxide, from soil or biomass stock to unspecified'] = self.LFG['Mass of CO2 storage'].values
            self._key1['Carbon dioxide, from soil or biomass stock to unspecified']=('biosphere3', 'e4e9febc-07c1-403d-8d3a-6707bb4d96e6')   

### Adding the Methane emissions to 'emission_to_air' dict  
        if 'Methane, non-fossil to unspecified' in self.emission_to_air.columns:
            self.emission_to_air['Methane, non-fossil to unspecified'] += self.LFG['Mass of emitted methane'].values
        else:
            self.emission_to_air['Methane, non-fossil to unspecified'] = self.LFG['Mass of emitted methane'].values
            self._key1['Methane, non-fossil to unspecified']=('biosphere3', 'da1157e2-7593-4dfd-80dd-a3449b37a4d8')          

# =============================================================================
#        
### LEACHATE
#
# =============================================================================
    def _Leachate(self):
        self._param3=pd.DataFrame(index = np.arange(1,self.timescale)) # Leachate
        self.lcht_conc=pd.DataFrame(index = np.arange(1,self.timescale)) # Concentration of emissions in leachate
        self.sludge = pd.DataFrame(index = self.Index) # Generated sludge from Leachate treatment
### LEACHATE GENERATION, QUANTITY AND CONSTITUENTS
        self._param3['year'] = np.arange(1,self.timescale)
        self._param3['Annual Precipitation (mm)'] = 900
        self._param3['Percent of Precipitation that Becomes Leachate (%)'] = [20, 13.3, 6.6, 6.6, 6.6, 6.5, 6.5, 6.5, 6.5, 6.5]+[0.04 for i in range(90)]
        self._param3['fraction of Leachate that is Recirculated'] = 0
        self._param3['farction of Collected Leachate that is Sent to WWTP'] = 1
        self._param3['Leachate Collection Efficiency (%)']= self._param3['year'].apply(lambda x: self.InputData.Leachate['LF_lcht_p']['amount'] if x<=self.InputData.Leachate['LF_time3']['amount'] \
                                                           and x>=self.InputData.Leachate['LF_time1']['amount'] else 0).values

        LF_msw_acre = 115802 # Mg/ha 
### Mass balance of Leachate
        self._param3['Generated Leachate (m3/Mg MSW)'] = (self._param3['Annual Precipitation (mm)'].values/1000)*(self._param3['Percent of Precipitation that Becomes Leachate (%)'].values/100)*(10000/LF_msw_acre)
        self._param3['Collected Leachate (m3/Mg MSW)'] = self._param3['Generated Leachate (m3/Mg MSW)'].values * self._param3['Leachate Collection Efficiency (%)'].values
        self._param3['Recirculated Leachate (m3/Mg MSW)'] = self._param3['Generated Leachate (m3/Mg MSW)'].values * self._param3['fraction of Leachate that is Recirculated'].values
        self._param3['Treated Leachate (m3/Mg MSW)'] = self._param3['Collected Leachate (m3/Mg MSW)'].values * self._param3['farction of Collected Leachate that is Sent to WWTP'].values
        self._param3['Fugitive Leachate  (m3/Mg MSW)'] = self._param3['Generated Leachate (m3/Mg MSW)'].values - self._param3['Treated Leachate (m3/Mg MSW)'].values -self._param3['Recirculated Leachate (m3/Mg MSW)'].values

### COD and BOD slope
        self._param3['Slope of BOD Concentration vs. Time (kg/L-yr)'] = self._param3['year'].apply(lambda x:
                                                                                        (self.InputData.BOD['LF_BOD_con2']['amount']-self.InputData.BOD['LF_BOD_con1']['amount'])/self.InputData.BOD['LF_BOD2']['amount'] if x <= self.InputData.BOD['LF_BOD2']['amount'] else
                                                                                        (self.InputData.BOD['LF_BOD_con4']['amount']-self.InputData.BOD['LF_BOD_con3']['amount'])/(self.InputData.BOD['LF_BOD4']['amount']-self.InputData.BOD['LF_BOD2']['amount']) if x <= self.InputData.BOD['LF_BOD4']['amount'] else
                                                                                        (self.InputData.BOD['LF_BOD_con6']['amount']-self.InputData.BOD['LF_BOD_con5']['amount'])/(self.InputData.BOD['LF_BOD6']['amount']-self.InputData.BOD['LF_BOD4']['amount']) if x <= self.InputData.BOD['LF_BOD6']['amount'] else
                                                                                        0).values
        self._param3['Slope of COD Concentration vs. Time (kg/L-yr)'] = self._param3['year'].apply(lambda x:
                                                                                        (self.InputData.COD['LF_COD_con2']['amount']-self.InputData.COD['LF_COD_con1']['amount'])/self.InputData.COD['LF_COD2']['amount'] if x <= self.InputData.COD['LF_COD2']['amount'] else
                                                                                        (self.InputData.COD['LF_COD_con4']['amount']-self.InputData.COD['LF_COD_con3']['amount'])/(self.InputData.COD['LF_COD4']['amount']-self.InputData.COD['LF_COD2']['amount']) if x <= self.InputData.COD['LF_COD4']['amount'] else
                                                                                        (self.InputData.COD['LF_COD_con6']['amount']-self.InputData.COD['LF_COD_con5']['amount'])/(self.InputData.COD['LF_COD6']['amount']-self.InputData.COD['LF_COD4']['amount']) if x <= self.InputData.COD['LF_COD6']['amount'] else
                                                                                        0).values
### Concentration of other effluents in leachate  (kg/L) 
# Only COD and BOD concentrations are calculated, for the other ones, data is in the ('LF_Leachate_Coeff.xlsx')                                                                                         
        self.lcht_conc = pd.DataFrame(np.array([np.ones(self.timescale-1)*self.lcht_coef['Concentrations (kg/L)'][i] for i in self.lcht_coef.index]).T,\
                                      index = np.arange(1,self.timescale),columns =self.lcht_coef['Emission'].values)
        
### Concentration of BOD and COD in leachate 
        self.lcht_conc['BOD5, Biological Oxygen Demand'] = self._param3['year'].apply(lambda x:
                                                                                        (self._param3['Slope of BOD Concentration vs. Time (kg/L-yr)'][x] * (-x) + self.InputData.BOD['LF_BOD_con1']['amount']) if x <= self.InputData.BOD['LF_BOD2']['amount'] else
                                                                                        (self._param3['Slope of BOD Concentration vs. Time (kg/L-yr)'][x] * (x-self.InputData.BOD['LF_BOD2']['amount']) + self.InputData.BOD['LF_BOD_con3']['amount']) if x <= self.InputData.BOD['LF_BOD4']['amount'] else
                                                                                        (self._param3['Slope of BOD Concentration vs. Time (kg/L-yr)'][x] * (x-self.InputData.BOD['LF_BOD4']['amount']) + self.InputData.BOD['LF_BOD_con5']['amount']) if x <= self.InputData.BOD['LF_BOD6']['amount'] else
                                                                                        0) .values
        
        self.lcht_conc['COD, Chemical Oxygen Demand'] = self._param3['year'].apply(lambda x:
                                                                                        (self._param3['Slope of COD Concentration vs. Time (kg/L-yr)'][x] * (-x) + self.InputData.COD['LF_COD_con1']['amount']) if x <= self.InputData.COD['LF_COD2']['amount'] else
                                                                                        (self._param3['Slope of COD Concentration vs. Time (kg/L-yr)'][x] * (x-self.InputData.COD['LF_COD2']['amount']) + self.InputData.COD['LF_COD_con3']['amount']) if x <= self.InputData.COD['LF_COD4']['amount'] else
                                                                                        (self._param3['Slope of COD Concentration vs. Time (kg/L-yr)'][x] * (x-self.InputData.COD['LF_COD4']['amount']) + self.InputData.COD['LF_COD_con5']['amount']) if x <= self.InputData.COD['LF_COD6']['amount'] else
                                                                                        self.InputData.COD['LF_COD_con7']['amount']).values

### Fugitive Leachate Emissions (leaks through liner) (kg/Mg MSW)
        self._Fugitive_Leachate = self.lcht_conc.multiply(self._param3['Fugitive Leachate  (m3/Mg MSW)'].values,axis=0).sum()*1000
        
### Post-treatment effluent emissions (kg/Mg MSW)       
        Effluent = pd.Series(np.multiply(np.multiply(self.lcht_conc.values.T,self._param3['Treated Leachate (m3/Mg MSW)'].values).sum(axis=1),1-self.lcht_coef['Removal Efficiency (%)'].values/100)*1000,index=self.lcht_coef['Emission'].values)
       
        self.Surface_water_emission = self.lcht_Alloc.values*Effluent.values
        self.Surface_water_emission = pd.DataFrame(self.Surface_water_emission,index = self.Index,columns = self.lcht_coef['Emission'].values+"_ to SW")
        
        key2=zip(self.Surface_water_emission.columns ,self.lcht_coef['Surface_water'].values)
        self._key2 = dict(key2)

        
        self.Ground_water_emission = self.lcht_Alloc.values*self._Fugitive_Leachate.values
        self.Ground_water_emission = pd.DataFrame(self.Ground_water_emission,index = self.Index,columns = self.lcht_coef['Emission'].values+"_ to GW")
        
        key3=zip(self.Ground_water_emission.columns ,self.lcht_coef['Ground_water'].values)
        self._key3 = dict(key3)


### Electricity Consumption for Leachate Treatment
        BOD_removed = (sum(self.lcht_conc['BOD5, Biological Oxygen Demand'].values*self._param3['Treated Leachate (m3/Mg MSW)'].values)*1000-Effluent['BOD5, Biological Oxygen Demand'])
        BOD_elec = BOD_removed * self.InputData.BOD['LF_lcht_ec']['amount']
        Pump_elec_per_litr = self.InputData.lcht_pump['leachAirPerLeach']['amount'] *(1/self.InputData.lcht_pump['leachCompPowReq']['amount'] )*(1/28.32)*(1/(60*24*365.25))*(self.InputData.lcht_pump['leachCompLoad']['amount'] /100)*(100/self.InputData.lcht_pump['leachEff']['amount'])*8766/1.341    
        Pump_elec = sum(self._param3['Collected Leachate (m3/Mg MSW)'].values * 1000 * Pump_elec_per_litr)
        Leachate_elec = self.lcht_Alloc['BOD5, Biological Oxygen Demand']*BOD_elec + Pump_elec

        #Adding Blower electricity use to LCI
        self.LCI.add('Electricity_consumption',Leachate_elec.values)

### List of metals in Leachate
        metals = ['Arsenic, ion','Barium','Cadmium, ion','Chromium, ion','Lead','Mercury','Selenium','Silver, ion']
        
### Calculating Slude generation and transport
        LF_sldg_BOD = self.InputData.BOD['LF_sldg_per_BOD']['amount'] * BOD_removed 
        LF_sldg_PO4 = Effluent['Phosphate']*(self.InputData.Leachate['LF_eff_PO4']['amount']/100)/((100-self.InputData.Leachate['LF_eff_PO4']['amount'])/100)
        LF_sldg_mtls = sum(Effluent[metals])*(self.InputData.Leachate['LF_eff_mtls']['amount']/100)/((100-self.InputData.Leachate['LF_eff_mtls']['amount'])/100)
        LF_sldg_tss = Effluent['Suspended solids, unspecified']*(self.InputData.Leachate['LF_eff_TSS']['amount']/100)/((100-self.InputData.Leachate['LF_eff_TSS']['amount'])/100)
        
        self.sludge['sludge generated from BOD removal'] = self.lcht_Alloc['BOD5, Biological Oxygen Demand'].values * LF_sldg_BOD
        
        self.sludge['sludge generated from phosphate removal'] = self.lcht_Alloc['Phosphate'].values * LF_sldg_PO4
        
        self.sludge['sludge generated from metals removal'] = (self.lcht_Alloc[metals].values*(Effluent[metals].values*(self.InputData.Leachate['LF_eff_mtls']['amount']/100)/((100-self.InputData.Leachate['LF_eff_mtls']['amount'])/100))).sum(axis=1)
        
        self.sludge['sludge generated from suspended solids removal'] = self.lcht_Alloc['Suspended solids, unspecified'].values * LF_sldg_tss
        
        self.sludge['total sludge generated'] = self.sludge['sludge generated from BOD removal'].values+self.sludge['sludge generated from phosphate removal'].values+\
                                                self.sludge['sludge generated from metals removal'].values+self.sludge['sludge generated from suspended solids removal'].values
                                                
        self.sludge['Medium-Heavy Duty Transportation'] = self.sludge['total sludge generated'].values/1000 * self.InputData.Leachate['dis_POTW']['amount']                            
        self.LCI.add('Internal_Process_Transportation_Medium_Duty_Diesel_Truck',self.sludge['Medium-Heavy Duty Transportation'].values*1000)
            
# =============================================================================
#
### Life-Cycle Costs
#
# =============================================================================
### Add economic data
    def _Add_cost(self):
        self.cost_DF = pd.DataFrame(index=self.Index)
        self.cost_DF[('biosphere3', 'Operational_Cost')] = [self.InputData.Operational_Cost[y]['amount'] for y in self.Index]

# =============================================================================
#
### Life-Cycle Inventory
#
# =============================================================================
    def _Material_energy_use(self):
### Electricity Use        
        #Building electricity use
        bld_elec = 0.596  #kWh/Mg
        self.LCI.add('Electricity_consumption',bld_elec)
### Fuel
        #Diesel	
        dies_pc=2.342866	#L/Mg
        self.LCI.add('Equipment_Diesel',dies_pc)
        #Gasoline
        gaso_pc=0.000616	#L/Mg
        self.LCI.add('Equipment_Gasoline',gaso_pc)
### Transportation
        #Heavy duty truck transportation required
        HD_trans = 0.1409593	#Mg-km/Mg
        self.LCI.add('Internal_Process_Transportation_Heavy_Duty_Diesel_Truck',HD_trans*1000)
        #Medium duty transportation required
        MD_trans = 	2.1137375	#Mg-km/Mg
        self.LCI.add('Internal_Process_Transportation_Medium_Duty_Diesel_Truck',MD_trans*1000)
#Heavy duty truck transportation required
        HD_trans_empty  = 4.02741E-03	#Mg-km/Mg
        self.LCI.add('Empty_Return_Heavy_Duty_Diesel_Truck',HD_trans_empty*1000)
        #Medium duty transportation required
        MD_trans_empty = 8.80724E-02	#Mg-km/Mg
        self.LCI.add('Empty_Return_Medium_Duty_Diesel_Truck',MD_trans_empty*1000)
### Material Use
        #HDPE liner	
        op_HDPE_Liner = 4.69579E-03  #kg/Mg
        self.LCI.add('HDPE_Liner',op_HDPE_Liner)
        #HDPE cover	
        cl_HDPE_Liner=1.15879E-01 #kg/Mg
        self.LCI.add('HDPE_Liner',cl_HDPE_Liner)
        #Geotextile
        cl_GeoTxt=1.14786E-02 #kg/Mg
        self.LCI.add('Geotextile',cl_GeoTxt)
        #HDPE pipe	
        cl_HDPE_Pipe=1.3349E-03 #m/Mg
        self.LCI.add('HDPE_Pipe',cl_HDPE_Pipe)
        #PVC pipe	
        cl_PVC_Pipe=2.5680E-04	#m/Mg
        self.LCI.add('PVC_Pipe',cl_PVC_Pipe)
        #HDPE cover	
        pc_HDPE_Liner=3.8626E-04 #kg/Mg
        self.LCI.add('HDPE_Liner',pc_HDPE_Liner)
        #Geotextile	
        pc_GeoTxt=3.8262E-05 #kg/Mg
        self.LCI.add('Geotextile',pc_GeoTxt)

        self._key4 = {'Electricity_production':('Technosphere', 'Electricity_production'),     
                    'Electricity_consumption':('Technosphere', 'Electricity_consumption'),
                    'Equipment_Diesel':('Technosphere', 'Equipment_Diesel'),
                    'Equipment_Gasoline':('Technosphere', 'Equipment_Gasoline'),
                    'Internal_Process_Transportation_Heavy_Duty_Diesel_Truck':('Technosphere', 'Internal_Process_Transportation_Heavy_Duty_Diesel_Truck'),
                    'Internal_Process_Transportation_Medium_Duty_Diesel_Truck':('Technosphere', 'Internal_Process_Transportation_Medium_Duty_Diesel_Truck'),
                    'Empty_Return_Heavy_Duty_Diesel_Truck':('Technosphere', 'Empty_Return_Heavy_Duty_Diesel_Truck'),
                    'Empty_Return_Medium_Duty_Diesel_Truck':('Technosphere', 'Empty_Return_Medium_Duty_Diesel_Truck'),
                    'HDPE_Liner':('Technosphere', 'HDPE_Liner'),
                    'Geotextile':('Technosphere', 'Geotextile'),
                    'HDPE_Pipe':('Technosphere', 'HDPE_Pipe'),
                    'PVC_Pipe':('Technosphere', 'PVC_Pipe')}

# =============================================================================
#
### Report
#
# =============================================================================
    def report(self):
### Output
        self.LF = {}
        Waste={}
        Technosphere={}
        self.LF["process name"] = 'LF'
        self.LF["Waste"] = Waste
        self.LF["Technosphere"] = Technosphere
        
        for x in [Waste,Technosphere]:
            for y in self.Index:
                x[y]={}
              
### Output Biosphere Database
        LCI_DF = self.LCI.report()       
        for y in self.Index:
            # Technosphere
            for x in self._key4:
                Technosphere[y][self._key4[x]]= LCI_DF[x][y]

        self.bio_rename_dict = dict(self._key1, **self._key2)
        self.bio_rename_dict = dict(self.bio_rename_dict , **self._key3)
        self.bio_rename_dict[('biosphere3','Operational_Cost')]=('biosphere3','Operational_Cost')
        self.LCI_bio = pd.concat([self.emission_to_air, self.Surface_water_emission, self.Ground_water_emission],axis=1)
        self.LCI_bio = self.LCI_bio.rename(columns = self.bio_rename_dict)
        self.LCI_bio_index = True
        keys = list(self.bio_rename_dict.keys())
        for x in keys:
            if "biosphere3" not in str(self.bio_rename_dict[x]):
                self.bio_rename_dict.pop(x)
        self.LCI_bio[('biosphere3','Operational_Cost')] = self.cost_DF[('biosphere3','Operational_Cost')].values
        self.Biosphere = self.LCI_bio[self.bio_rename_dict.values()].transpose().to_dict()
        self.LF["Biosphere"] = self.Biosphere
            
        return(self.LF)
        

### Calc function _ Do all the calculations 
    def calc(self):
        self._Cal_LFG_Col_Ox()
        self._Cal_LFG()
        self._Leachate()
        self._Material_energy_use()
        self._Add_cost()

### setup for Monte Carlo simulation   
    def setup_MC(self,seed=None):
        self.InputData.setup_MC(seed)

### Calculate based on the generated numbers   
    def MC_calc(self):      
        input_list = self.InputData.gen_MC()
        self.calc()
        return(input_list)


### LCI class
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
    
    def report(self):
        return(pd.DataFrame(self.LCI[:,:len(self.ColDict)],columns=list(self.ColDict.keys()),index=self.Index))

    def report_T(self):
        return(pd.DataFrame(self.LCI[:,:len(self.ColDict)].transpose(),index=list(self.ColDict.keys()),columns=self.Index))
