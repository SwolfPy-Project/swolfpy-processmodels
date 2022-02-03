# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 11:12:21 2020

@author: msardar2
"""
import numpy as np
import numpy_financial as npf


### Resource use calculation for equipments
def calc_resource(total_throughput, remaining, removed, Eqpt, InputData, LCI):
    #Calculating resource use
    #Elec use = (motor_size*Frac_motor)/(max_input*frac_input)  --> unit: kW/Mg
    elec = Eqpt['motor']['amount'] * Eqpt['frac_motor']['amount'] / \
                (Eqpt['Max_input']['amount'] * Eqpt['frac_MaxInput']['amount'])

    if Eqpt['Calc_base']['amount'] == 0: # 0: calculation based on the removed mass
        Aloc = (removed / sum(removed) if sum(removed) > 0 else 0)
    elif Eqpt['Calc_base']['amount'] == 1: # 1: calculation based on the remaining mass
        Aloc = (remaining / sum(remaining) if sum(remaining) > 0 else 0)
    elif Eqpt['Calc_base']['amount'] == 2:  # 2: calculation based on the total throughput mass
        Aloc = (total_throughput / sum(total_throughput) if sum(total_throughput) > 0 else 0)
    else:
        raise ValueError('Input parameter [Calc_base] is not valid')

    elec_use =  sum(total_throughput) * elec *  Aloc
    dsl_use = sum(total_throughput) * Eqpt['diesel_use']['amount'] * Aloc
    LPG_use = sum(total_throughput) * Eqpt['LPG_use']['amount'] * Aloc

    Cap = Eqpt['Investment_cost']['amount'] + Eqpt['Installation_cost']['amount']
    Rate = InputData.Constr_cost['Inerest_rate']['amount']
    Lftime = Eqpt['LifeTime']['amount']
    TotalHour = (
        InputData.Labor['Hr_shift']['amount']
        * InputData.Labor['Shift_day']['amount']
        * InputData.Labor['Day_year']['amount'])

    # Average Cost of Ownership ($/Mg)
    AveCostOwner = (
        (npf.pmt(Rate, Lftime, -Cap) + Eqpt['O&M']['amount'])
        / (TotalHour * Eqpt['Max_input']['amount'] * Eqpt['frac_MaxInput']['amount']))

    # Laborers Required (Sorter*hours/Mg)
    LaborReq = Eqpt['N_Labor']['amount'] / (Eqpt['Max_input']['amount'] * Eqpt['frac_MaxInput']['amount'])
    # Drivers Required (Driver*hours/Mg)
    DriverReq = Eqpt['N_Driver']['amount'] / (Eqpt['Max_input']['amount'] * Eqpt['frac_MaxInput']['amount'])
    # Labor (sorter+Driver) Cost ($/Mg input)
    LaborCost = (LaborReq * InputData.Labor['Labor_rate']['amount'] + DriverReq * InputData.Labor['Driver_rate']['amount']) *\
                (1 + InputData.Labor['Fringe_rate']['amount']) * (1 + InputData.Labor['Management_rate']['amount'])

    TotalOMcost = sum(total_throughput) * Aloc * (AveCostOwner + LaborCost)

    # adding the resource use
    LCI.add(('Technosphere', 'Electricity_consumption'), elec_use)
    LCI.add(('Technosphere', 'Equipment_Diesel'), dsl_use)
    LCI.add(('Technosphere', 'Equipment_LPG'), LPG_use)
    LCI.add(('biosphere3', 'Operational_Cost'), TotalOMcost)

### Drum Feeder
def Drum_Feeder(Input, InputData, LCI):
    #Mass Calculation
    feed = Input

    #Equipment input
    Eqpt = InputData.Eq_DFeeder

    #Resource use calculation
    calc_resource(Input, Input, Input, Eqpt, InputData, LCI) # For Drum Feeder removed, remaining and throughput are same.

    return feed

### Flail Mill
def Flail_Mill(Input, InputData, LCI):
    # Mass Calculation
    feed = Input

    # Equipment input
    Eqpt = InputData.Eq_FMill

    # Resource use calculation
    calc_resource(Input, Input, Input, Eqpt, InputData, LCI) # For Drum Feeder removed, remaining and throughput are same.

    return feed

### Trommel for separating <2"
def Trommel(Input, sep_eff, InputData, LCI):
    # Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    # Equipment input
    Eqpt = InputData.Eq_Trommel

    # Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Negative sort
def Neg_Sort(Input, sep_eff, InputData, LCI):
    # Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    # Equipment input
    Eqpt = InputData.Eq_Neg_Sort

    # Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Negative/positive sort
def Sorting(Input, sep_eff, InputData, Eqpt_data, LCI):
    # Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    # Equipment input
    Eqpt = Eqpt_data

    #Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Air Separator
def Air_Sep(Input, sep_eff, InputData, LCI):
    # Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    # Equipment input
    Eqpt = InputData.Eq_Air_Sep

    # Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed


### Air Separator
def Optical_sorter(Input, sep_eff, InputData, LCI):
    # Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    # Equipment input
    Eqpt = InputData.Eq_Opt_Sort

    # Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Shredder
def Shredder(Input, InputData, LCI):
    # Mass Calculation
    feed = Input

    # Equipment input
    Eqpt = InputData.Eq_Shred

    # Resource use calculation
    # For Shredders removed, remaining and throughput are same.
    calc_resource(Input, Input, Input, Eqpt, InputData, LCI)

    return feed

### Pelletizer
def Pelletizer(Input, InputData, LCI):
    # Mass Calculation
    feed = Input

    # Equipment input
    Eqpt = InputData.Eq_Pellet

    # Resource use calculation
    # For Shredders removed, remaining and throughput are same.
    calc_resource(Input, Input, Input, Eqpt, InputData, LCI)

    return feed

### Manual Sort 1 (Negative) for separating the plastic film
def Man_Sort1(Input, sep_eff, InputData, LCI):
    #Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    #Equipment input
    Eqpt = InputData.Eq_MS1

    #Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Vacuum
def Vacuum(Input, sep_eff, InputData, LCI):
    #Equipment input
    if InputData.Rec_material['Film']['amount'] == 1: # Automatic recovery
        Eqpt = InputData.Eq_Vac
        sep_eff = sep_eff[:, 0]
    elif InputData.Rec_material['Film']['amount'] == 2: # Manual recovery
        Eqpt = InputData.Eq_Vac_Manual
        sep_eff = sep_eff[:, 1]

    #Mass Calculation
    if InputData.Rec_material['Film']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Resource use calculation
    if InputData.Rec_material['Film']['amount'] > 0:
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed


### Disc Screen 1: OCC separation
def DS1(Input, sep_eff, InputData, LCI):
    #Equipment input
    if InputData.Rec_material['OCC']['amount'] == 1: # Automatic recovery
        Eqpt = InputData.Eq_DS1
        sep_eff = sep_eff[:, 0]
    elif InputData.Rec_material['OCC']['amount'] == 2: # Manual recovery
        Eqpt = InputData.Eq_DS1_Manual
        sep_eff = sep_eff[:, 1]

    #Mass Calculation
    if InputData.Rec_material['OCC']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Resource use calculation
    if InputData.Rec_material['OCC']['amount'] > 0:
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### ### Disc Screen 2: Newspaper separation
def DS2(Input, sep_eff, InputData, LCI):
    #Equipment input
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] == 1: # Automatic recovery
        Eqpt = InputData.Eq_DS2
        sep_eff = sep_eff[:, 0]
    elif InputData.Rec_material['Non_OCC_Fiber']['amount'] == 2: # Manual recovery
        Eqpt = InputData.Eq_DS2_Manual
        sep_eff = sep_eff[:, 1]

    #Mass Calculation
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Resource use calculation
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] > 0:
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed


### Disc Screen 3: Fiber separation
def DS3(Input, sep_eff, InputData, LCI):
    #Equipment input
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] == 1: # Automatic recovery
        Eqpt = InputData.Eq_DS3
        sep_eff = sep_eff[:, 0]
    elif InputData.Rec_material['Non_OCC_Fiber']['amount'] == 2: # Manual recovery
        Eqpt = InputData.Eq_DS3_Manual
        sep_eff = sep_eff[:, 1]

    #Mass Calculation
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Resource use calculation
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] > 0:
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed


###  ### Manual Sort 2-DS2 (Negative)
def MS2_DS2(Input, sep_eff, InputData, LCI):
    #Mass Calculation
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Equipment input
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] > 0: # Manual recovery
        Eqpt = InputData.Eq_MS2_DS2
        #Resource use calculation
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed



###  ### Manual Sort 2-DS3 (Negative)
def MS2_DS3(Input, sep_eff, InputData, LCI):
    #Mass Calculation
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Equipment input
    if InputData.Rec_material['Non_OCC_Fiber']['amount'] > 0: # Manual recovery
        Eqpt = InputData.Eq_MS2_DS3
        #Resource use calculation
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)
    return remained, removed

### ### Baler_1Way: product is baled OCC and mixed fiber
def Baler_1Way(OCC, Non_OCC_Fiber, InputData, LCI):
    # Mass Calculation
    baled = OCC + Non_OCC_Fiber

    # Equipment input
    Eqpt = InputData.Eq_Baler_1Way
    # Resource use calculation
    calc_resource(baled, baled, baled, Eqpt, InputData, LCI)

    # Wire use calculation
    # Bale volume
    Volumne = Eqpt['Bale_Width']['amount'] * Eqpt['Bale_Length']['amount'] * Eqpt['Bale_Height']['amount']
    #Bale Wire Length
    Wire_len = Eqpt['Straps_Per_Bale']['amount'] * 2 * (Eqpt['Bale_Height']['amount'] + Eqpt['Bale_Width']['amount'])
    # Wire use
    Wire_use = (OCC / InputData.Rec_BaleDens['OCC']['amount'] +
                Non_OCC_Fiber / InputData.Rec_BaleDens['Non_OCC_Fiber']['amount'])\
               / Volumne*Wire_len / InputData.Baler_Wire['Len_to_Mass']['amount']

    #Wire Transportation
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Heavy_Duty_Diesel_Truck'), Wire_use*InputData.Baler_Wire['Trans_HDDT']['amount'])
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Medium_Duty_Diesel_Truck'), Wire_use*InputData.Baler_Wire['Trans_MDDT']['amount'])
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Barge'), Wire_use*InputData.Baler_Wire['Trans_Barge']['amount'])
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Cargo_Ship'), Wire_use*InputData.Baler_Wire['Trans_CargoShip']['amount'])
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Rail'), Wire_use*InputData.Baler_Wire['Trans_Rail']['amount'])

    #Add Wire use to LCI
    LCI.add(('Technosphere', 'Wire'), Wire_use)
    return baled

### Baler
def Baler(Input, InputData, LCI):
    # Mass Calculation
    baled = Input

    # Equipment input
    Eqpt = InputData.Eq_Baler

    # Resource use calculation
    calc_resource(baled, baled, baled, Eqpt, InputData, LCI)

    # Wire use calculation
    # Bale volume
    Volumne = Eqpt['Bale_Width']['amount'] * Eqpt['Bale_Length']['amount'] * Eqpt['Bale_Height']['amount']
    #Bale Wire Length
    Wire_len = Eqpt['Straps_Per_Bale']['amount'] * 2 * (Eqpt['Bale_Height']['amount'] + Eqpt['Bale_Width']['amount'])
    # Wire use
    Wire_use = (baled
                / Eqpt['Bale_Density']['amount']
                / Volumne
                * Wire_len
                / InputData.Baler_Wire['Len_to_Mass']['amount'])

    #Wire Transportation
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Heavy_Duty_Diesel_Truck'), Wire_use*InputData.Baler_Wire['Trans_HDDT']['amount'])

    # Add Wire use to LCI
    LCI.add(('Technosphere', 'Wire'), Wire_use)

    return baled

### Glass Breaker Screen
def GBS(Input, sep_eff, InputData, LCI):  # GBS is always in system and working
    # Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    # Equipment input
    Eqpt = InputData.Eq_GBS
    # Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Air Knife
def AK(Input, sep_eff, InputData, LCI):
    #Mass Calculation
    if InputData.Rec_material['Glass']['amount'] == 1:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Equipment input
    if InputData.Rec_material['Glass']['amount'] > 0: # Manual recovery
        Eqpt = InputData.Eq_AK
        #Resource use calculation
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Optical Glass
def OG(Input, sep_eff, InputData, LCI):
    #Mass Calculation
    if InputData.Rec_material['Glass']['amount'] == 1:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Equipment input
    if InputData.Rec_material['Glass']['amount'] > 0: # Manual recovery
        Eqpt = InputData.Eq_OG
        #Resource use calculation
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Manual Sort 3-G (Negative)
def MS3_G(Input, sep_eff, InputData, LCI):
    #Mass Calculation
    if InputData.Rec_material['Glass']['amount'] == 1:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Equipment input
    if InputData.Rec_material['Glass']['amount'] > 0: # Manual recovery
        Eqpt = InputData.Eq_MS3_G
        #Resource use calculation
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Secondary sort glass
def Glass_type(Input, InputData):
    #Mass Calculation
    Res_Glass = np.zeros(Input.shape[0])
    Brown_glass = np.zeros(Input.shape[0])
    Clear_glass = np.zeros(Input.shape[0])
    Green_glass = np.zeros(Input.shape[0])
    Mixed_Glass = np.zeros(Input.shape[0])

    if InputData.Rec_material['Glass']['amount'] == 0:
        Res_Glass = Input
    else:
        if InputData.Rec_Sorted_material['Glass_Brown']['amount'] == 1:    # Brown_glass index = 33
            Brown_glass[33] = Input[33]

        if InputData.Rec_Sorted_material['Glass_Green']['amount'] == 1:    # Green_glass index = 34
            Green_glass[34] = Input[34]

        if InputData.Rec_Sorted_material['Glass_Clear']['amount'] == 1:    # Clear_glass index = 35
            Clear_glass[35] = Input[35]

        Mixed_Glass = Input - (Brown_glass + Green_glass + Clear_glass)

    return Res_Glass, Brown_glass, Clear_glass, Green_glass, Mixed_Glass

### Optical PET
def OPET(Input, sep_eff, InputData, LCI):
    #Equipment input
    if InputData.Rec_material['PET']['amount'] == 1: # Automatic recovery
        Eqpt = InputData.Eq_OPET
        sep_eff = sep_eff[:, 0]
    elif InputData.Rec_material['PET']['amount'] == 2: # Manual recovery
        Eqpt = InputData.Eq_OSPET
        sep_eff = sep_eff[:, 1]

    #Mass Calculation
    if InputData.Rec_material['PET']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed


    #Resource use calculation
    if InputData.Rec_material['PET']['amount'] > 0:
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Manual Sort 4-PET (Negative)
def MS4_PET(Input, sep_eff, InputData, LCI):
    #Mass Calculation
    if InputData.Rec_material['PET']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Equipment input
    if InputData.Rec_material['PET']['amount'] > 0: # Manual recovery
        Eqpt = InputData.Eq_MS4_PET
        #Resource use calculation
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Optical HDPE
def OHDPE(Input, sep_eff, InputData, LCI):
    #Equipment input
    if InputData.Rec_material['HDPE']['amount'] == 1: # Automatic recovery
        Eqpt = InputData.Eq_OHDPE
        sep_eff = sep_eff[:, 0]
    elif InputData.Rec_material['HDPE']['amount'] == 2: # Manual recovery
        Eqpt = InputData.Eq_OSHDPE
        sep_eff = sep_eff[:, 1]

    #Mass Calculation
    if InputData.Rec_material['HDPE']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Resource use calculation
    if InputData.Rec_material['HDPE']['amount'] > 0:
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Manual Sort 4-HDPE (Negative)
def MS4_HDPE(Input, sep_eff, InputData, LCI):
    # Mass Calculation
    if InputData.Rec_material['HDPE']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    # Equipment input
    if InputData.Rec_material['HDPE']['amount'] > 0: # Manual recovery
        Eqpt = InputData.Eq_MS4_HDPE
        #Resource use calculation
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### HDPE sold by type?
def HDPE_type(Input, InputData):
    # Mass Calculation
    HDPE_P = np.zeros(Input.shape[0])
    HDPE_T = np.zeros(Input.shape[0])

    # HDPE - Pigmented Containers index 19
    HDPE_P[19] = Input[19]

    #HDPE - Translucent Containers index 18
    HDPE_T[18] = Input[18]

    return HDPE_P, HDPE_T

### Magnet
def Magnet_RDF(Input, sep_eff, InputData, LCI):
    # Equipment input
    Eqpt = InputData.Eq_Magnet

    # Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    # Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Magnet
def Magnet(Input, sep_eff, InputData, LCI):
    # Equipment input
    if InputData.Rec_material['Ferrous']['amount'] == 1: # Automatic recovery
        Eqpt = InputData.Eq_Magnet
        sep_eff = sep_eff[:, 0]
    elif InputData.Rec_material['Ferrous']['amount'] == 2: # Manual recovery
        Eqpt = InputData.Eq_Magnet_Manual
        sep_eff = sep_eff[:, 1]

    # Mass Calculation
    if InputData.Rec_material['Ferrous']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    # Resource use calculation
    if InputData.Rec_material['Ferrous']['amount'] > 0:
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Manual Sort 4-Fe (Negative)
def MS4_Fe(Input, sep_eff, InputData, LCI):
    # Mass Calculation
    if InputData.Rec_material['Ferrous']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    # Equipment input
    if InputData.Rec_material['Ferrous']['amount'] > 0: # Manual recovery
        Eqpt = InputData.Eq_MS4_Fe
        # Resource use calculation
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Eddy Current Separator
def ECS(Input, sep_eff, InputData, LCI):
    #Equipment input
    if InputData.Rec_material['Aluminous']['amount'] == 1: # Automatic recovery
        Eqpt = InputData.Eq_ECS
        sep_eff = sep_eff[:, 0]
    elif InputData.Rec_material['Aluminous']['amount'] == 2: # Manual recovery
        Eqpt = InputData.Eq_ECS_Manual
        sep_eff = sep_eff[:, 1]

    #Mass Calculation
    if InputData.Rec_material['Aluminous']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Resource use calculation
    if InputData.Rec_material['Aluminous']['amount'] > 0:
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Eddy Current Separator (ECS)
def ECS_RDF(Input, sep_eff, InputData, Eqpt_data, LCI):
    # Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    # Equipment input
    Eqpt = Eqpt_data

    # Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed


### Manual Sort 4-Al (Negative)
def MS4_Al(Input, sep_eff, InputData, LCI):
    #Mass Calculation
    if InputData.Rec_material['Aluminous']['amount'] > 0:
        removed = Input * sep_eff
    else:
        removed = np.zeros(len(LCI.Index))
    remained = Input - removed

    #Equipment input
    if InputData.Rec_material['Aluminous']['amount'] > 0: # Manual recovery
        Eqpt = InputData.Eq_MS4_Al
        #Resource use calculation
        calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Manual Sort 5 (Positive)
def MS5(Input, sep_eff, InputData, LCI):
    #Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    #Equipment input
    Eqpt = InputData.Eq_MS5
    #Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### 2-Way Baler: product is baled plastics and metals (container)
def Baler_2Way(Input, InputData, LCI):
    #Mass Calculation
    baled = Input

    #Equipment input
    Eqpt = InputData.Eq_Baler_2Way
    #Resource use calculation
    calc_resource(baled, baled, baled, Eqpt, InputData, LCI)

    #Density
    Density = np.ones(len(LCI.index)) * 10**12 #using big density for non-recycab
    Density[[28, 29, 30, 32]] = InputData.Rec_BaleDens['Aluminous']['amount']
    Density[[26, 27, 31]] = InputData.Rec_BaleDens['Ferrous']['amount']
    Density[[18, 19]] = InputData.Rec_BaleDens['HDPE']['amount']
    Density[20] = InputData.Rec_BaleDens['PET']['amount']
    Density[24] = InputData.Rec_BaleDens['Film']['amount']

    #Wire use calculation
    #Bale volume
    Volumne = Eqpt['Bale_Width']['amount'] * Eqpt['Bale_Length']['amount'] * Eqpt['Bale_Height']['amount']
    #Bale Wire Length
    Wire_len = Eqpt['Straps_Per_Bale']['amount'] * 2 * (Eqpt['Bale_Height']['amount']+Eqpt['Bale_Width']['amount'])
    #Wire use
    Wire_use = (Input / Density) / Volumne * Wire_len / InputData.Baler_Wire['Len_to_Mass']['amount']

    #Add Wire use to LCI
    LCI.add(('Technosphere', 'Wire'), Wire_use)

    #Wire Transportation
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Heavy_Duty_Diesel_Truck'), Wire_use * InputData.Baler_Wire['Trans_HDDT']['amount'])
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Medium_Duty_Diesel_Truck'), Wire_use * InputData.Baler_Wire['Trans_MDDT']['amount'])
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Barge'), Wire_use * InputData.Baler_Wire['Trans_Barge']['amount'])
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Cargo_Ship'), Wire_use * InputData.Baler_Wire['Trans_CargoShip']['amount'])
    LCI.add(('Technosphere', 'Internal_Process_Transportation_Rail'), Wire_use * InputData.Baler_Wire['Trans_Rail']['amount'])

    return baled

### Densimetric table
def Densimetric_Table(Input, sep_eff, InputData, LCI):
    # Mass Calculation
    removed = Input * sep_eff
    remained = Input - removed

    # Equipment input
    Eqpt = InputData.Eq_DMT
    # Resource use calculation
    calc_resource(Input, remained, removed, Eqpt, InputData, LCI)

    return remained, removed

### Rolling_Stock
def Rolling_Stock(Input, InputData, LCI):
    #Equipment input
    Eqpt = InputData.Eq_Rolling_Stock
    #Resource use calculation
    calc_resource(Input, Input, Input, Eqpt, InputData, LCI)

### Conveyor
def Conveyor(Input, InputData, LCI):
    #Equipment input
    Eqpt = InputData.Eq_Conveyor
    #Resource use calculation
    calc_resource(Input, Input, Input, Eqpt, InputData, LCI)

### Secondary sort for mixed paper
def Mixed_paper_separation(Input, InputData):
    #Mass Calculation
    ONP = np.zeros(Input.shape[0])
    OFF = np.zeros(Input.shape[0])
    Fiber_Other = np.zeros(Input.shape[0])

    # Separate Newsprint index is 9
    if InputData.Rec_Sorted_material['Newsprint']['amount'] == 1:
        ONP[9] = Input[9] * InputData.Rec_Sep_eff['Newsprint']['amount']

    # Separate Office Paper index is 11
    if InputData.Rec_Sorted_material['Office_Paper']['amount'] == 1:
        OFF[11] = Input[11] * InputData.Rec_Sep_eff['Office_Paper']['amount']

    # Separate Magazines index is 12
    if InputData.Rec_Sorted_material['Magazines']['amount'] == 1:
        Fiber_Other[12] = Input[12] * InputData.Rec_Sep_eff['Magazines']['amount']

    # Separate Third_Class_Mail index is 13
    if InputData.Rec_Sorted_material['Third_Class_Mail']['amount'] == 1:
        Fiber_Other[13] = Input[13] * InputData.Rec_Sep_eff['Third_Class_Mail']['amount']

    # Separate Folding_Containers index is 14
    if InputData.Rec_Sorted_material['Folding_Containers']['amount'] == 1:
        Fiber_Other[14] = Input[14] * InputData.Rec_Sep_eff['Folding_Containers']['amount']

    # Separate Paper_Bags index is 15
    if InputData.Rec_Sorted_material['Paper_Bags']['amount'] == 1:
        Fiber_Other[15] = Input[15] * InputData.Rec_Sep_eff['Paper_Bags']['amount']

    # Remaining the mixed Paper
    Mixed_Paper = Input - (ONP + OFF + Fiber_Other)

    # Check to not get negative numbers
    if min(Mixed_Paper) < 0:
        raise ValueError('*** Mass Balance Error *** \n Check the separation efficiencies for secondary separation of Fiber.')

    return Mixed_Paper, ONP, OFF, Fiber_Other

### General Electricity
def Electricity(Input, InputData, LCI):
    #calculate electricity use in office and floor area
    elec_office = Input * InputData.Electricity['Area_rate']['amount'] * InputData.Electricity['Frac_office']['amount'] * InputData.Electricity['Elec_office']['amount']
    elec_floor = Input * InputData.Electricity['Area_rate']['amount'] * (1-InputData.Electricity['Frac_office']['amount']) * InputData.Electricity['Elec_floor']['amount']
    LCI.add(('Technosphere', 'Electricity_consumption'), elec_office+elec_floor)

### sterilizing the waste
def Sterilizer(Input, InputData, LCI):
    # Mass Calculation
    feed = Input

    # Equipment input
    Eqpt = InputData.Eq_Sterilizer

    # Resource use calculation
    # For Sterilizer removed, remaining and throughput are same.
    calc_resource(Input, Input, Input, Eqpt, InputData, LCI)

    return feed

### Dewater
def Dewater(Input, InputData, MaterialProperties, LCI):
    # Equipment input
    Eqpt = InputData.Eq_Dewater
    
    # Mass Calculation
    feed_moist = Input * MaterialProperties['Moisture Content'].values / 100
    feed_solid = Input - feed_moist
    product = feed_solid / (1 - InputData.AnF_operation['Dew_moist']['amount'])
    waste_water = Input - product

    # Resource use calculation
    calc_resource(Input, product, waste_water, Eqpt, InputData, LCI)

    return product, waste_water


### Dryer
def Dryer(Input, InputData, LCI):
    # Equipment input
    Eqpt = InputData.Eq_Dryer

    # Mass Calculation
    feed_moist = Input * InputData.AnF_operation['Dew_moist']['amount']
    feed_solid = Input - feed_moist
    product = feed_solid / (1 - InputData.AnF_operation['Dried_moist']['amount'])
    remove = Input - product

    # Resource use calculation
    calc_resource(Input, product, remove, Eqpt, InputData, LCI)

    return product