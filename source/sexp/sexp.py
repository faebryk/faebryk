# Copyright (c) 2021 ITENG
# SPDX-License-Identifier: MIT

def _expandable(obj):
    return type(obj) in [dict, list]

# Limitations:
# - dict only
#   -> no duplicate keys possible
def gensexp(obj):
    sexp = ""

    # Basecase
    if obj is None:
        return sexp

    if not _expandable(obj):
        return str(obj)


    # Recursion
    if type(obj) is dict:
        # Convert to tuple list
        obj = list(obj.items())

    # Assume tuple list
    if type(obj) is not list:
        raise Exception

    try:
        for k,v in obj:
            ksexp = gensexp(k) 
            vsexp = gensexp(v)
            if ksexp == "":
                raise Exception

            isexp = "({ksexp}{sep}{vsexp})".format(
                ksexp=ksexp,
                sep=" " if vsexp is not None else "",
                vsexp=vsexp
            )

            sexp += isexp
    except ValueError:
        print("Fault:", obj)
        raise Exception


    
    return sexp