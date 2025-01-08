import numpy as np
from scipy.signal import hilbert

N_A = 6.02214076e23
from astropy import units as u
from astropy.constants import N_A




def polarisability(wavelength:np.ndarray, absorbance:np.ndarray, cd:np.ndarray, concentration:float, path_length:float, refractive_index:float=1.0, wavelength_units=u.nm, cd_units=u.mdeg, concentration_units=u.mmol/u.L, path_length_units=u.cm, units=u.nm**3, astr_units=False):
    """
    !!!Function fully implemented  by Sebastian Golat @ KCL!!!!
    Calculate the chiral and achiral polarisability of a particle from absorption and CD data of a solution.

    Parameters
    ----------
    wavelength : array-like
        Wavelengths at which the absorbance and CD were measured.
    absorbance : array-like
        Absorbance of the solution at given wavelengths.
    cd : array-like
        CD of the solution at given wavelengths.
    concentration : float
        Concentration of the solution.  
    path_length : float
        Path length of the cuvette.
    refractive_index : float, optional
        Refractive index of the solution. Default is 1.
    wavelength_units : astropy.units.Quantity, optional
        Units of the wavelength. Default is nm.
    cd_units : astropy.units.Quantity, optional
        Units of the CD. Default is deg.:wq:pi
    concentration_units : astropy.units.Quantity, optional
        Units of the concentration. Default is mmol/L.
    path_length_units : astropy.units.Quantity, optional
        Units of the path length. Default is cm.
    units : astropy.units.Quantity, optional
        Units of the output. Default is nm³.
    astr_units : bool, optional
        If True, return the output in astropy.units.Quantity. Default is False.

    Returns
    -------
    alpha_achiral : np.ndarray
        Achiral polarisability of the particle. \n
        Im(αe+αm) = 1/(2π) (λₛ/ℓ) 1/(N_A*C) (A ln(10)) \n
    alpha_chiral : np.ndarray
        Chiral polarisability Im(αc) of the particle.\n
        Im(αc) = 1/(2π) (λₛ/ℓ)  1/(N_A*C) (atanh(tan(-θ))) \n
    """
    # Convert the input data to the correct units
    if not isinstance(wavelength, u.Quantity):
        wavelength = wavelength * wavelength_units
    if not isinstance(cd, u.Quantity):
        cd = cd * cd_units
    if not isinstance(concentration, u.Quantity):
        concentration = concentration * concentration_units
    if not isinstance(path_length, u.Quantity):
        path_length = path_length * path_length_units


    # Calculate imaginary parts of polarisabilies from the input data 
    # Im(αe+αm) Achiral polarisability
    Im_alpha_achiral = 1/(2*np.pi) * (wavelength/(refractive_index*path_length)) * (1/(N_A*concentration)) * (absorbance*np.log(10))
    # Im(αc)    Chiral polarisability (Exact)
    Im_alpha_chiral  = 1/(2*np.pi) * (wavelength/(refractive_index*path_length)) * (1/(N_A*concentration)) * np.arctanh(np.tan(-cd))/u.rad 
    
    # # Calculate the complex polarisabilities from the imaginary parts 
    # alpha_achiral = 1j*hilbert(Im_alpha_achiral)*Im_alpha_achiral.unit
    # alpha_chiral  = 1j*hilbert(Im_alpha_chiral) *Im_alpha_chiral.unit

    # Pad the imaginary parts to alleviate the edging effect of the Hilbert transform
    pad_width = len(Im_alpha_achiral) // 2
    padded_Im_alpha_achiral = np.pad(Im_alpha_achiral, pad_width, mode='reflect')
    padded_Im_alpha_chiral = np.pad(Im_alpha_chiral, pad_width, mode='reflect')

    # Calculate the complex polarisabilities from the imaginary parts using the Hilbert transform
    alpha_achiral = 1j * hilbert(padded_Im_alpha_achiral)[pad_width:-pad_width] * Im_alpha_achiral.unit
    alpha_chiral  = 1j * hilbert(padded_Im_alpha_chiral)[pad_width:-pad_width]  * Im_alpha_chiral.unit

    # If wavelength is not sorted in decreasing order, multiply polarisabilities by -1
    # (this is because hilbert assumes it is a function of frequency, which is decreasing with increasing wavelength)
    if not np.all(np.diff(wavelength) < 0):
        alpha_achiral *= -1
        alpha_chiral *= -1

    # Return the output in the correct units 
    if astr_units:  # Return the output in astropy.units
        return alpha_achiral.to(units), alpha_chiral.to(units)
    else:           # Return the output as numpy arrays (in case astropy is not desired)
        return (alpha_achiral.to(units)).value, (alpha_chiral.to(units)).value