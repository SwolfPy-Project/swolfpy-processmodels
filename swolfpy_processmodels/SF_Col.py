# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import pandas as pd
from swolfpy_inputdata import SF_Col_Input
from .ProcessModel import ProcessModel
import numpy_financial as npf
import numpy as np
import warnings


class SF_Col(ProcessModel):
    Process_Type = 'Collection'
    def __init__(self, process_name, Collection_scheme, Treatment_processes=None, Distance=None, CommonDataObjct=None, input_data_path=None):
        ### Importing the CommonData and Input data for SF_collection
        super().__init__(process_name, CommonDataObjct)
    
        self.InputData= SF_Col_Input(input_data_path, process_name=self.process_name, CommonDataObjct=CommonDataObjct)
        self.process_name = process_name
        
        if Treatment_processes:
            self.Treat_proc = Treatment_processes
            if Distance:
                self.Distance = Distance
            else:
                raise Exception('User should define both Distance and Treatment_processes together')
        else:
            self.Treat_proc =False
            
### Read Material properties related to the process        
        self.process_data = self.InputData.process_data

### Read input data        
        self.col= self.InputData.col

        self.col_schm = Collection_scheme

    @staticmethod
    def scheme():
        """
        Retrun the dictionary for collection_scheme as a sample. all the contributions are zero; user should define according to his/her case. 
        """
        SepOrg = ['N/A', 'SSYW', 'SSYWDO']
        SepRec = ['N/A', 'SSR', 'DSR', 'MSR', 'MSRDO']
        scheme = {}
        for i in SepOrg:
            for j in SepRec:
                scheme[('RWC', i, j)] = 0
        for i in SepOrg:
            scheme[('REC_WetRes', i, 'REC_WetRes')] = 0
        for j in SepRec:
            scheme[('SSO_DryRes', 'SSO_DryRes', j)] = 0
        for i in ['N/A', 'SSYWDO']:
            for j in ['N/A', 'MSRDO']:
                scheme[('MRDO', i, j)] = 0
        return(scheme)

    def _normalize_scheme(self, DropOff=True, warn=True):
        """
        Used in optimization. 
        """
        if not DropOff:
            for k in self.col_schm:
                if 'DO' in k:
                    self.col_schm[k] = 0

        contribution =  sum(self.col_schm.values())
        if abs(contribution - 1) > 0.01:
            if warn:
                warnings.warn('Error in collection scheme [Sum(Contribution) != 1]!')
            for k, v in self.col_schm.items():
                self.col_schm[k] = v/contribution

    def calc_composition(self):
        self._col_schm = {'RWC':{'Contribution':0,'separate_col':{'SSR':0,'DSR':0,'MSR':0,'MSRDO':0,'SSYW':0,'SSYWDO':0}},
          'SSO_DryRes':{'Contribution':0,'separate_col':{'SSR':0,'DSR':0,'MSR':0,'MSRDO':0,'SSYW':0,'SSYWDO':0}},
          'REC_WetRes':{'Contribution':0,'separate_col':{'SSR':0,'DSR':0,'MSR':0,'MSRDO':0,'SSYW':0,'SSYWDO':0}},
          'MRDO':{'Contribution':0,'separate_col':{'SSR':0,'DSR':0,'MSR':0,'MSRDO':0,'SSYW':0,'SSYWDO':0}}}
        
        for k, v in self.col_schm.items():
            if 'RWC' in k:
                self._col_schm['RWC']['Contribution'] += v
            elif 'SSO_DryRes' in k:
                self._col_schm['SSO_DryRes']['Contribution'] += v
            elif 'REC_WetRes' in k:
                self._col_schm['REC_WetRes']['Contribution'] += v
            elif 'MRDO' in k:
                self._col_schm['MRDO']['Contribution'] += v
            else:
                raise Exception('Error in collection scheme keys')

        for k, v in self.col_schm.items():
            if v > 0:
                if k[1] not in ['N/A', 'SSO_DryRes', 'REC_WetRes']:
                    self._col_schm[k[0]]['separate_col'][k[1]] += v/self._col_schm[k[0]]['Contribution']
                if k[2] not in ['N/A', 'SSO_DryRes', 'REC_WetRes']:
                    self._col_schm[k[0]]['separate_col'][k[2]] += v/self._col_schm[k[0]]['Contribution']

        #Single Family Residential Waste Generation Rate (kg/household-week)
        g_res = 7*self.InputData.Col['res_per_dwel']['amount']*self.InputData.Col['res_gen']['amount']
        gen_per_week = g_res * self.process_data['Comp']
        total_waste_gen = g_res * self.InputData.Col['houses_res']['amount'] * 52 /1000

        
        #Check for Leave Vaccum
        self.process_data['LV'] = 0
        if self.InputData.Col['Leaf_vacuum']['amount']==1:
            LV_gen = self.process_data.loc['Yard_Trimmings_Leaves','Comp']*self.InputData.Col['res_gen']['amount'] * 365
            LV_col = self.InputData.Col['Leaf_vacuum_amount']['amount']*1000/self.InputData.Col['res_pop']['amount']
            self.process_data.loc['Yard_Trimmings_Leaves','LV'] = 1 if LV_gen <= LV_col else LV_col/LV_gen
            for j in ['RWC','SSO_DryRes','REC_WetRes','MRDO']:
                self._col_schm[j]['separate_col']['LV']=1 
        else:
            for j in ['RWC','SSO_DryRes','REC_WetRes','MRDO']:
                self._col_schm[j]['separate_col']['LV']=0
        self.col.loc['LV','Fr'] = self.InputData.Col['LV_serv_times']['amount']/self.InputData.Col['LV_serv_pd']['amount']
                

        # Total fraction where this service is offered        
        self.col_proc = {'RWC':self._col_schm['RWC']['Contribution'],
                        'SSO':self._col_schm['SSO_DryRes']['Contribution'],
                        'DryRes':self._col_schm['SSO_DryRes']['Contribution'],
                        'REC':self._col_schm['REC_WetRes']['Contribution'],
                        'WetRes':self._col_schm['REC_WetRes']['Contribution'],
                        'MRDO':self._col_schm['MRDO']['Contribution']}
        for i in ['LV','SSR','DSR','MSR','MSRDO','SSYW','SSYWDO']:
            self.col_proc[i] = sum([self._col_schm[j]['Contribution']*self._col_schm[j]['separate_col'][i] for j in ['RWC','SSO_DryRes','REC_WetRes','MRDO']])
            
        #Is this collection process offered? (1: in use, 0: not used)
        self.P_use = {}
        for j in self.col_proc.keys():
            self.P_use[j]= 1 if self.col_proc[j]>0 else 0
        
        #SWM Mass separated by collection process (Calculation)
        columns = ['RWC', 'SSR', 'DSR', 'MSR', 'LV', 'SSYW', 'SSO', 'DryRes', 'REC', 'WetRes', 'MRDO', 'SSYWDO', 'MSRDO']
        self.mass=pd.DataFrame(index =self.Index,columns=columns)
        
        for i in ['SSR','DSR','MSR','SSYW','SSO','REC','SSYWDO','MSRDO']:
            self.mass[i] = g_res * self.process_data[i] * self.process_data['Comp'] * self.P_use[i]
            self.mass.loc['Yard_Trimmings_Leaves',i] *= (1-self.process_data.loc['Yard_Trimmings_Leaves','LV'] )
        self.mass['LV'] = g_res * self.process_data['LV'] * self.process_data['Comp'] * self.P_use['LV']

                
        def separate_col_mass(j):
            mass = pd.Series(data=np.zeros(len(self.mass)) ,index=self.mass.index)
            for i in ['SSR', 'DSR', 'MSR', 'LV', 'SSYW', 'SSYWDO', 'MSRDO']:
                mass += self.mass[i] * self._col_schm[j]['separate_col'][i]
            return(mass)

        # Calculating the residual waste after separate collection
        for j in ['RWC','MRDO']:
            self.mass[j]= (g_res * self.process_data[j] * self.process_data['Comp'] - separate_col_mass(j))* self.P_use[j]

        # SSO_DryRes
        index_with_error = self.mass['SSO'] + separate_col_mass('SSO_DryRes') > gen_per_week
        self.mass.loc[index_with_error, 'SSO'] = gen_per_week[index_with_error] - separate_col_mass('SSO_DryRes')[index_with_error]
        self.mass['DryRes']= (g_res * self.process_data['DryRes'] * self.process_data['Comp'] - separate_col_mass('SSO_DryRes') - self.mass['SSO'])* self.P_use['DryRes']

        # REC_WetRes
        index_with_error = self.mass['REC'] + separate_col_mass('REC_WetRes') > gen_per_week
        self.mass.loc[index_with_error, 'REC'] = gen_per_week[index_with_error] - separate_col_mass('REC_WetRes')[index_with_error]
        self.mass['WetRes']= (g_res * self.process_data['WetRes'] * self.process_data['Comp'] - separate_col_mass('REC_WetRes') - self.mass['REC'])* self.P_use['WetRes']

        #Annual Mass Flows (Mg/yr)
        self.col_massflow=pd.DataFrame(index =self.Index)
        for i in ['RWC','SSR','DSR','MSR','MSRDO','LV','SSYW','SSYWDO','SSO','DryRes','REC','WetRes','MRDO','SSYWDO','MSRDO']:
            self.col_massflow[i]=self.mass[i] * self.InputData.Col['houses_res']['amount'] * 52/1000 * self.col_proc[i]
        

        # Check for negative mass flows
        if (self.col_massflow.values<0).any().any():
            #raise Exception(f'Negative mass flows in collection model [{self.process_name}]!')
            warnings.warn('Negative mass flows in collection model [{self.process_name}]!')

        #Check generated mass = Collected mass
        ratio = sum(self.col_massflow.sum())/total_waste_gen
        if ratio > 1.01 or ratio < 0.99:
            #raise Exception(f'Mass balance error in collection model [{self.process_name}]!')
            warnings.warn(f'Mass balance error in collection model [{self.process_name}]!')

        #Volume Composition of each collection process for each sector
        mass_to_cyd = self.process_data['Bulk_Density'].apply(lambda x: 1/x*1.30795 if x >0 else 0)
        for i in ['RWC','SSR','DSR','MSR','LV','SSYW','MRDO','SSYWDO','MSRDO']:
            vol = sum(self.mass[i]*mass_to_cyd)  # Unit kg/cyd
            if vol > 0 :
                self.col.loc[i,'den_c'] = sum(self.mass[i]*2.205/ vol)  # Unit lb/cyd
            else:
                self.col.loc[i,'den_c'] = 0
        for i,j in [('SSO','DryRes'),('REC','WetRes')]:
            vol = sum((self.mass[i]+self.mass[j])*mass_to_cyd)  # Unit kg/cyd
            if vol > 0 :
                self.col.loc[i,'den_c'] = sum((self.mass[i]+self.mass[j])*2.205/ vol)  # Unit lb/cyd
            else:
                self.col.loc[i,'den_c'] = 0

    def find_destination(self,product,Treatment_processes):
        destination={}
        for P in Treatment_processes:
            if product in Treatment_processes[P]['input_type']:
                destination[P] = self.Distance.Distance[(self.process_name,P)]['Heavy Duty Truck'] / 1.60934 # Convert the distance from km to mile
        return(destination)

