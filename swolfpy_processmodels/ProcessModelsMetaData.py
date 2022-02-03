# -*- coding: utf-8 -*-

ProcessModelsMetaData = {}

ProcessModelsMetaData['AD'] = {}
ProcessModelsMetaData['AD']['Name'] = 'Anaerobic Digestion'
ProcessModelsMetaData['AD']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['AD']['File'] = 'AD.py'
ProcessModelsMetaData['AD']['InputType'] = ['Separated_Organics', 'SSO']

ProcessModelsMetaData['Comp'] = {}
ProcessModelsMetaData['Comp']['Name'] = 'Composting'
ProcessModelsMetaData['Comp']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['Comp']['File'] = 'Comp.py'
ProcessModelsMetaData['Comp']['InputType'] = ['SSYW', 'SSO', 'SSYWDO', 'Separated_Organics']

ProcessModelsMetaData['WTE'] = {}
ProcessModelsMetaData['WTE']['Name'] = 'Waste To Energy'
ProcessModelsMetaData['WTE']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['WTE']['File'] = 'WTE.py'
ProcessModelsMetaData['WTE']['InputType'] = ['RWC', 'MRDO', 'Other_Residual']

ProcessModelsMetaData['LF'] = {}
ProcessModelsMetaData['LF']['Name'] = 'Landfill'
ProcessModelsMetaData['LF']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['LF']['File'] = 'LF.py'
ProcessModelsMetaData['LF']['InputType'] = ['RWC', 'MRDO', 'Other_Residual', 'Bottom_Ash',
                                            'Fly_Ash', 'Unreacted_Ash']

ProcessModelsMetaData['SS_MRF'] = {}
ProcessModelsMetaData['SS_MRF']['Name'] = 'Single Stream Material Recovery Facility'
ProcessModelsMetaData['SS_MRF']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['SS_MRF']['File'] = 'SS_MRF.py'
ProcessModelsMetaData['SS_MRF']['InputType'] = ['SSR', 'Separated_Recyclables']

ProcessModelsMetaData['Reproc'] = {}
ProcessModelsMetaData['Reproc']['Name'] = 'Reprocessing'
ProcessModelsMetaData['Reproc']['Process_Type'] = 'Reprocessing'
ProcessModelsMetaData['Reproc']['File'] = 'Reproc.py'
ProcessModelsMetaData['Reproc']['InputType'] = ['Al','Fe',
                                                'OCC', 'Mixed_Paper', 'ONP', 'OFF', 'Fiber_Other',
                                                'Brown_glass', 'Clear_glass', 'Green_glass', 'Mixed_Glass',
                                                'PET', 'HDPE_P', 'HDPE_T', 'LDPE_Film']

ProcessModelsMetaData['SF_Col'] = {}
ProcessModelsMetaData['SF_Col']['Name'] = 'Single Family Collection'
ProcessModelsMetaData['SF_Col']['Process_Type'] = 'Collection'
ProcessModelsMetaData['SF_Col']['File'] = 'SF_Col.py'
ProcessModelsMetaData['SF_Col']['InputType'] = []

ProcessModelsMetaData['MF_Col'] = {}
ProcessModelsMetaData['MF_Col']['Name'] = 'Multi-Family Collection'
ProcessModelsMetaData['MF_Col']['Process_Type'] = 'Collection'
ProcessModelsMetaData['MF_Col']['File'] = 'MF_Col.py'
ProcessModelsMetaData['MF_Col']['InputType'] = []

ProcessModelsMetaData['COM_Col'] = {}
ProcessModelsMetaData['COM_Col']['Name'] = 'Commercial Collection'
ProcessModelsMetaData['COM_Col']['Process_Type'] = 'Collection'
ProcessModelsMetaData['COM_Col']['File'] = 'COM_Col.py'
ProcessModelsMetaData['COM_Col']['InputType'] = []

ProcessModelsMetaData['TS'] = {}
ProcessModelsMetaData['TS']['Name'] = 'Transfer Station'
ProcessModelsMetaData['TS']['Process_Type'] = 'Transfer_Station'
ProcessModelsMetaData['TS']['File'] = 'TS.py'
ProcessModelsMetaData['TS']['InputType'] = ['DryRes', 'WetRes', 'ORG', 'REC']

ProcessModelsMetaData['HC'] = {}
ProcessModelsMetaData['HC']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['HC']['Name'] = 'Home Composting'
ProcessModelsMetaData['HC']['File'] = 'HC.py'
ProcessModelsMetaData['HC']['InputType'] = ['SSO_HC']

ProcessModelsMetaData['GC'] = {}
ProcessModelsMetaData['GC']['Process_Type'] = 'RDF'
ProcessModelsMetaData['GC']['Name'] = 'Gasification Syngas Combustion'
ProcessModelsMetaData['GC']['File'] = 'GC.py'
ProcessModelsMetaData['GC']['InputType'] = ['RDF']

ProcessModelsMetaData['RDF'] = {}
ProcessModelsMetaData['RDF']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['RDF']['Name'] = 'Refuse-Derived Fuel'
ProcessModelsMetaData['RDF']['File'] = 'RDF.py'
ProcessModelsMetaData['RDF']['InputType'] = ['RWC', 'MRDO']

ProcessModelsMetaData['AnF'] = {}
ProcessModelsMetaData['AnF']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['AnF']['Name'] = 'Animal Feed'
ProcessModelsMetaData['AnF']['File'] = 'AnF.py'
ProcessModelsMetaData['AnF']['InputType'] = ['SSO_AnF']

