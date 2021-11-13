from sexp.sexp import gensexp
from .sexp_parser.sexp_parser import parseSexp

def _dict2tuple(obj):
    if type(obj) not in [dict, list]:
        return obj
    
    if type(obj) == dict:
        obj = list(obj.items())

    return [(k, _dict2tuple(v)) for k,v in obj]

def _cleanparsed(parsed):
    # basecase
    if type(parsed) is not list:
        return parsed

    if parsed[0] != 1:
        raise Exception

    # remove 1s
    parsed = parsed[1:]
    # recurse
    parsed[1:] = list(map(_cleanparsed, parsed[1:]))

    key = parsed[0]
    args = parsed[1:]

    if len(args) == 0:
        args = None
    elif len(args) == 1 and type(args[0]) is not tuple:
        args = args[0]
 
    
    return (key, args)

def _py2net2py(obj):
    sexp=gensexp(obj)
    parsed = parseSexp(sexp)
    cleaned = [_cleanparsed(parsed)]
    objtuple = _dict2tuple(obj)

    eq = objtuple == cleaned
    if not eq:
        print(objtuple)
        print(cleaned)

    return eq



def _net2py2net(netfilepath):
    with open(netfilepath, "r") as netfile:
        netsexp=netfile.read()
    netsexpparsed = parseSexp()


    

def test_sexp():
    testdict = {"testdict" : {"a": {"b" : "5"}, "c": "d"}}
    ok = _py2net2py(testdict)
    print("testdict:", ok)


    netlistdict = {
        "export":
            {
                "version": "D",
                "design": {
                    "source": "/home/...", 
                    "date": '"Sat 13 ..."',
                    "tool": '"Eeschema"',
                    "sheet": {
                        "number": "1",
                        "name" : "/",
                        "tstamps": "/",
                        "title_block": [
                            ("title", None),
                            ("company", None),
                            ("rev", None),
                            ("date", None),
                            ("source", "main.sch"),
                            ("comment",  {
                                "number": "1",
                                "value": "\"\""
                            }),
                            ("comment",  {
                                "number": "2",
                                "value": "\"\""
                            }),
                            ("comment",  {
                                "number": "3",
                                "value": "\"\""
                            }),
                            ("comment",  {
                                "number": "4",
                                "value": "\"\""
                            }),
                        ]
                    }
                }
            }
    }

    ok = _py2net2py(netlistdict)
    print("netlistdict:", ok)


