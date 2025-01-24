class A:
    
    def __init__(self):
        self.x = B()


class B:

    def __init__(self, a):
        self.y = a


lst = []
for i in [1, 2, 3]:
    top = A()
    lst.append(top)
    for j in ['a', 'b', 'c']:
        top.x = B(j)