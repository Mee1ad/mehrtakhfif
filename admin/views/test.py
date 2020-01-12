
def test(arg):
    print(arg)

def test2(arg):
    print(arg)
    return arg

test(test2('zert'))