### calculating LCI and cost for different locations
    def calc_destin(self):
        if self.Treat_proc:
            self.dest = {}
            self.result_destination={}
            for i in ['RWC','SSR','DSR','MSR','MSRDO','LV','SSYW','SSYWDO','SSO','DryRes','REC','WetRes','MRDO','SSYWDO','MSRDO']:
                self.dest[i]= self.find_destination(i,self.Treat_proc)   
                self.result_destination[i] = {}

            # Number of times we need to run the collection
            n_run= max([len(self.dest[i]) for i in self.dest.keys()])
            
            self._mean_dist_WetDry = {}
            for w, d in [('REC', 'WetRes'), ('SSO', 'DryRes')]:
                if len(self.dest[w]) > 0 and len(self.dest[d]) > 0:
                    self._mean_dist_WetDry[w] =  np.mean(list(self.dest[w].values())) + np.mean(list(self.dest[d].values())) * 0.3
                if len(self.dest[w]) > 0 and len(self.dest[d]) == 0:
                    self._mean_dist_WetDry[w] =  np.mean(list(self.dest[w].values())) + 7
                if len(self.dest[w]) == 0 and len(self.dest[d]) >= 0:
                    self._mean_dist_WetDry[w] =  np.mean(list(self.dest[d].values())) + 7                     

            for i in range(n_run):
                for j in ['RWC','SSR','DSR','MSR','MSRDO','LV','SSYW','SSYWDO','MRDO','SSYWDO','MSRDO']:
                    if len(self.dest[j]) > i:
                        self.col['Drf'][j] = self.dest[j][list(self.dest[j].keys())[i]] # Distance btwn collection route and destination  
                        self.col['Dfg'][j] = (self.dest[j][list(self.dest[j].keys())[i]] + # Distance between destination and garage
                                              self.col['Dgr'][j])

                for j in ['SSO', 'REC']:
                    if len(self.dest[j]) > i:
                        self.col['Drf'][j] = self._mean_dist_WetDry[w] # Distance btwn collection route and destination  
                        self.col['Dfg'][j] = self._mean_dist_WetDry[w] + self.col['Dgr'][j] # Distance between destination and garage
                        
                self.calc_lci()
                for j in self.dest.keys():
                    if len(self.dest[j]) > i:
                        self.result_destination[j][list(self.dest[j].keys())[i]] ={}
                        #if self.output['FuelMg'][j] + self.output['FuelMg_dov'][j] !=0:
                        self.result_destination[j][list(self.dest[j].keys())[i]][('Technosphere', 'Equipment_Diesel')]=self.output['FuelMg'][j] + self.output['FuelMg_dov'][j]
                        #if self.output['FuelMg_CNG'][j]!=0:
                        self.result_destination[j][list(self.dest[j].keys())[i]][('Technosphere', 'Equipment_CNG')]=self.output['FuelMg_CNG'][j]
                        #if self.output['ElecMg'][j]!=0:
                        self.result_destination[j][list(self.dest[j].keys())[i]][('Technosphere', 'Electricity_consumption')]=self.output['ElecMg'][j]
                        
                        self.result_destination[j][list(self.dest[j].keys())[i]][('biosphere3', 'Operational_Cost')]=self.output['C_collection'][j]
        else:
            self.calc_lci()
            self.result_destination={}

    def calc_lci(self):
        #Selected compartment compaction density  (lb/yd3)
        #Override calculated density den_c and use an average assumed in-truck density
        self.col['d_msw']= self.col[['den_asmd','den_c']].apply(lambda x: x[0] if x[0]>0 else x[1],axis=1)        
        #Travel time between service stops, adjusted based on participation                (min/stop)
        self.col['Tbtw'] = self.col['Dbtw'] / self.col['Vbet'] * 60
        #Travel time btwn route and disposal fac.       (min/trip)
        self.col['Trf'] = self.col['Drf'] / self.col['Vrf'] * 60        
        #Time from grg to 1st collection route     (min/day-vehicle)
        self.col['Tgr'] = self.col['Dgr'] / self.col['Vgr'] * 60        
        #Time from disposal fac. to garage    (min/day-vehicle)
        self.col['Tfg'] = self.col['Dfg'] / self.col['Vfg'] * 60

        for i in ['RWC','SSR','DSR','MSR','LV','SSYW','MRDO','SSYWDO','MSRDO']:
            self.col.loc[i,'option_frac'] = self.col_proc[i]
            self.col.loc[i,'mass'] = sum(self.mass[i])
        # Revising mass of SSO_DryRes and REC_WetRec 
        for i,j in [('SSO','DryRes'),('REC','WetRes')]:
            self.col.loc[i,'mass'] = sum(self.mass[i] + self.mass[j])
        # Revising mass of LV collection - as it happens only in LV_serv_pd
        self.col.loc['LV','mass'] = self.col.loc['LV','mass']*52/self.InputData.Col['LV_serv_pd']['amount']            

