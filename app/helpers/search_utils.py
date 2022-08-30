def get_cmp(value):
    if value == 'increase':
        def cmp(n, o):
            return n > o
    elif value == 'decrease':
        def cmp(n, o):
            return n < o
    elif value == 'unchanged':
        def cmp(n, o):
            return n == o
    else:
        def cmp(n, o):
            return n != o
    return cmp

direction_data = {
    'increase': {},
    'decrease': {},
    'unchanged': {},
    'changed': {}
}
