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
    if len(args) == 1:
        # either a port (int), or key (contains ':')
        try:
            return int(args[0]), None
        except ValueError:
            # not a number, must be the key
            if ':' not in args[0]:
                # not the expected user:pass either
                raise Exception(help)
            return None, args[0]
    if len(args) == 2:
        # both port and key passed
        try:
            assert ':' in args[1]
            return int(args[0]), args[1]
        except (AssertionError, ValueError):
            raise Exception(help)
    # else, too many args!
    raise Exception(help)
