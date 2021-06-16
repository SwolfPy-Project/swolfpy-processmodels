# -*- coding: utf-8 -*-
"""
Created on Fri Nov 22 21:23:49 2019

@author: msardar2
"""
import numpy as np
from copy import deepcopy


### AD_Screan
def screen(input_flow, sep_eff, Material_Properties, LCI, flow_init):
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

    return (product, residual)


### AD_Add Water
def add_water(input_flow, water_flow, Material_Properties, process_data, flow_init):
    product = deepcopy(flow_init)
    product.data['mass'] = input_flow.data['mass'].values + water_flow
    product.data['sol_cont'] = input_flow.data['sol_cont'].values
    product.data['moist_cont'] = input_flow.data['moist_cont'].values + water_flow
    product.data['vs_cont'] = input_flow.data['vs_cont'].values
    product.data['ash_cont'] = input_flow.data['ash_cont'].values

    # Nitrogen and carbon in the input stream
    product.data['C_cont'] = (input_flow.data['sol_cont'].values
                              * (Material_Properties['Biogenic Carbon Content'].values / 100)
                              * process_data['Degrades'].values)

    product.data['N_cont'] = (input_flow.data['sol_cont'].values
                              * (Material_Properties['Nitrogen Content'].values / 100)
                              * process_data['Degrades'].values)

    product.data['P_cont'] = (input_flow.data['sol_cont'].values
                              * (Material_Properties['Phosphorus Content'].values / 100)
                              * process_data['Degrades'].values)

    product.data['K_cont'] = (input_flow.data['sol_cont'].values
                              * (Material_Properties['Potassium Content'].values / 100)
                              * process_data['Degrades'].values)
    return product