### Calculations for collection vehicle activities
        #houses per trip (Volume limited) and (mass limited)
        for i in ['RWC','SSR','DSR','MSR','SSYW','SSO','REC','LV']:
            if not self.col.loc[i,'mass'] > 0:
                self.col.loc[i,'Ht_v']=0
                self.col.loc[i,'Ht_m']=0
            else:
                self.col.loc[i,'Ht_v']  = self.col.loc[i,'Ut']*self.col.loc[i,'Vt']*self.col.loc[i,'d_msw']*0.4536*self.col.loc[i,'Fr'] /self.col.loc[i,'mass']
                self.col.loc[i,'Ht_m']  = self.col.loc[i,'max_weight']*self.col.loc[i,'Fr']*1000 /  self.col.loc[i,'mass']                
            #households per trip (limited by mass or volume)
            if self.col.loc[i,'wt_lim'] == 1:
                self.col.loc[i,'Ht'] = min(self.col.loc[i,'Ht_v'],self.col.loc[i,'Ht_m'])
            else:
                self.col.loc[i,'Ht'] = self.col.loc[i,'Ht_v']

        #time per trip (min/trip) -- collection+travel+unload time
        self.col['Tc'] = self.col['Tbtw']*(self.col['Ht']/self.col['HS']-1)+self.col['TL']*self.col['Ht']/self.col['HS']+2*self.col['Trf']+self.col['S']

        #trips per day per vehicle (trip/day-vehicle)
        self.col['RD'] =  (self.col['WV']*60-(self.col['F1_']+self.col['F2_']+self.col['Tfg'])-0.5*(self.col['Trf']+self.col['S']))/self.col['Tc']
        if any(self.col['RD']<0):
            raise Exception("Travelling time is too long that the truck cannot make a loop trip in one day!")
        
        
        
        #daily weight of refuse collected per vehicle (Mg/vehicle-day)
        self.col['RefD'] = self.col['Ht'] * self.col['mass']/self.col['Fr']/1000 * self.col['RD']
 
        #number of collection stops per day (stops/vehicle-day)
        for i in ['RWC','SSR','DSR','MSR','SSYW','SSO','REC','LV']:
            self.col['SD'] = self.col['Ht']*self.col['RD']/self.col['HS']

