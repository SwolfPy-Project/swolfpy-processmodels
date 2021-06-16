# -*- coding: utf-8 -*-
"""
Created on Thu Jun 10 12:25:21 2021

@author: m.sardar
"""
from .ProcessModel import ProcessModel
from swolfpy_inputdata import HC_Input
from .HC_subprocess import active_comp
from .Common_subprocess import Flow, LCI
from .Common_subprocess import compost_use
import numpy_financial as npf


class HC(ProcessModel):
    Process_Type = 'Treatment'
    def __init__(self, process_name='Home Composting', input_data_path=None, CommonDataObjct=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData = HC_Input(input_data_path, process_name=self.process_name, CommonDataObjct=CommonDataObjct)

        self.process_data = self.InputData.process_data

    def calc(self):
        self.LCI = LCI(index=self.Index)

        # Incominh Mass
        self.input_flow = Flow(self.Material_Properties)
        self.input_flow.init_flow(1000)

        # Active Compostig
        self.final_compost = active_comp(input_flow=self.input_flow,
                                         common_data=self.CommonData,
                                         input_data=self.InputData,
                                         process_data=self.process_data,
                                         material_properties=self.Material_Properties,
                                         lci=self.LCI)

        # Compost use
        compost_use(input_flow=self.final_compost,
                    common_data=self.CommonData,
                    process_data=self.process_data,
                    material_properties=self.Material_Properties,
                    input_data=self.InputData,
                    lci=self.LCI,
                    include_diesel=False)

        # Cost
        op_cost_tot = -npf.pmt(rate=self.InputData.Economic_parameters['Inerest_rate']['amount'],
                               nper=self.InputData.Economic_parameters['lifetime']['amount'],
                               pv=self.InputData.Economic_parameters['comp_cost']['amount'])
        op_cost = (op_cost_tot
                   / (self.InputData.Op_param['Taod']['amount']
                      * self.InputData.Op_param['comp_cap']['amount'] / 1000))

        self.LCI.add(name=('biosphere3','Operational_Cost'),
                     flow=op_cost)

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

        lci_report = self.LCI.report()

        for i in [('Technosphere', 'Nitrogen_Fertilizer'),
                  ('Technosphere', 'Phosphorous_Fertilizer'),
                  ('Technosphere', 'Potassium_Fertilizer'),
                  ('Technosphere', 'Peat'),
                  'Nitrate (ground water)',
                  'Nitrate (surface water)',
                  'Carbon dioxide, fossil']:
            if i not in lci_report.columns:
                lci_report[i] = 0

        for x in ["Waste", "Technosphere", "Biosphere"]:
            for y in self.Index:
                report[x][y]={}

        for y in self.Index:
            # Output Technospphere Database
            report["Technosphere"][y][('Technosphere', 'Nitrogen_Fertilizer') ] = lci_report[('Technosphere', 'Nitrogen_Fertilizer')][y]
            report["Technosphere"][y][('Technosphere', 'Phosphorous_Fertilizer')] = lci_report[('Technosphere', 'Phosphorous_Fertilizer')][y]
            report["Technosphere"][y][('Technosphere', 'Potassium_Fertilizer')] = lci_report[('Technosphere', 'Potassium_Fertilizer')][y]
            report["Technosphere"][y][('Technosphere', 'Peat')] = lci_report[('Technosphere', 'Peat')][y]

            # Output Biosphere Database
            # C compounds
            report["Biosphere"][y][('biosphere3', 'e4e9febc-07c1-403d-8d3a-6707bb4d96e6')]= lci_report['Direct Carbon Storage and Humus Formation'][y]  # Carbon dioxide, from soil or biomass stock ('air',)
            report["Biosphere"][y][('biosphere3', 'eba59fd6-f37e-41dc-9ca3-c7ea22d602c7')]= lci_report['Carbon dioxide, non-fossil'][y] # Carbon dioxide, non-fossil (air,)
            report["Biosphere"][y][('biosphere3', '349b29d1-3e58-4c66-98b9-9d1a076efd2e')]= lci_report['Carbon dioxide, fossil'][y] # Carbon dioxide, fossil (air,)
            report["Biosphere"][y][('biosphere3', '2cb2333c-1599-46cf-8435-3dffce627524')]= lci_report['Carbon monoxide, non-fossil'][y] # Carbon monoxide, non-fossil (air,)
            report["Biosphere"][y][('biosphere3', 'da1157e2-7593-4dfd-80dd-a3449b37a4d8')]= lci_report['Methane, non-fossil'][y] # Methane, non-fossil (air,)

            # N compounds
            report["Biosphere"][y][('biosphere3', 'e5ea66ee-28e2-4e9b-9a25-4414551d821c')]= lci_report['Nitrogen'][y] # Nitrogen (air,)
            report["Biosphere"][y][('biosphere3', '87883a4e-1e3e-4c9d-90c0-f1bea36f8014')]= lci_report['Ammonia'][y] # Ammonia ('air',)
            report["Biosphere"][y][('biosphere3', '20185046-64bb-4c09-a8e7-e8a9e144ca98')]= lci_report['Dinitrogen monoxide'][y] # Dinitrogen monoxide (air,)
            report["Biosphere"][y][('biosphere3', 'b9291c72-4b1d-4275-8068-4c707dc3ce33')]= lci_report['Nitrate (ground water)'][y] # Nitrate (water, ground-)
            report["Biosphere"][y][('biosphere3', '7ce56135-2ca5-4fba-ad52-d62a34bfeb35')]= lci_report['Nitrate (surface water)'][y] # Nitrate (water, surface water)

            # VOCs
            report["Biosphere"][y][('biosphere3', 'd3260d0e-8203-4cbb-a45a-6a13131a5108')]= lci_report['VOCs emitted'][y] # NMVOC, non-methane volatile organic compounds, unspecified origin (air,)

            # Cost
            report["Biosphere"][y][('biosphere3','Operational_Cost')]= lci_report[('biosphere3','Operational_Cost')][y]

        return report
