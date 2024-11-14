def mdeg_to_ext(mdeg, M, C, L):
    ext = mdeg * M / (C * L * 32980)
    return ext
def abs_to_ext(abs, M, C, L):
    ext = abs * M / (C * L)
    return ext