### AD Reactor
def Reactor(input_flow, CommonData, process_data, input_data, Material_Properties, lci, flow_init):
    # Short names
    Engine_param = input_data.Engine_param
    Flare_param = input_data.Flare_param
    Biogas_gen = input_data.Biogas_gen

    # Methane production
    CH4_prod_vol = (input_flow.data['sol_cont'].values / 1000
                    * Material_Properties['Methane Yield'].values
                    * process_data['Percent of L0 reached'].values / 100)

    CH4_prod_mass_asC = (CH4_prod_vol
                         * CommonData.STP['m3CH4_to_kg']['amount']
                         * CommonData.MW['C']['amount'] / CommonData.MW['CH4']['amount'])

    # Mehtane Balance
    CH4_fugitiv_mass_asC = (CH4_prod_mass_asC
                            * (1 - Biogas_gen['ad_collEff']['amount']))

    CH4_Energy_rec_asC = (CH4_prod_mass_asC
                          * Biogas_gen['ad_collEff']['amount']
                          * (1 - Biogas_gen['ad_downTime']['amount']))

    CH4_Flare_asC = (CH4_prod_mass_asC
                     * Biogas_gen['ad_collEff']['amount']
                     * Biogas_gen['ad_downTime']['amount'])

    CH4_unburn_AsC = (CH4_Energy_rec_asC
                      * (1 - Engine_param['CH4_destruction']['amount'])
                      + CH4_Flare_asC
                      * (1 - Flare_param['CH4_destruction']['amount']))

    CO2_from_CH4Comb = (CH4_Energy_rec_asC
                        * Engine_param['CH4_destruction']['amount']
                        + CH4_Flare_asC
                        * Flare_param['CH4_destruction']['amount'])

    # ENergy content
    CH4_Energy_EngCont = (CH4_prod_vol * Biogas_gen['ad_collEff']['amount']
                          * (1 - Biogas_gen['ad_downTime']['amount'])
                          * Biogas_gen['ad_ch4EngCont']['amount'])

    CH4_Flare_EngCont = (CH4_prod_vol * Biogas_gen['ad_collEff']['amount']
                         * Biogas_gen['ad_downTime']['amount']
                         * Biogas_gen['ad_ch4EngCont']['amount'])

    # Calculate emissions based on the energy content
    CO_Comb = (CH4_Energy_EngCont * Engine_param['CO']['amount']
               + CH4_Flare_EngCont * Flare_param['CO']['amount']) / 10**6

    NOx_Comb = (CH4_Energy_EngCont * Engine_param['NO2']['amount']
                + CH4_Flare_EngCont * Flare_param['NO2']['amount']) / 10**6

    SO2_Comb = (CH4_Energy_EngCont * Engine_param['SO2']['amount']
                + CH4_Flare_EngCont * Flare_param['SO2']['amount']) / 10**6

    NMVOCs_Comb = (CH4_Energy_EngCont * Engine_param['NMVOC']['amount']
                   + CH4_Flare_EngCont * Flare_param['NMVOC']['amount']) / 10**6

    PM2_5_Comb = (CH4_Energy_EngCont * Engine_param['PM']['amount']
                  + CH4_Flare_EngCont * Flare_param['PM']['amount']) / 10**6

    lci.add(name='Fugitive (Leaked) Methane',
            flow=(CH4_fugitiv_mass_asC
                  * CommonData.MW['CH4']['amount'] / CommonData.MW['C']['amount']))

    lci.add(name='Carbon dioxide, non-fossil from comubstion',
            flow=(CO2_from_CH4Comb
                  * CommonData.MW['CO2']['amount'] / CommonData.MW['C']['amount']))

    lci.add(name='Methane, non-fossil (unburned)',
            flow=(CH4_unburn_AsC
                  * CommonData.MW['CH4']['amount'] / CommonData.MW['C']['amount']))

    lci.add(name='Carbon monoxide (CO)', flow=CO_Comb)
    lci.add(name='Nitrogen oxides (as NO2)', flow=NOx_Comb)
    lci.add(name='Sulfur dioxide (SO2)', flow=SO2_Comb)
    lci.add(name='NMVOCs', flow=NMVOCs_Comb)
    lci.add(name='PM2.5', flow=PM2_5_Comb)

    # Biogas production
    BioGas_vol = CH4_prod_vol / Biogas_gen['ad_ch4stoich']['amount']
    BioGas_mass = (CH4_prod_vol * CommonData.STP['m3CH4_to_kg']['amount']
                   + (BioGas_vol - CH4_prod_vol) * CommonData.STP['m3CO2_to_kg']['amount'])

    # Electricity production
    Elec_prod =  CH4_Energy_EngCont / Biogas_gen['ad_HeatRate']['amount']
    lci.add(name=('Technosphere', 'Electricity_production'), flow=Elec_prod)

    # CO2 production
    CO2_prod_mass_asC = ((BioGas_vol - CH4_prod_vol)
                         * CommonData.STP['m3CO2_to_kg']['amount']
                         * CommonData.MW['C']['amount'] / CommonData.MW['CO2']['amount'])

    lci.add(name='Carbon dioxide, non-fossil (in biogas)',
            flow=(CO2_prod_mass_asC
                  * CommonData.MW['CO2']['amount'] / CommonData.MW['C']['amount']))

    # Water and Volatile solid in Biogas
    BioGas_VS = BioGas_mass * Biogas_gen['perSolDec']['amount'] / 100
    BioGas_Water = BioGas_mass - BioGas_VS

    # Product
    product = deepcopy(flow_init)
    product.data['vs_cont'] = (input_flow.data['vs_cont'].values
                               - BioGas_VS)

    product.data['ash_cont'] = input_flow.data['ash_cont'].values

    product.data['sol_cont'] = (product.data['vs_cont'].values
                                + product.data['ash_cont'])

    product.data['moist_cont'] = (input_flow.data['moist_cont'].values
                                  - BioGas_Water)

    product.data['mass'] = (product.data['moist_cont'].values
                            + product.data['sol_cont'].values)

    product.data['C_cont'] = (input_flow.data['C_cont'].values
                              - CO2_prod_mass_asC
                              - CH4_prod_mass_asC)

    product.data['N_cont'] = input_flow.data['N_cont'].values
    product.data['P_cont'] = input_flow.data['P_cont'].values
    product.data['K_cont'] = input_flow.data['K_cont'].values

    return product


