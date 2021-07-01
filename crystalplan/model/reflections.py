"""Module defining the Reflection object.
"""

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id$

#--- General Imports ---
import numpy as np

#--- Model Imports ---
from crystalplan.model.numpy_utils import column, vector_length

#==================================================================
#==================================================================
#==================================================================
class Reflection():
    """The Reflection class holds data relevant to a single diffraction
    peak.
    """

    #------------------------------------------------------------
    def __init__(self, hkl, q_vector):
        """Constructor.

        Parameters:
            hkl: tuple of (h,k,l), the indices of the reflection in the reciprocal lattice system.
                Normally will be integer, but float would work too.
            q_vector: vector containing the corresponding q-vector for this
                reflection. This q-vector is in the coordinates of the reciprocal lattice.
        """
        #h,k,l coordinates of the reflection
        (self.h, self.k, self.l) = hkl
        #Save as tuple too
        self.hkl = hkl
        #And the pre-calculated q-vector
        self.q_vector = q_vector

        #List holds the predicted measurements.
        #   value: a list of tuples.
        #       each tuple holds  (poscov_id, detector_num, horizontal, vertical, wavelength, distance)
        self.measurements = list()

        #List holds the actual, loaded measurements.
        #   value: a list of ReflectionRealMeasurement objects
        self.real_measurements = list()

        #Divergence (half-width) in radians of the scattered beam
        self.divergence = 0.0

        #Is the reflection a 'primary' one, e.g. in the simplest half- or quarter-sphere
        self.is_primary = False

        #Link to the actual primary reflection, if this is a secondary one.
        self.primary = None

        #List of equivalent reflections (from symmetry); only set for primary reflections.
        #   Includes the container object (aka. I am an equivalent of myself)
        self.equivalent = []

        #This is a temp. value used in a calculation
        self.considered = False

        #List of float measurement values (ranging normally from 0.0 to 1.0)
        #   used for adjusted coverage statistics taking into account
        #   edges, for example
        self.measurement_adjusted_value = None

        #List of real measurements. Loaded from ISAW.
        self.real_measurements = []


    #----------------------------------------------------
    def __str__(self):
        """Return an informal string representing the reflection."""
        s = "Reflection at hkl " + str(self.hkl) + "; is %sprimary; q-vector " % ['not ',''][self.is_primary] + str(self.q_vector.flatten()) + "\n"
        s += "    Measurements: " + str(self.measurements)
        return s

    #----------------------------------------------------
    def get_q_norm(self):
        """Return the norm of the q-vector corresponding to this hkl"""
        return vector_length(self.q_vector)

    #----------------------------------------------------
    def get_d_spacing(self):
        """Return the d-spacing corresponding to this hkl"""
        return 1 / (vector_length(self.q_vector) / (2*np.pi))

    #----------------------------------------------------
    def get_all_measurements(self):
        """Returns all measurements, including those from equivalent reflections."""
        out = self.measurements
        for refl in self.equivalent:
            out += refl.measurements
        return out

    #----------------------------------------------------
    def add_measurement(self, poscov_id, detector_num, horizontal, vertical, wavelength, distance):
        """Saves a measurement to the list.

        Parameters:
            poscov_id: id of the PositionCoverage object
            detector_num: number of the detector (0-based array).
            horizontal: horizontal position in the detector coordinates (in mm)
            vertical: vertical position in the detector coordinates (in mm)
            wavelength: wavelength detected (in Angstroms)
            distance: distance between sample and spot on detector
        """
        #Add the tuple of data to the list
        self.measurements.append( (poscov_id, detector_num, horizontal, vertical, wavelength, distance) )

    #----------------------------------------------------
    def times_measured(self, position_ids=None, add_equivalent_ones=False):
        """Return how many times this peak was measured succesfully.
        Parameters:
            position_ids: list of position IDs to consider.
                Set to None to use all of them.
            add_equivalent_ones: add up the times measured of all
                the equivalent reflections too.
        """
        if position_ids is None:
            if add_equivalent_ones:
                num = 0
                for refl in self.equivalent:
                    num += len(refl.measurements)
                return num
            else:
                return len(self.measurements)
        else:
            #Count the matching ones
            num = 0
            if add_equivalent_ones:
                for refl in self.equivalent:
                    for data in refl.measurements:
                        if data[0] in position_ids:
                            num += 1
            else:
                for data in self.measurements:
                    if data[0] in position_ids:
                        num += 1
            return num

    #----------------------------------------------------
    def times_real_measured(self, threshold=-1.0, add_equivalent_ones=False):
        """Return the # of times the peak was really measured.

        Parameters:
            threshold: I / sigI has to be higher than this value in
                order for the peak to be considered "measured"; i.e.
                sufficient signal-to-noise.
            add_equivalent_ones: add up the times measured of all
                the equivalent reflections too."""
        total = 0
        if add_equivalent_ones:
            myreflist = self.equivalent
        else:
            myreflist = [self]
            
        #Go through all the equivalent reflections
        for ref in myreflist:
            #@type rrm ReflectionRealMeasurement
            for rrm in ref.real_measurements:
                if not rrm is None:
                    if threshold <= 0:
                        #A zero or lower threshold = take all comers
                        total += 1
                    else:
                        #Check the I/sigI value.
                        #Avoid divide by 0
                        if (rrm.sigI > 1e-8):
                            if (rrm.integrated / rrm.sigI) > threshold:
                                total += 1

        return total