### Calculations for collection vehicle activities  (Drop off)
        for i in ['MRDO','SSYWDO','MSRDO']:
            #volume of recyclables deposited at drop-off site per week (cy/week-house)
            self.col.loc[i,'Ht'] = sum(self.mass[i])*self.InputData.Col['houses_res']['amount']*self.col_proc[i]/0.4536 /self.col['d_msw'][i]

            #collection vehicle trips per week (trips/week)
            self.col.loc[i,'DO_trip_week'] =  self.col['Ht'][i] / (self.col['Vt'][i]*self.col['Ut'][i])

            #time per trip (min/trip) -- load+travel+unload time
            self.col.loc[i,'Tc'] = self.col['TL'][i]+2*self.col['Trf'][i]+self.col['S'][i]

            #trips per day per vehicle (trip/day-vehicle)
            self.col.loc[i,'RD'] = (self.col['WV'][i]*60-(self.col['F1_'][i]+self.col['F2_'][i]+self.col['Tfg'][i]+self.col['Tgr'][i])+self.col['Trf'][i])/self.col['Tc'][i]

            #daily weight of refuse collected per vehicle (tons/day-vehicle)
            self.col.loc[i,'RefD'] = self.col['Vt'][i]*self.col['Ut'][i]*self.col['d_msw'][i]*0.4536/1000*self.col['RD'][i]
            #number of collection stops per day (stops/vehicle-day) (1 stop per trip)
            self.col.loc[i,'SD'] = self.col['RD'][i]