### AD Dewater
def Dewater(input_flow, CommonData, process_data, input_data, Material_Properties, added_water, assumed_comp, lci, flow_init):
    if input_data.AD_operation['isDw']['amount'] == 1:
        # Calculating water removed
        liq_rem = ((input_flow.data['moist_cont'].values
                    - input_data.Dewater['ad_mcDigestate']['amount']
                    * input_flow.data['mass'].values)
                   / (1 - input_data.Dewater['ad_mcDigestate']['amount']))

        # Maximum water recirculate
        Recirculate_water_max = sum(added_water * assumed_comp) * input_data.AD_operation['recircMax']['amount']

        # Liquid to reatment, new water, recirculate watersum(liq_rem * assumed_co
        total_liq_to_treatment = max(sum(liq_rem * assumed_comp) - Recirculate_water_max, 0)
        liq_treatment_mass = total_liq_to_treatment * liq_rem / sum(liq_rem * assumed_comp)
        liq_treatment_vol = liq_treatment_mass / 1000 / input_data.Dig_prop['digliqdens']['amount']
        # Recirulate_water_mass = (sum(liq_rem * assumed_comp) - total_liq_to_treatment) * liq_rem / sum(liq_rem * assumed_comp)
        # New_water_mass = (sum(added_water * assumed_comp) - (sum(liq_rem * assumed_comp) - total_liq_to_treatment)) * liq_rem / sum(liq_rem * assumed_comp)

        # Product
        product = deepcopy(flow_init)
        product.data['vs_cont'] = input_flow.data['vs_cont'].values
        product.data['ash_cont'] = input_flow.data['ash_cont'].values
        product.data['sol_cont'] = input_flow.data['sol_cont'].values
        product.data['moist_cont'] = input_flow.data['moist_cont'].values - liq_rem
        product.data['mass'] = product.data['moist_cont'].values + product.data['sol_cont'].values
        product.data['C_cont']= input_flow.data['C_cont'].values
        product.data['N_cont'] = (input_flow.data['N_cont'].values
                                  * (1 - liq_rem / input_flow.data['moist_cont'].values 
                                     * (100 - input_data.Dig_prop['perNSolid']['amount']) / 100 ))
    
        product.data['P_cont'] = input_flow.data['P_cont'].values * (1 - liq_rem / input_flow.data['moist_cont'].values * (100 - input_data.Dig_prop['perPSolid']['amount']) / 100 )
        product.data['K_cont'] = input_flow.data['K_cont'].values * (1 - liq_rem / input_flow.data['moist_cont'].values * (100 - input_data.Dig_prop['perKSolid']['amount']) / 100 )

        # Resource use
        Electricity = input_data.Dewater['elec_dw']['amount'] * input_flow.data['sol_cont'].values / 1000
        lci.add(name=('Technosphere', 'Electricity_consumption'), flow=Electricity)

        return product,liq_rem, liq_treatment_vol

    if input_data.AD_operation['isDw']['amount'] != 1:
        # Product
        product = deepcopy(flow_init)
        product.data = input_flow.data * 1


### AD_Mixing two flows
def mix(input1, input2, Material_Properties, flow_init):
    product = deepcopy(flow_init)
    product.data['mass'] = (input1.data['mass'].values
                            + input2.data['mass'].values)

    product.data['sol_cont'] = (input1.data['sol_cont'].values
                                + input2.data['sol_cont'].values)

    product.data['moist_cont'] = (input1.data['moist_cont'].values
                                  + input2.data['moist_cont'].values)

    product.data['vs_cont'] = (input1.data['vs_cont'].values
                               + input2.data['vs_cont'].values)

    product.data['ash_cont'] = (input1.data['ash_cont'].values
                                + input2.data['ash_cont'].values)

    product.data['C_cont'] = (input1.data['C_cont'].values
                              + input2.data['sol_cont'].values
                              * Material_Properties['Biogenic Carbon Content'].values / 100)

    product.data['N_cont'] = (input1.data['N_cont'].values
                              + input2.data['sol_cont'].values
                              * Material_Properties['Nitrogen Content'].values / 100)

    product.data['P_cont'] = (input1.data['P_cont'].values
                              + input2.data['sol_cont'].values
                              * Material_Properties['Phosphorus Content'].values / 100)
    
    product.data['K_cont'] = (input1.data['K_cont'].values
                              + input2.data['sol_cont'].values
                              * Material_Properties['Potassium Content'].values / 100)
    return product

