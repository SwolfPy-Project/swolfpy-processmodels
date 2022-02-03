# -*- coding: utf-8 -*-
"""
Created on Thu Jun 10 13:24:59 2021

@author: msardar
"""
import numpy as np
import pandas as pd
from copy import deepcopy


class LCI():
    """
    This class store the LCI data in ``numpy.ndarray`` instead of ``pandas.DataFrame`` for speedup.
    Column names (flows names) are stored in ``self.col_dict``.

    Parameters
    ----------
    index : list
        List of waste fractions that are used as row index.
    n_col : int, optional
        The number of columns in the LCI ``ndarray``. The default is 30.

    """

    def __init__(self, index, n_col=30):
        self.index = index
        self.lci = np.zeros((len(index), n_col))
        self.col_dict={}
        self.col_index=0

    def add(self, name, flow):
        """
        Add new flow to the LCI.

        Parameters
        ----------
        name : str
            Name of the flow in the LCI.
        flow : ``numpy.array``.

        """
        if isinstance(flow, np.ndarray):
            if any(np.isnan(flow)):
                raise ValueError(f'The Value for the {name} is nan!')
        if name not in self.col_dict:
            self.col_dict[name] = self.col_index
            self.col_index += 1
        self.lci[:, self.col_dict[name]] += flow

    def report(self, input_mass=None, transpose=False):
        """
        Creates ``DataFrame`` from the LCI ``ndarray`` and return it.

        Parameters
        ----------
        input_mass : ``numpy.array``, optional
            Initial mass flows to calculate LCI accordingly. The default is None.
        transpose : boolean, optional

        """
        LCI = deepcopy(self.lci)
        if input_mass is not None:
            non_zero_fltr = input_mass > 0
            zero_fltr = input_mass == 0
            for j in range(self.col_index):
                LCI[non_zero_fltr, j] /= input_mass[non_zero_fltr]
                LCI[zero_fltr, j] = 0.0
        if transpose:
            report = pd.DataFrame(LCI[:, :self.col_index].transpose(),
                                  columns=self.index,
                                  index=list(self.col_dict.keys()))
        else:
            report = pd.DataFrame(LCI[:, :self.col_index],
                      columns=list(self.col_dict.keys()),
                      index=self.index)
        return report


class Flow():
    """
    Creates a ``pandas.DataFrame`` for the flow.

    Parameters
    ----------
    material_properties : ``pandas.DataFrame``
        Materail properties of the waste fractions.

    """

    def __init__(self, material_properties):
        self.prop = material_properties
        self.data = pd.DataFrame(index=self.prop.index,
                                 columns=['mass', 'sol_cont', 'moist_cont', 'vs_cont', 'ash_cont'])

    # Create new flow
    def init_flow(self, mass_flows):
        """
        Fill the flow ``DataFrame`` based on the mass_flows.

        Parameters
        ----------
        mass_flows : ``numpy.array`` or ``pandas.Series``.

        """
        self.data['mass'] = mass_flows
        self.data['sol_cont'] = self.data['mass'].values * (1 - self.prop['Moisture Content'].values / 100)
        self.data['moist_cont'] = self.data['mass'].values * (self.prop['Moisture Content'].values / 100)
        self.data['vs_cont'] = self.data['sol_cont'].values * self.prop['Volatile Solids'].values / 100
        self.data['ash_cont'] = self.data['sol_cont'].values * self.prop['Ash Content'].values / 100

    # Update flow
    def update(self, assumed_comp):
        """
        Calculates the flows properties based on the assumed composition.

        Parameters
        ----------
        assumed_comp : ``pd.Series``
            Assumed waste composition for the flow.

        """
        self.flow = sum(self.data['mass'].values * assumed_comp.values)
        self.water = sum(self.data['moist_cont'].values * assumed_comp.values)
        self.moist_cont = self.water / self.flow
        self.ash = sum(self.data['ash_cont'].values * assumed_comp.values)
        self.solid = sum(self.data['sol_cont'].values * assumed_comp.values)


