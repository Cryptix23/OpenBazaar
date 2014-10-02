import time
import unittest

from node import constants, guid, kbucket, routingtable


class TestRoutingTable(unittest.TestCase):
    """Test interface of abstract class RoutingTable."""

    @classmethod
    def setUpClass(cls):
        cls.id1 = "a" * 20
        cls.id2 = "b" * 20
        cls.uid1 = unicode(cls.id1)
        cls.uid2 = unicode(cls.id2)
        cls.parent_node_id = cls.id1
        cls.market_id = 42
        cls.guid = guid.GUIDMixin(cls.id1)

    def setUp(self):
        self.rt = routingtable.RoutingTable(
            self.parent_node_id,
            self.market_id
        )

    def test_init(self):
        self.assertEqual(self.rt.parent_node_id, self.parent_node_id)
        self.assertEqual(self.rt.market_id, self.market_id)
        self.assertTrue(hasattr(self.rt, 'log'))

    def test_addContact(self):
        self.assertRaises(
            NotImplementedError,
            self.rt.addContact,
            self.id1
        )

    def test_distance(self):
        dist = self.rt.distance

        self.assertEqual(0, dist("aaaa", "aaaa"))
        self.assertNotEqual(0, dist("abcd", "dcba"))
        self.assertEqual(0, dist("a" * 256, "a" * 256))
        self.assertEqual(1, dist("2", "3"))
        self.assertEqual(10, dist("2", "8"))
        self.assertEqual(1953184666628070171L, dist("a" * 8, "z" * 8))

        self.assertEqual(dist("aaaa", "bbbb"), dist("bbbb", "aaaa"))

        self.assertEqual(dist("a", "b"), dist(u"a", "b"))
        self.assertEqual(dist("a", "b"), dist("a", u"b"))
        self.assertEqual(dist("a", "b"), dist(guid.GUIDMixin("a"), "b"))
        self.assertEqual(dist("a", "b"), dist("a", guid.GUIDMixin("b")))

        self.assertRaises(ValueError, dist, "a"* 4, "a" * 3)

    def test_findCloseNodes(self):
        self.assertRaises(
            NotImplementedError,
            self.rt.findCloseNodes,
            self.id1,
            constants.k,
            rpc_node_id=self.id2
        )

    def test_getContact(self):
        self.assertRaises(
            NotImplementedError,
            self.rt.getContact,
            self.id1
        )

    def test_getRefreshList(self):
        self.assertRaises(
            NotImplementedError,
            self.rt.getRefreshList,
            start_index=1,
            force=True
        )

    def test_removeContact(self):
        self.assertRaises(
            NotImplementedError,
            self.rt.removeContact,
            self.id1
        )

    def test_touchKBucket(self):
        self.assertRaises(
            NotImplementedError,
            self.rt.touchKBucket,
            self.id1,
            timestamp=42
        )


