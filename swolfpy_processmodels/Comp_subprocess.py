# -*- coding: utf-8 -*-
"""
Created on Fri Nov 22 15:06:06 2019

@author: msardar2
"""
from copy import deepcopy


### Screan
def screen(input_flow, sep_eff, Op_param, lci, flow_init):
    product = deepcopy(flow_init)
    residual = deepcopy(flow_init)

    residual.data['mass'] = input_flow.data['mass'].values * sep_eff
    residual.data['sol_cont'] = input_flow.data['sol_cont'].values * sep_eff
    residual.data['moist_cont'] = input_flow.data['moist_cont'].values * sep_eff
    residual.data['vs_cont'] = input_flow.data['vs_cont'].values * sep_eff
    residual.data['ash_cont'] = input_flow.data['ash_cont'].values * sep_eff

    product.data['mass'] = input_flow.data['mass'].values - residual.data['mass'].values
    product.data['sol_cont'] = input_flow.data['sol_cont'].values - residual.data['sol_cont'].values
    product.data['moist_cont'] = input_flow.data['moist_cont'].values - residual.data['moist_cont'].values
    product.data['vs_cont'] = input_flow.data['vs_cont'].values - residual.data['vs_cont'].values
    product.data['ash_cont'] = input_flow.data['ash_cont'].values - residual.data['ash_cont'].values

    # Resource use
    lci.add(name=('Technosphere', 'Electricity_consumption'),
            flow=Op_param['Mtr']['amount'] * input_flow.data['mass'].values/1000)

    return product, residual

### Shredding
def shredding(input_flow, Op_param, lci, flow_init):
    product = deepcopy(flow_init)
    product.data = deepcopy(input_flow.data)

    # Resource use
    Shred_diesel = input_flow.data['mass'].values / 1000 * Op_param['Mtgp']['amount'] * Op_param['Mtgf']['amount']
    lci.add(name=('Technosphere', 'Equipment_Diesel'),
            flow=Shred_diesel)

    return product

### Mixing two flows
def mix(input1, input2, flow_init):
    product = deepcopy(flow_init)
    product.data['mass'] = input1.data['mass'].values + input2.data['mass'].values
    product.data['sol_cont'] = input1.data['sol_cont'].values + input2.data['sol_cont'].values
    product.data['moist_cont'] = input1.data['moist_cont'].values + input2.data['moist_cont'].values
    product.data['vs_cont'] = input1.data['vs_cont'].values + input2.data['vs_cont'].values
    product.data['ash_cont'] = input1.data['ash_cont'].values + input2.data['ash_cont'].values
    return product

### Add Water
def add_water(input_flow, water_flow, material_properties, process_data, flow_init):
    product = deepcopy(flow_init)
    product.data['mass'] = input_flow.data['mass'].values + water_flow
    product.data['sol_cont'] = input_flow.data['sol_cont'].values
    product.data['moist_cont'] = input_flow.data['moist_cont'].values + water_flow
    product.data['vs_cont'] = input_flow.data['vs_cont'].values
    product.data['ash_cont'] = input_flow.data['ash_cont'].values

    # Nitrogen and carbon in the input stream
    product.data['C_input'] = (product.data['sol_cont'].values
                               * material_properties['Biogenic Carbon Content'].values / 100
                               * process_data['Degrades'].values)

    product.data['N_input'] = (product.data['sol_cont'].values
                               * material_properties['Nitrogen Content'].values / 100
                               * process_data['Degrades'].values)
    return product

