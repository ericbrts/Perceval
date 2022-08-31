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

from abc import ABC, abstractmethod
from enum import Enum

from perceval.components.abstract_component import AComponent


class Encoding(Enum):
    dual_ray = 0
    polarization = 1
    qudit = 2
    time = 3
    none = 4


def _port_size(encoding: Encoding):
    if encoding == Encoding.dual_ray:
        return 2
    elif encoding == Encoding.polarization:
        return 1
    elif encoding == Encoding.time:
        return 1
    elif encoding == Encoding.none:
        return 1
    return None  # Port size cannot be deduced only with encoding in case of Qudit-encoding


class PortLocation(Enum):
    input = 0
    output = 1
    in_out = 2


class APort(AComponent, ABC):
    def __init__(self, size, name):
        super().__init__(size, name)

    @staticmethod
    def supports_location(loc: PortLocation) -> bool:
        return True

    @abstractmethod
    def is_output_photonic_mode_closed(self):
        """
        Returns True if the photonic mode is closed by the port
        """


class Port(APort):
    def __init__(self, encoding, name):
        assert encoding != Encoding.qudit, "Qudit encoded ports must be created by instanciating QuditPort"
        super().__init__(_port_size(encoding), name)
        self._encoding = encoding

    @property
    def encoding(self):
        return self._encoding

    def is_output_photonic_mode_closed(self):
        return False


class QuditPort(Port):
    def __init__(self, n_qubits, name):
        super(Port, self).__init__(2**n_qubits, name)
        self._encoding = Encoding.qudit


class Herald(APort):
    def __init__(self, value: int, name=None):
        assert value == 0 or value == 1, "Herald value should be 0 or 1"
        super().__init__(1, name)
        self._value = value

    def is_output_photonic_mode_closed(self):
        return True


class ADetector(APort, ABC):
    def __init__(self, name=''):
        super().__init__(1, name)

    @abstractmethod
    def trigger(self, value):
        pass

    @staticmethod
    def supports_location(loc: PortLocation) -> bool:
        return loc == PortLocation.output

    def is_output_photonic_mode_closed(self):
        return True


class CounterDetector(ADetector):
    def __init__(self, name=''):
        super().__init__(name)
        self._counter = 0

    def trigger(self, value):
        if value:
            self._counter += 1

    @property
    def count(self):
        return self._counter


class DigitalConverterDetector(ADetector):
    def __init__(self, name=''):
        super().__init__(name)
        self._connections = {}

    def trigger(self, value):
        for component, action in self._connections.items():
            action(value, component)

    def connect_to(self, obj, action_func):
        self._connections[obj] = action_func

    def is_connected_to(self, component) -> bool:
        return component in self._connections