### Daily collection vehicle activity times        
        #loading time at collection stops (min/day-vehicle) & loading time at drop-off site (min/day-vehicle)
        self.col['LD'] = self.col['SD']*self.col['TL']

        #travel time between collection stops (min/day-vehicle)
        self.col['Tb'] = self.col['SD'].apply(lambda x: 0 if (x-1)<1 else x-1)*self.col['Tbtw']

        #travel time between route and disposal facility (min/day-vehicle)
        self.col['F_R'] = (2*self.col['RD']+0.5)*self.col['Trf']

        #unloading time at disposal facility (min/day-vehicle)
        self.col['UD'] = (self.col['RD']+0.5)*self.col['S']

        for i in ['MRDO','SSYWDO','MSRDO']:
            self.col.loc[i,'Tb'] = 0

            #travel time between disposal facility and drop-off site (min/day-vehicle)
            self.col.loc[i,'F_R'] = (2*self.col['RD'][i]-1)*self.col['Trf'][i]

            #unloading time at disposal facility (min/day-vehicle)
            self.col.loc[i,'UD'] = self.col['RD'][i] *self.col['S'][i]                                                

### Daily fuel usage - Diesel
        for i in ['RWC','SSR','DSR','MSR','LV','SSYW','SSO','DryRes','REC','WetRes','MRDO','SSYWDO','MSRDO']:
            if self.col.loc[i,'MPG_all'] != 0:
                #from garage to first collection route (gallons/day-vehicle)
                self.col.loc[i,'diesel_gr'] = self.col['Fract_Dies'][i] * self.col['Dgr'][i] /self.col['MPG_all'][i]
                #break time, if spent idling
                self.col.loc[i,'diesel_idl'] = 0
                #from first through last collection stop (gallons/day-vehicle)
                if i in ['MRDO','SSYWDO','MSRDO']:
                    self.col.loc[i,'diesel_col'] = 0
                else:
                    self.col.loc[i,'diesel_col'] = self.col['Fract_Dies'][i] * self.col['Dbtw'][i] * self.col['SD'][i] /self.col['MPG_all'][i]
                #between disposal facility and route (gallons/day-vehicle)
                self.col.loc[i,'diesel_rf'] = self.col['Fract_Dies'][i] * self.col['F_R'][i]/60 * self.col['Vrf'][i]  /self.col['MPG_all'][i]
                #unloading at disposal facility (gallons/day-vehicle)
                self.col.loc[i,'diesel_ud'] = 0
                #from disposal facility to garage (gallons/day-vehicle)
                self.col.loc[i,'diesel_fg'] = self.col['Fract_Dies'][i] * self.col['Dfg'][i] /self.col['MPG_all'][i]
            else:
                self.col.loc[i,'diesel_gr'] = self.col['Fract_Dies'][i] * self.col['Dgr'][i]*((1-self.col['fDgr'][i])/self.col['MPG_urban'][i]+self.col['fDgr'][i]/self.col['MPG_highway'][i])
                self.col.loc[i,'diesel_idl'] = self.col['Fract_Dies'][i] * (self.col['F1_'][i]*self.col['F1_idle'][i] + self.col['F2_'][i]*self.col['F2_idle'][i])/60 * self.col['GPH_idle_cv'][i]
                if i in ['MRDO','SSYWDO','MSRDO']:
                    self.col.loc[i,'diesel_col'] = 0
                else:
                    self.col.loc[i,'diesel_col'] = self.col['Fract_Dies'][i] * self.col['Dbtw'][i] * self.col['SD'][i] /self.col['MPG_collection'][i]
                
                self.col.loc[i,'diesel_rf'] = self.col['Fract_Dies'][i] * self.col['F_R'][i]/60 * self.col['Vrf'][i]  *((1-self.col['fDrd'][i])/self.col['MPG_urban'][i] + self.col['fDrd'][i]/self.col['MPG_highway'][i])
                self.col.loc[i,'diesel_ud'] = self.col['Fract_Dies'][i] * self.col['UD'][i] /60 * self.col['GPH_idle_cv'][i]
                self.col.loc[i,'diesel_fg'] = self.col['Fract_Dies'][i] * self.col['Dfg'][i] *((1-self.col['fDfg'][i])/self.col['MPG_urban'][i] + self.col['fDfg'][i]/self.col['MPG_highway'][i])
            
            if self.col_proc[i]==0:
                self.col.loc[i,'FuelD'] =0
            else:
                self.col.loc[i,'FuelD'] = self.col['diesel_gr'][i] + self.col['diesel_idl'][i] + self.col['diesel_col'][i] + self.col['diesel_rf'][i] + self.col['diesel_ud'][i] + self.col['diesel_fg'][i]
