.. General

==============================================================
Life-Cylce Process Models for swolfpy (swolfpy_processmodels)
==============================================================

.. image:: https://img.shields.io/pypi/v/swolfpy_processmodels.svg
        :target: https://pypi.python.org/pypi/swolfpy_processmodels
        
.. image:: https://img.shields.io/pypi/pyversions/swolfpy_processmodels.svg
    :target: https://pypi.org/project/swolfpy_processmodels/
    :alt: Supported Python Versions

.. image:: https://img.shields.io/pypi/l/swolfpy_processmodels.svg
    :target: https://pypi.org/project/swolfpy_processmodels/
    :alt: License

.. image:: https://img.shields.io/pypi/dm/swolfpy-processmodels.svg?label=Pypi%20downloads
    :target: https://pypi.org/project/swolfpy-processmodels/
    :alt: Downloads

.. image:: https://img.shields.io/pypi/format/swolfpy_processmodels.svg
    :target: https://pypi.org/project/swolfpy_processmodels/
    :alt: Format

.. image:: https://readthedocs.org/projects/swolfpy/badge/?version=latest
        :target: https://swolfpy.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://github.com/SwolfPy-Project/swolfpy-processmodels/actions/workflows/python-app.yml/badge.svg?branch=master
        :target: https://github.com/SwolfPy-Project/swolfpy-processmodels/actions/workflows/python-app.yml
        :alt: Test

.. image:: https://zenodo.org/badge/395802174.svg
        :target: https://zenodo.org/badge/latestdoi/395802174
        :alt: DOI

* Free software: GNU GENERAL PUBLIC LICENSE V2
* Website: https://swolfpy-project.github.io
* Documentation: https://swolfpy.readthedocs.io.
* Repository: https://github.com/SwolfPy-Project/swolfpy-processmodels


Features
--------
* Life-cycle process models for solid waste management (SWM) processes.
* Built-in Monte Carlo simulation

.. list-table:: **Life-cycle process models**
   :widths: auto
   :header-rows: 1

   * - 
     - Process model 
     - Description
   * - 1
     - Landfill (**LF**)
     - Calculates emissions, material use, and energy use associated with construction, operations, 
       closure and post-closure activities, landfill gas and leachate management, and carbon storage.
   * - 2
     - Waste-to-Energy (**WTE**)
     - Calculates emissions, mass flows, and resource use and recovery for the mass burn WTE process.
   * - 3
     - Gasification & Syngas Combustion (**GC**)
     - Calculates emissions, mass flows, and resource use and recovery for the GC process (Produced syngas from
       gasification is combusted to produce electricity by steam turbine). 
   * - 4
     - Composting (**Comp**)
     - Calculates emissions, mass flows, and resource use and recovery for aerobic composting process and final use of compost.
   * - 5
     - Home Composting (**HC**)
     - Calculates emissions, mass flows, and resource use and recovery for home composting process and final use of compost.
   * - 6
     - Anaerobic Digestion (**AD**)
     - Calculates emissions, mass flows, and resource use and recovery for anaerobic digestion process and final use of compost.
   * - 7
     - Single-Stream Material Recovery facility (**SS_MRF**)
     - Calculates cost, emissions, and energy use associated with material recovery facilities.
   * - 8
     - Refuse-Derived Fuel (**RDF**)
     - Calculates cost, emissions, and energy use associated with RDF prodcution facilities.
   * - 9
     - Reprocessing (**Reproc**)
     - Calculates emissions, mass flows, and resource use and recovery associated with recycling materials.	 
   * - 10
     - Transfer Station (**TS**)
     - Calculates cost, emissions, and energy use associated with Transfer Stations.
   * - 11
     - Single Family Collection (**SF_Col**)
     - Calculates cost, emissions, and fossil fuel use associated with MSW collection.


.. Installation

Installation
------------
1- Download and install miniconda from:  https://docs.conda.io/en/latest/miniconda.html

2- Update conda in a terminal window or anaconda prompt::

        conda update conda

3- Create a new environment for swolfpy::

        conda create --name swolfpy python=3.7

4- Activate the environment::

        conda activate swolfpy

5- Install swolfpy_processmodels in the environment::

        pip install swolfpy_processmodels

6- Use in python (e.g., Landfill model)::

        import swolfpy_processmodels as sppm 
        model = sppm.LF()
        model.calc()
        LCI_report = model.report()
        LCI_report

.. endInstallation
