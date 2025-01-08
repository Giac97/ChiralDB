def mdeg_to_ext(mdeg, M, C, L):
    ext = mdeg * M / (C * L * 32980)
    return ext
def abs_to_ext(abs, M, C, L):
    ext = abs * M / (C * L)
    return ext

def ext_to_mdeg(ext, M, C, L):
    mdeg = ext * C * L * 32980 / M 
    return mdeg

def ext_to_abs(ext, M, C, L):
    
    abs = C * L / (M * ext)
    return abs