#==================================================================
#==================================================================
#==================================================================
class ReflectionMeasurement():
    """The ReflectionMeasurement class is used to show data about
    a single predicted measurement of a single reflection.
    It is not saved in the Reflection class (to save memory), but is
    re-generated when the GUI wants it.
    """

    #-------------------------------------------------------------------------------
    def __init__(self, refl, measurement_num, divergence_deg=0.0):
        """Create the object.

        Parameters:
            refl: Parent reflection object
            measurement_num: which entry in the list of refl.measurements?
            divergence_deg: half-width of the beam divergence in degreens
        """
        self.refl = refl
        if refl is None:
            self.measurement_num = -1
            #Extract the components of the measurement
            (self.poscov_id, self.detector_num, self.horizontal, self.vertical,
                self.wavelength, self.distance) \
                = (0, 0, 0, 0, 0, 0)
        else:
            self.measurement_num = measurement_num
            #Extract the components of the measurement
            (self.poscov_id, self.detector_num, self.horizontal, self.vertical,
                self.wavelength, self.distance) \
                = refl.measurements[measurement_num]
        
        #Now calculate the widths of the peak on the detector
        self.peak_width = self.calculate_peak_width(self.distance, divergence_deg)

#        (self.horizontal_delta, self.vertical_delta, self.wavelength_delta) = \
#            experiment.exp.calculate_peak_width(refl.hkl, delta_hkl)

    #-------------------------------------------------------------------------------
    def make_sample_orientation_string(self):
        """Return a friendly string of the sample orientation angles."""
        from . import instrument
        # @type poscov: PositionCoverage
        for poscov in instrument.inst.positions:
            if id(poscov)==self.poscov_id:
                return instrument.inst.make_angles_string( poscov.angles )
        return ""

    #-------------------------------------------------------------------------------
    def calculate_peak_width(self, distance, divergence_deg):
        """Calculate the width(radius) on a detector plate of a single peak, given a distance and a divergence.

        Parameters:
            distance: distance between sample and detector, usually in mm.
            divergence_deg: half-width of scattered beam divergence in degrees.

        Returns:
            width: half-width on the detector face, same units as distance
        """
        div = np.deg2rad(divergence_deg)
        multiplier = np.abs(np.tan(div))
        if multiplier > 10:
            return 10*distance
        else:
            return distance * multiplier
    


#==================================================================
#==================================================================
#==================================================================
class ReflectionRealMeasurement(ReflectionMeasurement):
    """Class holds info about a real peak measurement (loaded from an peaks or integrate file
    produced by ISAW)."""
    def __init__(self):
        """Constructor."""
        #The phi,chi,omega angles, in radians.
        self.angles = []
        # Detector number, AKA index in the instrument.detectors list.
        self.detector_num = 0
        self.wavelength = 0
        self.distance = 0
        #Integrated peak
        self.integrated = 0
        #Sigma I (error on intensity)
        self.sigI = 1.0
        #This won't be used
        self.peak_width = 0
        self.measurement_num = 0
        #Position
        self.horizontal = 0
        self.vertical = 0

    def make_sample_orientation_string(self):
        """Return a friendly string of the sample orientation angles."""
        if len(self.angles) >= 3:
            (phi, chi, omega) = np.rad2deg(self.angles)
            return "%.1f, %.1f, %.1f" % (phi, chi, omega)
        else:
            return ""
        
#================================================================================
#============================ UNIT TESTING ======================================
#================================================================================
import unittest

#==================================================================
class TestReflection(unittest.TestCase):
    """Unit test for the FlatDetector, checks what angles hit this detector"""
    #----------------------------------------------------
    def setUp(self):
        hkl = column([1.0,2,3])
        q_vector = 1.0/hkl
        self.ref = Reflection(hkl, q_vector)

    def test_constructor(self):
        """Reflection->Test the constructor"""
        ref = self.ref
        assert ref.h == 1
        assert ref.k == 2
        assert ref.l == 3
        assert np.all(ref.hkl == column([1,2,3]))
        assert np.allclose(ref.q_vector, column([1.0, 0.5, 1.0/3])), "q-vector was set to %s" % ref.q_vector
        assert isinstance(ref.measurements, list), "Made a list."
        assert len(ref.measurements) == 0, "No items in list."

#    def test_q_vector(self):
#        """Reflection->Q-vector calculation."""
#        rec = np.identity(3)
#        rec[1,0] = 1.0 #a_star_y = 1
#        ref = Reflection((1,2,3), rec)
#        assert np.all(ref.q_vector == column([1,3,3])), "q-vector was calculated"

    def test_add_measurement(self):
        "Reflection->add_measurement()"
        ref = self.ref
        ref.add_measurement(670, 5, 12.5, 32.3, 2.45, 400)
        assert len(ref.measurements) == 1, "One item in list."
        assert ref.measurements[0] == (670, 5, 12.5, 32.3, 2.45, 400), "Data tuple saved well."
        ref.add_measurement(223, 8, 13.5, 1.3, 3.45, 400)
        assert len(ref.measurements) == 2, "Two items in list."
        assert ref.measurements[1] == (223, 8, 13.5, 1.3, 3.45, 400), "Data tuple #2 saved well."
        assert ref.times_measured() == 2, "times_measured() works."
        


#==================================================================
if __name__ == "__main__":
    unittest.main()



