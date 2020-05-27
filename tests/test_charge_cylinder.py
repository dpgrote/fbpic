# Copyright 2016, FBPIC contributors
# Authors: Remi Lehe, Manuel Kirchen
# License: 3-Clause-BSD-LBNL
"""
This test file is part of FB-PIC (Fourier-Bessel Particle-In-Cell).

It verifies the validity of the space charge field generated by a
cylinder of charge for different radii that can be smaller than a single
radial cell.

Usage :
from the top-level directory of FBPIC run
$ python tests/test_charge_cylinder.py
"""
from scipy.constants import c, e, epsilon_0
from fbpic.main import Simulation
from fbpic.fields.smoothing import BinomialSmoother
from fbpic.lpa_utils.bunch import get_space_charge_spect
import numpy as np

# Parameters
# ----------
show = True     # Whether to show the results to the user, or to
                # automatically determine if they are correct.

# The simulation box
Nz = 10         # Number of gridpoints along z
zmax = 10.e-6    # Right end of the simulation box (meters)
zmin = -10.e-6   # Left end of the simulation box (meters)
Nr = 20         # Number of gridpoints along r
rmax = 2.e-6    # Length of the box along r (meters)
Nm = 1           # Number of modes used

# The particles
p_zmin =-100.e-6  # Position of the beginning of the plasma (meters)
p_zmax = 100.e-6 # Position of the end of the plasma (meters)
p_rmin = 0.      # Minimal radial position of the plasma (meters)
p_rmax = 1.e-6   # Maximal radial position of the plasma (meters)
n_e = 4.e18*1.e6 # Density (electrons.meters^-3)
p_nz = 1        # Number of particles per cell along z
p_nr = 8        # Number of particles per cell along r
p_nt = 1        # Number of particles per cell along theta

# Filter currents
filter_currents = True

# Scaling of radius of charge cylinder
scales = [1.0, 0.5, 0.25, 0.1, 0.05, 0.025, 0.01]

# -------------
# Test function
# -------------

def test_charge_cylinder(show=False):
    "Function that is run by py.test, when doing `python setup.py test`"
    for shape in ['linear', 'cubic']:
        charge_cylinder( shape, show )

def charge_cylinder(shape, show=False):
    "On-axis cylinder of charge for different radii"
    # Initialize the simulation object
    sim = Simulation( Nz, zmax, Nr, rmax, Nm, (zmax-zmin)/Nz/c,
        p_zmin, p_zmax, p_rmin, p_rmax, p_nz, p_nr, p_nt, n_e,
        zmin=zmin, boundaries='periodic', verbose_level=0,
        smoother=BinomialSmoother(1, False), particle_shape=shape)
    # store results in dict
    res = {}
    # Scale the radius of the cylinder and calculate the space charge field
    for i, scale in enumerate(scales):
        res[scale] = calculate_fields(sim, scale)

    if show is False:
        for i, scale in enumerate(scales):
            r, Er, Er_theory, rho_n = res[scale]
            # Check that the density is correct in mode 0, below this index
            assert np.allclose( (-Er*r)[-5:], (Er_theory*r)[-5:], 1.e-3 )
    else:
        import matplotlib.pyplot as plt
        import matplotlib
        # Segmented colormap
        cmap = matplotlib.cm.get_cmap('YlGnBu')
        colors = np.array([co for co in cmap(np.linspace(0.2,0.8,7))])[::-1]
        # Plot charge density
        plt.title('Cylinder charge density')
        for i, scale in enumerate(scales):
            r, Er, Er_theory, rho_n = res[scale]
            plt.plot(r*1.e6, rho_n/(n_e*e), label=str(scale), color=colors[i])
        plt.legend()
        plt.xlim(0, 1.25)
        plt.ylabel(r'$\rho_n$')
        plt.xlabel(r'$r$')
        plt.show()
        # Plot simulated and analytically calculated field
        plt.title('Cylinder space charge field')
        for i, scale in enumerate(scales):
            r, Er, Er_theory, rho_n = res[scale]
            E0 = (n_e*e*p_rmax**2/(2*epsilon_0))
            plt.plot(r*1.e6, -Er*r/E0, label=str(scale), color=colors[i])
            plt.plot(r*1.e6, Er_theory*r/E0, color=colors[i], ls='--')
        plt.legend()
        plt.xlim(0, 1.25)
        plt.ylabel(r'$-E_{r,norm} \times r$')
        plt.xlabel(r'$r$')
        plt.show()

def calculate_fields(sim, scale):
    """
    Scale the cylinder, deposit the charge density
    and caculate the space charge fields.
    """
    # Scale the radius of the particle cylinder
    elec = sim.ptcl[0]
    elec.x *= scale
    elec.y *= scale
    # Erase fields
    sim.fld.erase('rho')
    sim.fld.erase('E')
    sim.fld.erase('B')
    # Transform erased E and B fields to spectral space
    sim.fld.interp2spect( 'E' )
    sim.fld.interp2spect( 'B' )
    # Deposit the charge
    elec.deposit( sim.fld, 'rho')
    sim.fld.sum_reduce_deposition_array('rho')
    sim.fld.divide_by_volume('rho')
    # Transform to spectral space and filter
    sim.fld.interp2spect('rho_prev')
    if filter_currents:
        sim.fld.filter_spect('rho_prev')
    # Calculate em fields
    get_space_charge_spect( sim.fld.spect[0], 1)
    # Get em fields from spectral space
    sim.fld.spect2interp( 'E' )
    sim.fld.spect2interp( 'B' )
    # Get filtered rho from spectral space
    sim.fld.spect2interp('rho_prev')
    # Revert scaling of particle positions
    elec.x /= scale
    elec.y /= scale
    # r vector
    r = sim.fld.interp[0].r.copy()
    # Lineout of Er
    Er = sim.fld.interp[0].Er[5,:].real.copy()
    # Calculate theoretical Er field along cylinder
    Er_theory = np.where(r<(p_rmax*scale),
        r*n_e*e*np.pi*(p_rmax)**2 / (2*np.pi*epsilon_0*(p_rmax*scale)**2),
        n_e*e*np.pi*(p_rmax)**2 / (2*np.pi*epsilon_0*r))
    # Calculate normalized charge density along cylinder
    rho_n = scale**2*sim.fld.interp[0].rho[5,:].real.copy()

    return r, Er, Er_theory, rho_n

if __name__ == '__main__' :

    test_charge_cylinder(show)