### AD Curing
def curing(input_flow, input_to_reactor, CommonData, process_data, input_data, assumed_comp, Material_Properties, lci, flow_init):
        if input_data.AD_operation['isCured']['amount'] == 1:
            input_flow.update(assumed_comp)
            # Calculate wood chips\screen rejects for moisture control
            Tot_WoodChips = (input_flow.water - input_data.Dig_prop['mcInitComp']['amount'] * input_flow.flow)\
                / (input_data.Dig_prop['mcInitComp']['amount'] - input_data.Material_Properties['wcMC']['amount'])

            WC_SR = Tot_WoodChips * input_flow.data['moist_cont'].values / input_flow.water
            WC_SR_Water = WC_SR * input_data.Material_Properties['wcMC']['amount']
            WC_SR_solid = WC_SR - WC_SR_Water

            # Carbon balance
            C_Remain = np.where(input_flow.data['C_cont'].values / input_to_reactor.data['C_cont'].apply(lambda x: 1 if x <= 0 else x ).values
                                <= (1 - process_data['Percent Carbon loss during curing'].values / 100),
                                input_flow.data['C_cont'].values,
                                input_to_reactor.data['C_cont'].values * (1 - process_data['Percent Carbon loss during curing'].values / 100))
            C_loss = input_flow.data['C_cont'].values - C_Remain

            C_loss_as_CH4 = input_data.Curing_Bio['ad_pCasCH4']['amount'] * C_loss
            C_loss_as_CO2 = C_loss - C_loss_as_CH4

            lci.add(name='Methane, non-fossil',
                    flow=C_loss_as_CH4 * CommonData.MW['CH4']['amount'] / CommonData.MW['C']['amount'])
            lci.add(name='Carbon dioxide, non-fossil _ Curing',
                    flow=C_loss_as_CO2 * CommonData.MW['CO2']['amount'] / CommonData.MW['C']['amount'])

            # Nitrogen balance
            N_loss = input_flow.data['N_cont'].values * process_data['Percent N emitted during composting'].values
            N_loss_as_N2O = N_loss * input_data.Curing_Bio['ad_pNasN2O']['amount']
            N_loss_as_NH3 = N_loss * input_data.Curing_Bio['ad_pNasNH3']['amount']

            lci.add(name='Ammonia',
                    flow=N_loss_as_NH3 * CommonData.MW['Ammonia']['amount'] / CommonData.MW['N']['amount'])
            lci.add(name='Dinitrogen monoxide',
                    flow=N_loss_as_N2O * CommonData.MW['Nitrous_Oxide']['amount'] / CommonData.MW['N']['amount'] / 2)

            # VOC emission
            VS_loss = input_data.Curing_Bio['VSlossPerCloss']['amount'] * C_loss / CommonData.MW['C']['amount']
            VOC_emitted = VS_loss * process_data['VOC emissions during curing'].values / 1000000
            lci.add(name='NMVOC, non-methane volatile organic compounds, unspecified origin',
                    flow=VOC_emitted)

            # Product
            product = deepcopy(flow_init)
            product.data['vs_cont'] = input_flow.data['vs_cont'].values - VS_loss
            product.data['ash_cont'] = input_flow.data['ash_cont'].values
            product.data['sol_cont'] = product.data['vs_cont'].values + product.data['ash_cont'].values

            product.data['C_cont'] = input_flow.data['C_cont'].values - C_loss
            product.data['N_cont'] = input_flow.data['N_cont'].values - N_loss
            product.data['P_cont'] = input_flow.data['P_cont'].values
            product.data['K_cont'] = input_flow.data['K_cont'].values

            # Water
            Water_curing = (WC_SR_Water - input_data.Material_Properties['ad_mcFC']['amount'] * (WC_SR_Water + WC_SR_solid + product.data['sol_cont'].values))\
                /(input_data.Material_Properties['ad_mcFC']['amount'] - 1)

            # Product
            product.data['moist_cont'] = Water_curing
            product.data['mass'] = product.data['moist_cont'].values + product.data['sol_cont'].values

            # Resource use
            loder_dsl = input_flow.data['mass'].values / 1000 * input_data.Loader['hpFEL']['amount'] * input_data.Loader['mfFEL']['amount'] * input_data.AD_operation['ophrsperday']['amount']
            WC_shred_dsl = input_data.shredding['Mtgp']['amount'] * input_data.shredding['Mtgf']['amount'] * WC_SR / 1000
            Windrow_turner_dsl = (WC_SR + input_flow.data['mass'].values) / 1000 * input_data.Windrow_turn['Tcur']['amount'] * input_data.Windrow_turn['Mwta']['amount']\
                * input_data.Windrow_turn['turnFreq']['amount'] * input_data.Windrow_turn['Mwfa']['amount']

            lci.add(name=('Technosphere', 'Equipment_Diesel'), flow=loder_dsl)
            lci.add(name=('Technosphere', 'Equipment_Diesel'), flow=WC_shred_dsl)
            lci.add(name=('Technosphere', 'Equipment_Diesel'), flow=Windrow_turner_dsl)

        return product, WC_SR