### Active Composting
def ac_comp(input_flow, common_data, process_data, input_data, assumed_comp, lci, flow_init):
    # Degradation
    C_loss = input_flow.data['C_input'].values * process_data['C_loss'].values/100 * input_data.Deg_Param['acDegProp']['amount']/100
    N_loss = input_flow.data['N_input'].values * process_data['N_loss'].values/100 * input_data.Deg_Param['acDegProp']['amount']/100
    VS_loss = C_loss * process_data[' VS_loss to C_loss'].values
    VOCs_loss = VS_loss * process_data['VOC to VS_loss'].values / 1000000

    #Product
    product = deepcopy(flow_init)
    product.data['vs_cont'] = input_flow.data['vs_cont'].values - VS_loss
    product.data['ash_cont'] = input_flow.data['ash_cont'].values
    product.data['sol_cont'] = product.data['vs_cont'].values + product.data['ash_cont'].values
    product.data['C_cont']= input_flow.data['C_input'].values - C_loss
    product.data['N_cont']= input_flow.data['N_input'].values - N_loss

    #Off Gas
    C_loss_as_CH4 = C_loss * input_data.Deg_Param['pCasCH4']['amount']
    C_loss_as_CO2 = C_loss - C_loss_as_CH4
    lci.add(name='Carbon dioxide, non-fossil',
            flow=C_loss_as_CO2 * common_data.MW['CO2']['amount']/common_data.MW['C']['amount'])

    N_loss_as_NH3 = N_loss * input_data.Deg_Param['pNasNH3']['amount']
    N_loss_as_N2O = N_loss * input_data.Deg_Param['pNasN2O']['amount']

    #Biofilter
    Biofilter_CH4 = C_loss_as_CH4 * (1-input_data.Deg_Param['bfCH4re']['amount'])
    Biofilter_CO2 = C_loss_as_CH4-Biofilter_CH4
    lci.add(name='Methane, non-fossil',
            flow=Biofilter_CH4 * common_data.MW['CH4']['amount']/common_data.MW['C']['amount'])
    lci.add(name='Carbon dioxide, non-fossil',
            flow=Biofilter_CO2 * common_data.MW['CO2']['amount']/common_data.MW['C']['amount'])

    Biofilter_NH3= N_loss_as_NH3 * (1-input_data.Deg_Param['bfNH3re']['amount']/100)
    Biofilter_N2O= N_loss_as_N2O * (1-input_data.Deg_Param['bfN2Ore']['amount']/100)
    Biofilter_NH3_to_N2O= (N_loss_as_NH3-Biofilter_NH3) * input_data.Deg_Param['preNH3toN2O']['amount']
    Biofilter_NH3_to_NOx= (N_loss_as_NH3-Biofilter_NH3) * input_data.Deg_Param['preNH3toNOx']['amount']
    Biofilter_VOCs = VOCs_loss  * (1-input_data.Deg_Param['bfVOCre']['amount']/100)

    lci.add(name='Ammonia',
            flow=Biofilter_NH3 * common_data.MW['Ammonia']['amount']/common_data.MW['N']['amount'])
    lci.add(name='Dinitrogen monoxide',
            flow=(Biofilter_N2O+Biofilter_NH3_to_N2O) * common_data.MW['Nitrous_Oxide']['amount']/common_data.MW['N']['amount']/2)
    lci.add(name='Nitrogen oxides',
            flow=Biofilter_NH3_to_NOx * common_data.MW['NOx']['amount']/common_data.MW['N']['amount'])
    lci.add(name='VOCs emitted', flow=Biofilter_VOCs)

    # Caculating the moisture
    input_flow.update(assumed_comp)
    product.data['moist_cont'] = (product.data['sol_cont'].values
                                  / (1-input_data.Deg_Param['MCac']['amount'])
                                  * input_data.Deg_Param['MCac']['amount'])
    product.data['mass']= product.data['sol_cont'].values + product.data['moist_cont'].values

    # Resource use
    Loader_diesel = input_data.Op_Param['Tdoh']['amount']*input_data.Loader['hpfel']['amount']*input_data.Loader['Mffel']['amount']
    Windrow_turner_diesel = input_data.Op_Param['Tact']['amount']*input_data.AC_Turning['Fta']['amount']* input_flow.data['mass']/1000 * \
                                input_data.AC_Turning['Mwta']['amount'] * input_data.AC_Turning['Mwfa']['amount']
    lci.add(name=('Technosphere', 'Equipment_Diesel'),
            flow=Windrow_turner_diesel + Loader_diesel)

    return product