class TestTreeRoutingTable(TestRoutingTable):
    """Test TreeRoutingTable implementation of RoutingTable."""

    def _ad_hoc_KBucket_eq(self, kbucket1, kbucket2, msg=None):
        self.assertEqual(kbucket1.rangeMin, kbucket2.rangeMin, msg)
        self.assertEqual(kbucket1.rangeMax, kbucket2.rangeMax, msg)
        self.assertItemsEqual(kbucket1.contacts, kbucket2.contacts, msg)

    @staticmethod
    def _make_KBucket(range_min, range_max, market_id):
        return kbucket.KBucket(
            rangeMin=range_min,
            rangeMax=range_max,
            market_id=market_id
        )

    @classmethod
    def setUpClass(cls):
        super(TestTreeRoutingTable, cls).setUpClass()
        cls.range_min = 0
        cls.range_max = 2**routingtable.BIT_NODE_ID_LEN
        cls.init_kbuckets = [
            cls._make_KBucket(cls.range_min, cls.range_max, cls.market_id)
        ]

    def setUp(self):
        self.rt = routingtable.TreeRoutingTable(
            self.parent_node_id,
            self.market_id
        )

    def test_subclassing(self):
        self.assertIsInstance(self.rt, routingtable.RoutingTable)

    def test_init(self):
        super(TestTreeRoutingTable, self).test_init()
        self.assertTrue(hasattr(self.rt, 'buckets'))
        self.addTypeEqualityFunc(kbucket.KBucket, self._ad_hoc_KBucket_eq)
        # The following check cannot be simplified due to this bug
        # http://www.gossamer-threads.com/lists/python/bugs/1159468
        self.assertEqual(len(self.rt.buckets), 1)
        self.assertEqual(self.rt.buckets[0], self.init_kbuckets[0])

    def test_addContact(self):
        pass

    def test_findCloseNodes(self):
        pass

    def test_getContact(self):
        self.rt.buckets[0].addContact(self.id1)
        self.assertEqual(self.id1, self.rt.getContact(self.id1))
        self.assertIsNone(self.rt.getContact(self.id2))

    def test_getRefreshList(self):
        pass

    def _test_removeContact_scenario(self, contact):
        self.assertNotIn(contact, self.rt.buckets[0])
        self.rt.buckets[0].addContact(contact)
        self.assertIn(contact, self.rt.buckets[0])
        self.rt.removeContact(contact)
        self.assertNotIn(contact, self.rt.buckets[0])

    def test_removeContact(self):
        self._test_removeContact_scenario(self.id1)
        self._test_removeContact_scenario(unicode(self.id1))
        self._test_removeContact_scenario(guid.GUIDMixin(self.id1))

        # Removing an absent contact shouldn't raise a ValueError
        self._test_removeContact_scenario(self.id2)

    def test_touchKBucket(self):
        half_range = self.range_min + (self.range_max - self.range_min) // 2
        self.rt.buckets = [
            self._make_KBucket(
                self.range_min, half_range, self.market_id
            ),
            self._make_KBucket(
                half_range, self.range_max, self.market_id
            )
        ]

        self.assertEqual(
            self.rt.buckets[0].lastAccessed,
            self.rt.buckets[1].lastAccessed
        )

        now = int(time.time())
        self.assertNotEqual(now, self.rt.buckets[0].lastAccessed)

        hex_key = hex(half_range)
        self.rt.touchKBucket(hex_key, timestamp=now)
        self.assertLessEqual(now, self.rt.buckets[1].lastAccessed)
        self.assertNotEqual(
            self.rt.buckets[0].lastAccessed,
            self.rt.buckets[1].lastAccessed
        )

        now2 = now + 1
        self.rt.touchKBucket(hex(half_range - 1), now2)
        self.assertEqual(now, self.rt.buckets[1].lastAccessed)
        self.assertEqual(now2, self.rt.buckets[0].lastAccessed)

    def test_kbucketIndex_bad_key(self):
        bad_hex_key = "z"  # not a hex value
        self.assertRaises(ValueError, self.rt.kbucketIndex, bad_hex_key)

    def test_kbucketIndex_not_found(self):
        ghost_hex_key = hex(self.range_max)
        self.assertRaises(KeyError, self.rt.kbucketIndex, ghost_hex_key)

    def test_kbucketIndex_many_found(self):
        hex_key = hex(self.range_min)
        # Insert duplicate kbucket
        self.rt.buckets.append(self.rt.buckets[0])
        self.assertRaises(RuntimeError, self.rt.kbucketIndex, hex_key)

    def test_kbucketIndex_default(self):
        half_range = self.range_min + (self.range_max - self.range_min) // 2
        self.rt.buckets = [
            self._make_KBucket(
                self.range_min, half_range, self.market_id
            ),
            self._make_KBucket(
                half_range, self.range_max, self.market_id
            )
        ]
        hex_key = hex(half_range)
        self.assertEqual(1, self.rt.kbucketIndex(hex_key))
        self.assertEqual(1, self.rt.kbucketIndex(unicode(hex_key)))
        self.assertEqual(1, self.rt.kbucketIndex(guid.GUIDMixin(hex_key)))


class TestOptimizedTreeRoutingTable(TestTreeRoutingTable):
    """Test OptimizedTreeRoutingTable implementation of RoutingTable."""

    @classmethod
    def setUpClass(cls):
        super(TestOptimizedTreeRoutingTable, cls).setUpClass()

    def setUp(self):
        self.rt = routingtable.OptimizedTreeRoutingTable(
            self.parent_node_id,
            self.market_id
        )

    def test_subclassing(self):
        self.assertIsInstance(self.rt, routingtable.TreeRoutingTable)

    def test_init(self):
        super(TestOptimizedTreeRoutingTable, self).test_init()
        self.assertTrue(hasattr(self.rt, 'replacement_cache'))
        self.assertEqual(self.rt.replacement_cache, dict())


if __name__ == "__main__":
    unittest.main()
