# -*- coding: utf-8 -*-
"""
Created on Mon Jun 14 15:07:13 2021

@author: m.sardar
"""
from .Common_subprocess import Flow


### Active Composting
def active_comp(input_flow, common_data, input_data ,process_data, material_properties, lci):
    # Calculate organic C and N content
    input_flow.data['C_cont'] = (input_flow.data['sol_cont'].values
                                  * material_properties['Biogenic Carbon Content'].values / 100
                                  * process_data['Degrades'].values)

    input_flow.data['N_cont'] = (input_flow.data['sol_cont'].values
                                  * material_properties['Nitrogen Content'].values / 100
                                  * process_data['Degrades'].values)

    input_flow.data['P_cont'] = (input_flow.data['sol_cont'].values
                                  * material_properties['Phosphorus Content'].values / 100
                                  * process_data['Degrades'].values)

    input_flow.data['K_cont'] = (input_flow.data['sol_cont'].values
                                  * material_properties['Potassium Content'].values / 100
                                  * process_data['Degrades'].values)

    # Degradation
    C_loss = (input_flow.data['C_cont'].values
              * process_data['C_loss'].values / 100
              * input_data.Degradation_param['acDegProp']['amount'] / 100)

    N_loss = (input_flow.data['N_cont'].values
              * process_data['N_loss'].values / 100
              * input_data.Degradation_param['acDegProp']['amount'] / 100)

    VS_loss = C_loss * process_data['VS_loss to C_loss'].values

    VOCs_loss = VS_loss * process_data['VOC to VS_loss'].values / 10**6

    # Product: Final compost
    product = Flow(material_properties)
    product.data['vs_cont'] = input_flow.data['vs_cont'].values - VS_loss
    product.data['ash_cont'] = input_flow.data['ash_cont'].values
    product.data['sol_cont'] = product.data['vs_cont'].values + product.data['ash_cont'].values
    # L = S / (1-Mc) * Mc
    product.data['moist_cont'] = (product.data['sol_cont'].values
                                  / (1 - input_data.Degradation_param['MCac']['amount'])
                                  * input_data.Degradation_param['MCac']['amount'])
    product.data['mass'] = product.data['sol_cont'].values + product.data['moist_cont'].values
    product.data['C_cont']= input_flow.data['C_cont'].values - C_loss
    product.data['N_cont']= input_flow.data['N_cont'].values - N_loss
    product.data['P_cont']= input_flow.data['P_cont'].values
    product.data['K_cont']= input_flow.data['K_cont'].values

    # C losses fate
    C_loss_as_CH4 = C_loss * input_data.Degradation_param['pCasCH4']['amount']
    C_loss_as_CO = C_loss * input_data.Degradation_param['pCasCO']['amount']
    C_loss_as_CO2 = C_loss - C_loss_as_CH4 - C_loss_as_CO

    lci.add(name='Carbon dioxide, non-fossil',
            flow=(C_loss_as_CO2
                  * common_data.MW['CO2']['amount'] / common_data.MW['C']['amount']))

    lci.add(name='Methane, non-fossil',
            flow=(C_loss_as_CH4
                  * common_data.MW['CH4']['amount'] / common_data.MW['C']['amount']))

    lci.add(name='Carbon monoxide, non-fossil',
            flow=(C_loss_as_CO
                  * common_data.MW['CO']['amount'] / common_data.MW['C']['amount']))

    # N losses fate
    N_loss_as_NH3 = N_loss * input_data.Degradation_param['pNasNH3']['amount']
    N_loss_as_N2O = N_loss * input_data.Degradation_param['pNasN2O']['amount']
    N_loss_as_N2 = N_loss - N_loss_as_NH3 - N_loss_as_N2O

    lci.add(name='Ammonia',
            flow=(N_loss_as_NH3
                  * common_data.MW['Ammonia']['amount'] / common_data.MW['N']['amount']))

    lci.add(name='Dinitrogen monoxide',
            flow=(N_loss_as_N2O
                  * common_data.MW['Nitrous_Oxide']['amount']
                  / (common_data.MW['N']['amount'] * 2)))

    lci.add(name='Nitrogen',
            flow=N_loss_as_N2)

    # VOCs
    lci.add(name='VOCs emitted', flow=VOCs_loss)

    return(product)