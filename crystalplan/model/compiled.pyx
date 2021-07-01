#cython: boundscheck=False, wraparound=False, nonecheck=False, cdivision=True
#cython: language_level=3

import numpy as np
cimport numpy as np

from cython.parallel import prange

cimport cython

from libc.math cimport M_PI, sin, cos, acos, atan2, fabs, round, sqrt

ctypedef double (*f_type)(double, double, double, double[:])

def init_vol_symm_map(double [:,:] B, 
                      double [:,:] invB, 
                      long [:,:] symm, 
                      double qres, 
                      double qlim, 
                      Py_ssize_t n, 
                      Py_ssize_t order, 
                      double [:,:,:] table):
    
    cdef Py_ssize_t ix, iy, iz
    cdef Py_ssize_t eix, eiy, eiz, eindex
    cdef Py_ssize_t index, rd
    cdef double qx, qy, qz
    cdef double eqx, eqy, eqz
    cdef double h, k, l
    cdef double eh, ek, el
    
    for ix in range(n):
        qx = ix*qres - qlim
        for iy in range(n):
            qy = iy*qres - qlim
            for iz in range(n):
                qz = iz*qres - qlim
                index = iz + iy*n + ix*n*n
                # Ok, now we matrix multiply invB.hkl to get all the HKLs as a column array
                h = qx * invB[0,0] + qy * invB[0,1] + qz * invB[0,2]
                k = qx * invB[1,0] + qy * invB[1,1] + qz * invB[1,2]
                l = qx * invB[2,0] + qy * invB[2,1] + qz * invB[2,2]

                # Now go through each equivalency table.
                for rd in range(order):
                    # Do TABLE.hkl to find a new equivalent hkl
                    eh = h * table[rd, 0,0] + k * table[rd, 0,1] + l * table[rd, 0,2]
                    ek = h * table[rd, 1,0] + k * table[rd, 1,1] + l * table[rd, 1,2]
                    el = h * table[rd, 2,0] + k * table[rd, 2,1] + l * table[rd, 2,2]
                    # Now, matrix mult B . equiv_hkl to get the other q vector
                    eqx = eh * B[0,0] + ek * B[0,1] + el * B[0,2]
                    eqy = eh * B[1,0] + ek * B[1,1] + el * B[1,2]
                    eqz = eh * B[2,0] + ek * B[2,1] + el * B[2,2]

                    # Ok, now you have to find the index into QSPACE
                    eix = int( round( (eqx+qlim)/qres ) )
                    if ((eix >= n) or (eix < 0)):
                        eix = -1
                    eiy = int( round( (eqy+qlim)/qres ) )
                    if ((eiy >= n) or (eiy < 0)):
                        eiy = -1
                    eiz = int( round( (eqz+qlim)/qres ) )
                    if ((eiz >= n) or (eiz < 0)):
                        eiz = -1

                    if ((eix < 0) or (eiy < 0) or (eiz < 0)):
                        # One of the indices was out of bounds.
                        # Put this marker to mean NO EQUIVALENT
                        symm[index, rd] = -1
                    else:
                        # No problem!, Now I put it in there
                        eindex = eiz + eiy*n + eix*n*n
                        # This pixel (index) has this equivalent pixel index (eindex) for this order transform ord.
                        symm[index, rd] = eindex

def app_vol_symm(double[:] old_q, 
                 double[:] qspace_flat, 
                 Py_ssize_t numpix, 
                 Py_ssize_t order, 
                 long [:,:] symm):
    
    cdef Py_ssize_t pix, rd, index
    
    for pix in range(numpix):
        # Go through each pixel
        for rd in range(order):
            # Now go through each equivalent q.
            index = symm[pix, rd]
            if (index >= 0):
                # Valid index.
                qspace_flat[pix] += old_q[index]
                # printf("%d\\n", index)
             
