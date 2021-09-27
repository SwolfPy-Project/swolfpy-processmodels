# -*- coding: utf-8 -*-
"""
Created on Thu Sep  2 12:42:12 2021

@author: msardar2
"""
import pandas as pd
import numpy_financial as npf
from swolfpy_inputdata import GC_Input
from .ProcessModel import ProcessModel


class GC(ProcessModel):
    """
    """
    Process_Type = 'RDF'
    def __init__(self, process_name='Gasification Syngas Combustion',
                 input_data_path=None, CommonDataObjct=None):
        super().__init__(process_name, CommonDataObjct)

        self.InputData = GC_Input(input_data_path, process_name=self.process_name,
                                  CommonDataObjct=CommonDataObjct)

        self.process_data = self.InputData.process_data

    def calc(self):
        self._input_rdf = pd.DataFrame(index=self.CommonData.Index)
        self._input_rdf['mass'] = self.process_data['Assumed_Comp'].values
        self._input_rdf['moist'] = (self._input_rdf['mass'].values
                                    * self.Material_Properties['Moisture Content'].values / 100)
        self._input_rdf['solid'] = self._input_rdf['mass'].values - self._input_rdf['moist'].values
        self._input_rdf['solid_comp'] = self._input_rdf['solid'].values / sum(self._input_rdf['solid'].values)


        # RDF drying: Energy use (heat & electricity)
        moist_cont = self._input_rdf['moist'].sum() / self._input_rdf['mass'].sum()
        if  moist_cont > self.InputData.Dryer['moist_cont']['amount']:
            water_evap = (moist_cont - self._input_rdf['solid'].sum()
                          / (1 - self.InputData.Dryer['moist_cont']['amount'])
                          * self.InputData.Dryer['moist_cont']['amount'])
        else:
            water_evap = 0

        # Dried RDF: chemical/physical properties
        self._dry_rdf = pd.DataFrame(columns=['value', 'unit'])
        if water_evap > 0:
            self._dry_rdf.loc['moist', 'value'] = (self._input_rdf['moist'].sum()
                                                   - water_evap)
            self._dry_rdf.loc['moist_cont', 'value'] = self.InputData.Dryer['moist_cont']['amount']
        else:
            self._dry_rdf.loc['moist', 'value'] = self._input_rdf['moist'].sum()
            self._dry_rdf.loc['moist_cont', 'value'] = moist_cont

        self._dry_rdf.loc['solid', 'value'] = self._input_rdf['solid'].sum()
        self._dry_rdf.loc['mass', 'value'] = (self._dry_rdf.loc['solid', 'value']
                                              + self._dry_rdf.loc['moist', 'value'])
        self._dry_rdf.loc['ash', 'value'] = sum(self._input_rdf['solid'].values
                                                * self.Material_Properties['Ash Content']
                                                / 100)
        self._dry_rdf.loc[['moist', 'solid', 'mass', 'ash'], 'unit'] = 'Mg/Mg RDF'
        self._dry_rdf.loc['moist_cont', 'unit'] = 'fraction'

        agent_ratio, ratio, CH4 = self._feed_stock_spec(self._input_rdf['solid'],
                                                        self._dry_rdf.loc['moist', 'value'],
                                                        self._dry_rdf.loc['mass', 'value'])
        # Calculation of C, H, N, O
        self._dry_rdf.loc['C_mole', :] = (sum(self._input_rdf['solid']
                                              * (self.Material_Properties['Biogenic Carbon Content']
                                                 + self.Material_Properties['Fossil Carbon Content'])
                                              / 100
                                              / self.CommonData.MW['C']['amount']),
                                          'Mg mole/Mg RDF')

        self._dry_rdf.loc['frac_biogenic_C', :] = (
            sum(self._input_rdf['solid'] * self.Material_Properties['Biogenic Carbon Content'])
            / sum(self._input_rdf['solid']
                  * (self.Material_Properties['Biogenic Carbon Content']
                     + self.Material_Properties['Fossil Carbon Content']))), 'fraction'

        def helper_sld_cont(cont, element):
            sld_cont = sum(self._input_rdf['solid']
                           * self.Material_Properties[cont]
                           / 100
                           / self.CommonData.MW[element]['amount'])
            return sld_cont, 'Mg mole/Mg RDF'

        self._dry_rdf.loc['H_mole', :] = helper_sld_cont('Hydrogen Content', 'H')
        self._dry_rdf.loc['N_mole', :] = helper_sld_cont('Nitrogen Content', 'N')
        self._dry_rdf.loc['O_mole', :] = helper_sld_cont('Oxygen Content', 'O')
        self._dry_rdf.loc['S_mole', :] = helper_sld_cont('Sulphur', 'S')
        self._dry_rdf.loc['Cl_mole', :] = helper_sld_cont('Chlorine', 'Cl')

        def helper_react(element):
            self._dry_rdf.loc[element + '_react', :] = (
                self._dry_rdf.loc[element, 'value']
                * self.InputData.Gasifier['frac_react']['amount'],
                'Mg mole/Mg RDF')

        # Calculation of reated C, H, N, O
        for element in ['C_mole', 'H_mole', 'N_mole', 'O_mole', 'S_mole', 'Cl_mole']:
            helper_react(element)

        # Add the H and O of moisture
        self._dry_rdf.loc['H_mole_react_tot', :] = (self._dry_rdf.loc['H_mole_react', 'value']
                                                    + self._dry_rdf.loc['moist', 'value']
                                                    / self.CommonData.MW['H2O']['amount']
                                                    * 2,
                                                    'Mg mole/Mg RDF')
        self._dry_rdf.loc['O_mole_react_tot', :] = (self._dry_rdf.loc['O_mole_react', 'value']
                                                    + self._dry_rdf.loc['moist', 'value']
                                                    / self.CommonData.MW['H2O']['amount'],
                                                    'Mg mole/Mg RDF')

        self._dry_rdf.loc['C_cont', :] = (sum(self._input_rdf['solid']
                                              * (self.Material_Properties['Biogenic Carbon Content']
                                                 + self.Material_Properties['Fossil Carbon Content'])
                                              / 100) / self._input_rdf['solid'].sum(),
                                          'Mg mole/Mg RDF')

        # Mass ratio of gasifier agent to RDF
        self._dry_rdf.loc['agent_ratio', :] = (agent_ratio, 'Mg/Mg Dry RDF')
        self._dry_rdf.loc['agent_mass', :] = (agent_ratio
                                              * self._dry_rdf.loc['mass', 'value'],
                                              'Mg/Mg RDF')


        self._dry_rdf.loc['agent_O_mole', :] = (self._dry_rdf.loc['agent_mass', 'value']
                                                / self.CommonData.Air['MW']['amount']
                                                * self.CommonData.Air['O_cont']['amount'] * 2,
                                                'Mg mole/Mg RDF')
        self._dry_rdf.loc['agent_N_mole', :] = (self._dry_rdf.loc['agent_mass', 'value']
                                                / self.CommonData.Air['MW']['amount']
                                                * self.CommonData.Air['N_cont']['amount'] * 2,
                                                'Mg mole/Mg RDF')

        self._dry_rdf.loc['O_mole_final', :] = (self._dry_rdf.loc['O_mole_react_tot', 'value']
                                                + self._dry_rdf.loc['agent_O_mole', 'value'],
                                                'Mg mole/Mg RDF')

        self._dry_rdf.loc['N_mole_final', :] = (self._dry_rdf.loc['N_mole_react', 'value']
                                                + self._dry_rdf.loc['agent_N_mole', 'value'],
                                                'Mg mole/Mg RDF')

        # gasification products
        self.gasifier_products = pd.DataFrame(columns=['value', 'unit'])
        self.gasifier_products.loc['H2/CO', :] = (ratio, 'mole/mole')
        CH4_mole = CH4 * self._dry_rdf.loc['mass', 'value']
        self.gasifier_products.loc['CH4', :] = CH4_mole, 'Mg mole/Mg RDF'

        CO_mole, CO2_mole, H2_mole, N2_mole, H2O_mole = GC._gasifier_products(
            C_mole=self._dry_rdf.loc['C_mole_react', 'value'],
            H_mole=self._dry_rdf.loc['H_mole_react_tot', 'value'],
            O_mole=self._dry_rdf.loc['O_mole_final', 'value'],
            N_mol=self._dry_rdf.loc['N_mole_final', 'value'],
            CH4_mole=CH4_mole,
            ratio=ratio,
            moist_mole=self._dry_rdf.loc['moist', 'value']/self.CommonData.MW['H2O']['amount'])

        self.gasifier_products.loc['CO', :] = CO_mole, 'Mg mole/Mg RDF'
        self.gasifier_products.loc['CO2', :] = CO2_mole, 'Mg mole/Mg RDF'
        self.gasifier_products.loc['H2', :] = H2_mole, 'Mg mole/Mg RDF'
        self.gasifier_products.loc['N2', :] = N2_mole, 'Mg mole/Mg RDF'
        self.gasifier_products.loc['H2O', :] = H2O_mole, 'Mg mole/Mg RDF'

        self.gasifier_products.loc['Bottom Ash', :] = (
            self._dry_rdf.loc['ash', 'value']
            + self._dry_rdf.loc['solid', 'value']
            * (1 - self.InputData.Gasifier['frac_react']['amount'])), 'Mg/Mg RDF'

        # Energy calculations
        self.energy = pd.DataFrame(columns=['value', 'unit'])

        self.energy.loc['LHV_SYNGAS', :] = (
            self.gasifier_products.loc['CO', 'value'] * self.CommonData.LHV['CO_mole']['amount']
            + self.gasifier_products.loc['H2', 'value'] * self.CommonData.LHV['H2_mole']['amount']
            + self.gasifier_products.loc['CH4', 'value'] * self.CommonData.LHV['CH4_mole']['amount']
            ) * 1000, 'MJ/Mg RDF'

        self.energy.loc['LHV_RDF', :] = (
            sum(self._input_rdf['solid'] * self.CommonData.Material_Properties['Lower Heating Value'])
            - sum(self._input_rdf['moist']) * self.CommonData.Evap_heat['water']['amount']) * 1000, 'MJ/Mg RDF'

        # Cold Gas Efficiency
        self.energy.loc['Cold Gas Eff', :] = (
            self.energy.loc['LHV_SYNGAS', 'value']
            / self.energy.loc['LHV_RDF', 'value'] * 100), '%'

        total_moles = CO_mole + CO2_mole + H2_mole + N2_mole + H2O_mole + CH4_mole
        self.syngas = pd.DataFrame(columns=['value', 'unit'])
        self.syngas.loc['CO', :] = CO_mole / total_moles * 100, '%mole'
        self.syngas.loc['CO2', :] = CO2_mole / total_moles* 100, '%mole'
        self.syngas.loc['H2', :] = H2_mole / total_moles* 100, '%mole'
        self.syngas.loc['N2', :] = N2_mole / total_moles* 100, '%mole'
        self.syngas.loc['H2O', :] = H2O_mole / total_moles* 100, '%mole'
        self.syngas.loc['CH4', :] = CH4_mole / total_moles* 100, '%mole'
        self.syngas.loc['LHV', :] = (
            self.energy.loc['LHV_SYNGAS', 'value']
            / (total_moles
               * self.CommonData.STP['mole_to_L']['amount'] * 1000)
            ), 'MJ/NM3'

        # Sensible heat of syngas: Gasifier temp at 900 C
        # Syngas is cooled to 150 C
        self.energy.loc['Sensible_Heat_SYNGAS', :] = (
            CO_mole * self.CommonData.Heat_cap['CO']['amount']
            + CO2_mole * self.CommonData.Heat_cap['CO2']['amount']
            + H2_mole * self.CommonData.Heat_cap['H2']['amount']
            + N2_mole * self.CommonData.Heat_cap['N2']['amount']
            + H2O_mole * self.CommonData.Heat_cap['H2O']['amount']
            + CH4_mole * self.CommonData.Heat_cap['CH4']['amount']
            ) * (900 - 150), 'MJ/Mg RDF'

        # Hot gas eff
        self.energy.loc['Hot Gas Eff', :] = (
            (self.energy.loc['LHV_SYNGAS', 'value']
             + self.energy.loc['Sensible_Heat_SYNGAS', 'value'])
            / self.energy.loc['LHV_RDF', 'value'] * 100), '%'

        # Dryer
        if water_evap > 0:
            self.energy.loc['Elec Dryer', :] = (
                water_evap * 1000
                * self.InputData.Dryer['elec_use']['amount']
                / 3.6), 'kWh/Mg RDF'
            self.energy.loc['Heat Dryer', :] = (
                water_evap * 1000
                * self.InputData.Dryer['heat_use']['amount']
                ), 'MJ/Mg RDF'
        else:
            self.energy.loc['Elec Dryer', :] = 0.0, 'kWh/Mg RDF'
            self.energy.loc['Heat Dryer', :] = 0.0, 'MJ/Mg RDF'

        # Steam turbine for electricity production
        self.energy.loc['Elec Steam_Turbin HP', :] = (
            self.energy.loc['LHV_SYNGAS', 'value']
            * self.InputData.Energy['elec_gen_eff_HP']['amount']
            / 3.6), 'kWh/Mg RDF'

        # Elec produced from MP steam recovered from excess heat
        self.energy.loc['Elec Steam_Turbin MP', :] = (
            (self.energy.loc['Sensible_Heat_SYNGAS', 'value']
             * self.InputData.Energy['heat_rec_eff']['amount']
             - self.energy.loc['Heat Dryer', 'value'])
            * self.InputData.Energy['elec_gen_eff_MP']['amount']
            / 3.6), 'kWh/Mg RDF'

        # Internal electricity use for syngas cleaning and ...
        self.energy.loc['Elec Internal_use', :] = (
            self.energy.loc['LHV_RDF', 'value']
            * self.InputData.Energy['frac_lhv_internal_elec']['amount']
            / 3.6), 'kWh/Mg RDF'

        # Net electricity production
        self.energy.loc['Net Elec prod', :] = (
            self.energy.loc['Elec Steam_Turbin HP', 'value']
            + self.energy.loc['Elec Steam_Turbin MP', 'value']
            - self.energy.loc['Elec Internal_use', 'value']
            - self.energy.loc['Elec Dryer', 'value']), 'kWh/Mg RDF'

        # Emissions
        self.bio_flows = self._biosphere_flows()

        # Add cost
        self._calc_cost()

    def _feed_stock_spec(self, solids, moist, mass):
        """
        Calculates agent_ratio, ratio, CH4
        """
        # Calculate O, H, N, and C content (Mg Mole / Mg)
        C_cont = sum(solids
                     * (self.Material_Properties['Biogenic Carbon Content']
                        + self.Material_Properties['Fossil Carbon Content'])
                     / 100
                     * self.InputData.Gasifier['frac_react']['amount']
                     / self.CommonData.MW['C']['amount']) / mass

        N_cont = sum(solids
                     * self.Material_Properties['Nitrogen Content']
                     / 100
                     * self.InputData.Gasifier['frac_react']['amount']
                     / self.CommonData.MW['N']['amount']) / mass

        H_cont = sum(solids
                     * self.Material_Properties['Hydrogen Content']
                     / 100
                     * self.InputData.Gasifier['frac_react']['amount']
                     / self.CommonData.MW['H']['amount']) / mass

        O_cont = sum(solids
                     * self.Material_Properties['Oxygen Content']
                     / 100
                     * self.InputData.Gasifier['frac_react']['amount']
                     / self.CommonData.MW['O']['amount']) / mass

        # Add O and H content of moisture
        H_cont += (moist / self.CommonData.MW['H2O']['amount'] * 2) / mass
        O_cont += (moist / self.CommonData.MW['H2O']['amount']) / mass

        # Calculate moist content (Mg moist/Mg)
        moist_cont = moist / mass

        agent_ratio = GC._agent_ratio(C_cont, H_cont, O_cont, moist_cont)

        # Add O and N content of agent
        O_cont += agent_ratio / self.CommonData.Air['MW']['amount'] * self.CommonData.Air['O_cont']['amount'] * 2
        N_cont += agent_ratio / self.CommonData.Air['MW']['amount'] * self.CommonData.Air['N_cont']['amount'] * 2

        ash = sum(solids
                  * self.Material_Properties['Ash Content']
                  / 100) / mass

        ratio, CH4 = GC._gasifier_prod_spec(C_cont, H_cont, O_cont, N_cont, moist_cont, ash)

        return agent_ratio, ratio, CH4

    @staticmethod
    def _agent_ratio(C_mole, H_mole, O_mole, moist):
        """
        Calculates the mass ratio of gasifying agent to feedstock
        """
        ratio = (47.056 * C_mole
                 + 14.687 * H_mole
                 - 21.327 * O_mole
                 + 0.957 * moist)
        return ratio

    @staticmethod
    def _gasifier_prod_spec(C_mole, H_mole, O_mole, N_mole, moist, ash):
        """
        Calculates the H2/CO and CH4 in the gasifier products
        """
        ratio = (2.038698561 * ash
                 - 157.4311171 * C_mole
                 - 41.41348052 * H_mole
                 + 33.9749132 * N_mole
                 + 106.660806 * O_mole
                 + 0.940837584 * (O_mole / C_mole)
                 + 0.862032712 * (O_mole / H_mole)
                 - 2.578002065 * (O_mole / (C_mole + H_mole / 4))
                 - 0.568261819 * (C_mole / H_mole)
                 - 3.2554175 * moist)

        if ratio <= 0:
            raise ValueError('Ratio of H2/CO cannot be negative! Check _gasifier_prod_spec method')

        CH4 = (- 0.00001681 * ash
               + 0.001043993 * C_mole
               + 0.000369682 * H_mole
               - 0.000209205 * N_mole
               - 0.000907571 * O_mole
               + 7.58E-06 * (C_mole / O_mole)
               - 7.95E-06 * (O_mole / H_mole)
               + 1.31E-05 * (O_mole / (C_mole + H_mole / 4))
               + 7.46E-06 * (C_mole / H_mole)
               + 2.11E-05 * moist)

        CH4 = 0 if CH4 <= 0 else CH4
        return ratio, CH4

    def _gasifier_products(C_mole, H_mole, O_mole, N_mol, CH4_mole, ratio, moist_mole):
        """
        Calculates the syngas
        """
        CO_mole = (4 * C_mole - 8 * CH4_mole - 2 * O_mole + H_mole) / (2 + 2 * ratio)
        if CO_mole > C_mole:
            raise Exception("More CO is produced than the incoming C!")

        CO2_mole = C_mole - CO_mole - CH4_mole
        if CO2_mole < 0:
            raise Exception("Error in C balance: The CO and CH4 are more than incoming C!")

        H2_mole = CO_mole * ratio
        if H2_mole * 2 + CH4_mole * 4 > H_mole:
            raise Exception("Error in H balance")

        N2_mole = N_mol / 2

        H2O_mole = (H_mole - 4 * CH4_mole - 2 * H2_mole + 2 * moist_mole) / 2
        if H2O_mole < 0:
            raise Exception("Error in water balance or H balance!")
        return CO_mole, CO2_mole, H2_mole, N2_mole, H2O_mole

    def _stack_vol_flow(self):
        """
        Calculate the exhaust flow @ 7% oxygen
        """
        alpha = (0.535 * self.gasifier_products.loc['CO', 'value']
                 + 0.07 * self.gasifier_products.loc['CO2', 'value']
                 + 0.465 * self.gasifier_products.loc['H2', 'value']
                 - 0.1625 * self._dry_rdf.loc['Cl_mole_react', 'value']
                 + 0.035 * self._dry_rdf.loc['N_mole_react', 'value']
                 + 0.07 * self.gasifier_products.loc['N2', 'value']
                 + self._dry_rdf.loc['S_mole_react', 'value']) / 0.6654

        O2_exhaust = (-self.gasifier_products.loc['CO', 'value'] / 2
                      + alpha
                      + self._dry_rdf.loc['Cl_mole_react', 'value'] / 4
                      - self.gasifier_products.loc['H2', 'value'] / 2
                      - self._dry_rdf.loc['S_mole_react', 'value'])
        HCl_exhaust = self._dry_rdf.loc['Cl_mole_react', 'value']
        N2_exhaust = (self._dry_rdf.loc['N_mole_react', 'value'] / 2
                      + self.gasifier_products.loc['N2', 'value']
                      + 3.78 * alpha)
        SO2_exhaust = self._dry_rdf.loc['S_mole_react', 'value']
        CO2_exhaust = (self.gasifier_products.loc['CO', 'value']
                       + self.gasifier_products.loc['CO2', 'value'])
        vol_flow = ((O2_exhaust + HCl_exhaust
                     + N2_exhaust + SO2_exhaust
                     + CO2_exhaust)
                    * self.CommonData.STP['mole_to_L']['amount']
                    / 1000 * 10**6)
        return vol_flow

    def _biosphere_flows(self):
        """
        Calculate the flows to environment (emissions)
        """
        bio_flows = dict()

        # CO2 emissions from combustion and gasification
        bio_flows['CO2'] = (
            (self.gasifier_products.loc['CO2', 'value']
             + self.gasifier_products.loc['CO', 'value']
             + self.gasifier_products.loc['CH4', 'value'])
            * self.CommonData.MW['CO2']['amount'] * 1000)
        bio_flows['CO2_fossil'] = bio_flows['CO2'] * (1 - self._dry_rdf.loc['frac_biogenic_C', 'value'])
        bio_flows['CO2_biogenic'] = bio_flows['CO2'] * self._dry_rdf.loc['frac_biogenic_C', 'value']

        # Carbon storage: unreacted carbon
        bio_flows['CO2_storage_biogenic'] = (
            (self._dry_rdf.loc['C_mole', 'value']
             - self._dry_rdf.loc['C_mole_react', 'value'])
            * self.CommonData.MW['CO2']['amount'] * 1000
            * (-1)
            * self._dry_rdf.loc['frac_biogenic_C', 'value'])

        # Stack emissions based on average concentration
        vol_flow = self._stack_vol_flow()
        for i in ['PM', 'HCl', 'NOx', 'SOx']:
            bio_flows[i] = (vol_flow
                            * self.InputData.Stack[i]['amount']
                            / 10**6)

        bio_flows['Dioxins_Furans'] = (
            vol_flow
            * self.InputData.Stack['Dioxins_Furans']['amount']
            / 10**12)

        # Metal emissions from stack based on fraction incoming metals
        for element in ['Arsenic', 'Barium', 'Cadmium', 'Chromium', 'Copper',
                        'Mercury', 'Nickel', 'Lead', 'Antimony', 'Selenium',
                        'Zinc', 'Silver']:
            bio_flows[element] = sum(self._input_rdf['solid']
                                     * self.Material_Properties[element]
                                     / 100) * 1000 * self.InputData.Stack[element]['amount']
        return bio_flows

    def _calc_cost(self):
        self.cost = {}
        self.cost[('biosphere3', 'Capital_Cost')] = -npf.pmt(rate=self.InputData.Economic_params[' Interest_rate']['amount'],
                                                             nper=self.InputData.Economic_params['lifetime']['amount'],
                                                             pv=self.InputData.Economic_params['capital_cost']['amount'])
        self.cost[('biosphere3', 'Operational_Cost')] = self.InputData.Economic_params['O&M_cost']['amount']

    def setup_MC(self, seed=None):
        self.InputData.setup_MC(seed)

    def MC_calc(self):
        input_list = self.InputData.gen_MC()
        self.calc()
        return input_list

    def report(self):
        ### Output
        self.GC = {}
        Waste = {}
        Technosphere = {}
        Biosphere = {}
        self.GC["process name"] = (self.process_name, self.Process_Type, self.__class__)
        self.GC["Waste"] = Waste
        self.GC["Technosphere"] = Technosphere
        self.GC["Biosphere"] = Biosphere

        bio_dict = {
            'CO2_fossil': ('biosphere3', '349b29d1-3e58-4c66-98b9-9d1a076efd2e'),  # 'Carbon dioxide, fossil' ('air')
            'CO2_biogenic': ('biosphere3', 'eba59fd6-f37e-41dc-9ca3-c7ea22d602c7'),  #  'Carbon dioxide, non-fossil' ('air')
            'CO2_storage_biogenic': ('biosphere3', 'e4e9febc-07c1-403d-8d3a-6707bb4d96e6'),  # 'Carbon dioxide, from soil or biomass stock' ('air')
            'PM': ('biosphere3', '21e46cb8-6233-4c99-bac3-c41d2ab99498'),  # 'Particulates, < 2.5 um' ('air')
            'HCl': ('biosphere3', 'c941d6d0-a56c-4e6c-95de-ac685635218d'),  # 'Hydrogen chloride' ('air')
            'NOx': ('biosphere3', 'c1b91234-6f24-417b-8309-46111d09c457'),  # 'Nitrogen oxides' ('air')
            'SOx': ('biosphere3', 'ba5fc0b6-770b-4da1-9b3f-e3b5087f07cd'),  # 'Sulfur oxides' ('air')
            'Dioxins_Furans': ('biosphere3', '082903e4-45d8-4078-94cb-736b15279277'),  # 'Dioxins, measured as 2,3,7,8-tetrachlorodibenzo-p-dioxin' ('air')
            'Arsenic': ('biosphere3', 'dc6dbdaa-9f13-43a8-8af5-6603688c6ad0'),  # 'Arsenic' ('air')
            'Barium': ('biosphere3', '7e246e3a-5cff-43fc-a8e6-02d191424559'),  # 'Barium' ('air')
            'Cadmium': ('biosphere3', '1c5a7322-9261-4d59-a692-adde6c12de92'),  # 'Cadmium' ('air')
            'Chromium': ('biosphere3', 'e142b577-e934-4085-9a07-3983d4d92afb'),  # 'Chromium' ('air')
            'Copper': ('biosphere3', 'ec8144d6-d123-43b1-9c17-a295422a0498'),  # 'Copper' ('air')
            'Mercury': ('biosphere3', '71234253-b3a7-4dfe-b166-a484ad15bee7'),  # 'Mercury' ('air')
            'Nickel': ('biosphere3', 'a5506f4b-113f-4713-95c3-c819dde6e48b'),  # 'Nickel' ('air')
            'Lead': ('biosphere3', '8e123669-94d3-41d8-9480-a79211fe7c43'),  # 'Lead' ('air')
            'Antimony': ('biosphere3', '77927dac-dea3-429d-a434-d5a71d92c4f7'),  # 'Antimony' ('air')
            'Selenium': ('biosphere3', '454c61fd-c52b-4a04-9731-f141bb7b5264'),  # 'Selenium' ('air')
            'Zinc': ('biosphere3', '5ce378a0-b48d-471c-977d-79681521efde'),  # 'Zinc' ('air')
            'Silver': ('biosphere3', '7da45a0b-0dcf-413c-8de0-44d8ebca9e6e'),  # 'Silver' ('soil')
        }
        Biosphere['RDF'] = {}
        for k, v in self.bio_flows.items():
            if k in bio_dict:
                Biosphere['RDF'][bio_dict[k]] = v

        for k, v in self.cost.items():
            Biosphere['RDF'][k] = v

        Technosphere['RDF'] = {}
        Technosphere['RDF'][('Technosphere', 'Electricity_production')] = self.energy.loc['Net Elec prod', 'value']


        Waste['RDF'] = {}
        Waste['RDF']['Bottom_Ash'] = self.gasifier_products.loc['Bottom Ash', 'value']

        return self.GC