### Daily fuel usage - CNG - diesel gal equivalent
        for i in ['RWC','SSR','DSR','MSR','LV','SSYW','SSO','DryRes','REC','WetRes','MRDO','SSYWDO','MSRDO']:
            if self.col.loc[i,'MPG_all_CNG'] != 0:
                #from garage to first collection route (gallons/day-vehicle)
                self.col.loc[i,'CNG_gr'] = self.col['Fract_CNG'][i] * self.col['Dgr'][i] /self.col['MPG_all_CNG'][i]
                #break time, if spent idling
                self.col.loc[i,'CNG_idl'] = 0
                #from first through last collection stop (diesel gal equivalent/day-vehicle)
                if i in ['MRDO','SSYWDO','MSRDO']:
                    self.col.loc[i,'CNG_col'] = 0
                else:
                    self.col.loc[i,'CNG_col'] = self.col['Fract_CNG'][i] * self.col['Dbtw'][i] * self.col['SD'][i] /self.col['MPG_all_CNG'][i]
                #between disposal facility and route (diesel gal equivalent/day-vehicle)
                self.col.loc[i,'CNG_rf'] = self.col['Fract_CNG'][i] * self.col['F_R'][i]/60 * self.col['Vrf'][i]  /self.col['MPG_all_CNG'][i]
                #unloading at disposal facility (diesel gal equivalent/day-vehicle)
                self.col.loc[i,'CNG_ud'] = 0
                #from disposal facility to garage (diesel gal equivalent/day-vehicle)
                self.col.loc[i,'CNG_fg'] = self.col['Fract_CNG'][i] * self.col['Dfg'][i] /self.col['MPG_all_CNG'][i]
            else:
                self.col.loc[i,'CNG_gr'] = self.col['Fract_CNG'][i] * self.col['Dgr'][i]*((1-self.col['fDgr'][i])/self.col['MPG_urban_CNG'][i]+self.col['fDgr'][i]/self.col['MPG_hwy_CNG'][i])
                self.col.loc[i,'CNG_idl'] = self.col['Fract_CNG'][i] * (self.col['F1_'][i]*self.col['F1_idle'][i] + self.col['F2_'][i]*self.col['F2_idle'][i])/60 * self.col['GPH_idle_CNG'][i]
                if i in ['MRDO','SSYWDO','MSRDO']:
                    self.col.loc[i,'CNG_col'] = 0
                else:
                    self.col.loc[i,'CNG_col'] = self.col['Fract_CNG'][i] * self.col['Dbtw'][i] * self.col['SD'][i] /self.col['MPG_col_CNG'][i]
                self.col.loc[i,'CNG_rf'] = self.col['Fract_CNG'][i] * self.col['F_R'][i]/60 * self.col['Vrf'][i]  *((1-self.col['fDrd'][i])/self.col['MPG_urban_CNG'][i] + self.col['fDrd'][i]/self.col['MPG_hwy_CNG'][i])
                self.col.loc[i,'CNG_ud'] = self.col['Fract_CNG'][i] * self.col['UD'][i] /60 * self.col['GPH_idle_CNG'][i]
                self.col.loc[i,'CNG_fg'] = self.col['Fract_CNG'][i] * self.col['Dfg'][i] *((1-self.col['fDfg'][i])/self.col['MPG_urban_CNG'][i] + self.col['fDfg'][i]/self.col['MPG_hwy_CNG'][i])
            
            if self.col_proc[i]==0:
                self.col.loc[i,'FuelD_CNG'] = 0
            else:
                self.col.loc[i,'FuelD_CNG'] = self.col['CNG_gr'][i] + self.col['CNG_idl'][i] + self.col['CNG_col'][i] + self.col['CNG_rf'][i] + self.col['CNG_ud'][i] + self.col['CNG_fg'][i]

