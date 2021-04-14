# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 14:50:00 2020

@author: msardar2
"""
import pandas as pd
import numpy as np


class Distance():
    """
    Python class for importing the distances between the process models.
    
    Transport modes include:
    
    * Heavy Duty Truck
    * Medium Duty Truck
    * Rail 
    * Barge
    * Cargo Ship
        
    :param data: `Dictionary` that includes `Pandas DataFrame` for the distances between the process models as `value` and 
        tranport modes as `key`. `DataFrame` should use the name of processes as both `column` and row `index`.
    :type Data: dict

    :Example:

    >>> from swolfpy_processmodels import Distance
    >>> data = Distance.create_distance_table(['LF','WTE','AD'], ['Heavy Duty Truck'], default_dist=20)
    >>> data
    {'Heavy Duty Truck':      LF   WTE    AD
                         LF  NaN  20.0  20.0
                         WTE NaN   NaN  20.0
                         AD  NaN   NaN   NaN}
    >>> distance = Distance(data)
    >>> distance.Distance[('LF','WTE')]
    {'Heavy Duty Truck': 20.0}
    >>> distance.Distance[('LF','WTE')]['Heavy Duty Truck']
    20.0

    """
    def __init__(self, data=None):
        """
        Create Distance object.                    
        """
        self.data = data
        self.Distance = {}
        self.transport_modes = list(self.data.keys())
        for mode in self.transport_modes:
            for i in self.data[mode].columns:
                for j in self.data[mode].index:
                    if (i,j) not in self.Distance.keys():
                        self.Distance[(i,j)] = {}
                    if (j,i) not in self.Distance.keys():
                        self.Distance[(j,i)] = {}
                    if not pd.isna(self.data[mode][i][j]) and self.data[mode][i][j]!='':
                        self.Distance[(i,j)][mode] = self.data[mode][i][j]
                        self.Distance[(j,i)][mode] = self.data[mode][i][j]
                        if not pd.isna(self.data[mode][j][i]) and self.data[mode][j][i]!='' and self.data[mode][j][i]!=self.data[mode][i][j]:
                            raise Exception(f'Distance from {i} to {j} is not equal to distance from {j} to {i} in transport mode of {mode}')    

    @staticmethod
    def create_distance_table(process_names, transport_modes, default_dist=np.nan):
        """
        Static method for creating the data structure for distances and transport modes.

        :param process_names: `List` of process names (e.g., ``['LF', 'WTE']``)
        :param transport_modes: `List` of transport modes (i.e., Heavy Duty Truck, Medium Duty Truck, Rail, Barge, Cargo Ship).
            Example: ``['Heavy Duty Truck', 'Medium Duty Truck']``
        :param default_dist: Default distance that is used to fill the `DataFrame`.
        
        """
        dist_dict = dict()
        dist_array = np.full((len(process_names), len(process_names)),
                     np.nan,
                     dtype='float')
        dist_array[np.triu_indices_from(dist_array, k=1)] = default_dist 
        for mode in transport_modes:
            dist_dict[mode] = pd.DataFrame(data=dist_array,
                                           columns=process_names,
                                           index=process_names)
        return(dist_dict)
