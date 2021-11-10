def AsList(arg):
    """return the given argument unchanged if already a list or tuple, otherwise return a single
    element list"""
    return arg if isinstance(arg, (tuple, list)) else [arg]
