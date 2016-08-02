import re
import numpy as np


def RemoveETKC(adaf_obj):
    for system_name, orig_system in adaf_obj.sys.items():
        for raster_name, orig_raster in orig_system.items():
            for signal_name, orig_signal in orig_raster.items():
                new_signal_name = re.sub(
                    r"\\ETKC:[0-9]+", r"", signal_name)
                if( new_signal_name == signal_name ):
                    continue
                s = orig_raster[signal_name]
                orig_raster.create_signal(
                    new_signal_name, s.y, s.get_attributes())
                orig_raster.delete_signal(signal_name)


def RenameCrankAngleRaster(adaf_obj):
    """
    Tries to find a raster that seems to be segment synchronous. If it finds at
    least one such raster rename it to CRANK_ANGLE_INTERPOLATION_TARGET,
    otherwise do nothing.
    """
    # These are the names that are accepted as segment synchronous rasters.
    crank_angle_raster_names = ['segment synchronous', 'TDC', 'BaseCrank']

    for system_name, orig_system in adaf_obj.sys.items():
        for raster_name, orig_raster in orig_system.items():
            if any([rname in orig_raster.attr.get_or_empty('comment')
                    for rname in crank_angle_raster_names]):
                new_raster = orig_system.create(
                    'CRANK_ANGLE_INTERPOLATION_TARGET')
                new_raster.from_table(
                    orig_raster.to_table('__unique_basis_name__'),
                    '__unique_basis_name__')
                del orig_system[raster_name]
                break


def ExtractVIN(adaf_obj):
    def extract_vin_number(vin_columns, zero_index=True):
        # vin_characters = []
        # for elem in vin_columns:
        #     if bool(re.search('\[(\d+)\]', elem)):
        #         i = int(re.search('\[(\d+)\]', elem).groups()[0])
        #         c = chr(adaf_obj.ts[elem].y[0])
        #         vin_characters.append((i, c))
        vin_characters = [
            (int(re.search('\[(\d+)\]', elem).groups()[0]),
             chr(np.array(adaf_obj.ts[elem].y)[0]))
            for elem in vin_columns if bool(re.search('\[(\d+)\]', elem))]

        vin_list = [u'?'] * 17
        for index, value in vin_characters:
            if not zero_index:
                index -= 1
            vin_list[index] = unicode(value)

        vin_number = ''.join(vin_list)
        return vin_number

    vin_column_list = [
        elem for elem in adaf_obj.ts.keys()
        if re.match(r'^UAccAppl_numTestCDVIN', elem)]
    if vin_column_list:
        vin_number = extract_vin_number(vin_column_list)
    else:
        vin_column_list = [
            elem for elem in adaf_obj.ts.keys()
            if re.match(r'^Scn_GP_VI', elem)]
        vin_number = extract_vin_number(vin_column_list, zero_index=False)

    adaf_obj.meta.create_column('VIN_Number', np.array([vin_number]))
