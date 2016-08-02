    # def _add_timeseries(self):
    #     """Add timeseries and their timebasis to the data file."""
    #     rcounter = 0
    #
    #     # Create helper progress function
    #     set_partial_progress = lambda i: self.set_progress(
    #         100.0 * i / self.mdf.hdblock.number_of_data_groups)
    #
    #     # Loop over datagroups
    #     for i, dgblock in enumerate(self.mdf.hdblock.get_data_group_blocks()):
    #         cdict = OrderedDict()
    #         dblock = None
    #
    #         # Loop over channelgroup
    #         for cgblock in dgblock.get_channel_group_blocks():
    #             cdict = OrderedDict([(cnblock.get_signal_name(), cnblock)
    #                                  for cnblock in
    #                                  cgblock.get_channel_blocks()])
    #             clist = cdict.keys()
    #             dblock = dgblock.get_data_block()
    #
    #             if not dblock:
    #                 continue
    #
    #             bases = [cnblock for cnblock in cdict.values()
    #                      if (cnblock.channel_type ==
    #                          mdflib.Channel.Types.TIMECHANNEL)]
    #
    #             # Check raster type
    #             if len(bases) != 1:
    #                 sywarn("The group should have exactly one TIMECHANNEL")
    #             else:
    #                 cnblock = bases[0]
    #                 # Remove basis from channel list.
    #                 clist.remove(cnblock.get_signal_name())
    #
    #                 if not cnblock:
    #                     continue
    #                 # Sampling rate in ms
    #                 sampling_rate = cnblock.get_sampling_rate()
    #                 signaldata, signalattr = dblock.get_channel_signal(cnblock)
    #                 extra_attr = signalattr or {}
    #
    #                 # Create time raster
    #                 rcounter += 1
    #
    #                 if cnblock.conversion_formula != 0:
    #                     ccblock = cnblock.get_conversion_formula()
    #                     unit = ccblock.get_physical_unit()
    #                 else:
    #                     unit = 's'
    #                 unit = unit.decode(self.encoding)
    #                 # Add this raster to list of timerasters
    #                 raster = self.system.create(
    #                     'Group{COUNT}'.format(COUNT=rcounter))
    #
    #                 signaldescription = cnblock.get_signal_description()
    #                 signaldescription = signaldescription.decode(self.encoding)
    #
    #                 # Add basis to raster
    #                 txblock = cnblock.get_comment()
    #                 comment = txblock.get_text() if txblock else None
    #
    #                 raster.create_basis(signaldata, DictWithoutNone(
    #                     unit=unit,
    #                     description=signaldescription,
    #                     sampling_rate=sampling_rate,
    #                     comment=comment,
    #                     **{key: json.dumps(value) for key, value in
    #                        extra_attr.items()}))
    #
    #                 txblock = cgblock.get_comment_block()
    #                 comment = txblock.get_text() if txblock else None
    #
    #                 if comment:
    #                     raster.attr.set('comment', comment)
    #                 if self.reftime:
    #                     raster.attr.set('reference_time', self.reftime)
    #
    #                 # Loop over channels
    #                 for cname in clist:
    #
    #                     # Ignore channels with empty name
    #                     if not cname:
    #                         sywarn ('Ignoring channel with empty name')
    #                         continue
    #
    #                     # Get channel and extract needed information
    #                     cnblock = cdict[cname]
    #
    #                     # Replace problematic character: /
    #                     cname = cname.replace('/', '#')
    #                     signaldata, signalattr = dblock.get_channel_signal(
    #                         cnblock)
    #                     if signaldata.dtype.kind == 'S':
    #                         try:
    #                             signaldata = np.char.decode(
    #                                 signaldata, self.encoding)
    #                         except UnicodeDecodeError:
    #                             pass
    #                     extra_attr = signalattr or {}
    #                     desc = cnblock.get_signal_description()
    #                     desc = desc.decode(self.encoding)
    #                     if cnblock.conversion_formula != 0:
    #                         ccblock = cnblock.get_conversion_formula()
    #                         unit = ccblock.get_physical_unit()
    #                     else:
    #                         unit = "Unknown"
    #                     unit = unit.decode(self.encoding)
    #
    #                     txblock = cnblock.get_comment()
    #                     comment = (txblock.get_text().rstrip().decode(
    #                         self.encoding) if txblock else None)
    #                     raster.create_signal(cname,
    #                                          signaldata, DictWithoutNone(
    #                                              unit=unit,
    #                                              description=desc,
    #                                              sampling_rate=sampling_rate,
    #                                              comment=comment,
    #                                              **{key: json.dumps(value)
    #                                                 for key, value in
    #                                                 extra_attr.items()}))
    #
    #         set_partial_progress(i)
    #
    #     # HACK(alexander): If exist, move active calibration page to result
    #     try:
    #         # Safest way if names are changed
    #         acp_name = self.ddf.ts.keys_fnmatch('*ActiveCalibration*')[0]
    #         # Get first sample
    #         acp_0 = self.ddf.ts[acp_name][:][0]
    #         self.ddf.res.create_column(
    #             'ActiveCalibrationPage', [acp_0],
    #             {'description': 'First sample from ActiveCalibrationPage'})
    #     except Exception:
    #         pass
