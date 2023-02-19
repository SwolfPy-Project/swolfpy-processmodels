# -*- coding: utf-8 -*-
"""
Created on Sat May  9 17:43:11 2020.

@author: Mojtaba Sardarmehni

Tests for `swolfpy_processmodels` package
"""
import numpy as np
from swolfpy_inputdata import CommonData

import swolfpy_processmodels as sp


def LCA_model_helper(model):
    commondata = CommonData()
    Index = set(commondata.Index)
    Reprocessing_Index = set(commondata.Reprocessing_Index)

    model.calc()
    report = model.report()

    assert isinstance(report, dict)
    assert "process name" in report.keys()

    assert "Waste" in report.keys()
    assert "Technosphere" in report.keys()
    assert "Biosphere" in report.keys()

    if model.Process_Type == "Reprocessing":
        assert Reprocessing_Index.issubset(report["Waste"])
        assert len(Reprocessing_Index) == len(report["Waste"])
        for x in Reprocessing_Index:
            for y in report["Waste"][x]:
                assert not np.isnan(report["Waste"][x][y])

        assert Reprocessing_Index.issubset(report["Technosphere"])
        assert len(Reprocessing_Index) == len(report["Technosphere"])
        for x in Reprocessing_Index:
            for y in report["Technosphere"][x]:
                assert not np.isnan(report["Technosphere"][x][y])

        assert Reprocessing_Index.issubset(report["Biosphere"])
        assert len(Reprocessing_Index) == len(report["Biosphere"])
        for x in Reprocessing_Index:
            for y in report["Biosphere"][x]:
                assert not np.isnan(report["Biosphere"][x][y])

    elif model.Process_Type == "Treatment" or model.Process_Type == "Collection":
        assert Index.issubset(report["Waste"])
        assert len(Index) == len(report["Waste"])
        for x in Index:
            for y in report["Waste"][x]:
                assert not np.isnan(report["Waste"][x][y])

        assert Index.issubset(report["Technosphere"])
        assert len(Index) == len(report["Technosphere"])
        for x in Index:
            for y in report["Technosphere"][x]:
                assert not np.isnan(report["Technosphere"][x][y])

        assert Index.issubset(report["Biosphere"])
        assert len(Index) == len(report["Biosphere"])
        for x in Index:
            for y in report["Biosphere"][x]:
                assert not np.isnan(report["Biosphere"][x][y])

    model.setup_MC()
    model.MC_calc()
    report = model.report()
    report1 = model.report()
    assert report == report1


def test_LF():
    assert sp.LF.Process_Type == "Treatment"
    LCA_model_helper(sp.LF())


def test_WTE():
    assert sp.WTE.Process_Type == "Treatment"
    LCA_model_helper(sp.WTE())


def test_Composting():
    assert sp.Comp.Process_Type == "Treatment"
    LCA_model_helper(sp.Comp())


def test_AD():
    assert sp.AD.Process_Type == "Treatment"
    LCA_model_helper(sp.AD())


def test_SS_MRF():
    assert sp.SS_MRF.Process_Type == "Treatment"
    LCA_model_helper(sp.SS_MRF())


def test_HC():
    assert sp.HC.Process_Type == "Treatment"
    LCA_model_helper(sp.HC())


def test_AnF():
    assert sp.AnF.Process_Type == "Treatment"
    LCA_model_helper(sp.AnF())


def test_Reproc():
    assert sp.Reproc.Process_Type == "Reprocessing"
    LCA_model_helper(sp.Reproc())


def test_TS():
    assert sp.TS.Process_Type == "Transfer_Station"
    LCA_model_helper(sp.TS())


def test_GC():
    assert sp.GC.Process_Type == "RDF"
    LCA_model_helper(sp.GC())


def test_RDF():
    assert sp.RDF.Process_Type == "Treatment"
    LCA_model_helper(sp.RDF())


def test_SF_Col():
    assert sp.SF_Col.Process_Type == "Collection"
    col_scheme = sp.SF_Col.scheme()
    col_scheme[("RWC", "SSYW", "SSR")] = 1
    LCA_model_helper(sp.SF_Col("SF_test", Collection_scheme=col_scheme))


def test_MF_Col():
    assert sp.MF_Col.Process_Type == "Collection"
    col_scheme = sp.MF_Col.scheme()
    col_scheme[("RWC", "SSYW", "SSR")] = 1
    LCA_model_helper(sp.MF_Col("MF_test", Collection_scheme=col_scheme))


def test_COM_Col():
    assert sp.COM_Col.Process_Type == "Collection"
    col_scheme = sp.COM_Col.scheme()
    col_scheme[("RWC", "SSYW", "SSR")] = 1
    LCA_model_helper(sp.COM_Col("COM_test", Collection_scheme=col_scheme))


def test_Distance():
    dist_data = sp.Distance.create_distance_table(["P1", "P2", "P3"], ["Heavy Duty Truck"])
    dist_data["Heavy Duty Truck"]["P1"]["P2"] = 20
    dist_data["Heavy Duty Truck"]["P3"]["P1"] = 30
    dist_data["Heavy Duty Truck"]["P3"]["P2"] = 20
    dist = sp.Distance(dist_data)
    assert dist.Distance[("P1", "P2")]["Heavy Duty Truck"] == 20
    assert dist.Distance[("P3", "P1")]["Heavy Duty Truck"] == 30
    assert (
        dist.Distance[("P2", "P3")]["Heavy Duty Truck"]
        == dist.Distance[("P3", "P2")]["Heavy Duty Truck"]
    )
