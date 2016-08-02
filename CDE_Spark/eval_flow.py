import numpy as np
from cde_plot import distribution_plot_subsets

def add_flow_name(adaf_obj):
    adaf_obj.meta.create_column('DATASET_Workflow_name', np.array(["B_KatDiagnos"]))

def get_required_signals():
    return ['Exh_tSim1Fld_mp', 'OxiCat_mHCMonPas_mp', 'OxiCat_facHCCnvRat']

def get_selected_raster():
    return ['0.1']

def select_raster(adaf_obj, selected_rasters):
    """
    select the specific raster
    """
    matched_raster_name = ""
    for system_name, system in adaf_obj.sys.items():
        for raster_name, raster in system.items():
            if raster_name not in selected_rasters:
                del system[raster_name]
            else:
                matched_raster_name = raster_name
                # rename the selected raster
                new_raster = system.create('Resampled raster')
                new_raster.from_table(raster.to_table('__unique_basis_name__'),
                                      '__unique_basis_name__')
                del system[raster_name]

    # update the meta
    if matched_raster_name:
        adaf_obj.meta.create_column('DATASET_raster', np.array([matched_raster_name]))
        adaf_obj.meta.create_column('DATASET_sample_time', np.array([0.1000]))


def select_signals(adaf_obj, required_signals):
    """
    select the signals
    """
    for system_name, system in adaf_obj.sys.items():
        for raster_name, raster in system.items():
            for signal_name, signal in raster.items():
                if signal_name == "(Resampled raster)":
                    continue
                if signal_name not in required_signals:
                    raster.delete_signal(signal_name)


def select_raster_signals(subsets):
    selected_rasters = get_selected_raster()
    required_signals = get_required_signals()

    # rename the selected_rasters
    selected_rasters = ["Resampled raster {}".format(r) for r in selected_rasters]
    # select rasters
    for adaf_obj in subsets:
        select_raster(adaf_obj, selected_rasters)
    # select signals
    for adaf_obj in subsets:
        select_signals(adaf_obj, required_signals)
        adaf_obj.meta.create_column('used_aliases', np.array(['{}']))


def create_signals(subsets):
    """
    create "katDiag_Enable" signal
    """
    signal_name = 'katDiag_Enable'
    for adaf_obj in subsets:
        for system_name, system in adaf_obj.sys.items():
            for raster_name, raster in system.items():
                raster.create_signal(signal_name, np.array([False for i in xrange(raster.number_of_rows())]))
        adaf_obj.meta.create_column('missing_signals', np.array(['{}']))


def eval_flow(subsets, out_dir):
    for adaf_obj in subsets:
        add_flow_name(adaf_obj)
    select_raster_signals(subsets)
    create_signals(subsets)
    distribution_plot_subsets(subsets, out_dir)


def select_raster_signals_spark(adaf_obj):
    selected_rasters = get_selected_raster()
    required_signals = get_required_signals()

    # rename the selected_rasters
    selected_rasters = ["Resampled raster {}".format(r) for r in selected_rasters]
    # select rasters

    select_raster(adaf_obj, selected_rasters)
    # select signals

    select_signals(adaf_obj, required_signals)
    adaf_obj.meta.create_column('used_aliases', np.array(['{}']))

def create_signals_spark(adaf_obj):
    """
    create "katDiag_Enable" signal
    """
    signal_name = 'katDiag_Enable'

    for system_name, system in adaf_obj.sys.items():
        for raster_name, raster in system.items():
            raster.create_signal(signal_name, np.array([False for i in xrange(raster.number_of_rows())]))
    adaf_obj.meta.create_column('missing_signals', np.array(['{}']))

def eval_flow_spark(adaf_obj, out_dir):
    # for adaf_obj in subsets:
    #     add_flow_name(adaf_obj)
    select_raster_signals_spark(adaf_obj)
    create_signals_spark(adaf_obj)
    signal_name = "OxiCat_facHCCnvRat"
    #

    field0 =adaf_obj.meta["FILENAME_field_0"].value()[0]
    #(field0,time_series)
    return (field0,adaf_obj.ts[signal_name])