###ENERGY CONSUMPTION
###Energy consumption by collection vehicles
        #total coll. vehicle fuel use per Mg of refuse (L/Mg)
        self.col['FuelMg'] = self.col[['FuelD','RefD']].apply(lambda x: 0 if x[1]==0 else x[0] *3.785 /x[1] , axis = 1)

        #total coll. vehicle CNG fuel use per Mg of refuse (diesel L equivalent/Mg)
        self.col['FuelMg_CNG'] = self.col[['FuelD_CNG','RefD']].apply(lambda x: 0 if x[1]==0 else x[0] *3.785 /x[1] , axis = 1)

###Energy consumption by drop-off vehicles
        for i in ['MRDO','SSYWDO','MSRDO']:
            #fuel usage per trip to drop-off site (gallons/trip)
            self.col.loc[i,'FuelT'] = self.P_use[i]*self.col['RTDdos'][i]*self.col['DED'][i]/self.col['dropoff_MPG'][i]
            
            #weight of refuse delivered per trip (kg/trip)
            self.col.loc[i,'RefT'] = sum(self.mass[i]) * self.col['Prtcp'][i] * 52 / (self.col['FREQdos'][i]*12)
            
            #total dropoff vehicle  fuel use per Mg of refuse (L/Mg)
            self.col.loc[i,'FuelMg_dov'] = 0 if self.col.loc[i,'RefT'] == 0 else self.col.loc[i,'FuelT'] * 3.785 / (self.col.loc[i,'RefT']/1000)
        
###Energy consumption by garage
        for i in ['RWC','SSR','DSR','MSR','MSRDO','LV','SSYW','SSYWDO','SSO','DryRes','REC','WetRes','MRDO','SSYWDO','MSRDO']:
            #daily electricity usage per vehicle  (kWh/vehicle-day)
            self.col.loc[i,'ElecD'] = self.P_use[i]*(self.col['grg_area'][i]*self.col['grg_enrg'][i]+self.col['off_area'][i]*self.col['off_enrg'][i])
        #electricity usage per Mg of refuse  (kWh/Mg)
        self.col['ElecMg'] = self.col[['ElecD','RefD']].apply(lambda x: 0 if x[1]==0 else x[0]/x[1] , axis = 1)
        
###Mass
        for i in ['RWC','SSR','DSR','MSR','MSRDO','LV','SSYW','SSYWDO','SSO','DryRes','REC','WetRes','MRDO','SSYWDO','MSRDO']:
            #total mass of refuse collected per year (Mg) 
            self.col.loc[i,'TotalMass'] =sum(self.col_massflow[i])

