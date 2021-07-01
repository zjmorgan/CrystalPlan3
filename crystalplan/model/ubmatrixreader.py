""" ubmatrixreader: Program to read in a UB Matrix text file.
"""

# Author: Janik Zikovsky, zikovskyjl@ornl.gov
# Version: $Id$

#--- General Imports ---
import os.path
import sys
import numpy as np
import optparse

#--- Model Imports ---
from crystalplan.model import crystal_calc


#-----------------------------------------------------------------
def read_ISAW_ubmatrix_file(filename, verbose):
    """Open and read a UB matrix file produced by ISAW.

    Parameters:
        filename: string, path to the file to load
        verbose: more output

    Returns:
        lattice_lengths: tuple of 3 lattice dimensions in angstroms.
        lattice_angles: tuple of 3 lattice angles in degrees.
        ub_matrix: the UB matrix read from the file
        niggli: calculated niggli matrix
    """

    if not (os.path.exists(filename)):
        raise IOError("The file %s cannot be found" % filename)
        return None

    # Read the file.
    #try:
    if True:
        if verbose: print('Opening file', filename)
        f = open(filename)

        #Read the transposed UB matrix. 3x3, first 3 lines
        UBtransposed = np.zeros([0,3])

        for i in range(0, 3):
            s = f.readline()
            temp = np.fromstring(s, float, 3, ' ')
            UBtransposed = np.vstack((UBtransposed, temp))

        if verbose: print("Transposed UB matrix is:\n", UBtransposed)

        #Fourth line: is the unit cell which describes the smallest repeatable unit that can build up
        #the sample in three dimensions:  the first three numbers are a, b, c in Angstroms (10^-8cm)
        # followed by the three angles (in degrees) followed by the volume in Angstroms cubed.
        s = f.readline()
        temp = np.fromstring(s, float, 7, ' ')
        if verbose: print("Lattice parameters in file are (a,b,c, alpha,beta,gamma, volume):\n", temp)

        #Unit cell sizes in angstroms
        a = temp[0]
        b = temp[1]
        c = temp[2]
        #Angles
        alpha = temp[3]
        beta = temp[4]
        gamma = temp[5]

        #Calculate the niggli matrix
#        niggli = crystal_calc.make_niggli_matrix(a,b,c,alpha,beta,gamma)

        #Return params
        lattice_lengths = (a,b,c)
        lattice_angles = (alpha,beta,gamma)
        #Transpose the matrix
        ub_matrix = UBtransposed.transpose()
        #Convert from IPNS coordinate system to SNS:

        # The (ISAW UB) matrix is the Transpose of the UB Matrix. The UB matrix maps the column
        # vector (h,k,l ) to the column vector (q'x,q'y,q'z).
        # |Q'|=1/dspacing and its coordinates are a right-hand coordinate system where
        #  x is the beam direction and z is vertically upward.(IPNS convention)

        #First, we multiply by the missing 2 * pi
        ub_matrix =  2 * np.pi * ub_matrix

        #Make a copy
        ub_out = 1. * ub_matrix
        #Now we permute COLUMNS around to change the coordinate system
#        ub_out[:,2] = ub_matrix[:,0] #x gets put in z
#        ub_out[:,1] = ub_matrix[:,2] #z gets put in y
#        ub_out[:,0] = ub_matrix[:,1] #y gets put in x

        return (lattice_lengths, lattice_angles, ub_out)

    #Error checking here
    #except:
        print("Error reading UB matrix file:", sys.exc_info()[0])
    #finally:
        #Clean up in case of error.
        f.close()

    #There was an exception if we reached this point
    return None


#-----------------------------------------------------------------
def read_HFIR_ubmatrix_file(filename):
    """Open and read a UB matrix file produced by software at HFIR beamline HB3A.

    Parameters:
        filename: string, path to the file to load
        verbose: more output

    Returns:
        ub_matrix: the UB matrix read from the file
    """

    if not (os.path.exists(filename)):
        raise IOError("The file %s cannot be found" % filename)
        return None

    f = open(filename)

    #Read the UB matrix. 3x3, first 3 lines
    ub_matrix = np.zeros([0,3])

    for i in range(0, 3):
        s = f.readline()
        temp = np.fromstring(s, float, 3, ' ')
        ub_matrix = np.vstack((ub_matrix, temp))
        
    # First, we multiply by the missing 2 * pi
    ub_matrix =  2 * np.pi * ub_matrix
    
    # HFIR uses busing-levy 1967 convention:
    #    +Y = beam direction
    #    +Z = vertical axis
    #    +X = (find using right-handed coordinates)
    
    ub_out = ub_matrix
     
#    #Now we permute COLUMNS around to change the coordinate system
#    ub_out[:,2] = ub_matrix[:,0] #x gets put in z
#    ub_out[:,1] = ub_matrix[:,2] #z gets put in y
#    ub_out[:,0] = ub_matrix[:,1] #y gets put in x

#    #Now we permute COLUMNS around to change the coordinate system
#    ub_out[2,:] = ub_matrix[0,:] #x gets put in z
#    ub_out[1,:] = ub_matrix[2,:] #z gets put in y
#    ub_out[0,:] = ub_matrix[1,:] #y gets put in x
     
    
    f.close()

    return ub_out



#-----------------------------------------------------------------
def read_HFIR_lattice_parameters_file(filename):
    """Open and read a lattice parameters file produced by software at HFIR beamline HB3A.

    Parameters:
        filename: string, path to the file to load

    Returns:
        lattice_lengths: tuple of 3 lattice dimensions in angstroms.
        lattice_angles: tuple of 3 lattice angles in degrees.
    """
    if not (os.path.exists(filename)):
        raise IOError("The file %s cannot be found" % filename)
        return None

    f = open(filename)

    #Fourth line: is the unit cell which describes the smallest repeatable unit that can build up
    #the sample in three dimensions:  the first three numbers are a, b, c in Angstroms (10^-8cm)
    # followed by the three angles (in degrees) followed by the volume in Angstroms cubed.
    s = f.readline()
    temp = np.fromstring(s, float, 7, ' ')

    f.close()

    #Unit cell sizes in angstroms
    a = temp[0]
    b = temp[1]
    c = temp[2]
    #Angles
    alpha = temp[3]
    beta = temp[4]
    gamma = temp[5]

    #Return params
    lattice_lengths = (a,b,c)
    lattice_angles = (alpha,beta,gamma)

    # First, we multiply by the missing 2 * pi
    #ub_matrix =  2 * np.pi * ub_matrix

    return (lattice_lengths, lattice_angles)





#============================ MAIN CODE ==========================
if __name__ == "__main__":
    #Parse the command line arguments
    parser = optparse.OptionParser(usage="Usage: %prog [options] filename")
    parser.add_option("-v", "--verbose", action="store_true", default=False, help="verbose output.")
    (options, args) = parser.parse_args()

   #We need a single argument, the filename
    if len(args) != 1:
        parser.error("Please specify the filename!")
        parser.print_help()

    #Arguments were sufficient.
    filename = args[0]
    (lattice_lengths, lattice_angles, ub_matrix) = read_ISAW_ubmatrix_file(filename, options.verbose)

    #Perhaps format ouptput differently.
    print("Resulting ub_matrix Matrix is:\n", ub_matrix)

   

