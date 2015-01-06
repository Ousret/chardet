######################## BEGIN LICENSE BLOCK ########################
# The Original Code is mozilla.org code.
#
# The Initial Developer of the Original Code is
# Netscape Communications Corporation.
# Portions created by the Initial Developer are Copyright (C) 1998
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Mark Pilgrim - port to Python
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301  USA
######################### END LICENSE BLOCK #########################

from .mbcharsetprober import MultiByteCharSetProber
from .codingstatemachine import CodingStateMachine
from .chardistribution import SJISDistributionAnalysis
from .jpcntx import SJISContextAnalysis
from .mbcssm import SJIS_SM_MODEL
from .enums import ProbingState, MachineState


class SJISProber(MultiByteCharSetProber):
    def __init__(self):
        super(SJISProber, self).__init__()
        self.coding_sm = CodingStateMachine(SJIS_SM_MODEL)
        self._distribution_analyzer = SJISDistributionAnalysis()
        self._context_analyzer = SJISContextAnalysis()
        self.reset()

    def reset(self):
        super(SJISProber, self).reset()
        self._context_analyzer.reset()

    @property
    def charset_name(self):
        return self._context_analyzer.charset_name

    def feed(self, byte_str):
        for i in range(len(byte_str)):
            coding_state = self.coding_sm.next_state(byte_str[i])
            if coding_state == MachineState.error:
                self.logger.debug('%s prober hit error at byte %s',
                                  self.charset_name, i)
                self._state = ProbingState.not_me
                break
            elif coding_state == MachineState.its_me:
                self._state = ProbingState.found_it
                break
            elif coding_state == MachineState.start:
                char_len = self.coding_sm.get_current_charlen()
                if i == 0:
                    self._last_char[1] = byte_str[0]
                    self._context_analyzer.feed(self._last_char[2 - char_len:],
                                                char_len)
                    self._distribution_analyzer.feed(self._last_char, char_len)
                else:
                    self._context_analyzer.feed(byte_str[i + 1 - char_len:i + 3
                                                     - char_len], char_len)
                    self._distribution_analyzer.feed(byte_str[i - 1:i + 1],
                                                     char_len)

        self._last_char[0] = byte_str[-1]

        if self.state == ProbingState.detecting:
            if (self._context_analyzer.got_enough_data() and
               (self.get_confidence() > self.SHORTCUT_THRESHOLD)):
                self._state = ProbingState.found_it

        return self.state

    def get_confidence(self):
        context_conf = self._context_analyzer.get_confidence()
        distrib_conf = self._distribution_analyzer.get_confidence()
        return max(context_conf, distrib_conf)