def calc_cov_stats(double [:] qspace, 
                   double [:] qspace_radius, 
                   double q_step, 
                   double qlim, 
                   double [:] total_points, 
                   Py_ssize_t qspace_size, 
                   Py_ssize_t num, 
                   double [:] covered_points0, 
                   double [:] covered_points1, 
                   double [:] covered_points2, 
                   double [:] covered_points3):
    
    cdef Py_ssize_t i, j
    cdef Py_ssize_t layer
    cdef Py_ssize_t val
    cdef Py_ssize_t overall_points = 0
    cdef Py_ssize_t overall_covered_points = 0
    cdef Py_ssize_t overall_redundant_points = 0
    
    for i in range(qspace_size):
        # Coverage value at this points
        val = int( qspace[i] )
        # Do the overall stats
        if (qspace_radius[i] < qlim):
            # But only within the sphere
            overall_points += 1
            if (val > 0):
                overall_covered_points += 1
                if (val > 1):
                    overall_redundant_points += 1
    
        # Which slice are we looking at?
        layer = int( qspace_radius[i] / q_step )
        if ((layer < num) and (layer >= 0)):
            total_points[layer] += 1
            if (val>0):
                covered_points0[layer] += 1
                if (val>1):
                    covered_points1[layer] += 1
                    if (val>2):
                        covered_points2[layer] += 1
                        if (val>3):
                            covered_points3[layer] += 1
    
    return overall_points, overall_covered_points, overall_redundant_points

cdef void _ang_fit_brute(Py_ssize_t [:] rot_angle_list, 
                         double [:] ending_vec, 
                         double [:,:] initial_rotation_matrix, 
                         double [:] fitnesses, 
                         double [:] chi_list, 
                         double [:] phi_list, 
                         double [:] omega_list,
                         f_type fitness_function,
                         double [:] angles):
    
    cdef double rot_angle
    cdef Py_ssize_t angle_num
    
    cdef double c, s
    
    cdef double x = ending_vec[0]
    cdef double y = ending_vec[1]
    cdef double z = ending_vec[2]
    
    cdef double [:,:] extra_rotation_matrix = np.zeros((3,3))
    cdef double [:,:] total_rot_matrix = np.zeros((3,3))
    
    cdef Py_ssize_t i, j, k
            
    cdef double ux, uy, uz
    cdef double vx, vy, vz
    cdef double nx, ny, nz
    
    cdef double fitness
    cdef double old_ph, phi
    cdef double old_chi, chi
    cdef double old_omega, omega
        
    for angle_num in range(rot_angle_list[0]):
        rot_angle = float( rot_angle_list[angle_num] )
        # printf("angle of %e\\n", rot_angle)
        #  --- Make the rotation matrix around the ending_vec ----
        c = cos(rot_angle)
        s = sin(rot_angle)

        extra_rotation_matrix[0,0] =  1 + (1-c)*(x*x-1)
        extra_rotation_matrix[0,1] = -z*s+(1-c)*x*y
        extra_rotation_matrix[0,2] =  y*s+(1-c)*x*z
        extra_rotation_matrix[1,0] =  z*s+(1-c)*x*y
        extra_rotation_matrix[1,1] =  1 + (1-c)*(y*y-1)
        extra_rotation_matrix[1,2] = -x*s+(1-c)*y*z
        extra_rotation_matrix[2,0] = -y*s+(1-c)*x*z
        extra_rotation_matrix[2,1] =  x*s+(1-c)*y*z
        extra_rotation_matrix[2,2] =  1 + (1-c)*(z*z-1)

        #  Do matrix multiplication

        for i in range(3):
            for j in range(3):
                total_rot_matrix[i,j] = 0
                for k in range(3):
                    total_rot_matrix[i,j] += extra_rotation_matrix[i,k] * initial_rotation_matrix[k,j]
                # printf("%f, ", total_rot_matrix[i][j])

        # -------- Now we find angles_from_rotation_matrix() -----------

        # Let's make 3 vectors describing XYZ after rotations
        ux = total_rot_matrix[0,0]
        uy = total_rot_matrix[1,0]
        uz = total_rot_matrix[2,0]
        vx = total_rot_matrix[0,1]
        vy = total_rot_matrix[1,1]
        vz = total_rot_matrix[2,1]
        nx = total_rot_matrix[0,2]
        ny = total_rot_matrix[1,2]
        nz = total_rot_matrix[2,2]

        # is v.y vertical?
        if (fabs(vy) < 1e-8):
            # Chi rotation is 0, so we just have a rotation about y
            chi = 0.0
            phi = atan2(nx, nz)
            omega = 0.0
        elif (fabs(vy+1) < 1e-8):
            # Chi rotation is 180 degrees
            chi = M_PI
            phi = -atan2(nx, nz)
            if (fabs(phi+M_PI) < 1e-8): 
                phi = M_PI
            omega = 0.0
        else:
            # General case
            phi = atan2(ny, uy)
            chi = acos(vy)
            omega = atan2(vz, -vx)

        old_phi = phi
        old_chi = chi
        old_omega = omega

        #  Try the original angles
        fitness = fitness_function(phi, chi, omega, angles)
        fitnesses[3*angle_num] = fitness
        phi_list[3*angle_num] = phi
        chi_list[3*angle_num] = chi
        omega_list[3*angle_num] = omega

        # Make angles closer to 0
        if (phi > M_PI):
            phi -= 2*M_PI
        if (chi > M_PI):
            chi -= 2*M_PI
        if (omega > M_PI):
            omega -= 2*M_PI
        if (phi < -M_PI):
            phi += 2*M_PI
        if (chi < -M_PI):
            chi += 2*M_PI
        if (omega < -M_PI):
            omega += 2*M_PI
            
        fitness = fitness_function(phi, chi, omega, angles)
        fitnesses[1+3*angle_num] = fitness
        phi_list[1+3*angle_num] = phi
        chi_list[1+3*angle_num] = chi
        omega_list[1+3*angle_num] = omega

        # (phi-pi, -chi, omega-pi) is always equivalent
        phi = old_phi-M_PI
        chi = -old_chi
        omega = old_omega-M_PI
        if (phi > M_PI): 
            phi -= 2*M_PI
        if (chi > M_PI): 
            chi -= 2*M_PI
        if (omega > M_PI): 
            omega -= 2*M_PI
        if (phi < -M_PI): 
            phi += 2*M_PI
        if (chi < -M_PI): 
            chi += 2*M_PI
        if (omega < -M_PI): 
            omega += 2*M_PI
            
        fitness = fitness_function(phi, chi, omega, angles)
        fitnesses[2+3*angle_num] = fitness
        phi_list[2+3*angle_num] = phi
        chi_list[2+3*angle_num] = chi
        omega_list[2+3*angle_num] = omega

