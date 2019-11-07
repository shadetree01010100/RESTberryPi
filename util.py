channels = {
    4: 7,
    5: 29,
    6: 31,
    12: 32,
    13: 33,
    16: 36,
    17: 11,
    18: 12,
    19: 35,
    20: 38,
    21: 40,
    22: 15,
    23: 16,
    24: 18,
    25: 22,
    26: 37,
    27: 13,
}

def parse_sys_args(args):
    help = 'INVALID ARGS, TRY: python3 server.py 31415 username:password'
    if not args:
        return None, None
    elif len(args) == 1:
        # either a port (int), or key (contains ':')
        try:
            port = int(args[0])
            auth = None
        except ValueError:
            # not a number, must be the key
            port = None
            auth = args[0]
            if ':' not in auth:
                # not the expected user:pass either
                raise Exception(help)
    elif len(args) == 2:
        # both port and key passed
        try:
            port = int(args[0])
            auth = args[1]
            assert ':' in auth
        except (ValueError, AssertionError):
            raise Exception(help)
    else:
        # too many args!
        raise Exception(help)
    return port, auth