###COLLECTION COSTS
        #Breakdown of capital costs
        #annual capital cost per vehicle ($/vehicle-year)
        self.col['C_cap_v'] = (1+self.col['e'])* npf.pmt(self.InputData.LCC['Discount_rate']['amount'],
                                                         self.col['Lt'].values,
                                                         -self.col['Pt'].values)
        #number of collection vehicles (vehicles)
        for i in ['RWC','SSR','DSR','MSR','LV','SSYW','SSO','DryRes','REC','WetRes','MRDO','SSYWDO','MSRDO']:
            self.col.loc[i,'Nt'] = self.InputData.Col['houses_res']['amount'] * self.col_proc[i] *\
                                   self.col['Fr'][i]/(self.col['Ht'][i]*self.col['RD'][i]*self.col['CD'][i])
        #annualized capital cost per bin ($/bin-year)
        self.col['Cb'] = (1+self.col['e'])* npf.pmt(self.InputData.LCC['Discount_rate']['amount'],
                                                         self.col['Lb'].values,
                                                         -self.col['Pb'].values)  
        #no. of bins per vehicle (bins/vehicle)
        self.col['Nb'] = self.col['Rb'] * (self.col['Ht']/self.col['Prtcp']) * self.col['RD'] * self.col['CD'] / self.col['Fr']
        #bin annual cost per vehicle ($/vehicle-year)
        self.col['C_cap_b'] = self.col['Cb'] * self.col['Nb']
        
        #Breakdown of operating costs
        #labor cost per vehicle ($/vehicle-year)
        self.col['Cw'] = (1 + self.col['a']) * ((1+self.col['bw'])*
                                                (self.col['Wa']*self.col['Nw']+self.col['Wd']*1)*
                                                self.col['WP']*self.col['CD']*365/7)
        #O&M cost per vehicle ($/vehicle-year)
        self.col['Cvo'] = self.col['c']
        #other expenses per vehicle ($/vehicle-year)
        self.col['Coe'] = self.col['d'] * (self.col['Nw'] + 1)
        #Annual operating cost ($/vehicle-year)
        self.col['C_op'] = (1+self.col['e'])*(self.col['Cw']+self.col['Cvo']+self.col['Coe'])
        
        #Total annual cost per vehicle -- cap + O&M ($/vehicle-year)
        self.col['C_vehicle'] = (1+self.col['bv'])*self.col['C_cap_v']+self.col['C_op']
        
        #Total annual cost per house, including bins ($/house-year)   -Includes all houses provided service, even if not participating
        self.col['C_house'] = (self.col['C_vehicle'] / (self.col['Ht']*self.col['RD']*self.col['CD']/self.col['Fr'])) * self.col['Prtcp']\
                              + self.col['Cb'] * self.col['Rb']
        self.col['C_house'].replace([np.inf, np.NAN], 0, inplace=True)
        
        #Cost per ton of refuse collected - Cap+OM+bins ($/Mg)
        self.col['C_collection'] = (self.col['C_house'] * 7/365) / (self.mass.sum()/1000)

# =============================================================================
# =============================================================================
###      OUTPUT
# =============================================================================
# =============================================================================
        # Energy use is calculated for SSO and it is same with Dryres
        self.col.loc['DryRes','FuelMg'] = self.col['FuelMg']['SSO']
        self.col.loc['DryRes','FuelMg_CNG'] = self.col['FuelMg_CNG']['SSO']
        self.col.loc['DryRes','ElecMg'] = self.col['ElecMg']['SSO']
        
        # Energy use is calculated for REC and it is same with WetRes
        self.col.loc['WetRes','FuelMg'] = self.col['FuelMg']['REC']
        self.col.loc['WetRes','FuelMg_CNG'] = self.col['FuelMg_CNG']['REC']
        self.col.loc['WetRes','ElecMg'] = self.col['ElecMg']['REC']
        
        
        self.output = self.col[['TotalMass','FuelMg','FuelMg_CNG','ElecMg','FuelMg_dov','C_collection']]
        self.output = self.output.fillna(0)
            

    def calc(self):
        self.calc_composition()
        self.calc_destin()
            
        
### setup for Monte Carlo simulation   
    def setup_MC(self,seed=None):
        self.InputData.setup_MC(seed)

### Calculate based on the generated numbers   
    def MC_calc(self):      
        input_list = self.InputData.gen_MC()
        self.calc()
        return(input_list)        


    def report(self):
### Output
        self.collection = {}
        Waste={}
        Technosphere={}
        Biosphere={}
        self.collection["process name"] = self.process_name 
        self.collection["Waste"] = Waste
        self.collection["Technosphere"] = Technosphere
        self.collection["Biosphere"] = Biosphere
        self.collection['LCI'] = self.result_destination
        
        for x in [Waste,Technosphere, Biosphere]:
            for y in self.Index:
                x[y]={}
        
        for y in self.Index: 
            for x in self.col_massflow.columns:
                Waste[y][x]= self.col_massflow[x][y]
        return(self.collection)