cdef double fit_fun3(double phi, double chi, double omega, double [:] angles):
    
    cdef double phi_min = angles[0]
    cdef double phi_max = angles[1]
    cdef double chi_min = angles[2]
    cdef double chi_max = angles[3]
    cdef double omega_min = angles[4]
    cdef double omega_max = angles[5]

    cdef double phi_mid = (phi_min + phi_max) / 2
    cdef double chi_mid = (chi_min + chi_max) / 2
    cdef double omega_mid = (omega_min + omega_max) / 2

    cdef double fitness = fabs(chi - chi_mid) + fabs(omega - omega_mid) + fabs(phi - phi_mid)

    # Big penalties for being out of the range
    if (phi < phi_min):
        fitness += (phi_min - phi) * 1.0
    if (phi > phi_max):
        fitness += (phi - phi_max) * 1.0
    if (chi < chi_min):
        fitness += (chi_min - chi) * 1.0
    if (chi > chi_max):
        fitness += (chi - chi_max) * 1.0
    if (omega < omega_min):
        fitness += (omega_min - omega) * 1.0
    if (omega > omega_max):
        fitness += (omega - omega_max) * 1.0

    return fitness

cdef double fit_fun2(double phi, double chi, double omega, double [:] angles):

    cdef double phi_min = angles[0]
    cdef double phi_max = angles[1]

    cdef double chi_mid = angles[2]
    cdef double phi_mid = (phi_min + phi_max) / 2

    cdef double fitness = fabs(chi - chi_mid)*10.0 + fabs(phi - phi_mid)/10.0

    # Big penalties for being out of the range
    if (phi < phi_min): 
        fitness += (phi_min - phi) * 1.0
    if (phi > phi_max): 
        fitness += (phi - phi_max) * 1.0

    return fitness

cdef double fit_fun1(double phi, double chi, double omega):

    cdef double fitness = fabs(phi)
    
    return fitness
        
