from sympathy.api import adaf
from remove_bad_signals import remove_bad_signals
from interpolate import interpolate

def process_dat_adaf(adaf_obj):
    remove_bad_signals(adaf_obj)
    new_adaf_obj = interpolate(adaf_obj)
    return new_adaf_obj
