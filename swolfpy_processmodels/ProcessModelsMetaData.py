# -*- coding: utf-8 -*-

ProcessModelsMetaData = {}

ProcessModelsMetaData['AD'] = {}
ProcessModelsMetaData['AD']['Name'] = 'Anaerobic Digestion'
ProcessModelsMetaData['AD']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['AD']['File'] = 'AD.py'
ProcessModelsMetaData['AD']['InputType'] = ['SSO', 'Separated_Organics']

ProcessModelsMetaData['Comp'] = {}
ProcessModelsMetaData['Comp']['Name'] = 'Composting'
ProcessModelsMetaData['Comp']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['Comp']['File'] = 'Comp.py'
ProcessModelsMetaData['Comp']['InputType'] = ['SSO', 'SSYW', 'SSYWDO', 'Separated_Organics']

ProcessModelsMetaData['WTE'] = {}
ProcessModelsMetaData['WTE']['Name'] = 'Waste To Energy'
ProcessModelsMetaData['WTE']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['WTE']['File'] = 'WTE.py'
ProcessModelsMetaData['WTE']['InputType'] = ['RWC', 'DryRes', 'WetRes', 'MRDO', 'Other_Residual']

ProcessModelsMetaData['LF'] = {}
ProcessModelsMetaData['LF']['Name'] = 'Landfill'
ProcessModelsMetaData['LF']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['LF']['File'] = 'LF.py'
ProcessModelsMetaData['LF']['InputType'] = ['RWC', 'DryRes', 'WetRes', 'MRDO', 'Other_Residual', 'Bottom_Ash', 'Fly_Ash']

ProcessModelsMetaData['SS_MRF'] = {}
ProcessModelsMetaData['SS_MRF']['Name'] = 'Single Stream Material Recovery Facility'
ProcessModelsMetaData['SS_MRF']['Process_Type'] = 'Treatment'
ProcessModelsMetaData['SS_MRF']['File'] = 'SS_MRF.py'
ProcessModelsMetaData['SS_MRF']['InputType'] = ['SSR', 'REC']

ProcessModelsMetaData['Reproc'] = {}
ProcessModelsMetaData['Reproc']['Name'] = 'Reprocessing'
ProcessModelsMetaData['Reproc']['Process_Type'] = 'Reprocessing'
ProcessModelsMetaData['Reproc']['File'] = 'Reproc.py'
ProcessModelsMetaData['Reproc']['InputType'] = ['Al','Fe','Cu',
                                                'OCC', 'Mixed_Paper', 'ONP', 'OFF', 'Fiber_Other',
                                                'Brown_glass', 'Clear_glass', 'Green_glass', 'Mixed_Glass',
                                                'PET', 'HDPE_Unsorted', 'HDPE_P', 'HDPE_T', 'PVC', 'LDPE_Film',
                                                'Polypropylene', 'Polystyrene', 'Plastic_Other', 'Mixed_Plastic']
                                               
ProcessModelsMetaData['SF_Col'] = {}
ProcessModelsMetaData['SF_Col']['Name'] = 'Single Family Collection'
ProcessModelsMetaData['SF_Col']['Process_Type'] = 'Collection'
ProcessModelsMetaData['SF_Col']['File'] = 'SF_Col.py'
ProcessModelsMetaData['SF_Col']['InputType'] = []