### Post Screen
def post_screen(input_flow, sep_eff, Op_param, lci, flow_init):
    product = deepcopy(flow_init)
    residual = deepcopy(flow_init)

    residual.data['mass'] = input_flow.data['mass'].values * sep_eff
    residual.data['sol_cont'] = input_flow.data['sol_cont'].values * sep_eff
    residual.data['moist_cont'] = input_flow.data['moist_cont'].values * sep_eff
    residual.data['vs_cont'] = input_flow.data['vs_cont'].values * sep_eff
    residual.data['ash_cont'] = input_flow.data['ash_cont'].values * sep_eff
    residual.data['C_cont'] = input_flow.data['C_cont'].values * sep_eff
    residual.data['N_cont'] = input_flow.data['N_cont'].values * sep_eff

    product.data['mass'] = input_flow.data['mass'].values - residual.data['mass'].values
    product.data['sol_cont'] = input_flow.data['sol_cont'].values - residual.data['sol_cont'].values
    product.data['moist_cont'] = input_flow.data['moist_cont'].values - residual.data['moist_cont'].values
    product.data['vs_cont'] = input_flow.data['vs_cont'].values - residual.data['vs_cont'].values
    product.data['ash_cont'] = input_flow.data['ash_cont'].values - residual.data['ash_cont'].values
    product.data['C_cont'] = input_flow.data['C_cont'].values - residual.data['C_cont'].values
    product.data['N_cont'] = input_flow.data['N_cont'].values- residual.data['N_cont'].values

    # Resource use
    lci.add(name=('Technosphere', 'Electricity_consumption'),
            flow=Op_param['Mtr']['amount'] * input_flow.data['mass'].values/1000)

    return product, residual


### Vaccuum
def vacuum(input_flow, sep_eff, Op_param, lci, flow_init):
    product = deepcopy(flow_init)
    vacuumed = deepcopy(flow_init)

    vacuumed.data['mass'] = input_flow.data['mass'].values * sep_eff
    vacuumed.data['sol_cont'] = input_flow.data['sol_cont'].values * sep_eff
    vacuumed.data['moist_cont'] = input_flow.data['moist_cont'].values * sep_eff
    vacuumed.data['vs_cont'] = input_flow.data['vs_cont'].values * sep_eff
    vacuumed.data['ash_cont'] = input_flow.data['ash_cont'].values * sep_eff
    vacuumed.data['C_cont'] = input_flow.data['C_cont'].values * sep_eff
    vacuumed.data['N_cont'] = input_flow.data['N_cont'].values * sep_eff

    product.data['mass'] = input_flow.data['mass'].values - vacuumed.data['mass'].values
    product.data['sol_cont'] = input_flow.data['sol_cont'].values - vacuumed.data['sol_cont'].values
    product.data['moist_cont'] = input_flow.data['moist_cont'].values - vacuumed.data['moist_cont'].values
    product.data['vs_cont'] = input_flow.data['vs_cont'].values - vacuumed.data['vs_cont'].values
    product.data['ash_cont'] = input_flow.data['ash_cont'].values - vacuumed.data['ash_cont'].values
    product.data['C_cont'] = input_flow.data['C_cont'].values- vacuumed.data['C_cont'].values
    product.data['N_cont'] = input_flow.data['N_cont'].values - vacuumed.data['N_cont'].values

    # Resource use
    lci.add(name=('Technosphere', 'Electricity_consumption'),
            flow=Op_param['vacElecFac']['amount'] * input_flow.data['mass'].values/1000)
    lci.add(name=('Technosphere', 'Equipment_Diesel'),
            flow=Op_param['vacDiesFac']['amount'] * input_flow.data['mass'].values/1000)

    return product, vacuumed