### AD Post_screen
def Post_screen(input_flow, input_WC_SR, input_data, assumed_comp, Material_Properties, lci, flow_init):
    product = deepcopy(flow_init)

    Screen_rejects = input_WC_SR * input_data.Post_Screen['ad_scrEff_WC']['amount']

    Remain_WC = input_WC_SR - Screen_rejects
    Remain_WC_water = Remain_WC * input_data.Material_Properties['wcMC']['amount']
    Remain_WC_solid = Remain_WC - Remain_WC_water
    Remain_WC_VS = Remain_WC_solid * input_data.Material_Properties['wcVSC']['amount']
    Remain_WC_Ash = Remain_WC_solid - Remain_WC_VS

    # Product
    product = deepcopy(flow_init)
    product.data['vs_cont'] = input_flow.data['vs_cont'].values +  Remain_WC_VS
    product.data['ash_cont'] = input_flow.data['ash_cont'].values + Remain_WC_Ash
    product.data['sol_cont'] = input_flow.data['sol_cont'].values + Remain_WC_solid
    product.data['moist_cont'] = input_flow.data['moist_cont'].values + Remain_WC_water
    product.data['mass'] = product.data['moist_cont'].values + product.data['sol_cont'].values
    product.data['C_cont'] = input_flow.data['C_cont'].values # Does not culculate the carbon in the WC
    product.data['N_cont'] = input_flow.data['N_cont'].values
    product.data['P_cont'] = input_flow.data['P_cont'].values
    product.data['K_cont'] = input_flow.data['K_cont'].values

    # Resource use
    Electricity = input_data.Post_Screen['ad_engScreen']['amount'] * (input_flow.data['mass'].values + input_WC_SR)
    lci.add(name=('Technosphere', 'Electricity_consumption'), flow=Electricity)
    return product, Screen_rejects


