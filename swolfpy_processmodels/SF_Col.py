# -*- coding: utf-8 -*-
"""
@author: msardar2
"""
import pandas as pd
from swolfpy_inputdata import SF_Col_Input
from .ProcessModel import ProcessModel
import numpy_financial as npf
import numpy as np
import warnings


class SF_Col(ProcessModel):
    Process_Type = 'Collection'
    def __init__(self, process_name, Collection_scheme,
                 Treatment_processes=None,
                 Distance=None,
                 CommonDataObjct=None,
                 input_data_path=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData = SF_Col_Input(input_data_path,
                                      process_name=self.process_name,
                                      CommonDataObjct=CommonDataObjct)

        self.process_name = process_name

        if Treatment_processes is not None:
            self.Treat_proc = Treatment_processes
            if Distance:
                self.Distance = Distance
            else:
                raise Exception('User should define both Distance and Treatment_processes together!')
        else:
            self.Treat_proc = False

        self.process_data = self.InputData.process_data
        self.col_schm = Collection_scheme

    @staticmethod
    def scheme():
        """
        Retrun the dictionary for collection_scheme. all the
        contributions are zero; user should define them according to his/her case.
        """
        SepOrg = ['N/A', 'SSYW', 'SSO', 'SSYWDO']
        SepRec = ['N/A', 'SSR', 'DSR', 'MSR', 'MSRDO']
        scheme = {}
        for i in SepOrg:
            for j in SepRec:
                scheme[('RWC', i, j)] = 0
        for i in SepOrg:
            scheme[('REC_WetRes', i, 'REC_WetRes')] = 0
        for j in SepRec:
            scheme[('ORG_DryRes', 'ORG_DryRes', j)] = 0
        for i in ['N/A', 'SSYWDO']:
            for j in ['N/A', 'MSRDO']:
                scheme[('MRDO', i, j)] = 0
        return scheme

    def _normalize_scheme(self, DropOff=True, warn=True):
        """
        Used in optimization. Check that sum of the contributions is 1.
        """
        if not DropOff:
            for k in self.col_schm:
                if 'DO' in k:
                    self.col_schm[k] = 0

        contribution =  sum(self.col_schm.values())
        if abs(contribution - 1) > 0.01:
            if warn:
                warnings.warn('Error in collection scheme: Sum(Contribution) != 1')
            for k, v in self.col_schm.items():
                self.col_schm[k] = v / contribution

    def calc_composition(self):
        # Creating the sel.col Data frame
        col_data = np.zeros((14, 61), dtype=float)
        col_data[:] = np.nan
        col_columns = []
        col_index = ['RWC', 'SSR', 'DSR', 'MSR', 'LV',
                                       'SSYW', 'SSO', 'ORG', 'DryRes', 'REC',
                                        'WetRes', 'MRDO', 'SSYWDO', 'MSRDO']
        col_i = 0

        for key, val in self.InputData.den_asmd.items():
            col_data[col_index.index(key), col_i] = val['amount']
        col_columns.append('den_asmd')
        col_i += 1

        for key, val in self.InputData.Prtcp.items():
            col_data[col_index.index(key), col_i] = val['amount']
        col_columns.append('Prtcp')
        col_i += 1

        for key, val in self.InputData.Fr.items():
            col_data[col_index.index(key), col_i] = val['amount']
        col_columns.append('Fr')
        col_i += 1

        for key, val in self.InputData.TL.items():
            col_data[col_index.index(key), col_i] = val['amount']
        col_columns.append('TL')
        col_i += 1

        for key, val in self.InputData.S.items():
            col_data[col_index.index(key), col_i] = val['amount']
        col_columns.append('S')
        col_i += 1

        for key, val in self.InputData.Nw.items():
            col_data[col_index.index(key), col_i] = val['amount']
        col_columns.append('Nw')
        col_i += 1

        for key, val in self.InputData.Rb.items():
            col_data[col_index.index(key), col_i] = val['amount']
        col_columns.append('Rb')
        col_i += 1

        for key, val in self.InputData.Col_Root.items():
            col_data[:, col_i] = val['amount']
            col_columns.append(key)
            col_i += 1

        for key, val in self.InputData.LCC.items():
            col_data[:, col_i] = val['amount']
            col_columns.append(key)
            col_i += 1

        for key, val in self.InputData.DropOff.items():
            col_data[:, col_i] = val['amount']
            col_columns.append(key)
            col_i += 1

        for key, val in self.InputData.Mpg.items():
            col_data[:, col_i] = val['amount']
            col_columns.append(key)
            col_i += 1

        for key, val in self.InputData.Speed.items():
            col_data[:, col_i] = val['amount']
            col_columns.append(key)
            col_i += 1

        for key in ['CD', 'WV', 'WP', 'wt_lim', 'max_weight', 'F1_', 'F1_idle',
                    'F2_', 'F2_idle', 'bw', 'bv', 'Lt', 'Ut', 'Vt', 'Fract_CNG',
                    'grg_area', 'off_area', 'grg_enrg', 'off_enrg', 'Lb']:
            col_data[:, col_i] = self.InputData.Col[key]['amount']
            col_columns.append(key)
            col_i += 1

        self.col = pd.DataFrame(data=col_data,
                                columns=col_columns,
                                index=['RWC', 'SSR', 'DSR', 'MSR', 'LV',
                                       'SSYW', 'SSO', 'ORG', 'DryRes', 'REC',
                                        'WetRes', 'MRDO', 'SSYWDO', 'MSRDO'],
                                dtype=float)

        self.col['Fract_Dies'] = 1 - self.InputData.Col['Fract_CNG']['amount']

        self._col_schm = {
            'RWC': {'Contribution': 0,
                    'separate_col':{'SSR': 0, 'DSR': 0, 'MSR': 0, 'MSRDO': 0, 'SSYW': 0, 'SSO': 0, 'SSYWDO': 0}},
            'ORG_DryRes': {'Contribution': 0,
                           'separate_col': {'SSR': 0, 'DSR': 0, 'MSR': 0, 'MSRDO': 0, 'SSYW': 0, 'SSO': 0, 'SSYWDO': 0}},
            'REC_WetRes': {'Contribution': 0,
                           'separate_col': {'SSR': 0, 'DSR': 0, 'MSR': 0, 'MSRDO': 0, 'SSYW': 0, 'SSO': 0, 'SSYWDO': 0}},
            'MRDO': {'Contribution': 0,
                     'separate_col': {'SSR': 0, 'DSR': 0, 'MSR': 0, 'MSRDO': 0, 'SSYW': 0, 'SSO': 0, 'SSYWDO': 0}}}

        for k, v in self.col_schm.items():
            if k[0] == 'RWC':
                self._col_schm['RWC']['Contribution'] += v
            elif k[0] == 'ORG_DryRes':
                self._col_schm['ORG_DryRes']['Contribution'] += v
            elif k[0] == 'REC_WetRes':
                self._col_schm['REC_WetRes']['Contribution'] += v
            elif k[0] == 'MRDO':
                self._col_schm['MRDO']['Contribution'] += v
            else:
                raise Exception(f'Error in collection scheme keys: "{k[0]}" is not defined!')

        for k, v in self.col_schm.items():
            if v > 0:
                if k[1] not in ['N/A', 'ORG_DryRes', 'REC_WetRes']:
                    self._col_schm[k[0]]['separate_col'][k[1]] += v / self._col_schm[k[0]]['Contribution']
                if k[2] not in ['N/A', 'ORG_DryRes', 'REC_WetRes']:
                    self._col_schm[k[0]]['separate_col'][k[2]] += v / self._col_schm[k[0]]['Contribution']

        # Single Family Residential Waste Generation Rate (kg/household-week)
        g_res = 7 * self.InputData.Col['res_per_dwel']['amount'] * self.InputData.Col['res_gen']['amount']
        gen_per_week = g_res * self.process_data['Comp']
        total_waste_gen = (
            g_res
            * self.InputData.Col['houses_res']['amount']
            * 365 / 7 / 1000)  # 52 weeks per year & 1000 kg = 1 Mg

        # Check for Leave Vaccum
        self.process_data['LV'] = 0
        if self.InputData.Col['Leaf_vacuum']['amount'] == 1:
            LV_gen = (gen_per_week['Yard_Trimmings_Leaves']
                      * self.InputData.Col['houses_res']['amount']
                      * 365 / 7 / 1000)
            LV_col = self.InputData.Col['Leaf_vacuum_amount']['amount']

            if LV_gen <= LV_col:
                self.process_data.loc['Yard_Trimmings_Leaves', 'LV'] = 1
            else:
                self.process_data.loc['Yard_Trimmings_Leaves', 'LV'] = LV_col / LV_gen

            for j in ['RWC', 'ORG_DryRes', 'REC_WetRes', 'MRDO']:
                self._col_schm[j]['separate_col']['LV'] = 1
        else:
            for j in ['RWC', 'ORG_DryRes', 'REC_WetRes', 'MRDO']:
                self._col_schm[j]['separate_col']['LV'] = 0

        self.col.loc['LV', 'Fr'] = (
            self.InputData.Col['LV_serv_times']['amount']
            / self.InputData.Col['LV_serv_pd']['amount'])

        # Total fraction where this service is offered
        self.col_proc = {
            'RWC': self._col_schm['RWC']['Contribution'],
            'ORG': self._col_schm['ORG_DryRes']['Contribution'],
            'DryRes': self._col_schm['ORG_DryRes']['Contribution'],
            'REC': self._col_schm['REC_WetRes']['Contribution'],
            'WetRes': self._col_schm['REC_WetRes']['Contribution'],
            'MRDO': self._col_schm['MRDO']['Contribution']}

        # SSO_HC contribution
        for j in ['RWC', 'ORG_DryRes', 'REC_WetRes', 'MRDO']:
            if self.InputData.Col['HC_partic']['amount'] > 0:
                self._col_schm[j]['separate_col']['SSO_HC'] = 1
            else:
                self._col_schm[j]['separate_col']['SSO_HC'] = 0

        for i in ['LV', 'SSR', 'DSR', 'MSR', 'MSRDO', 'SSYW', 'SSO', 'SSO_HC', 'SSYWDO']:
            self.col_proc[i] = 0
            for j in ['RWC', 'ORG_DryRes', 'REC_WetRes', 'MRDO']:
                self.col_proc[i] += (
                    self._col_schm[j]['Contribution']
                    * self._col_schm[j]['separate_col'][i])

        # Is this collection process offered? (1: in use, 0: not used)
        self.P_use = {}
        for j in self.col_proc.keys():
            self.P_use[j] = 1 if self.col_proc[j] > 0 else 0

        # Mass separated by collection process (kg/week.Household)
        columns = ['RWC', 'SSR', 'DSR', 'MSR', 'LV', 'SSYW', 'SSO',
                   'SSO_HC', 'ORG', 'DryRes', 'REC', 'WetRes',
                   'MRDO', 'SSYWDO', 'MSRDO']
        self.mass = pd.DataFrame(index=self.Index,
                                 columns=columns,
                                 data=0.0,
                                 dtype=float)

        for i in ['SSR', 'DSR', 'MSR', 'SSYW', 'SSO', 'ORG', 'REC', 'SSYWDO', 'MSRDO']:
            self.mass[i] = (
                gen_per_week.values
                * self.process_data[i].values
                * self.P_use[i])

            self.mass.loc['Yard_Trimmings_Leaves', i] *= (1 - self.process_data.loc['Yard_Trimmings_Leaves', 'LV'])

        self.mass['LV'] = (gen_per_week.values
                           * self.process_data['LV'].values
                           * self.P_use['LV'])

        # SSO_HC mass
        """
        For home composting, it is assumed that only yard waste and
        food waste (vegetables) are used.
        """
        if self.InputData.Col['HC_partic']['amount'] > 0:
            HC_frac = self.InputData.Col['HC_partic']['amount'] / 100
            c = ['SSR', 'DSR', 'MSR', 'SSYW', 'SSO', 'ORG', 'REC', 'SSYWDO', 'MSRDO']
            OFMSW = ['Yard_Trimmings_Leaves',
                     'Yard_Trimmings_Grass',
                     'Yard_Trimmings_Branches',
                     'Food_Waste_Vegetable']

            self.mass.loc[OFMSW, 'SSO_HC'] = (
                gen_per_week[OFMSW] * HC_frac)

            self.mass.loc['Yard_Trimmings_Leaves', 'SSO_HC'] *= (
                    1 - self.process_data.loc['Yard_Trimmings_Leaves', 'LV'])

            self.mass.loc[OFMSW, c] *= (1 - HC_frac)

        def separate_col_mass(j):
            mass = np.zeros(len(self.CommonData.Index))
            for i in ['SSR', 'DSR', 'MSR', 'LV', 'SSYW', 'SSO', 'SSO_HC', 'SSYWDO', 'MSRDO']:
                mass += self.mass[i].values * self._col_schm[j]['separate_col'][i]
            return mass

        # Calculating the residual waste after separate collection
        for j in ['RWC', 'MRDO']:
            self.mass[j]= (
                gen_per_week.values
                * self.process_data[j].values
                - separate_col_mass(j)) * self.P_use[j]

        # ORG_DryRes
        self.mass['DryRes']= (
            (gen_per_week.values
             * self.process_data['DryRes'].values
             - separate_col_mass('ORG_DryRes')
             - self.mass['ORG'].values) * self.P_use['DryRes'])

        # REC_WetRes
        self.mass['WetRes'] = (
            gen_per_week.values
            * self.process_data['WetRes'].values
            - separate_col_mass('REC_WetRes')
            - self.mass['REC'].values) * self.P_use['WetRes']

        # Annual Mass Flows (Mg/yr)
        self.col_massflow = pd.DataFrame(index=self.Index)
        for i in columns:
            self.col_massflow[i] = (self.mass[i]
                                    * self.InputData.Col['houses_res']['amount']
                                    * 365 / 7 / 1000
                                    * self.col_proc[i])

        # Check for negative mass flows
        if (self.col_massflow.values < 0).any().any():
            raise Exception(f'Negative mass flows in collection model [{self.process_name}]!')
            # warnings.warn('Negative mass flows in collection model [{self.process_name}]!')

        # Check generated mass = Collected mass
        ratio = self.col_massflow.sum().sum() / total_waste_gen
        if ratio > 1.01 or ratio < 0.99:
            raise Exception(f'Mass balance error in collection model [{self.process_name}]!')
            # warnings.warn(f'Mass balance error in collection model [{self.process_name}]!')

        # Volume Composition of each collection process for each sector
        mass_to_cyd = (1 / (self.process_data['Bulk_Density'].values + 0.000001)
                       * 1.30795)  # m3 --> Cubic yard
        mass_to_cyd[self.process_data['Bulk_Density'].values <= 0] = 0.0

        for i in ['RWC', 'SSR', 'DSR', 'MSR', 'LV', 'SSYW', 'SSO', 'MRDO', 'SSYWDO', 'MSRDO']:
            vol = (self.mass[i].values * mass_to_cyd).sum()  # Unit kg/cyd
            if vol > 0:
                self.col.loc[i, 'den_c'] = (self.mass[i].values
                                            * 2.205 / vol).sum()  # Unit lb/cyd
            else:
                self.col.loc[i, 'den_c'] = 0

        for i, j in [('ORG', 'DryRes'), ('REC', 'WetRes')]:
            m = self.mass[i].values + self.mass[j].values
            vol = (m * mass_to_cyd).sum()  # Unit kg/cyd
            if vol > 0:
                self.col.loc[i, 'den_c'] = (m * 2.205 / vol).sum()  # Unit lb/cyd
            else:
                self.col.loc[i, 'den_c'] = 0

    def find_destination(self, product, Treatment_processes):
        destination = {}
        for P in Treatment_processes:
            if product in Treatment_processes[P]['input_type']:
                destination[P] = (
                    self.Distance.Distance[(self.process_name, P)]['Heavy Duty Truck']
                    / 1.60934)  # Convert the distance from km to mile
        return destination

    # calculating LCI and cost for different locations
    def calc_destin(self):
        if self.Treat_proc:
            self.dest = {}
            self.result_destination = {}
            for i in ['RWC', 'SSR', 'DSR', 'MSR', 'LV', 'SSYW', 'SSO',
                      'SSO_HC', 'ORG', 'DryRes', 'REC', 'WetRes',
                      'MRDO', 'SSYWDO', 'MSRDO']:
                self.dest[i] = self.find_destination(i, self.Treat_proc)
                self.result_destination[i] = {}

            # Number of times we need to run the collection
            n_run = max([len(self.dest[i]) for i in self.dest.keys()])

            for i in range(n_run):
                for j in ['RWC', 'SSR', 'DSR', 'MSR', 'MSRDO', 'LV', 'SSYW',
                          'SSO', 'SSYWDO', 'MRDO', 'SSYWDO', 'MSRDO', 'ORG', 'REC']:
                    if len(self.dest[j]) > i:
                        # Distance btwn collection route and destination
                        self.col['Drf'][j] = self.dest[j][list(self.dest[j].keys())[i]]

                        # Distance between destination and garage
                        self.col['Dfg'][j] = (
                            self.dest[j][list(self.dest[j].keys())[i]]
                            + self.col['Dgr'][j])

                self.calc_lci()
                for j in self.dest.keys():
                    if len(self.dest[j]) > i:
                        key = list(self.dest[j].keys())[i]
                        self.result_destination[j][key] = {}

                        self.result_destination[j][key][('Technosphere', 'Equipment_Diesel')] = (
                            self.output['FuelMg'][j]
                            + self.output['FuelMg_dov'][j])

                        self.result_destination[j][key][('Technosphere', 'Equipment_CNG')] = (
                            self.output['FuelMg_CNG'][j])

                        self.result_destination[j][key][('Technosphere', 'Electricity_consumption')] = (
                            self.output['ElecMg'][j])

                        self.result_destination[j][key][('biosphere3', 'Operational_Cost')] = (
                            self.output['C_collection'][j])
        else:
            self.calc_lci()
            self.result_destination = {}

    def calc_lci(self):
        # Selected compartment compaction density  (lb/yd3)
        # Override calculated density den_c and use an average assumed in-truck density
        d_msw = self.col['den_asmd'].values
        d_msw[d_msw <= 0] = self.col['den_c'].values[d_msw <= 0]
        self.col['d_msw'] = d_msw

        # Distance between service stops, adjusted (miles)
        self.col['Dbtw'] = self.col['D100'].values / self.col['Prtcp'].values

        # Travel time between service stops, adjusted based on participation (min/stop)
        self.col['Tbtw'] = self.col['Dbtw'].values / self.col['Vbet'].values * 60

        # Travel time btwn route and disposal fac. (min/trip)
        self.col['Trf'] = self.col['Drf'].values / self.col['Vrf'].values * 60

        # Time from grg to 1st collection route (min/day-vehicle)
        self.col['Tgr'] = self.col['Dgr'].values / self.col['Vgr'].values * 60

        # Time from disposal fac. to garage (min/day-vehicle)
        self.col['Tfg'] = self.col['Dfg'].values / self.col['Vfg'].values * 60

        for i in ['RWC', 'SSR', 'DSR', 'MSR', 'LV',
                  'SSYW', 'SSO', 'MRDO', 'SSYWDO', 'MSRDO']:
            self.col.loc[i, 'mass'] = self.mass[i].values.sum()

        # Mass of ORG_DryRes and REC_WetRec
        for i, j in [('ORG', 'DryRes'), ('REC', 'WetRes')]:
            self.col.loc[i, 'mass'] = (self.mass[i].values + self.mass[j].values).sum()

        # Revising mass of LV collection - as it happens only in LV_serv_pd
        self.col.loc['LV', 'mass'] = (
            self.col.loc['LV', 'mass'] * 365 / 7
            / self.InputData.Col['LV_serv_pd']['amount'])

        # Calculations for collection vehicle activities
        # Houses per trip (Volume limited) and (mass limited)
        Ht_v = np.zeros(self.col.shape[0])
        Ht_m = np.zeros(self.col.shape[0])

        fltr = self.col['mass'].values > 0
        Ht_v[fltr] = (
            self.col['Ut'].values[fltr]
            * self.col['Vt'].values[fltr]
            * self.col['d_msw'].values[fltr]
            * 0.4536  # lb to kg
            * self.col['Fr'].values[fltr]
            / self.col['mass'].values[fltr])

        Ht_m[fltr] = (
            self.col['max_weight'].values[fltr]
            * self.col['Fr'].values[fltr]
            * 1000
            / self.col['mass'].values[fltr])

        self.col['Ht_v'] = Ht_v
        self.col['Ht_m'] = Ht_m

        # Households per trip (limited by mass or volume)
        Ht = self.col['Ht_v'].values
        fltr_2 = self.col['wt_lim'].values == 1
        fltr_3 = Ht[fltr_2] > self.col['Ht_m'].values[fltr_2]
        Ht[fltr_2][fltr_3] = self.col['Ht_m'].values[fltr_3]
        self.col['Ht'] = Ht

        # Time per trip (min/trip)
        # Collection
        self.col['Tc'] = (
            self.col['Tbtw'].values * (self.col['Ht'].values /self.InputData.Col['HS']['amount'] - 1)  # collection travel
            + self.col['TL'].values * self.col['Ht'].values / self.InputData.Col['HS']['amount']  # collection loading
            + 2 * self.col['Trf'].values  # travel
            + self.col['S'].values)  # unload time

        # Trips per day per vehicle (trip/day-vehicle)
        self.col['RD'] = (
            self.col['WV'].values * 60
            - (self.col['F1_'].values + self.col['F2_'].values + self.col['Tfg'].values)
            - 0.5 * (self.col['Trf'].values + self.col['S'].values)) / self.col['Tc'].values

        # Check that the inputs are realistic
        if any(self.col['RD'].values < 0):
            raise Exception("Travelling time is too long that the truck cannot make a loop trip in one day!")

        # Daily weight of refuse collected per vehicle (Mg/vehicle-day)
        self.col['RefD'] = (
            self.col['Ht'].values
            * self.col['mass'].values / 1000
            / self.col['Fr'].values
            * self.col['RD'].values)

        # Number of collection stops per day (stops/vehicle-day)
        self.col['SD'] = (
            self.col['Ht'].values
            * self.col['RD'].values
            / self.InputData.Col['HS']['amount'])

        # Calculations for collection vehicle activities (Drop off)
        for i in ['MRDO', 'SSYWDO', 'MSRDO']:
            # volume of recyclables deposited at drop-off site per week (cy/week-house)
            self.col.loc[i, 'Ht'] = (
                self.mass[i].values.sum()
                * self.InputData.Col['houses_res']['amount']
                * self.col_proc[i]
                / 0.4536  # lb to kg
                / self.col['d_msw'][i])

            # collection vehicle trips per week (trips/week)
            self.col.loc[i, 'DO_trip_week'] = (
                self.col['Ht'][i]
                / (self.col['Vt'][i] * self.col['Ut'][i]))

            # time per trip (min/trip) -- load+travel+unload time
            self.col.loc[i, 'Tc'] = (
                self.col['TL'][i]
                + 2 * self.col['Trf'][i]
                + self.col['S'][i])

            # trips per day per vehicle (trip/day-vehicle)
            self.col.loc[i, 'RD'] = (
                self.col['WV'][i] * 60
                - (self.col['F1_'][i]
                   + self.col['F2_'][i]
                   + self.col['Tfg'][i]
                   + self.col['Tgr'][i])
                + self.col['Trf'][i]) / self.col['Tc'][i]

            # daily weight of refuse collected per vehicle (tons/day-vehicle)
            self.col.loc[i, 'RefD'] = (
                self.col['Vt'][i]
                * self.col['Ut'][i]
                * self.col['d_msw'][i]
                * 0.4536  # lb to kg
                / 1000  # kg to Mg
                * self.col['RD'][i])

            # number of collection stops per day (stops/vehicle-day) (1 stop per trip)
            self.col.loc[i, 'SD'] = self.col['RD'][i]

        # Daily collection vehicle activity times
        # loading time at collection stops (min/day-vehicle) & loading time at drop-off site (min/day-vehicle)
        self.col['LD'] = self.col['SD'].values * self.col['TL'].values

        # travel time between collection stops (min/day-vehicle)
        fltr_3 = self.col['SD'].values - 1 >= 1
        Tb = np.zeros(self.col.shape[0])
        Tb[fltr_3] = (self.col['SD'].values[fltr_3] - 1) * self.col['Tbtw'].values[fltr_3]
        self.col['Tb'] = Tb

        # travel time between route and disposal facility (min/day-vehicle)
        self.col['F_R'] = (2 * self.col['RD'].values + 0.5) * self.col['Trf'].values

        # unloading time at disposal facility (min/day-vehicle)
        self.col['UD'] = (self.col['RD'].values + 0.5) * self.col['S'].values

        for i in ['MRDO', 'SSYWDO', 'MSRDO']:
            self.col.loc[i, 'Tb'] = 0

            # travel time between disposal facility and drop-off site (min/day-vehicle)
            self.col.loc[i, 'F_R'] = (2 * self.col['RD'][i] - 1) * self.col['Trf'][i]

            # unloading time at disposal facility (min/day-vehicle)
            self.col.loc[i, 'UD'] = self.col['RD'][i] * self.col['S'][i]


        # Daily fuel usage - Diesel
        fltr_4 = self.col['MPG_all'].values != 0

        # from garage to first collection route (gallons/day-vehicle)
        diesel_gr = (
            self.col['Fract_Dies'].values
            * self.col['Dgr'].values
            *((1 - self.col['fDgr'].values)
              / self.col['MPG_urban'].values
              + self.col['fDgr'].values
              /self.col['MPG_highway'].values))

        diesel_gr[fltr_4] = (
            self.col['Fract_Dies'].values[fltr_4]
            * self.col['Dgr'].values[fltr_4]
            / self.col['MPG_all'].values[fltr_4])


        # break time, if spent idling
        diesel_idl = (
            self.col['Fract_Dies'].values
            * (self.col['F1_'].values
               * self.col['F1_idle'].values
               + self.col['F2_'].values
               * self.col['F2_idle'].values)
            / 60
            * self.col['GPH_idle_cv'].values)

        diesel_idl[fltr_4] = 0

        # from first through last collection stop (gallons/day-vehicle)
        diesel_col = (
            self.col['Fract_Dies'].values
            * self.col['Dbtw'].values
            * self.col['SD'].values
            / self.col['MPG_collection'].values)

        diesel_col[fltr_4] = (
            self.col['Fract_Dies'].values[fltr_4]
            * self.col['Dbtw'].values[fltr_4]
            * self.col['SD'].values[fltr_4]
            / self.col['MPG_all'].values[fltr_4])


        index_dict = dict(zip(self.col.index,
                              np.arange(len(self.col.index))))
        fltr_DO = [False for i in self.col.index]
        for i in ['MRDO', 'SSYWDO', 'MSRDO']:
            fltr_DO[index_dict[i]] = True
        diesel_col[fltr_DO] = 0

       # between disposal facility and route (gallons/day-vehicle)
        diesel_rf = (
            self.col['Fract_Dies'].values
            * self.col['F_R'].values / 60
            * self.col['Vrf'].values
            * ((1 - self.col['fDrd'].values) / self.col['MPG_urban'].values
               + self.col['fDrd'].values / self.col['MPG_highway'].values))

        diesel_rf[fltr_4] = (
            self.col['Fract_Dies'].values[fltr_4]
            * self.col['F_R'].values[fltr_4] / 60
            * self.col['Vrf'].values[fltr_4]
            / self.col['MPG_all'].values[fltr_4])

        # unloading at disposal facility (gallons/day-vehicle)
        diesel_ud = (
            self.col['Fract_Dies'].values
            * self.col['UD'].values / 60
            * self.col['GPH_idle_cv'].values)

        diesel_ud[fltr_4] = 0

       # from disposal facility to garage (gallons/day-vehicle)
        diesel_fg = (
            self.col['Fract_Dies'].values
            * self.col['Dfg'].values
            * ((1 - self.col['fDfg'].values) / self.col['MPG_urban'].values
               + self.col['fDfg'].values / self.col['MPG_highway'].values))

        diesel_fg[fltr_4] = (
            self.col['Fract_Dies'].values[fltr_4]
            * self.col['Dfg'].values[fltr_4]
            / self.col['MPG_all'].values[fltr_4])

        FuelD = pd.Series(
            (diesel_gr + diesel_idl + diesel_col
             + diesel_rf + diesel_ud + diesel_fg),
             index=self.col.index)

        for key, val in self.col_proc.items():
            if val == 0:
                FuelD[key] = 0

        self.col['FuelD'] = FuelD

        # Daily fuel usage - CNG - diesel gal equivalent
        fltr_6 = self.col['MPG_all_CNG'].values != 0

        # from garage to first collection route ((diesel gal equivalent/day-vehicle)
        CNG_gr = (
            self.col['Fract_CNG'].values
            * self.col['Dgr'].values
            *((1 - self.col['fDgr'].values)
              / self.col['MPG_urban_CNG'].values
              + self.col['fDgr'].values
              /self.col['MPG_hwy_CNG'].values))

        CNG_gr[fltr_6] = (
            self.col['Fract_CNG'].values[fltr_6]
            * self.col['Dgr'].values[fltr_6]
            / self.col['MPG_all_CNG'].values[fltr_6])


        # break time, if spent idling
        CNG_idl = (
            self.col['Fract_CNG'].values
            * (self.col['F1_'].values
               * self.col['F1_idle'].values
               + self.col['F2_'].values
               * self.col['F2_idle'].values)
            / 60
            * self.col['GPH_idle_CNG'].values)

        CNG_idl[fltr_6] = 0

        # from first through last collection stop (diesel gal equivalent/day-vehicle)
        CNG_col = (
            self.col['Fract_CNG'].values
            * self.col['Dbtw'].values
            * self.col['SD'].values
            / self.col['MPG_col_CNG'].values)

        CNG_col[fltr_6] = (
            self.col['Fract_CNG'].values[fltr_6]
            * self.col['Dbtw'].values[fltr_6]
            * self.col['SD'].values[fltr_6]
            / self.col['MPG_all_CNG'].values[fltr_6])

        CNG_col[fltr_DO] = 0

       # between disposal facility and route (diesel gal equivalent/day-vehicle)
        CNG_rf = (
            self.col['Fract_CNG'].values
            * self.col['F_R'].values / 60
            * self.col['Vrf'].values
            * ((1 - self.col['fDrd'].values) / self.col['MPG_urban_CNG'].values
               + self.col['fDrd'].values / self.col['MPG_hwy_CNG'].values))

        CNG_rf[fltr_6] = (
            self.col['Fract_CNG'].values[fltr_6]
            * self.col['F_R'].values[fltr_6] / 60
            * self.col['Vrf'].values[fltr_6]
            / self.col['MPG_all_CNG'].values[fltr_6])

        # unloading at disposal facility (diesel gal equivalent/day-vehicle)
        CNG_ud = (
            self.col['Fract_CNG'].values
            * self.col['UD'].values / 60
            * self.col['GPH_idle_CNG'].values)

        CNG_ud[fltr_6] = 0

       # from disposal facility to garage (diesel gal equivalent/day-vehicle)
        CNG_fg = (
            self.col['Fract_CNG'].values
            * self.col['Dfg'].values
            * ((1 - self.col['fDfg'].values) / self.col['MPG_urban_CNG'].values
               + self.col['fDfg'].values / self.col['MPG_hwy_CNG'].values))

        CNG_fg[fltr_6] = (
            self.col['Fract_CNG'].values[fltr_6]
            * self.col['Dfg'].values[fltr_6]
            / self.col['MPG_all_CNG'].values[fltr_6])

        FuelD_CNG = pd.Series(
            (CNG_gr + CNG_idl + CNG_col
             + CNG_rf + CNG_ud + CNG_fg),
             index=self.col.index)

        for key, val in self.col_proc.items():
            if val == 0:
                FuelD_CNG[key] = 0

        self.col['FuelD_CNG'] = FuelD_CNG

        # ENERGY CONSUMPTION
        # Energy consumption by collection vehicles
        # total coll. vehicle fuel use per Mg of refuse (L/Mg)
        FuelMg = np.zeros(self.col.shape[0])
        flter_7 = self.col['RefD'].values > 0
        FuelMg[flter_7] = (
            self.col['FuelD'].values[flter_7]
            * 3.785  # gal to ltr
            / self.col['RefD'].values[flter_7])
        self.col['FuelMg'] = FuelMg

        # total coll. vehicle CNG fuel use per Mg of refuse (diesel L equivalent/Mg)
        FuelMg_CNG = np.zeros(self.col.shape[0])
        FuelMg_CNG[flter_7] = (
            self.col['FuelD_CNG'].values[flter_7]
            * 3.785  # gal to ltr
            / self.col['RefD'].values[flter_7])
        self.col['FuelMg_CNG'] = FuelMg_CNG

        # Energy consumption by drop-off vehicles
        P_use_Seri = pd.Series(index=self.col.index)
        col_proc_Seri = pd.Series(index=self.col.index)
        self.col_proc
        for key, val in index_dict.items():
            P_use_Seri[val] = self.P_use[key]
            col_proc_Seri[val] = self.col_proc[key]

        # fuel usage per trip to drop-off site (gallons/trip)
        FuelT = np.zeros(self.col.shape[0])
        FuelT[fltr_DO] = (
            P_use_Seri.values[fltr_DO]
            * self.col['RTDdos'].values[fltr_DO]
            * self.col['DED'].values[fltr_DO]
            / self.col['dropoff_MPG'].values[fltr_DO] )
        self.col['FuelT'] = FuelT

        for i in ['MRDO', 'SSYWDO', 'MSRDO']:
            # weight of refuse delivered per trip (kg/trip)
            self.col.loc[i, 'RefT'] = (
                self.mass[i].values.sum()
                * self.col['Prtcp'][i]
                * 365 / 7
                / (self.col['FREQdos'][i] * 12))

        # total dropoff vehicle  fuel use per Mg of refuse (L/Mg)
        FuelMg_dov = np.zeros(self.col.shape[0])
        flter_8 = self.col['RefT'].values > 0
        FuelMg_dov[flter_8] = (
            self.col['FuelT'].values[flter_8]
            * 3.785  # gal to ltr
            / (self.col['RefT'].values[flter_8] / 1000))
        self.col['FuelMg_dov'] = FuelMg_dov

        # Energy consumption by garage
        # daily electricity usage per vehicle  (kWh/vehicle-day)
        self.col['ElecD'] = (
            P_use_Seri.values
            * (self.col['grg_area'].values * self.col['grg_enrg'].values
               + self.col['off_area'].values * self.col['off_enrg'].values))

        # electricity usage per Mg of refuse  (kWh/Mg)
        ElecMg = np.zeros(self.col.shape[0])
        ElecMg[flter_7] = (
            self.col['ElecD'].values[flter_7]
            / self.col['RefD'].values[flter_7])
        self.col['ElecMg'] =  ElecMg

        # Mass
        # total mass of refuse collected per year (Mg)
        self.col['TotalMass'] = self.col_massflow.sum()

        # COLLECTION COSTS
        # Breakdown of capital costs

        # annual capital cost per vehicle ($/vehicle-year)
        self.col['C_cap_v'] = (
            (1 + self.col['e'].values)
            * npf.pmt(self.InputData.LCC['Discount_rate']['amount'],
                      self.col['Lt'].values,
                      -self.col['Pt'].values))

        # number of collection vehicles (vehicles)
        self.col['Nt'] = (
            self.InputData.Col['houses_res']['amount']
            * col_proc_Seri.values
            * self.col['Fr'].values
            / (self.col['Ht'].values
               * self.col['RD'].values
               * self.col['CD'].values))

        # annualized capital cost per bin ($/bin-year)
        self.col['Cb'] = (
            (1 + self.col['e'].values)
            * npf.pmt(self.InputData.LCC['Discount_rate']['amount'],
                      self.col['Lb'].values,
                      -self.col['Pb'].values))

        # no. of bins per vehicle (bins/vehicle)
        self.col['Nb'] = (
            self.col['Rb'].values
            * (self.col['Ht'].values / self.col['Prtcp'].values)
            * self.col['RD'].values
            * self.col['CD'].values
            / self.col['Fr'].values)

        # bin annual cost per vehicle ($/vehicle-year)
        self.col['C_cap_b'] = (
            self.col['Cb'].values * self.col['Nb'].values)

        # Breakdown of operating costs
        # labor cost per vehicle ($/vehicle-year)
        self.col['Cw'] = (
            (1 + self.col['a'].values)
            * ((1 + self.col['bw'].values)
               * (self.col['Wa'].values * self.col['Nw'].values
                  + self.col['Wd'].values)
               * self.col['WP'].values
               * self.col['CD'].values
               * 365 / 7))

        # O&M cost per vehicle ($/vehicle-year)
        self.col['Cvo'] = self.col['c'].values

        # other expenses per vehicle ($/vehicle-year)
        self.col['Coe'] = self.col['d'].values * (self.col['Nw'].values + 1)

        # Annual operating cost ($/vehicle-year)
        self.col['C_op'] = (
            (1 + self.col['e'].values)
            * (self.col['Cw'].values
               + self.col['Cvo'].values
               + self.col['Coe'].values))

        # Total annual cost per vehicle -- cap + O&M ($/vehicle-year)
        self.col['C_vehicle'] = (
            (1 + self.col['bv'].values)
            * self.col['C_cap_v'].values
            + self.col['C_op'].values)

        # Total annual cost per house, including bins ($/house-year)
        # Includes all houses provided service, even if not participating
        hpdv = (self.col['Ht'].values
                * self.col['RD'].values
                * self.col['CD'].values
                / self.col['Fr'].values)

        fltr_9 = hpdv > 0.0

        C_house = np.zeros(self.col.shape[0])

        C_house[fltr_9] = (
            self.col['C_vehicle'].values[fltr_9]
            / hpdv[fltr_9]
            * self.col['Prtcp'].values[fltr_9])

        C_house += (self.col['Cb'].values * self.col['Rb'].values)
        C_house[np.isnan(C_house)] = 0.0
        self.col['C_house'] = C_house

        # Cost per ton of refuse collected - Cap+OM+bins ($/Mg)
        self.col['C_collection'] = (
            (self.col['C_house'] * 7 / 365)
            / (self.mass.sum() / 1000)).replace([np.inf, np.nan], 0)

        # OUTPUT
        # Energy use is calculated for ORG and it is same with Dryres
        self.col.loc['DryRes', 'FuelMg'] = self.col['FuelMg']['ORG']
        self.col.loc['DryRes', 'FuelMg_CNG'] = self.col['FuelMg_CNG']['ORG']
        self.col.loc['DryRes', 'ElecMg'] = self.col['ElecMg']['ORG']

        # Energy use is calculated for REC and it is same with WetRes
        self.col.loc['WetRes', 'FuelMg'] = self.col['FuelMg']['REC']
        self.col.loc['WetRes', 'FuelMg_CNG'] = self.col['FuelMg_CNG']['REC']
        self.col.loc['WetRes', 'ElecMg'] = self.col['ElecMg']['REC']


        self.output = self.col[['TotalMass', 'FuelMg', 'FuelMg_CNG',
                                'ElecMg', 'FuelMg_dov', 'C_collection']]
        self.output = self.output.fillna(0.0)
        self.output.loc['SSO_HC', :] = 0.0

    def calc(self):
        self.calc_composition()
        self.calc_destin()

    # setup for Monte Carlo simulation
    def setup_MC(self, seed=None):
        self.InputData.setup_MC(seed)

    # Calculate based on the generated numbers
    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        self.calc()
        return input_list

    def report(self):
        # report
        self.collection = {}
        Waste = {}
        Technosphere = {}
        Biosphere = {}
        self.collection["process name"] = (self.process_name,
                                           self.Process_Type,
                                           self.__class__)
        self.collection["Waste"] = Waste
        self.collection["Technosphere"] = Technosphere
        self.collection["Biosphere"] = Biosphere
        self.collection['LCI'] = self.result_destination

        for x in [Waste, Technosphere, Biosphere]:
            for y in self.Index:
                x[y] = {}

        for y in self.Index:
            for x in self.col_massflow.columns:
                Waste[y][x] = self.col_massflow[x][y]
        return self.collection