### Curing
def curing(input_flow, common_data, process_data, input_data, assumed_comp, lci, flow_init):
    #Degradation
    C_loss = input_flow.data['C_cont'].values * process_data['C_loss'].values/100 * (100-input_data.Deg_Param['acDegProp']['amount'])/100
    N_loss = input_flow.data['N_cont'].values * process_data['N_loss'].values/100 * (100-input_data.Deg_Param['acDegProp']['amount'])/100
    VS_loss = C_loss * process_data[' VS_loss to C_loss'].values
    VOCs_loss = VS_loss * process_data['VOC to VS_loss'].values / 1000000

    #Product
    product = deepcopy(flow_init)
    product.data['vs_cont'] = input_flow.data['vs_cont'].values - VS_loss
    product.data['ash_cont'] = input_flow.data['ash_cont'].values
    product.data['sol_cont'] = product.data['vs_cont'].values + product.data['ash_cont'].values
    product.data['C_cont'] = input_flow.data['C_cont'].values - C_loss
    product.data['N_cont'] = input_flow.data['N_cont'].values - N_loss

    #Off Gas
    C_loss_as_CH4 = C_loss * input_data.Deg_Param['pCasCH4']['amount']
    C_loss_as_CO2 = C_loss - C_loss_as_CH4
    lci.add(name='Carbon dioxide, non-fossil',
            flow=C_loss_as_CO2 * common_data.MW['CO2']['amount']/common_data.MW['C']['amount'])

    N_loss_as_NH3 = N_loss * input_data.Deg_Param['pNasNH3']['amount']
    N_loss_as_N2O = N_loss * input_data.Deg_Param['pNasN2O']['amount']

    #Biofilter
    Biofilter_CH4 = C_loss_as_CH4 * (1-input_data.Deg_Param['bfCH4re']['amount'])
    Biofilter_CO2 = C_loss_as_CH4-Biofilter_CH4
    lci.add(name='Methane, non-fossil',
            flow=Biofilter_CH4 * common_data.MW['CH4']['amount']/common_data.MW['C']['amount'])
    lci.add(name='Carbon dioxide, non-fossil',
            flow=Biofilter_CO2 * common_data.MW['CO2']['amount']/common_data.MW['C']['amount'])

    Biofilter_NH3 = N_loss_as_NH3 * (1-input_data.Deg_Param['bfNH3re']['amount']/100)
    Biofilter_N2O = N_loss_as_N2O * (1-input_data.Deg_Param['bfN2Ore']['amount']/100)
    Biofilter_NH3_to_N2O = (N_loss_as_NH3-Biofilter_NH3) * input_data.Deg_Param['preNH3toN2O']['amount']
    Biofilter_NH3_to_NOx = (N_loss_as_NH3-Biofilter_NH3) * input_data.Deg_Param['preNH3toNOx']['amount']
    Biofilter_VOCs = VOCs_loss  * (1-input_data.Deg_Param['bfVOCre']['amount']/100)

    lci.add(name='Ammonia',
            flow=Biofilter_NH3 * common_data.MW['Ammonia']['amount']/common_data.MW['N']['amount'])
    lci.add(name='Dinitrogen monoxide',
            flow=(Biofilter_N2O+Biofilter_NH3_to_N2O) * common_data.MW['Nitrous_Oxide']['amount']/common_data.MW['N']['amount']/2)
    lci.add(name='Nitrogen oxides',
            flow=Biofilter_NH3_to_NOx * common_data.MW['NOx']['amount']/common_data.MW['N']['amount'])
    lci.add(name='VOCs emitted',
            flow=Biofilter_VOCs)

    # Caculating the moisture
    input_flow.update(assumed_comp)
    product.data['moist_cont'] = (product.data['sol_cont'].values
                                  / (1-input_data.Deg_Param['MCcu']['amount'])
                                  * input_data.Deg_Param['MCcu']['amount'])
    product.data['mass']= product.data['sol_cont'].values + product.data['moist_cont'].values

    # Resource use
    Curing_diesel = input_data.Op_Param['Tcur']['amount']*input_data.Curing['Ftc']['amount']*input_data.AC_Turning['Mwta']['amount']*\
                    input_data.AC_Turning['Mwfa']['amount']*input_flow.data['mass'].values/1000
    lci.add(name=('Technosphere', 'Equipment_Diesel'),
            flow=Curing_diesel)

    return product
