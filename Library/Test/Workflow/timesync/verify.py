import numpy as np

from sympathy.api import adaf_wrapper
from sympathy.api.exceptions import SyNodeError


class VerifyGoodSync(adaf_wrapper.ADAFWrapper):
    """
    Verify that the sync was performed and that the offset was correct to
    within 1 second.
    """

    def execute(self):
        assert(self.in_adaf.meta['SYNC_PERFORMED_SYSTEM1_SYSTEM0'].value()[0] == True)

        # Check that the offset has been calculated correctly. Correct offset
        # is in the region of 80.8 seconds. Plus/minus half a second is also
        # considered correct.
        if self.in_adaf.meta['SYNC_OFFSET_SYSTEM1_SYSTEM0'].value().dtype.kind == 'm':
            timeunit = np.timedelta64(1000000, 'us')  # 1 second with microsecond resolution
        else:
            timeunit = 1
        assert(80.3*timeunit <
               self.in_adaf.meta['SYNC_OFFSET_SYSTEM1_SYSTEM0'].value()[0] <=
               81.3*timeunit)

        # Check that the offset has been applied.
        assert(self.in_adaf.meta['SYNC_OFFSET_SYSTEM1_SYSTEM0'].value()[0] ==
                (self.in_adaf.sys['system0']['raster']['y'].t[0] -
                 self.in_adaf.sys['system1']['raster']['ref_y'].t[0]))


class VerifyFailedSync(adaf_wrapper.ADAFWrapper):
    """
    Verify that the sync has reported its failure correctly in the meta data.
    """

    def execute(self):
        assert(self.in_adaf.meta['SYNC_PERFORMED_SYSTEM1_SYSTEM2'].value()[0] == False)

        # A failed sync should always have offset 0.
        assert(self.in_adaf.meta['SYNC_OFFSET_SYSTEM1_SYSTEM2'].value()[0] == 0)