def POTW (liq_treatment_vol, liq_rem, input_to_reactor, Dig_to_Curing, FinalCompost, index,input_data, assumed_comp, Material_Properties, CommonData, lci):
    # Allocation factor
    AF_total = {}
    AF_total['COD'] = sum((1 - Material_Properties['Moisture Content'].values / 100) * assumed_comp * liq_treatment_vol * Material_Properties['Biogenic Carbon Content'].values / 100 * 1000)
    AF_total['BOD'] = sum((1 - Material_Properties['Moisture Content'].values / 100) * assumed_comp * liq_treatment_vol * Material_Properties['Methane Yield'].values)
    AF_total['TSS'] = sum(assumed_comp * liq_treatment_vol)
    AF_total['Total_N'] = sum(input_to_reactor.data['N_cont'].values * assumed_comp * FinalCompost.data['mass'].values/input_data.Material_Properties['densFC']['amount'] )
    AF_total['Phosphate'] = sum((1 - Material_Properties['Moisture Content'].values / 100) * assumed_comp * FinalCompost.data['mass'].values
                                / input_data.Material_Properties['densFC']['amount'] * Material_Properties['Phosphorus Content'].values / 100 * 1000)

    for i in ['Iron','Copper','Cadmium','Arsenic','Mercury','Selenium','Chromium','Lead','Zinc','Barium','Silver']:
        AF_total[i] = sum((1-Material_Properties['Moisture Content'].values/100) * assumed_comp * FinalCompost.data['mass'].values/input_data.Material_Properties['densFC']['amount'] * Material_Properties[i].values/100 *1000)


    AF={}
    AF['COD'] = (1-Material_Properties['Moisture Content'].values/100) * liq_treatment_vol * Material_Properties['Biogenic Carbon Content'].values/100 * 1000 / AF_total['COD']
    AF['BOD'] = (1-Material_Properties['Moisture Content'].values/100) * liq_treatment_vol * Material_Properties['Methane Yield'].values / AF_total['BOD']
    AF['TSS'] = liq_treatment_vol/AF_total['TSS']
    AF['Total_N'] = input_to_reactor.data['N_cont'].values * FinalCompost.data['mass'].values/input_data.Material_Properties['densFC']['amount']/AF_total['Total_N']
    AF['Phosphate'] = (1-Material_Properties['Moisture Content'].values/100) * FinalCompost.data['mass'].values/input_data.Material_Properties['densFC']['amount'] * Material_Properties['Phosphorus Content'].values/100 * 1000 / AF_total['Phosphate']

    for i in ['Iron','Copper','Cadmium','Arsenic','Mercury','Selenium','Chromium','Lead','Zinc','Barium','Silver']:
        if AF_total[i] == 0:
            AF[i]=0
        else:
            AF[i] = (1-Material_Properties['Moisture Content'].values/100) * FinalCompost.data['mass'].values/input_data.Material_Properties['densFC']['amount'] * Material_Properties[i].values/100 * 1000 / AF_total[i]

    #Emission from POTW
    Emission={}
    Emission['Total_N'] =  input_to_reactor.data['N_cont'].values * (100-input_data.Dig_prop['perNSolid']['amount'])/100 * liq_rem/(Dig_to_Curing.data['moist_cont'].values+liq_rem) * (1-CommonData.WWT['n_rem']['amount']/100)
    Emission['Phosphate'] = input_to_reactor.data['sol_cont'].values * Material_Properties['Phosphorus Content'].values/100 * (100-input_data.Dig_prop['perPSolid']['amount'])/100 * liq_rem/(Dig_to_Curing.data['moist_cont'].values+liq_rem) *(94.97/30.97) * (1-CommonData.WWT['p_rem']['amount']/100)

    for i,j,k in [('COD','lchCODcont','cod_rem'),('BOD','lchBODcont','bod_rem'),('TSS','lchTSScont','tss_rem')\
                  ,('Iron','conc_Fe','metals_rem'),('Copper','conc_Cu','metals_rem'),('Cadmium','conc_Cd','metals_rem')\
                  ,('Arsenic','conc_As','metals_rem'),('Mercury','conc_Hg','metals_rem'),('Selenium','conc_Se','metals_rem')\
                  ,('Chromium','conc_Cr','metals_rem'),('Lead','conc_Pb','metals_rem'),('Zinc','conc_Zn','metals_rem')\
                  ,('Barium','conc_Ba','metals_rem'),('Silver','conc_Ag','metals_rem')]:
        Emission[i] = input_data.Digestate_treatment[j]['amount'] * AF[i] * liq_treatment_vol * (1-CommonData.WWT[k]['amount']/100)

    for i,j in [('COD','COD'),('BOD','BOD'),('TSS','Total suspended solids')\
                  ,('Iron','Iron'),('Copper','Copper'),('Cadmium','Cadmium')\
                  ,('Arsenic','Arsenic'),('Mercury','Mercury'),('Phosphate','Phosphate'),('Selenium','Selenium')\
                  ,('Chromium','Chromium'),('Lead','Lead'),('Zinc','Zinc')\
                  ,('Barium','Barium'),('Silver','Silver'),('Total_N','Total N')]:
        lci.add(name=j, flow=Emission[i])


    BOD_removed = input_data.Digestate_treatment['lchBODcont']['amount'] * AF['BOD'] * liq_treatment_vol * CommonData.WWT['bod_rem']['amount']/100
    lci.add(name='CO2-biogenic emissions from digested liquids treatment',
            flow=BOD_removed * CommonData.Leachate_treat['co2bod']['amount'])

    #Sludge to LF
    sludge_prod = liq_treatment_vol * CommonData.Leachate_treat['sludgef']['amount'] # Unit kg

    #Resouce use
    lci.add(name=('Technosphere', 'Internal_Process_Transportation_Heavy_Duty_Diesel_Truck'),
            flow=input_data.Digestate_treatment['ad_distPOTW']['amount'] * liq_treatment_vol * 1000 * input_data.Dig_prop['digliqdens']['amount'])
    lci.add(name=('Technosphere', 'Empty_Return_Heavy_Duty_Diesel_Truck'),
            flow=liq_treatment_vol * input_data.Dig_prop['digliqdens']['amount'] / input_data.Digestate_treatment['payload_POTW']['amount']\
                * input_data.Digestate_treatment['ad_distPOTW']['amount'] * input_data.Digestate_treatment['ad_erPOTW']['amount'])

    lci.add(name='Full_Total heavy duty truck tranport',
            flow=input_data.Digestate_treatment['wwtp_lf_dist']['amount'] * sludge_prod)
    lci.add(name=('Technosphere', 'Empty_Return_Heavy_Duty_Diesel_Truck'),
            flow=input_data.Digestate_treatment['wwtp_lf_dist']['amount'] * sludge_prod /1000\
            /input_data.Digestate_treatment['payload_LFPOTW']['amount'] * input_data.Digestate_treatment['er_wwtpLF']['amount'])

    lci.add(name=('Technosphere', 'Electricity_consumption'),
            flow=BOD_removed * CommonData.Leachate_treat['elecBOD']['amount'])
