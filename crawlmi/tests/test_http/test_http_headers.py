import copy

from twisted.trial import unittest

from crawlmi.http import Headers


class HeadersTest(unittest.TestCase):
    def test_basics(self):
        h = Headers({'Content-Type': 'text/html', 'Content-Length': 1234})
        self.assertIn('Content-Type', h)
        self.assertIn('Content-Length', h)

        self.assertRaises(KeyError, h.__getitem__, 'Accept')
        self.assertEqual(h.get('Accept'), None)
        self.assertEqual(h.getlist('Accept'), [])

        self.assertEqual(h.get('Accept', '*/*'), '*/*')
        self.assertEqual(h.getlist('Accept', '*/*'), ['*/*'])
        self.assertEqual(h.getlist('Accept', ['text/html', 'images/jpeg']), ['text/html', 'images/jpeg'])

    def test_single_value(self):
        h = Headers()
        h['Content-Type'] = 'text/html'
        self.assertEqual(h['Content-Type'], 'text/html')
        self.assertEqual(h.get('Content-Type'), 'text/html')
        self.assertEqual(h.getlist('Content-Type'), ['text/html'])

    def test_multivalue(self):
        h = Headers()

        h['X-Forwarded-For'] = hlist = ['ip1', 'ip2']
        self.assertEqual(h['X-Forwarded-For'], 'ip2')
        self.assertEqual(h.get('X-Forwarded-For'), 'ip2')
        self.assertEqual(h.getlist('X-Forwarded-For'), hlist)
        self.assertIsNot(h.getlist('X-Forwarded-For'), hlist)

    def test_encode_utf8(self):
        h = Headers({u'key': u'\xa3'}, encoding='utf-8')
        key, val = dict(h).items()[0]
        self.assertIsInstance(key, str)
        self.assertIsInstance(val[0], str)
        self.assertEqual(val[0], '\xc2\xa3')

    def test_encode_latin1(self):
        h = Headers({u'key': u'\xa3'}, encoding='latin1')
        key, val = dict(h).items()[0]
        self.assertEqual(val[0], '\xa3')

    def test_encode_multiple(self):
        h = Headers({u'key': [u'\xa3']}, encoding='utf-8')
        key, val = dict(h).items()[0]
        self.assertEqual(val[0], '\xc2\xa3')

    def test_delete_and_contains(self):
        h = Headers()
        h['Content-Type'] = 'text/html'
        self.assertIn('Content-Type', h)
        del h['Content-Type']
        self.assertNotIn('Content-Type', h)

    def test_setdefault(self):
        h = Headers()
        hlist = ['ip1', 'ip2']
        olist = h.setdefault('X-Forwarded-For', hlist)
        self.assertIsNot(h.getlist('X-Forwarded-For'), hlist)
        self.assertIs(h.getlist('X-Forwarded-For'), olist)

        h = Headers()
        olist = h.setdefault('X-Forwarded-For', 'ip1')
        self.assertEqual(h.getlist('X-Forwarded-For'), ['ip1'])
        self.assertIs(h.getlist('X-Forwarded-For'), olist)

    def test_iterables(self):
        idict = {'Content-Type': 'text/html', 'X-Forwarded-For': ['ip1', 'ip2']}
        h = Headers(idict)
        self.assertEqual(dict(h), {'Content-Type': ['text/html'], 'X-Forwarded-For': ['ip1', 'ip2']})
        self.assertEqual(h.keys(), ['X-Forwarded-For', 'Content-Type'])
        self.assertEqual(h.items(), [('X-Forwarded-For', ['ip1', 'ip2']), ('Content-Type', ['text/html'])])
        self.assertEqual(list(h.iteritems()),
                [('X-Forwarded-For', ['ip1', 'ip2']), ('Content-Type', ['text/html'])])
        self.assertEqual(h.values(), ['ip2', 'text/html'])

    def test_update(self):
        h = Headers()
        h.update({'Content-Type': 'text/html', 'X-Forwarded-For': ['ip1', 'ip2']})
        self.assertEqual(h.getlist('Content-Type'), ['text/html'])
        self.assertEqual(h.getlist('X-Forwarded-For'), ['ip1', 'ip2'])

    def test_copy(self):
        h1 = Headers({'header1': ['value1', 'value2']}, encoding='ascii')
        h2 = copy.copy(h1)
        self.assertEqual(h1, h2)
        self.assertEqual(h1.encoding, h2.encoding)
        self.assertEqual(h1.getlist('header1'), h2.getlist('header1'))
        self.assertIsNot(h1.getlist('header1'), h2.getlist('header1'))
        self.assertIsInstance(h2, Headers)

    def test_add(self):
        h1 = Headers({'header1': 'value1'})
        h1.add('header1', 'value3')
        self.assertEqual(h1.getlist('header1'), ['value1', 'value3'])

        h1 = Headers()
        h1.add('header1', 'value1')
        h1.add('header1', 'value3')
        self.assertEqual(h1.getlist('header1'), ['value1', 'value3'])

    def test_clear(self):
        h = Headers({'a': 'b'})
        self.assertIn('a', h)
        h.clear()
        self.assertNotIn('a', h)

    def test_to_string(self):
        h = Headers({'Content-type': 'text/html', 'Accept': 'gzip'})
        self.assertEqual(h.to_string(), 'Content-Type: text/html\r\nAccept: gzip')
        h = Headers({'Content-type': ['text/html'], 'Accept': ['gzip']})
        self.assertEqual(h.to_string(), 'Content-Type: text/html\r\nAccept: gzip')
