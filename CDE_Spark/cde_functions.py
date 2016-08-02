# import collections
# import os
# import re
#
# import numpy as np
# from scipy.stats import norm
# from sympathy.platform.exceptions import sywarn
#
# from sympathy.api import adaf_wrapper, table_wrapper
#
#
# class StoreFilter(table_wrapper.TableWrapper):
#     def execute(self):
#         filter_text = self.in_table.get_column_attributes('filter')['filter']
#         self.out_table.set_column_from_array('DATASET_filter',
#                                              np.array([filter_text]))
#
#
# class StoreEnableCalculation(table_wrapper.TableWrapper):
#     def execute(self):
#         calc_text = self.in_table.get_column_attributes(
#             'colnames')['calculation']
#         self.out_table.set_column_from_array('DATASET_filter',
#                                              np.array([calc_text]))
#
#
# class FilenameFieldsToMetadata(table_wrapper. TableWrapper):
#     def execute(self):
#         filepath_no_extension = os.path.basename(
#             self.in_table.get_column_to_array('filename')[0])
#
#         for nr, field in enumerate(filepath_no_extension.split('_')):
#             self.out_table.set_column_from_array(
#                 'FILENAME_field_{}'.format(nr), np.array([field]))
#
#
# class CreateFilterLogTable(table_wrapper.TableWrapper):
#     def execute(self):
#         filename_array = self.in_table.get_column_to_array('MDF_filename')
#         filter_text = self.in_table.get_column_to_array('DATASET_filter')[0]
#         output_path = self.in_table.get_column_to_array(
#             'DATASET_Output_Path')[0]
#
#         # data_source = os.path.dirname(filename_array[0])
#         # filter_log_file = os.path.join(data_source, 'FilterInfo.txt')
#
#         log_list = ['Selected Meta Filter:']
#         log_list.extend(filter_text.split(' & '))
#         log_list.extend([' **********************************'])
#         log_list.extend(['Running CDE for files:'])
#         log_list.extend([os.path.basename(filepath)
#                         for filepath in filename_array])
#
#         self.out_table.set_column_from_array(
#             'FilterInfo', np.array(log_list))
#         self.out_table.set_name(
#             os.path.join(output_path, 'FilterInfo'))
#
#
# class FillConfigGaps(table_wrapper.TableWrapper):
#     types_and_gaps = {
#         'U': {'gap': '',
#               'unknown': u'<unknown>'}}
#
#     def execute(self):
#         for column in self.in_table.column_names():
#             data = self.in_table.get_column_to_array(column)
#             idxs = []
#             if data.dtype.kind in self.types_and_gaps:
#                 idxs = np.flatnonzero(
#                     data == self.types_and_gaps[data.dtype.kind]['gap'])
#
#             if len(idxs) > 0:
#                 # If array starts with a gap we fill it with the unknown value
#                 # for this dtype.
#                 if idxs[0] == 0:
#                     unknown = self.types_and_gaps[data.dtype.kind]['unknown']
#
#                     # If the unknown string is longer that what can fit into
#                     # the dtype of the data we need to create a new array which
#                     # can take longer strings.
#                     if data.dtype.kind in ('U', 'S'):
#                         old_max_length = max([len(s) for s in data])
#                         new_max_length = max(old_max_length, len(unknown))
#                         if new_max_length > old_max_length:
#                             new_dtype = '{}{}'.format(
#                                 data.dtype.kind, new_max_length)
#                             data = data.astype(new_dtype)
#
#                     data[0] = unknown
#                     idxs = idxs[1:]
#
#                 # Go through all values and fill all gaps with the latest
#                 # preceding value.
#                 for idx in idxs:
#                     data[idx] = data[idx - 1]
#
#                 self.out_table.set_column_from_array(
#                     column, data, self.in_table.get_column_attributes(column))
#
#
# class ExtractVIN(adaf_wrapper.ADAFWrapper):
#     def execute(self):
#         def extract_vin_number(vin_columns, zero_index=True):
#             vin_characters = [
#                 (int(re.search('\[(\d+)\]', elem).groups()[0]),
#                  chr(self.in_adaf.ts[elem].y[0]))
#                 for elem in vin_columns if bool(re.search('\[(\d+)\]', elem))]
#
#             vin_list = [u'?'] * 17
#             for index, value in vin_characters:
#                 if not zero_index:
#                     index -= 1
#                 vin_list[index] = unicode(value)
#
#             vin_number = ''.join(vin_list)
#             return vin_number
#
#         vin_column_list = [
#             elem for elem in self.in_adaf.ts.keys()
#             if re.match(r'^UAccAppl_numTestCDVIN', elem)]
#         if vin_column_list:
#             vin_number = extract_vin_number(vin_column_list)
#         else:
#             vin_column_list = [
#                 elem for elem in self.in_adaf.ts.keys()
#                 if re.match(r'^Scn_GP_VI', elem)]
#             vin_number = extract_vin_number(vin_column_list, zero_index=False)
#
#         self.out_adaf.meta.create_column('VIN_Number', np.array([vin_number]))
#
#
# class DataVinPattern(table_wrapper.TableWrapper):
#     def execute(self):
#         patterns = []
#         for data_vin in np.unique(
#                 self.in_table.get_column_to_array('VIN_Number')):
#             pattern_txt = ','.join([
#                 str(idx) for idx, char in enumerate(data_vin) if char == '?'])
#             if pattern_txt not in patterns:
#                 patterns.append(pattern_txt)
#
#         self.out_table.set_column_from_array(
#             'VIN_Patterns', np.array(patterns))
#
#
# class ConvertVehicleVin(table_wrapper.TableWrapper):
#     def execute(self):
#         pattern_idx = (
#             self.extra_table.get_column_to_array('VIN_Patterns')[0].split(','))
#         converted_vins = []
#         vehicle_vins = self.in_table.get_column_to_array('VIN')
#         for vehicle_vin in vehicle_vins:
#             vin_list = list(vehicle_vin)
#             for idx in pattern_idx:
#                 vin_list[int(idx)] = '?'
#             converted_vins.append(''.join(vin_list))
#
#         if len(np.unique(vehicle_vins)) != len(np.unique(converted_vins)):
#             sywarn(
#                 'Two or more VIN numbers are converted to the same pattern!')
#
#         self.out_table.set_column_from_array(
#             'Reduced_VIN', np.array(converted_vins))
#
#
# class StoreRasterName(adaf_wrapper.ADAFWrapper):
#     def execute(self):
#         system_names = self.in_adaf.sys.keys()
#         if system_names:
#             first_system_name = system_names[0]
#             first_system = self.in_adaf.sys[first_system_name]
#             raster_names = first_system.keys()
#             if raster_names:
#                 first_raster_name = raster_names[0]
#                 self.out_adaf.meta.create_column(
#                     'DATASET_raster', np.array([first_raster_name]))
#
#
# class ChangeSelectedRasterName(adaf_wrapper.ADAFWrapper):
#     def copy_group(self, source_group, target_group):
#         """Copy a group from source to target."""
#         for signal_name, signal in source_group.items():
#             data_array = signal.value()
#             target_group.create_column(
#                 name=signal_name, data=data_array,
#                 attributes=dict(signal.attr.items()))
#
#     def execute(self):
#         system_names = self.in_adaf.sys.keys()
#         if system_names:
#             first_system_name = system_names[0]
#             first_system = self.in_adaf.sys[first_system_name]
#             raster_names = first_system.keys()
#             if raster_names:
#                 first_raster_name = raster_names[0]
#                 self.copy_group(self.in_adaf.meta, self.out_adaf.meta)
#                 self.copy_group(self.in_adaf.res, self.out_adaf.res)
#                 self.out_adaf.sys.create('Resampled system').copy(
#                     first_raster_name, self.in_adaf.sys[first_system_name],
#                     'Resampled raster')
#
#
# class SetSourceIDs(adaf_wrapper.ADAFWrapper):
#     def execute(self):
#         self.out_adaf.set_source_id("data")
#
#
# class RenameCrankAngleRaster(adaf_wrapper.ADAFWrapper):
#     """
#     Tries to find a raster that seems to be segment synchronous. If it finds at
#     least one such raster rename it to CRANK_ANGLE_INTERPOLATION_TARGET,
#     otherwise do nothing.
#     """
#     def execute(self):
#         # These are the names that are accepted as segment synchronous rasters.
#         crank_angle_raster_names = ['segment synchronous', 'TDC', 'BaseCrank']
#
#         for system_name, orig_system in self.in_adaf.sys.items():
#             new_system = self.out_adaf.sys[system_name]
#             for raster_name, orig_raster in orig_system.items():
#                 if any([rname in orig_raster.attr.get_or_empty('comment')
#                         for rname in crank_angle_raster_names]):
#                     new_raster = new_system.create(
#                         'CRANK_ANGLE_INTERPOLATION_TARGET')
#                     new_raster.from_table(
#                         orig_raster.to_table('__unique_basis_name__'),
#                         '__unique_basis_name__')
#                     break
#
#
# class AddETKC(adaf_wrapper.ADAFWrapper):
#     def execute(self):
#         spec = self.extra_table
#         dts = spec.get_column_to_array('sample_rate')
#         to_tbs = spec.get_column_to_array('basis_signal')
#         signals = spec.get_column_to_array('input_headers')
#
#         new_signals = []
#         for i, (dt, to_tb, signal) in enumerate(zip(dts, to_tbs, signals)):
#             pattern = signal + r'(\\ETKC:[0-9]+)?$'
#             filtered_ts = filter(
#                 re.compile(pattern).match, self.in_adaf.ts.keys())
#             if not filtered_ts:
#                 sywarn("Missing signal: {}".format(signal))
#                 continue
#             elif len(filtered_ts) != 1:
#                 print "Multiple matches for {}, choosing first one".format(
#                     pattern)
#             new_signals.append(filtered_ts[0])
#         self.out_adaf.meta.create_column(
#             'input_headers', np.array(new_signals))
#
#         self.out_adaf.meta.create_column(
#             'sample_rate', spec.get_column_to_array('sample_rate'))
#         self.out_adaf.meta.create_column(
#             'basis_signal', spec.get_column_to_array('basis_signal'))
#
#
# class RemoveETKC(adaf_wrapper.ADAFWrapper):
#     def execute(self):
#         self.out_adaf.meta.from_table(self.in_adaf.meta.to_table())
#         self.out_adaf.res.from_table(self.in_adaf.res.to_table())
#         self.out_adaf.set_source_id(self.in_adaf.source_id())
#
#         for system_name, orig_system in self.in_adaf.sys.items():
#             new_system = self.out_adaf.sys.create(system_name)
#             for raster_name, orig_raster in orig_system.items():
#                 new_raster = new_system.create(raster_name)
#                 new_raster.create_basis(
#                     orig_raster.basis_column().value(),
#                     dict(orig_raster.basis_column().attr.items()))
#                 new_raster.attr.update(orig_raster.attr)
#                 for signal_name, orig_signal in orig_raster.items():
#                     new_signal_name = re.sub(
#                         r"\\ETKC:[0-9]+", r"", signal_name)
#                     s = orig_raster[signal_name]
#                     new_raster.create_signal(
#                         new_signal_name, s.y, s.get_attributes())
#
#
# class FitNormalDistribution(adaf_wrapper.ADAFWrapper):
#     def execute(self):
#         from scipy.stats import probplot
#         x_min, x_max = -1, 3
#
#         signal_name = self.extra_table.get_column_to_array('signal_name')[0]
#         signal = self.in_adaf.sys[
#             "Resampled system"]["Resampled raster"][signal_name].y
#         plot_info_system = self.out_adaf.sys.create("Plot info")
#
#         # Continuous version of fitted pdf and cdf
#         mean, std = norm.fit(signal)
#         x = np.linspace(x_min, x_max, 1000)
#         pdf = norm.pdf(x, mean, std)
#         cdf = norm.cdf(x, mean, std)
#         dist_raster = plot_info_system.create("Distribution")
#         dist_raster.create_basis(x)
#         dist_raster.create_signal('pdf', pdf)
#         dist_raster.create_signal('cdf', cdf)
#
#         # Data for probability plot
#         # TODO: WRONG ORDER FOR OSR AND OSM!
#         ((osr, osm), (slope, intercept, r)) = probplot(signal)
#         prob_plot_raster = plot_info_system.create("Probplot")
#         prob_plot_raster.create_basis(osr)
#         prob_plot_raster.create_signal("osm", osm)
#         prob_dist_raster = plot_info_system.create("Probplot_dist")
#         x = np.array([osr[0], osr[-1]])
#         prob_dist_raster.create_basis(x)
#         prob_dist_raster.create_signal("y", slope * x + intercept)
#
#         # Fault limits
#         prob_dist_raster = plot_info_system.create("Fault limits")
#         fl = [0.3]
#         prob_dist_raster.create_basis(np.arange(len(fl)))
#         prob_dist_raster.create_signal("Fault limits", np.array(fl))
#         prob_dist_raster.create_signal("cdf", norm.cdf(fl, mean, std))
#
#         # Desc stats
#         desc_stats = collections.OrderedDict((
#             ('samples', signal.size),
#             ('mean', signal.mean()),
#             ('std', signal.std()),
#             ('x_min', signal.min()),
#             ('x_max', signal.max()),
#             ('x_1', np.percentile(signal, 1)),
#             ('x_99', np.percentile(signal, 99))))
#         desc_stat_text = u''
#         for k, v in desc_stats.items():
#             desc_stat_text += u'{}: {}<br>'.format(k, v)
#         self.out_adaf.meta.create_column(
#             "DATASET_extra_text",
#             np.array([desc_stat_text] * self.in_adaf.meta.number_of_rows()))
#
#
# if __name__ == "__main__":
#     from sympathy.api import adaf
#     input_filename = r"/home/freidrichen/jobb/debug/fx/input_adaf.sydata"
#
#     with adaf.File(filename=input_filename, mode='r') as input_file:
#         output_file = adaf.File(source=input_file)
#         FitNormalDistribution(input_file, output_file).execute()
