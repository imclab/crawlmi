import unittest2

from crawlmi.utils.conf import build_component_list


class UtilsConfTest(unittest2.TestCase):

    def test_build_component_list(self):
        base = {'one': 1, 'two': 2, 'three': 3, 'five': 5, 'six': None}
        custom = {'two': None, 'three': 8, 'four': 4}
        self.assertEqual(build_component_list(base, custom),
                         ['one', 'four', 'five', 'three'])

        custom = ['a', 'b', 'c']
        self.assertEqual(build_component_list(base, custom), custom)
