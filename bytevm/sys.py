import sys
pseudosys = sys.modules[__name__]
_exc_info = (None, None, None)
for k,v in sys.__dict__.items():
    if k in ['path']:
        #dont clobber
        newv = v[:]
        setattr(pseudosys, k, newv)
    elif k in ['exc_info']:
        # make sure we have a function
        setattr(pseudosys, k, lambda: _exc_info)
    else:
        setattr(pseudosys, k, v)

