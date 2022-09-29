# MIT License
#
# Copyright (c) 2022 Quandela
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from perceval.components import Circuit, Processor
from perceval.components.base_components import *
from perceval.components.component_catalog import CatalogItem, AsType
from perceval.components.port import Herald, Port, Encoding


def _post_process(s):
    return (s[1] or s[2]) and (s[3] or s[4])


class PostProcessedCnotItem(CatalogItem):
    article_ref = "https://journals.aps.org/pra/abstract/10.1103/PhysRevA.65.062324"
    R1 = 1 / 3
    R2 = 1 / 2

    def __init__(self):
        super().__init__("postprocessed cnot")
        self._default_opts['type'] = AsType.PROCESSOR

    def build(self):
        c_cnot = (Circuit(6, name="PostProcessed CNOT")
                  .add((0, 1), GenericBS(R=self.R1, phi_b=np.pi, phi_d=0))
                  .add((3, 4), GenericBS(R=self.R2))
                  .add((2, 3), GenericBS(R=self.R1, phi_b=np.pi, phi_d=0))
                  .add((4, 5), GenericBS(R=self.R1))
                  .add((3, 4), GenericBS(R=self.R2)))

        if self._opt('type') == AsType.CIRCUIT:
            return c_cnot
        elif self._opt('type') == AsType.PROCESSOR:
            p = Processor(6)
            p.add(0, c_cnot) \
                .add_herald(0, 0) \
                .add_port(1, Port(Encoding.DUAL_RAIL, 'data')) \
                .add_port(3, Port(Encoding.DUAL_RAIL, 'ctrl')) \
                .add_herald(5, 0)
            p.set_postprocess(_post_process)
            return p

# With simple BS convention:
# c_cnot = (Circuit(6, name="PostProcessed CNOT")
#           .add((0, 1), SimpleBS(R=1 / 3, phi=np.pi))
#           .add((3, 4), SimpleBS(R=1 / 2))
#           .add((2, 3), SimpleBS(R=1 / 3, phi=np.pi))
#           .add((4, 5), SimpleBS(R=1 / 3))
#           .add((3, 4), SimpleBS(R=1 / 2)))





# postprocessed_cnot = PredefinedCircuit(c_cnot,
#                                        "postprocessed cnot",
#                                        description="https://journals.aps.org/pra/abstract/10.1103/PhysRevA.65.062324",
#                                        heralds={0: 0, 5: 0},
#                                        post_select_fn=_post_process)
