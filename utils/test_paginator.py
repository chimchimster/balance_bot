import unittest
from paginator import Paginator


class TestPaginator(unittest.TestCase):

    p = Paginator([1, 2, 3, 4, 5, 6, 7], True)

    def test001_paginate_forward(self):

        counter = 0

        try:
            while self.p.has_next():
                self.p.__next__()
                counter += 1
        except StopIteration:
            self.assertEqual(counter, len(self.p._struct))

    def test002_paginate_backward(self):

        self.p._flag = False
        counter = len(self.p._struct)

        try:
            while self.p.has_prev():
                self.p.__next__()
                counter -= 1
        except StopIteration:
            self.assertEqual(counter, 0)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPaginator)
    unittest.TextTestRunner(failfast=False).run(suite)