cdef double fit_fun_HB3A(double phi, double chi, double omega):
    
    cdef double center = 3.14159*25.0/180.0
    cdef double omegadiff = omega - center
    
    if (omegadiff < 0):
        omegadiff = -omegadiff
    
    return fabs(chi) + omegadiff + fabs(phi)/1000.0

cdef double fit_fun_VARY(double phi, double chi, double omega, double [:] angles):

    cdef double phi_min = angles[0]
    cdef double phi_max = angles[1]
    cdef double omega_min = angles[2]
    cdef double omega_max = angles[3]

    cdef double phi_mid = (phi_min + phi_max) / 2
    cdef double chi_mid = angles[4]
    cdef double omega_mid = (omega_min + omega_max) / 2

    cdef double fitness = fabs(chi - chi_mid)*10.0 + fabs(omega - omega_mid)/10.0 + fabs(phi - phi_mid)/10.0

    # Big penalties for being out of the range
    if (phi < phi_min):
        fitness += (phi_min - phi) * 1.0
    if (phi > phi_max):
        fitness += (phi - phi_max) * 1.0
    if (omega < omega_min):
        fitness += (omega_min - omega) * 1.0
    if (omega > omega_max):
        fitness += (omega - omega_max) * 1.0

    return fitness

def tot_coverage(Py_ssize_t number_of_ints, 
                 short [:,:,:] coverage, 
                 Py_ssize_t coverage_size, 
                 unsigned long mask1, 
                 unsigned long mask2, 
                 Py_ssize_t num_coverage, 
                 list coverage_list):
    
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t ix, iy, iz
    
    cdef Py_ssize_t Ncoverage0 = coverage.shape[0]
    cdef Py_ssize_t Ncoverage1 = coverage.shape[1]
    cdef Py_ssize_t Ncoverage2 = coverage.shape[2]

    cdef unsigned long [:,:,:,:,::1] each_coverage = np.zeros((Ncoverage0,Ncoverage2,Ncoverage2,number_of_ints,num_coverage), dtype=np.uint32)

    for j in range(num_coverage):
        for ix in range(Ncoverage0):
            for iy in range(Ncoverage1):
                for iz in range(Ncoverage2):
                    for k in range(number_of_ints):
                        each_coverage[ix,iy,iz,k,j] = coverage_list[j][ix,iy,iz,k]
    
    # for one_coverage in coverage_list:
    #     #By applying the mask and the >0 we take away any unwanted detectors.
    #     if number_of_ints==1:
    #         #coverage = coverage + ((one_coverage & mask) != 0)
    #         coverage += ((one_coverage[:,:,:,0] & mask1) != 0)
    #     else:
    #         coverage += (((one_coverage[:,:,:,0] & mask1) | (one_coverage[:,:,:,1] & mask2)) != 0)

    for j in range(num_coverage):
        
        for ix in range(Ncoverage0):

            for iy in range(Ncoverage1):

                for iz in range(Ncoverage2):

                    if (number_of_ints == 2):

                        # NOTE: This code assumes LSB-first ints.
                        if ((each_coverage[ix,iy,iz,0,j] and mask1) or (each_coverage[ix,iy,iz,1,j] and mask2)):

                            coverage[ix,iy,iz] += 1

                    else:

                        # Only 1 int
                        # Index into the coverage array
                        if (each_coverage[ix,iy,iz,0,j] and mask1):
                            coverage[ix,iy,iz] += 1
    
