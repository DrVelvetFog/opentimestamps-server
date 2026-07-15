# Copyright (C) 2016 The OpenTimestamps developers
#
# This file is part of the OpenTimestamps Server.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of the OpenTimestamps Server including this file, may be copied,
# modified, propagated, or distributed except according to the terms contained
# in the LICENSE file.

import unittest

from bitcoin.core import CTxIn, CTxOut, COutPoint, CTransaction, lx
from bitcoin.core.script import CScript, OP_RETURN

from otsserver.stamper import Stamper, DUST

# __update_timestamp_tx is a name-mangled private static method
_update_timestamp_tx = Stamper._Stamper__update_timestamp_tx


def _make_old_tx(change_value):
    """A minimal timestamp tx: one input, a change output (vout[0]) + OP_RETURN"""
    txin = CTxIn(COutPoint(lx('00' * 32), 0), nSequence=0xfffffffe)
    change = CTxOut(change_value, CScript([b'\x00' * 20]))
    commitment = CTxOut(0, CScript([OP_RETURN, b'\x11' * 32]))
    return CTransaction([txin], [change, commitment])


class Test_update_timestamp_tx(unittest.TestCase):
    def test_normal_feerate_keeps_change(self):
        old_tx = _make_old_tx(100000)
        new_tx = _update_timestamp_tx(old_tx, b'\x22' * 32, 0, 1)  # 1 sat/vB
        self.assertEqual(len(new_tx.vout), 2)  # change output preserved
        self.assertGreater(new_tx.vout[0].nValue, DUST)
        self.assertLess(new_tx.vout[0].nValue, 100000)

    def test_large_feerate_drops_change(self):
        # A feerate whose delta_fee eats the whole change collapses to the
        # minimal single-OP_RETURN transaction (no negative-value output).
        old_tx = _make_old_tx(100000)
        new_tx = _update_timestamp_tx(old_tx, b'\x22' * 32, 0, 10 ** 9)
        self.assertEqual(len(new_tx.vout), 1)
        self.assertEqual(new_tx.vout[0].nValue, 0)

    def test_infinite_feerate_does_not_overflow(self):
        # Regression for #114/#116: a fee-bump that overflowed to inf must not
        # raise OverflowError (which crashed the stamper and bricked the
        # calendar); it degrades to the minimal transaction instead.
        old_tx = _make_old_tx(100000)
        new_tx = _update_timestamp_tx(old_tx, b'\x22' * 32, 0, float('inf'))
        self.assertEqual(len(new_tx.vout), 1)


if __name__ == '__main__':
    unittest.main()
