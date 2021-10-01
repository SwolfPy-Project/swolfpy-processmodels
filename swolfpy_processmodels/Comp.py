# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 21:59:44 2019

@author: msardar2
"""
import numpy_financial as npf
from .ProcessModel import ProcessModel
from swolfpy_inputdata import Comp_Input
from .Common_subprocess import Flow, LCI
from .Common_subprocess import compost_use
from .Comp_subprocess import ac_comp, shredding, screen, mix, add_water, vacuum, post_screen, curing


class Comp(ProcessModel):
    Process_Type = 'Treatment'
    def __init__(self, process_name='Composting', input_data_path=None, CommonDataObjct=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData = Comp_Input(input_data_path, process_name=self.process_name, CommonDataObjct=CommonDataObjct)
        self.Assumed_Comp = self.InputData.process_data['Assumed_Comp']

        self.process_data = self.InputData.process_data

        self.flow_init = Flow(self.Material_Properties)

    def calc(self):
        self.LCI = LCI(index=self.Index)
        ### Initial mass at tipping floor
        self.input_flow = Flow(self.Material_Properties)
        self.input_flow.init_flow(1000)

        ### Primary Pre_screen
        self.S1_unders, self.S1_overs = screen(input_flow=self.input_flow,
                                               sep_eff=self.process_data['Pre Screen 1'].values/100,
                                               Op_param=self.InputData.Screen,
                                               lci=self.LCI,
                                               flow_init=self.flow_init)

        ### Secondary Pre_screen
        self.S2_to_shredding, self.S2_residuls = screen(input_flow=self.S1_overs,
                                                        sep_eff=self.process_data['Pre Screen 2'].values/100,
                                                        Op_param=self.InputData.Screen,
                                                        lci=self.LCI,
                                                        flow_init=self.flow_init)

        ### Shredding/Grinding of seconday screen's unders
        self.shred = shredding(self.S2_to_shredding,
                               self.InputData.Shredding,
                               self.LCI,
                               self.flow_init)

        ### Mixing the shredded and screened materials
        self.mixed = mix(self.S1_unders,
                         self.shred,
                         self.flow_init)

        ### Adding Water
        self.mixed.update(self.Assumed_Comp)
        if self.mixed.moist_cont > self.InputData.Deg_Param['initMC']['amount']:
            self.water_added = 0
        else:
            self.water_added = ((self.InputData.Deg_Param['initMC']['amount']
                                 * self.mixed.flow - self.mixed.water)
                                / (1 - self.InputData.Deg_Param['initMC']['amount']))

        water_flow = (self.water_added * self.mixed.data['sol_cont'].values
                      / self.mixed.solid)

        self.substrate_to_ac = add_water(self.mixed,
                                         water_flow,
                                         self.Material_Properties,
                                         self.process_data,
                                         self.flow_init)

        ### Active Composting
        self.substrate_to_ps = ac_comp(self.substrate_to_ac,
                                       self.CommonData,
                                       self.process_data,
                                       self.InputData,
                                       self.Assumed_Comp,
                                       self.LCI,
                                       self.flow_init)

        ### Post screen
        self.substrate_to_vac, self.ps_res = post_screen(self.substrate_to_ps,
                                                         self.process_data['Post Screen'].values/100,
                                                         self.InputData.Screen,
                                                         self.LCI,
                                                         self.flow_init)

        ### Vacuum
        self.substrate_to_cu, self.vac_res = vacuum(self.substrate_to_vac,
                                                    self.process_data['Vacuum'].values/100,
                                                    self.InputData.Vaccum_sys,
                                                    self.LCI,
                                                    self.flow_init)

        ### Curing
        self.final_comp = curing(self.substrate_to_cu,
                                 self.CommonData,
                                 self.process_data,
                                 self.InputData,
                                 self.Assumed_Comp,
                                 self.LCI,
                                 self.flow_init)

        ### Calculating the P and K in final compost
        """
        Assumption: composition of ps_res == composition of vac_res  == composition of mixed,
        while the composition has changed because of active composting and curing
        """
        solids = (self.mixed.data['sol_cont'].values
                  - self.ps_res.data['sol_cont'].values
                  - self.vac_res.data['sol_cont'].values)

        self.final_comp.data['P_cont'] = (solids
                                          * self.Material_Properties['Phosphorus Content'].values / 100
                                          * self.process_data['Degrades'].values)

        self.final_comp.data['K_cont'] = (solids
                                          * self.Material_Properties['Potassium Content'].values / 100
                                          * self.process_data['Degrades'].values)

        ### Compost use
        compost_use(input_flow=self.final_comp,
                    common_data=self.CommonData,
                    process_data=self.process_data,
                    material_properties=self.Material_Properties,
                    input_data=self.InputData,
                    lci=self.LCI)

        ### All Residuals
        self.LCI.add(name='Other_Residual',
                     flow=(self.ps_res.data['mass'].values
                           + self.vac_res.data['mass'].values
                           + self.S2_residuls.data['mass'].values) / 1000)

        ### office
        Office_elec = ((self.InputData.Office['Mta']['amount']
                        * self.InputData.Office['Mea']['amount'] / 1000)
                       / self.InputData.Op_Param['Taod']['amount'])

        self.LCI.add(name=('Technosphere', 'Electricity_consumption'),
                     flow=Office_elec)

        ### Transportation
        self.LCI.add(name='Medium-duty truck transportation to land application',
                     flow=(self.final_comp.data['mass'].values
                           * self.InputData.Land_app['distLand']['amount']))

        self.LCI.add(name='Medium-duty empty return',
                     flow=(self.final_comp.data['mass'].values / 1000
                           / self.InputData.Land_app['land_payload']['amount']
                           * self.InputData.Land_app['distLand']['amount']))

        ### Cost Calculation
        capital_cost = -npf.pmt(rate=self.InputData.Economic_parameters['Inerest_rate']['amount'],
                                nper=self.InputData.Economic_parameters['lifetime']['amount'],
                                pv=self.InputData.Economic_parameters['Unit_capital_cost']['amount'])
        self.LCI.add(name=('biosphere3','Capital_Cost'),
                     flow=capital_cost)

        self.LCI.add(name=('biosphere3','Operational_Cost'),
                     flow=[self.InputData.Operational_Cost[y]['amount'] for y in self.Index])

    def setup_MC(self,seed=None):
        self.InputData.setup_MC(seed)
        #self.create_uncertainty_from_inputs()

    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        #self.uncertainty_input_next()
        self.calc()
        return input_list

    def report(self):
        report = {}
        report["process name"] = (self.process_name, self.Process_Type, self.__class__)
        report["Waste"] = {}
        report["Technosphere"] = {}
        report["Biosphere"] = {}

        lci_report = self.LCI.report()

        for i in [('Technosphere', 'compost_to_LF'), ('Technosphere', 'Nitrogen_Fertilizer'),
                  ('Technosphere', 'Phosphorous_Fertilizer'), ('Technosphere', 'Potassium_Fertilizer'),
                  ('Technosphere', 'Peat'), 'Ammonium, ion (ground water)',
                  'Ammonium, ion (surface water)', 'Nitrate (ground water)',
                  ('Technosphere', 'market_for_excavation_skid_steer_loader'),
                  ('Technosphere', 'Electricity_production'),
                  'Carbon dioxide, fossil']:
            if i not in lci_report.columns:
                lci_report[i] = 0

        for x in ['Waste', 'Technosphere', 'Biosphere']:
            for y in self.Index:
                report[x][y] = {}

        net_elec = ((lci_report[('Technosphere', 'Electricity_production')].values
                     - lci_report[('Technosphere', 'Electricity_consumption')].values)
                    * self.Assumed_Comp.values).sum()

        if net_elec >= 0:
            lci_report[('Technosphere', 'Electricity_production')] = (
                lci_report[('Technosphere', 'Electricity_production')].values
                - lci_report[('Technosphere', 'Electricity_consumption')].values)
            lci_report[('Technosphere', 'Electricity_consumption')] = 0
        else:
            lci_report[('Technosphere', 'Electricity_consumption')] = (
                lci_report[('Technosphere', 'Electricity_consumption')].values
                - lci_report[('Technosphere', 'Electricity_production')].values)
            lci_report[('Technosphere', 'Electricity_production')] = 0
        
        for y in self.Index:
            ### Output Waste Database
            report["Waste"][y]['Other_Residual'] = lci_report['Other_Residual'][y]

            ### Output Technospphere Database
            report["Technosphere"][y][('Technosphere', 'Electricity_consumption')] =  lci_report[('Technosphere', 'Electricity_consumption')][y]
            report["Technosphere"][y][('Technosphere', 'Electricity_production')] =  lci_report[('Technosphere', 'Electricity_production')][y]
            report["Technosphere"][y][('Technosphere', 'Equipment_Diesel')] =  lci_report[('Technosphere', 'Equipment_Diesel')][y]
            report["Technosphere"][y][('Technosphere', 'Internal_Process_Transportation_Medium_Duty_Diesel_Truck')] = lci_report['Medium-duty truck transportation to land application'][y]
            report["Technosphere"][y][('Technosphere', 'Empty_Return_Medium_Duty_Diesel_Truck')] =lci_report['Medium-duty empty return'][y]
            report["Technosphere"][y][('Technosphere', 'Nitrogen_Fertilizer') ] = lci_report[('Technosphere', 'Nitrogen_Fertilizer')][y]
            report["Technosphere"][y][('Technosphere', 'Phosphorous_Fertilizer')] = lci_report[('Technosphere', 'Phosphorous_Fertilizer')][y]
            report["Technosphere"][y][('Technosphere', 'Potassium_Fertilizer')] = lci_report[('Technosphere', 'Potassium_Fertilizer')][y]
            report["Technosphere"][y][('Technosphere', 'Peat')] = lci_report[('Technosphere', 'Peat')][y]
            report["Technosphere"][y][('Technosphere', 'compost_to_LF')] = lci_report[('Technosphere', 'compost_to_LF')][y]
            report["Technosphere"][y][('Technosphere', 'market_for_excavation_skid_steer_loader')] = lci_report[('Technosphere', 'market_for_excavation_skid_steer_loader')][y]

            ### Output Biosphere Database
            report['Biosphere'][y][('biosphere3', '87883a4e-1e3e-4c9d-90c0-f1bea36f8014')] = lci_report['Ammonia'][y] #  Ammonia ('air',)
            report['Biosphere'][y][('biosphere3', 'e4e9febc-07c1-403d-8d3a-6707bb4d96e6')] = lci_report['Direct Carbon Storage and Humus Formation'][y]  #Carbon dioxide, from soil or biomass stock ('air',)
            report['Biosphere'][y][('biosphere3', 'eba59fd6-f37e-41dc-9ca3-c7ea22d602c7')] = lci_report['Carbon dioxide, non-fossil'][y] #Carbon dioxide, non-fossil ('air',)
            report['Biosphere'][y][('biosphere3', '349b29d1-3e58-4c66-98b9-9d1a076efd2e')] = lci_report['Carbon dioxide, fossil'][y] # Carbon dioxide, fossil (air,)
            report['Biosphere'][y][('biosphere3', '20185046-64bb-4c09-a8e7-e8a9e144ca98')] = lci_report['Dinitrogen monoxide'][y] #Dinitrogen monoxide ('air',)
            report['Biosphere'][y][('biosphere3', 'da1157e2-7593-4dfd-80dd-a3449b37a4d8')] = lci_report['Methane, non-fossil'][y] #Methane, non-fossil ('air',)
            report['Biosphere'][y][('biosphere3', 'c1b91234-6f24-417b-8309-46111d09c457')] = lci_report['Nitrogen oxides'][y] #Nitrogen oxides ('air',)
            report['Biosphere'][y][('biosphere3', 'd3260d0e-8203-4cbb-a45a-6a13131a5108')] = lci_report['VOCs emitted'][y] #NMVOC, non-methane volatile organic compounds, unspecified origin ('air',)
            report['Biosphere'][y][('biosphere3', 'b9291c72-4b1d-4275-8068-4c707dc3ce33')] = lci_report['Nitrate (ground water)'][y] #Nitrate ('water', 'ground-')
            report['Biosphere'][y][('biosphere3', '7ce56135-2ca5-4fba-ad52-d62a34bfeb35')] = lci_report['Nitrate (surface water)'][y] #Nitrate ('water', 'surface water')
            report['Biosphere'][y][('biosphere3', '736f52e8-9703-4076-8909-7ae80a7f8005')] = lci_report['Ammonium, ion (ground water)'][y] #'Ammonium, ion' (kilogram, None, ('water', 'ground-'))
            report['Biosphere'][y][('biosphere3', '13331e67-6006-48c4-bdb4-340c12010036')] = lci_report['Ammonium, ion (surface water)'][y] # 'Ammonium, ion' (kilogram, None, ('water', 'surface water'))
            report['Biosphere'][y][('biosphere3','Capital_Cost')] = lci_report[('biosphere3','Capital_Cost')][y]
            report['Biosphere'][y][('biosphere3','Operational_Cost')] = lci_report[('biosphere3','Operational_Cost')][y]

        return report
