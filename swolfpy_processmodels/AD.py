# -*- coding: utf-8 -*-
"""
Created on Wed Jul 17 16:35:15 2019

@author: msardar2
"""
from .ProcessModel import ProcessModel
from swolfpy_inputdata import AD_Input
from .Common_subprocess import Flow, LCI
from .Common_subprocess import compost_use
from .AD_subprocess import screen, Post_screen, mix, curing
from .AD_subprocess import add_water, Reactor, Dewater
import numpy_financial as npf
import plotly.graph_objects as go
from plotly.offline import plot


class AD(ProcessModel):
    Process_Type = 'Treatment'
    def __init__(self, process_name='AD', input_data_path=None, CommonDataObjct=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData = AD_Input(input_data_path=input_data_path,
                                  process_name=self.process_name,
                                  CommonDataObjct=CommonDataObjct)

        self.Assumed_Comp = self.InputData.process_data['Assumed_Comp']

        self.process_data = self.InputData.process_data

        self.flow_init = Flow(self.Material_Properties)

    def calc(self):
        self.LCI = LCI(index=self.Index, n_col=51)

        # Methane Yield (m3/dry Mg)
        self.Material_Properties['Methane Yield'] = (
            self.Material_Properties['Biogenic Carbon Content'].values / 100
            * self.Material_Properties['Ultimate Biogenic C Converted to Biogas'].values / 100
            * self.CommonData.STP['mole_to_L']['amount']
            / self.CommonData.MW['C']['amount']
            * 0.5
            * 1000)

        ### Initial mass
        self.Input = Flow(self.Material_Properties)
        self.Input.init_flow(1000)

        ### Primary Pre_screen
        self.S1_unders, self.S1_overs = screen(self.Input,
                                               self.process_data['Pre Screen 1'].values / 100,
                                               self.Material_Properties,
                                               self.LCI,
                                               self.flow_init)

        ### Secondary Pre_screen
        self.S2_to_curing, self.S2_residuls = screen(self.S1_overs,
                                                     self.process_data['Pre Screen 2'].values / 100,
                                                     self.Material_Properties,
                                                     self.LCI,
                                                     self.flow_init)

        self.LCI.add(name='Residual',
             flow=self.S2_residuls.data['mass'].values / 1000)

        # Dsl use for grinding
        self.LCI.add(name=('Technosphere', 'Equipment_Diesel'),
                     flow=(self.S2_to_curing.data['mass'].values / 1000
                           * self.InputData.shredding['Mtgp']['amount']
                           * self.InputData.shredding['Mtgf']['amount']))

        ### Adding Water
        """
        M: Moisture, S: solids, Liq: Added water, mc=moisture content
        mc = (Liq + M)/(S + M + Liq)
        mc*Liq = Liq + M - S*mc - mc*M
        Liq = (M - S*mc - mc*M)/(mc-1)
        S + M = mass ==> Liq = (M - mass*mc)/(mc-1)
        Liq = (mass*mc - M)/(1-mc)
        """
        self.water_flow = ((self.S1_unders.data['mass'].values
                            * self.InputData.Material_Properties['ad_mcReactor']['amount']
                            - self.S1_unders.data['moist_cont'].values)
                           / (1 - self.InputData.Material_Properties['ad_mcReactor']['amount']))

        self.to_reactor = add_water(self.S1_unders,
                                    self.water_flow,
                                    self.Material_Properties,
                                    self.process_data,
                                    self.flow_init)

        ### Reactor
        self.digestate = Reactor(self.to_reactor, self.CommonData, self.process_data, self.InputData, self.Material_Properties,
                                 self.LCI, self.flow_init)

        ### Dewatering
        self.Dig_to_Curing_1, self.liq_rem, self.liq_treatment_vol = Dewater(self.digestate, self.to_reactor, self.CommonData, self.process_data, self.InputData,
                                                                             self.Material_Properties, self.water_flow, self.Assumed_Comp.values,
                                                                             self.LCI, self.flow_init)

        ### Mix Dig_to_Curing_1 and S2_to_curing
        self.Dig_to_Curing = mix(self.Dig_to_Curing_1, self.S2_to_curing, self.Material_Properties, self.flow_init)

        ### Curing
        self.compost_to_ps, self.WC_SC = curing(self.Dig_to_Curing, self.to_reactor, self.CommonData, self.process_data,
                                                  self.InputData, self.Assumed_Comp, self.Material_Properties, self.LCI,
                                                  self.flow_init)

        ### Post_screen
        self.FinalCompost, self.Compost_WC, self.Screen_rejects = Post_screen(self.compost_to_ps, self.WC_SC, self.InputData, self.Assumed_Comp.values,
                                                                self.Material_Properties, self.LCI, self.flow_init)

        ### AD Diesel and electricity use (general)
        self.LCI.add(name=('Technosphere', 'Equipment_Diesel'),
                     flow=self.InputData.Fac_Energy['Dsl_facility']['amount'])
        self.LCI.add(name=('Technosphere', 'Electricity_consumption'),
                     flow=self.InputData.Fac_Energy['elec_facility']['amount'])
        self.LCI.add(name=('Technosphere', 'Electricity_consumption'),
                     flow=self.InputData.Fac_Energy['elec_preproc']['amount'])

        ### Compost use
        compost_use(input_flow=self.FinalCompost,
                    common_data=self.CommonData,
                    process_data=self.process_data,
                    material_properties=self.Material_Properties,
                    input_data=self.InputData,
                    lci=self.LCI)

        ### Transportation Compost
        self.LCI.add(name=('Technosphere', 'Internal_Process_Transportation_Medium_Duty_Diesel_Truck'),
                     flow=self.FinalCompost.data['mass'].values * self.InputData.Land_app['distLand']['amount'])
        self.LCI.add(name=('Technosphere', 'Empty_Return_Medium_Duty_Diesel_Truck'),
                     flow=self.FinalCompost.data['mass'].values / 1000 / self.InputData.Land_app['land_payload']['amount'] * self.InputData.Land_app['distLand']['amount'])

        ### Cost Calculation
        capital_cost = -npf.pmt(rate=self.InputData.Economic_parameters['Inerest_rate']['amount'],
                        nper=self.InputData.Economic_parameters['lifetime']['amount'],
                        pv=self.InputData.Economic_parameters['Unit_capital_cost']['amount'])
        self.LCI.add(name=('biosphere3','Capital_Cost'),
                     flow=capital_cost)
        self.LCI.add(name=('biosphere3','Operational_Cost'),
                     flow=[self.InputData.Operational_Cost[y]['amount'] for y in self.Index])

    def setup_MC(self, seed=None):
        self.InputData.setup_MC(seed)
        #self.create_uncertainty_from_inputs()

    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        #self.uncertainty_input_next()
        self.calc()
        return(input_list)

    def report(self):
        report = {}
        report["process name"] = (self.process_name, self.Process_Type, self.__class__)

        self.lci_report = self.LCI.report()

        # Set the value zero if the flow is not in the LCI dataframe.
        for i in [('Technosphere', 'Nitrogen_Fertilizer'),
                  ('Technosphere', 'Phosphorous_Fertilizer'),
                  ('Technosphere', 'Potassium_Fertilizer'),
                  ('Technosphere', 'Peat'),
                  ('Technosphere', 'compost_to_LF'),
                  'Ammonium, ion (ground water)',
                  'Ammonium, ion (surface water)',
                  'Nitrate (ground water)',
                  'Nitrate (surface water)',
                  ('Technosphere', 'market_for_excavation_skid_steer_loader'),
                  'Carbon dioxide, fossil',
                  'Carbon dioxide, non-fossil']:
            if i not in self.lci_report.columns:
                self.lci_report[i] = 0

        net_elec = ((self.lci_report[('Technosphere', 'Electricity_production')].values
                     - self.lci_report[('Technosphere', 'Electricity_consumption')].values)
                    * self.Assumed_Comp.values).sum()
        if net_elec >= 0:
            self.lci_report[('Technosphere', 'Electricity_production')] = (
                self.lci_report[('Technosphere', 'Electricity_production')].values
                - self.lci_report[('Technosphere', 'Electricity_consumption')].values)
            self.lci_report[('Technosphere', 'Electricity_consumption')] = 0
        else:
            self.lci_report[('Technosphere', 'Electricity_consumption')] = (
                self.lci_report[('Technosphere', 'Electricity_consumption')].values
                - self.lci_report[('Technosphere', 'Electricity_production')].values)
            self.lci_report[('Technosphere', 'Electricity_production')] = 0

        self.lci_report['report_Methane, non-fossil'] = (self.lci_report['Methane, non-fossil'].values
                                                         + self.lci_report['Methane, non-fossil (unburned)'].values
                                                         + self.lci_report['Fugitive (Leaked) Methane'].values)

        self.lci_report['report_ CO2 non-fossil'] = (self.lci_report['CO2-biogenic emissions from digested liquids treatment'].values
                                                     + self.lci_report['Carbon dioxide, non-fossil _ Curing'].values
                                                     + self.lci_report['Carbon dioxide, non-fossil'].values
                                                     + self.lci_report['Carbon dioxide, non-fossil (in biogas)'].values
                                                     + self.lci_report['Carbon dioxide, non-fossil from comubstion'].values)

        # NMVOC, non-methane volatile organic compounds, unspecified origin ('air',)
        self.lci_report['report_ NMVOC'] = (self.lci_report['NMVOC, non-methane volatile organic compounds, unspecified origin'].values
                                            + self.lci_report['NMVOCs'].values)


        self._bio_rename_dict = {
            'Ammonia':('biosphere3', '87883a4e-1e3e-4c9d-90c0-f1bea36f8014'), # Ammonia ('air',)
            'Direct Carbon Storage and Humus Formation':('biosphere3', 'e4e9febc-07c1-403d-8d3a-6707bb4d96e6'), # Carbon dioxide, from soil or biomass stock ('air',)
            'report_ CO2 non-fossil':('biosphere3', 'eba59fd6-f37e-41dc-9ca3-c7ea22d602c7'), # Carbon dioxide, non-fossil ('air',)
            'Carbon monoxide (CO)':('biosphere3', '2cb2333c-1599-46cf-8435-3dffce627524'), # Carbon monoxide, non-fossil ('air',)
            'Carbon dioxide, fossil': ('biosphere3', '349b29d1-3e58-4c66-98b9-9d1a076efd2e'), # Carbon dioxide, fossil (air,)
            'Dinitrogen monoxide':('biosphere3', '20185046-64bb-4c09-a8e7-e8a9e144ca98'), # Dinitrogen monoxide ('air',)
            'report_Methane, non-fossil':('biosphere3', 'da1157e2-7593-4dfd-80dd-a3449b37a4d8') , # Methane, non-fossil ('air',)
            'Nitrogen oxides (as NO2)':('biosphere3', 'c1b91234-6f24-417b-8309-46111d09c457'), # Nitrogen oxides ('air',)
            'report_ NMVOC':('biosphere3', 'd3260d0e-8203-4cbb-a45a-6a13131a5108'), # NMVOC, non-methane volatile organic compounds, unspecified origin ('air',)
            'PM2.5':('biosphere3', '21e46cb8-6233-4c99-bac3-c41d2ab99498'), # Particulates, < 2.5 um ('air',)
            'Sulfur dioxide (SO2)':('biosphere3', 'fd7aa71c-508c-480d-81a6-8052aad92646'), # Sulfur dioxide ('air',)
            'Arsenic':('biosphere3', '8c8ffaa5-84ed-4668-ba7d-80fd0f47013f'), # Arsenic, ion ('water', 'surface water')
            'Barium':('biosphere3', '2c872773-0a29-4831-93b9-d49b116fa7d5'),  # Barium ('water', 'surface water')
            'BOD':('biosphere3', '70d467b6-115e-43c5-add2-441de9411348'), # BOD5, Biological Oxygen Demand ('water', 'surface water')
            'Cadmium':('biosphere3', 'af83b42f-a4e6-4457-be74-46a87798f82a'), # Cadmium, ion ('water', 'surface water')
            'Chromium':('biosphere3', 'e34d3da4-a3d5-41be-84b5-458afe32c990'), # Chromium, ion ('water', 'surface water')
            'COD':('biosphere3', 'fc0b5c85-3b49-42c2-a3fd-db7e57b696e3'), # COD, Chemical Oxygen Demand ('water', 'surface water')
            'Copper':('biosphere3', '6d9550e2-e670-44c1-bad8-c0c4975ffca7'), # Copper, ion ('water', 'surface water')
            'Iron':('biosphere3', '7c335b9c-a403-47a8-bb6d-2e7d3c3a230e'), # Iron, ion ('water', 'surface water')
            'Lead':('biosphere3', 'b3ebdcc3-c588-4997-95d2-9785b26b34e1'), # Lead ('water', 'surface water')
            'Mercury':('biosphere3', '66bfb434-78ab-4183-b1a7-7f87d08974fa'), # Mercury ('water', 'surface water')
            'Total N':('biosphere3', 'ae70ca6c-807a-482b-9ddc-e449b4893fe3'), # Nitrogen ('water', 'surface water')
            'Phosphate':('biosphere3', '1727b41d-377e-43cd-bc01-9eaba946eccb'),  # Phosphate ('water', 'surface water')
            'Selenium':('biosphere3', '544dbea9-1d18-44ff-b92b-7866e3baa6dd'), # Selenium ('water', 'surface water')
            'Silver':('biosphere3', 'af9793ba-25a1-4928-a14a-4bcf7d5bd3f7'),  # Silver, ion ('water', 'surface water')
            'Total suspended solids':('biosphere3', '3844f446-ded5-4727-8421-17a00ef4eba7'), # Suspended solids, unspecified ('water', 'surface water')
            'Zinc':('biosphere3', '541b633c-17a3-4047-bce6-0c0e4fdb7c10'), # Zinc, ion ('water', 'surface water')
            'Nitrate (ground water)':('biosphere3', 'b9291c72-4b1d-4275-8068-4c707dc3ce33'), # Nitrate ('water', 'ground-')
            'Nitrate (surface water)':('biosphere3', '7ce56135-2ca5-4fba-ad52-d62a34bfeb35'), # Nitrate ('water', 'surface water')
            'Ammonium, ion (ground water)':('biosphere3', '736f52e8-9703-4076-8909-7ae80a7f8005'), #'Ammonium, ion' (kilogram, None, ('water', 'ground-'))
            'Ammonium, ion (surface water)':('biosphere3', '13331e67-6006-48c4-bdb4-340c12010036') # 'Ammonium, ion' (kilogram, None, ('water', 'surface water'))
            }

        tech_flows = [
            ('Technosphere', 'Electricity_production'),
            ('Technosphere', 'Electricity_consumption'),
            ('Technosphere', 'Equipment_Diesel'),
            ('Technosphere', 'Internal_Process_Transportation_Heavy_Duty_Diesel_Truck'),
            ('Technosphere', 'Internal_Process_Transportation_Medium_Duty_Diesel_Truck'),
            ('Technosphere', 'Empty_Return_Heavy_Duty_Diesel_Truck'),
            ('Technosphere', 'Empty_Return_Medium_Duty_Diesel_Truck'),
            ('Technosphere', 'Nitrogen_Fertilizer'),
            ('Technosphere', 'Phosphorous_Fertilizer'),
            ('Technosphere', 'Potassium_Fertilizer'),
            ('Technosphere', 'Peat'),
            ('Technosphere', 'compost_to_LF'),
            ('Technosphere', 'market_for_excavation_skid_steer_loader')]

        report["Waste"] = {}
        for y in self.Index:
            report["Waste"][y] = {}
            report["Waste"][y]['Other_Residual'] = self.lci_report['Residual'][y]

        report["Technosphere"] = self.lci_report[tech_flows].transpose().to_dict()

        self.lci_report = self.lci_report.rename(columns=self._bio_rename_dict)
        report["Biosphere"] = self.lci_report[list(self._bio_rename_dict.values())
                                              + [('biosphere3','Capital_Cost'),
                                                 ('biosphere3','Operational_Cost')]].transpose().to_dict()
        return(report)

    def plot(self, composition, saveHTML=False):
        source = []
        target = []
        value = []
        lable = ['Incoming Mass', 'Screen 1', 'Screen 2', 'Residuals', 'Add Water', 'Mixer', 'Reactor', 'Dewater',
                 'Curing', 'Post Screen', 'Finished Compost', 'WWT', 'Makeup Water', 'Wood Chips']
        lable_link = []
        color_link = []

        # Link for colors: https://www.rapidtables.com/web/color/RGB_Color.html

        self.Input.update(composition)
        source.append(lable.index('Incoming Mass'))
        target.append(lable.index('Screen 1'))
        value.append(self.Input.flow)
        lable_link.append('Input')
        self.S1_unders.update(composition)
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(128,128,0))) # Olive

        source.append(lable.index('Screen 1'))
        target.append(lable.index('Add Water'))
        value.append(self.S1_unders.flow)
        lable_link.append('S1_unders')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(128,128,0))) # Olive

        self.S1_overs.update(composition)
        source.append(lable.index('Screen 1'))
        target.append(lable.index('Screen 2'))
        value.append(self.S1_overs.flow)
        lable_link.append('S1_overs')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(128,128,128))) # Gray

        self.S2_residuls.update(composition)
        source.append(lable.index('Screen 2'))
        target.append(lable.index('Residuals'))
        value.append(self.S2_residuls.flow)
        lable_link.append('S2_residuls')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(128,128,128))) # Gray

        self.S2_to_curing.update(composition)
        source.append(lable.index('Screen 2'))
        target.append(lable.index('Mixer'))
        value.append(self.S2_to_curing.flow)
        lable_link.append('S2_to_curing')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*	(128,128,0))) # Olive

        self.to_reactor.update(composition)
        source.append(lable.index('Add Water'))
        target.append(lable.index('Reactor'))
        value.append(self.to_reactor.flow)
        lable_link.append('to_reactor')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(85,107,47))) # dark olive green

        self.digestate.update(composition)
        source.append(lable.index('Reactor'))
        target.append(lable.index('Dewater'))
        value.append(self.digestate.flow)
        lable_link.append('digestate')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(107,142,35))) # olive drab

        self.Dig_to_Curing_1.update(composition)
        source.append(lable.index('Dewater'))
        target.append(lable.index('Mixer'))
        value.append(self.Dig_to_Curing_1.flow)
        lable_link.append('Dig_to_Curing_1')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(124,252,0))) # lawn green


        source.append(lable.index('Dewater'))
        target.append(lable.index('Add Water'))
        rec_water = sum(self.liq_rem * composition) - sum(self.liq_treatment_vol * composition) * 1000
        value.append(rec_water)
        lable_link.append('liq_rem')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(0,0,128))) # navy

        self.Dig_to_Curing.update(composition)
        source.append(lable.index('Mixer'))
        target.append(lable.index('Curing'))
        value.append(self.Dig_to_Curing.flow)
        lable_link.append('Dig_to_Curing')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(60,179,113))) # medium sea green

        self.compost_to_ps.update(composition)
        source.append(lable.index('Curing'))
        target.append(lable.index('Post Screen'))
        value.append(self.compost_to_ps.flow)
        lable_link.append('compost_to_ps')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(0,100,0))) # dark green

        source.append(lable.index('Curing'))
        target.append(lable.index('Post Screen'))
        value.append(sum(self.WC_SC * composition))
        lable_link.append('WC_SC')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(160,82,45))) # sienna

        source.append(lable.index('Wood Chips'))
        target.append(lable.index('Curing'))
        value.append(sum(self.WC_SC * composition) - sum(self.Screen_rejects * composition))
        lable_link.append('Wood Chips')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(160,82,45))) # sienna

        source.append(lable.index('Post Screen'))
        target.append(lable.index('Curing'))
        value.append(sum(self.Screen_rejects * composition))
        lable_link.append('Screen_rejects')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(160,82,45))) # sienna

        self.FinalCompost.update(composition)
        source.append(lable.index('Post Screen'))
        target.append(lable.index('Finished Compost'))
        value.append(self.FinalCompost.flow)
        lable_link.append('FinalCompost')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(0,128,0))) # green

        source.append(lable.index('Makeup Water'))
        target.append(lable.index('Add Water'))
        value.append(sum(self.water_flow * composition) - rec_water)
        lable_link.append('Makeup_water')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(0,0,255))) # blue

        source.append(lable.index('Dewater'))
        target.append(lable.index('WWT'))
        value.append(sum(self.liq_treatment_vol * composition)*1000)
        lable_link.append('liq_treatment_vol')
        color_link.append('rgba({}, {}, {}, 0.8)'.format(*(0,0,139))) #dark blue

        fig = go.Figure(data=[go.Sankey(orientation="h",
                                        valueformat=".0f",
                                        valuesuffix="kg",
                                        node=dict(pad=20,
                                                  thickness=20,
                                                  line=dict(color="black", width = 0.5),
                                                  label=lable),
                                        link=dict(source=source,
                                                  target=target,
                                                  value=value,
                                                  label=lable_link,
                                                  color=color_link))])

        fig.update_layout(title_text="Mass flow diagram for AD process",
                          font_size=14,
                          hoverlabel=dict(font_size=14))
        if not saveHTML:
            fig.show()
        else:
            plot(fig, 'plot.html', auto_open=True)