def compost_use(input_flow, common_data, process_data, material_properties,
                input_data, lci, include_diesel=True):
    """
    Calculates the emissions and offsets from final compost use (i.e., land application, ADC)

    """
    # Compost to land application
    if input_data.Compost_use['choice_BU']['amount'] == 1:
        # Carbon in final compost
        C_storage = input_flow.data['C_cont'].values * common_data.Land_app['perCStor']['amount'] / 100
        C_released = input_flow.data['C_cont'].values - C_storage
        C_storage_hummus_formation = input_flow.data['C_cont'].values * common_data.Land_app['humFormFac']['amount']

        lci.add(name='Carbon dioxide, non-fossil',
                flow=C_released * common_data.MW['CO2']['amount'] / common_data.MW['C']['amount'])
        lci.add(name='Direct Carbon Storage and Humus Formation',
                flow=-(C_storage + C_storage_hummus_formation) * common_data.MW['CO2']['amount'] / common_data.MW['C']['amount'])

        #Nitrogen in final compost
        input_flow.data['N_cont'] = input_flow.data['N_cont'].values
        input_flow.data['P_cont'] = input_flow.data['P_cont'].values
        input_flow.data['K_cont'] = input_flow.data['K_cont'].values

        N2O = input_flow.data['N_cont'].values * common_data.Land_app['perN2Oevap']['amount'] / 100
        NH3 = input_flow.data['N_cont'].values * common_data.Land_app['perNasNH3fc']['amount'] / 100 * common_data.Land_app['perNH3evap']['amount'] / 100
        NO3_GW = input_flow.data['N_cont'].values * common_data.Land_app['NO3leach']['amount']
        NO3_SW = input_flow.data['N_cont'].values * common_data.Land_app['NO3runoff']['amount']

        lci.add(name='Dinitrogen monoxide',
                flow=N2O * common_data.MW['Nitrous_Oxide']['amount'] / (common_data.MW['N']['amount'] * 2))
        lci.add(name='Ammonia',
                flow=NH3 * common_data.MW['Ammonia']['amount'] / common_data.MW['N']['amount'])
        lci.add(name='Nitrate (ground water)',
                flow=NO3_GW * common_data.MW['Nitrate']['amount'] / common_data.MW['N']['amount'])
        lci.add(name='Nitrate (surface water)',
                flow=NO3_SW * common_data.MW['Nitrate']['amount'] / common_data.MW['N']['amount'])

        if input_data.Compost_use['fertOff']['amount'] == 1:
            # Nutrients availble in the final compost
            Navail = input_flow.data['N_cont'].values * common_data.Land_app['MFEN']['amount']
            Pavail = input_flow.data['P_cont'].values * common_data.Land_app['MFEP']['amount']
            Kavail = input_flow.data['K_cont'].values * common_data.Land_app['MFEK']['amount']

            if include_diesel:
                # Diesel use for applying the compost
                Diesel_use = input_flow.data['mass'].values / 1000 * common_data.Land_app['cmpLandDies']['amount']
                Diesel_offset = -(Navail * common_data.Land_app['DslAppN']['amount']
                                  + Pavail * common_data.Land_app['DslAppP']['amount']
                                  + Kavail * common_data.Land_app['DslAppK']['amount'])
                Net_diesel = Diesel_use + Diesel_offset
                lci.add(name=('Technosphere', 'Equipment_Diesel'),
                        flow=Net_diesel)

            # Offset from fertilizer
            lci.add(name=('Technosphere', 'Nitrogen_Fertilizer'),
                    flow=-Navail)
            lci.add(name=('Technosphere', 'Phosphorous_Fertilizer'),
                    flow=-Pavail)
            lci.add(name=('Technosphere', 'Potassium_Fertilizer'),
                    flow=-Kavail)

            # offset from applying fertilizer
            Fert_N2O = -Navail * common_data.Land_app['fert_N2O']['amount'] / 100
            Fert_NH3 = -Navail * common_data.Land_app['fert_NH3']['amount'] / 100 * common_data.Land_app['fert_NH3Evap']['amount'] / 100
            Fert_NO3_GW = -Navail * common_data.Land_app['fert_NO3Leach']['amount'] /100
            Fert_NO3_SW = -Navail * common_data.Land_app['fert_NO3Run']['amount'] / 100

            lci.add(name='Dinitrogen monoxide',
                    flow=Fert_N2O * common_data.MW['Nitrous_Oxide']['amount']/common_data.MW['N']['amount']/2)
            lci.add(name='Ammonia',
                    flow=Fert_NH3 * common_data.MW['Ammonia']['amount']/common_data.MW['N']['amount'])
            lci.add(name='Nitrate (ground water)',
                    flow=Fert_NO3_GW * common_data.MW['Nitrate']['amount']/common_data.MW['N']['amount'])
            lci.add(name='Nitrate (surface water)',
                    flow=Fert_NO3_SW * common_data.MW['Nitrate']['amount']/common_data.MW['N']['amount'])

        # Peat offsets
        if input_data.Compost_use['peatOff']['amount'] == 1:
            compost_vol = input_flow.data['mass'].values / input_data.Material_Properties['densFC']['amount']
            peat_vol = compost_vol * common_data.Land_app['PeatSubFac']['amount']
            peat_mass = peat_vol * common_data.Land_app['densPeat']['amount'] / 1000  # Mg

            # Avoided emissions from peat saving
            peat_C = (peat_mass
                      * (1 - common_data.Land_app['PeatMoist']['amount'])
                      * common_data.Land_app['PeatC']['amount'])
            peat_C_release = peat_C * (1 - common_data.Land_app['perCStorPeat']['amount'] / 100)

            lci.add(name=('Technosphere', 'Peat'),
                    flow=-peat_mass)
            lci.add(name='Carbon dioxide, fossil',
                    flow=-peat_C_release * common_data.MW['CO2']['amount'] / common_data.MW['C']['amount'])

    # Compost as AD
    if input_data.Compost_use['choice_BU']['amount'] == 0:
        # Carbon in final compost
        Max_C_storage = (1 - material_properties['Moisture Content'].values / 100) * material_properties['Carbon Storage Factor'].values
        C_storage = np.where(input_flow.data['C_cont'].values * (common_data.ADC['perCStor_LF']['amount'] / 100) <= Max_C_storage,
                             input_flow.data['C_cont'].values * (common_data.ADC['perCStor_LF']['amount'] / 100),
                             Max_C_storage)

        C_released = (input_flow.data['C_cont'].values - C_storage) * (1 - common_data.ADC['frac_CH4']['amount'] / 100)
        C_CH4 = (input_flow.data['C_cont'].values - C_storage) * (common_data.ADC['frac_CH4']['amount'] / 100)
        C_CH4_Oxidized = C_CH4 * process_data['Methane Oxidized'].values / 100
        C_CH4_Flared = C_CH4 * process_data['Methane Flared'].values / 100
        C_CH4_Emitted = C_CH4 * process_data['Methane Emitted'].values / 100
        C_CH4_EnergyRec = C_CH4 * process_data['Methane to Energy'].values / 100
        C_CH4_EnergyRec_mass = C_CH4_EnergyRec * (common_data.MW['CH4']['amount'] / common_data.MW['C']['amount'])
        CH4_LHV = common_data.LHV['CH4']['amount'] / common_data.STP['m3CH4_to_kg']['amount']  # MJ/kgCH4
        C_CH4_Electricity = C_CH4_EnergyRec_mass * CH4_LHV * (common_data.ADC['Elec_eff']['amount'] / 100) / 3.6  #kWhElec

        lci.add(name='Direct Carbon Storage and Humus Formation',
                flow=-(C_storage * common_data.MW['CO2']['amount'] / common_data.MW['C']['amount']))
        lci.add(name='Carbon dioxide, non-fossil',
                flow=(C_released + C_CH4_EnergyRec + C_CH4_Flared + C_CH4_Oxidized) * common_data.MW['CO2']['amount'] / common_data.MW['C']['amount'])
        lci.add(name='Methane, non-fossil',
                flow=C_CH4_Emitted * common_data.MW['CH4']['amount'] / common_data.MW['C']['amount'])
        lci.add(name=('Technosphere', 'Electricity_production'),
                flow=C_CH4_Electricity)

        #General emissions from LF
        lci.add(name=('Technosphere', 'compost_to_LF'),
                flow=(input_flow.data['mass'].values / 1000) * common_data.ADC['Aloc_ADC']['amount'])

        #Amomonium emission from LF (Calculated base on the ammomium/N_cont ratio in LF)
        NH4_LF = common_data.ADC['Frac_NH4']['amount'] * input_flow.data['N_cont']
        NH4_GW=  NH4_LF * (1 - common_data.ADC['LCRS_eff']['amount'])
        NH4_SW=  NH4_LF * common_data.ADC['LCRS_eff']['amount'] * (1 - common_data.ADC['NH4_rmv_eff']['amount'])
        NO3_SW = NH4_LF * common_data.ADC['LCRS_eff']['amount'] * common_data.ADC['NH4_rmv_eff']['amount']

        lci.add(name='Ammonium, ion (ground water)',
                flow=NH4_GW * common_data.MW['Ammonium']['amount']/common_data.MW['N']['amount'])
        lci.add(name='Ammonium, ion (surface water)',
                flow=NH4_SW * common_data.MW['Ammonium']['amount']/common_data.MW['N']['amount'])
        lci.add(name='Nitrate (surface water)',
                flow=NO3_SW * common_data.MW['Nitrate']['amount']/common_data.MW['N']['amount'])

        #Avoided excavation
        compost_vol = input_flow.data['mass'].values / input_data.Material_Properties['densFC']['amount']
        dc_soil_vol = compost_vol * (common_data.ADC['DC_thick']['amount'] / common_data.ADC['ADC_thick']['amount'])\
            * common_data.ADC['DC_subs_fac']['amount']

        lci.add(name=('Technosphere', 'market_for_excavation_skid_steer_loader'),
                flow=dc_soil_vol)