cpdef double det_coord(double [::1] base_point, 
                       double [::1] horizontal, 
                       double [::1] vertical, 
                       double [::1] normal, 
                       double [::1] h_out, 
                       double [::1] v_out, 
                       double [::1] wl_out, 
                       double [::1] distance_out, 
                       unsigned char [::1] hits_it, 
                       double [:,::1] beam, 
                       Py_ssize_t array_size, 
                       double n_dot_base, 
                       double height, 
                       double width, 
                       double wl_min, 
                       double wl_max):
        
    cdef double az, elev
    cdef double bx, by, bz
    cdef double x, y, z, temp
    cdef double h, v, d
    cdef double diff_x, diff_y, diff_z

    # some vars
    cdef double base_point_x = base_point[0]
    cdef double base_point_y = base_point[1]
    cdef double base_point_z = base_point[2]
    cdef double horizontal_x = horizontal[0]
    cdef double horizontal_y = horizontal[1]
    cdef double horizontal_z = horizontal[2]
    cdef double vertical_x = vertical[0]
    cdef double vertical_y = vertical[1]
    cdef double vertical_z = vertical[2]
    cdef double nx = normal[0]
    cdef double ny = normal[1]
    cdef double nz = normal[2]
    cdef double n_dot_base_f = float(n_dot_base)

    cdef Py_ssize_t i
    cdef Py_ssize_t error_count = 0
    cdef Py_ssize_t bad_beam = 0
    cdef double projection, beam_length, wavelength
    
    cdef double min = 1e-6
    cdef double NAN = np.nan

    for i in range(array_size):

        # Good beam, nice beam.
        bad_beam = 0

        # Non-normalized beam direction
        bx = beam[0,i]
        by = beam[1,i]
        bz = beam[2,i]

        # So we normalize it
        beam_length = sqrt(bx*bx + by*by + bz*bz)
        bx = bx/beam_length
        by = by/beam_length
        bz = bz/beam_length

        # Check if the wavelength is within range
        wavelength = 6.2831853071795862/beam_length

        # If there are any nan's in the beam direction, this next check will return false.
        if ((wavelength <= wl_max) and (wavelength >= wl_min)):

            # Wavelength in range! Keep going.

            # Make sure the beam points in the same direction as the detector, not opposite to it
            # project beam onto detector's base_point
            projection = (base_point_x*bx)+(base_point_y*by)+(base_point_z*bz)
            
            if (projection > 0):

                # beam points towards the detector

                # This beam coincides with the origin (0,0,0)
                # Therefore the line equation is x/bx = y/by = z/bz

                # Now we look for the intersection between the plane of normal nx,ny,nz and the given angle.

                # Threshold to avoid divide-by-zero
                min = 1e-6
                if ((fabs(bz) > min)): # and (fabs(nz) > min)):

                    z = n_dot_base_f / ((nx*bx)/bz + (ny*by)/bz + nz)
                    temp = (z / bz)
                    y = by * temp
                    x = bx * temp

                elif ((fabs(by) > min)): # and && (fabs(ny) > min))

                    y = n_dot_base_f / (nx*bx/by + ny + nz*bz/by)
                    temp = (y / by)
                    x = bx * temp
                    z = bz * temp

                elif ((fabs(bx) > min)): # and && (fabs(nx) > min))

                    x = n_dot_base_f / (nx + ny*by/bx + nz*bz/bx)
                    temp = (x / bx)
                    y = by * temp
                    z = bz * temp

                else:

                    # The scattered beam is 0,0,0
                    error_count += 1
                    bad_beam = 1
                    
            else:

                # The projection is <0
                # means the beam is opposite the detector. BAD BEAM! No cookie!
                bad_beam = 1

        else:

            # Wavelength is out of range. Can't measure it!
            bad_beam = 1

        if (bad_beam):

           # A bad beam means it does not hit, for sure.
            h_out[i] = NAN
            v_out[i] = NAN
            wl_out[i] = wavelength # This may be NAN too, for NAN inputs.
            hits_it[i] = 0

        else:

            # Valid beam calculation
            # Difference between this point and the base point (the center)
            diff_x = x - base_point_x
            diff_y = y - base_point_y
            diff_z = z - base_point_z

            # Project onto horizontal and vertical axes by doing a dot product
            h = diff_x*horizontal_x + diff_y*horizontal_y + diff_z*horizontal_z
            v = diff_x*vertical_x + diff_y*vertical_y + diff_z*vertical_z

            # Save to matrix
            h_out[i] = h
            v_out[i] = v

            # the scattered beam is 1/wl long.
            wl_out[i] = wavelength

            # What was the distance to the detector spot?
            distance_out[i] = sqrt(x*x + y*y + z*z)

            # And do we hit that detector?
            # Detector is square and our h,v coordinates are relative to the center of it.
            hits_it[i] = (v > -height/2) and (v < height/2) and (h > -width/2) and (h < width/2)

    return error_count