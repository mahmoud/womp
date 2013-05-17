# -*- coding: utf-8 -*-


def get_decoded_kwargs(args):
    import sys
    kwargs = dict(args._get_kwargs())
    for k, v in kwargs.items():
        if not isinstance(v, unicode):
            try:
                kwargs[k] = v.decode(sys.stdin.encoding)
            except AttributeError:
                pass
    return kwargs


def rotated_sequence(seq, start_index):
    n = len(seq)
    for i in xrange(n):
        yield seq[(i + start_index) % n]


def get_max_width(table, index):
    """Get the maximum width of the given column index"""
    return max([len(str(row[index])) for row in table])


def pprint_table(table):
    """Prints out a table of data, padded for alignment
    @param out: Output stream (file-like object)
    @param table: The table to print. A list of lists.
    Each row must have the same number of columns. """
    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        # left col
        print str(row[0]).ljust(col_paddings[0] + 1),
        # rest of the cols
        for i in range(1, len(row)):
            col = str(row[i]).rjust(col_paddings[i] + 2)
            print col,
        print
