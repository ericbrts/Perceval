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

from .abstract_component import AComponent
from .abstract_processor import AProcessor, ProcessorType
from .base_components import PERM
from .port import APort, PortLocation, Herald, Encoding
from .source import Source
from .linear_circuit import ACircuit, Circuit
from ._mode_connector import ModeConnector, UnavailableModeException
from perceval.utils import SVDistribution, BasicState, StateVector, global_params, Matrix, Parameter
from perceval.utils.algorithms.simplification import perm_compose
from perceval.backends import Backend, BACKEND_LIST

from typing import Dict, Callable, Type, List, Union
import copy


class Processor(AProcessor):
    """
    Generic definition of processor as a source + components (both linear and non-linear) + ports
    + optional post-processing logic
    """
    def __init__(self, backend_name: str, m_circuit: Union[int, ACircuit], source: Source = Source()):
        r"""Define a processor with sources connected to the circuit and possible post_selection

        :param backend_name: Name of the simulator backend to run
        :param m_circuit: can either be:
            - a int: number of modes of interest (MOI). A mode of interest is any non-heralded mode.
            - a circuit: the input circuit to start with. Other components can still be added afterwards with `add()`
        :param source: the Source used by the processor (defaults to perfect source)
        """
        super().__init__()
        self._source = source
        self._components = []  # Any type of components, not only linear ones
        self._in_ports = {}
        self._out_ports = {}

        self._post_select = None
        self._n_heralds = 0
        if isinstance(m_circuit, int):
            self._n_moi = m_circuit  # number of modes of interest (MOI)
        else:
            self._n_moi = m_circuit.m
            self.add(0, m_circuit)

        # Mode post selection: expect at least # modes with photons in output
        self._min_mode_post_select = None

        self._anon_herald_num = 0  # This is not a herald count!
        self._inputs_map: Union[SVDistribution, None] = None
        self._simulator = None
        assert backend_name in BACKEND_LIST, f"Simulation backend '{backend_name}' does not exist"
        self._backend_name = backend_name

    def _setup_simulator(self, **kwargs):
        self._simulator = BACKEND_LIST[self._backend_name](self.linear_circuit(), **kwargs)

    def type(self) -> ProcessorType:
        return ProcessorType.SIMULATOR

    @property
    def is_remote(self) -> bool:
        return False

    def mode_post_selection(self, n: int):
        super().mode_post_selection(n)
        self._min_mode_post_select = n

    @property
    def m(self) -> int:
        return self._n_moi

    @property
    def circuit_size(self) -> int:
        return self._n_moi + self._n_heralds

    @property
    def post_select_fn(self):
        return self._post_select

    def with_input(self, input_state: BasicState) -> None:
        """
        Simulates plugging the photonic source on certain modes and turning it on.
        Computes the probability distribution of the processor input
        """
        self._inputs_map = SVDistribution()
        expected_input_length = self.m
        assert len(input_state) == expected_input_length, \
            f"Input length not compatible with circuit (expects {expected_input_length}, got {len(input_state)})"
        input_idx = 0
        expected_photons = 0
        for k in range(self.circuit_size):
            distribution = SVDistribution(StateVector("|0>"))
            if k in self.heralds:
                if self.heralds[k] == 1:
                    distribution = self._source.probability_distribution()
                    expected_photons += 1
            else:
                if input_state[input_idx] > 0:
                    distribution = self._source.probability_distribution()
                    expected_photons += 1
                input_idx += 1
            self._inputs_map *= distribution  # combine distributions

        self._min_mode_post_select = expected_photons
        if 'mode_post_select' in self._parameters:
            self._min_mode_post_select = self._parameters['mode_post_select']

    @property
    def components(self):
        return self._components

    def copy(self, subs: Union[dict, list] = None):
        new_proc = copy.deepcopy(self)
        new_proc._components = []
        for r, c in self._components:
            new_proc._components.append((r, c.copy(subs=subs)))
        return new_proc

    def set_postprocess(self, postprocess_func):
        self._post_select = postprocess_func

    def add(self, mode_mapping, component, keep_port=True):
        """
        Add a component (linear or non linear)
        Checks if it's possible:
        - No output is set on used modes
        - Should fail if lock_inputs has been called and the component uses new modes or defines new inputs
        """
        if self._post_select is not None:
            raise RuntimeError("Cannot add any component to a processor with post-process function")

        self._simulator = None  # Invalidate simulator which will have to be recreated later on
        component = component.copy()
        connector = ModeConnector(self, component, mode_mapping)
        if isinstance(component, Processor):
            self._compose_processor(connector, component, keep_port)
        elif isinstance(component, AComponent):
            self._add_component(connector.resolve(), component)
        else:
            raise RuntimeError(f"Cannot add {type(component)} object to a Processor")
        return self

    @property
    def out_port_names(self):
        result = [''] * self.circuit_size
        for port, m_range in self._out_ports.items():
            for m in m_range:
                result[m] = port.name
        return result

    @property
    def in_port_names(self):
        result = [''] * self.circuit_size
        for port, m_range in self._in_ports.items():
            for m in m_range:
                result[m] = port.name
        return result

    def _compose_processor(self, connector, processor, keep_port: bool):
        mode_mapping = connector.resolve()
        if not keep_port:
            # Remove output ports used to connect the new processor
            for i in mode_mapping:
                port = self.get_output_port(i)
                if port is not None:
                    del self._out_ports[port]

        # Compute new herald positions
        n_new_heralds = connector.add_heralded_modes(mode_mapping)
        self._n_heralds += n_new_heralds

        # Add PERM, component, PERM^-1
        perm_modes, perm_component = connector.generate_permutation(mode_mapping)
        if perm_component is not None:
            if len(self._components) > 0 and isinstance(self._components[-1][1], PERM):
                # Simplify composition by merging two consecutive PERM components
                l_perm_r = self._components[-1][0]
                l_perm_vect = self._components[-1][1].perm_vector
                new_range, new_perm_vect = perm_compose(l_perm_r, l_perm_vect, perm_modes, perm_component.perm_vector)
                self._components[-1] = (new_range, PERM(new_perm_vect))
            else:
                self._components.append((perm_modes, perm_component))
        for pos, c in processor.components:
            pos = [x + min(mode_mapping) for x in pos]
            self._components.append((pos, c))
        if perm_component is not None:
            perm_inv = perm_component.copy()
            perm_inv.inverse(h=True)
            self._components.append((perm_modes, perm_inv))

        # Retrieve ports from the other processor
        for port, port_range in processor._out_ports.items():
            port_mode = list(mode_mapping.keys())[list(mode_mapping.values()).index(port_range[0])]
            if isinstance(port, Herald):
                self._add_herald(port_mode, port.expected, port.user_given_name)
            else:
                if self.are_modes_free(range(port_mode, port_mode + port.m)):
                    self.add_port(port_mode, port, PortLocation.OUTPUT)

        # Retrieve post process function from the other processor
        if processor._post_select is not None:
            if perm_component is None:
                self._post_select = processor._post_select
            else:
                perm = perm_component.perm_vector
                c_first = perm_modes[0]
                self._post_select = lambda s: processor._post_select(BasicState([s[perm.index(ii) + c_first]
                                                                                 for ii in range(processor.circuit_size)]))

    def _add_component(self, mode_mapping, component):
        perm_modes, perm_component = ModeConnector.generate_permutation(mode_mapping)
        if perm_component is not None:
            self._components.append((perm_modes, perm_component))

        sorted_modes = list(range(min(mode_mapping), min(mode_mapping)+component.m))
        self._components.append((sorted_modes, component))

    def _add_herald(self, mode, expected, name=None):
        """
        This internal implementation neither increases the herald count nor decreases the mode of interest count
        """
        if not self.are_modes_free([mode], PortLocation.IN_OUT):
            raise UnavailableModeException(mode, "Another port overlaps")
        if name is None:
            name = self._anon_herald_num
            self._anon_herald_num += 1
        self._in_ports[Herald(expected, name)] = [mode]
        self._out_ports[Herald(expected, name)] = [mode]

    def add_herald(self, mode, expected, name=None):
        self._n_moi -= 1
        self._n_heralds += 1
        self._add_herald(mode, expected, name)
        return self

    def add_port(self, m, port: APort, location: PortLocation = PortLocation.IN_OUT):
        port_range = list(range(m, m + port.m))
        assert port.supports_location(location), f"Port is not compatible with location '{location.name}'"

        if location == PortLocation.IN_OUT or location == PortLocation.INPUT:
            if not self.are_modes_free(port_range, PortLocation.INPUT):
                raise UnavailableModeException(port_range, "Another port overlaps")
            self._in_ports[port] = port_range

        if location == PortLocation.IN_OUT or location == PortLocation.OUTPUT:
            if not self.are_modes_free(port_range, PortLocation.OUTPUT):
                raise UnavailableModeException(port_range, "Another port overlaps")
            self._out_ports[port] = port_range
        return self

    @property
    def _closed_photonic_modes(self):
        output = [False] * self.circuit_size
        for port, m_range in self._out_ports.items():
            if port.is_output_photonic_mode_closed():
                for i in m_range:
                    output[i] = True
        return output

    def is_mode_connectible(self, mode: int) -> bool:
        if mode < 0:
            return False
        if mode >= self.circuit_size:
            return False
        return not self._closed_photonic_modes[mode]

    def are_modes_free(self, mode_range, location: PortLocation = PortLocation.OUTPUT) -> bool:
        """
        Returns True if all modes in mode_range are free of ports, for a given location (input, output or both)
        """
        if location == PortLocation.IN_OUT or location == PortLocation.INPUT:
            for m in mode_range:
                if self.get_input_port(m) is not None:
                    return False
        if location == PortLocation.IN_OUT or location == PortLocation.OUTPUT:
            for m in mode_range:
                if self.get_output_port(m) is not None:
                    return False
        return True

    def get_input_port(self, mode):
        for port, mode_range in self._in_ports.items():
            if mode in mode_range:
                return port
        return None

    def get_output_port(self, mode):
        for port, mode_range in self._out_ports.items():
            if mode in mode_range:
                return port
        return None

    @property
    def heralds(self):
        pos = {}
        for port, port_range in self._out_ports.items():
            if isinstance(port, Herald):
                pos[port_range[0]] = port.expected
        return pos

    @property
    def source_distribution(self):
        return self._inputs_map

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, source):
        self._source = source
        self._inputs_map = None

    def linear_circuit(self, flatten: bool = False) -> Circuit:
        """
        Creates a linear circuit from internal components.
        If the processor contains at least one non-linear component, calling linear_circuit will try to convert it to
        a working linear circuit, or raise an exception
        """
        circuit = Circuit(self.circuit_size)
        for component in self._components:
            circuit.add(component[0], component[1], merge=flatten)
        return circuit

    def filter_herald(self, s: BasicState, keep_herald: bool = False) -> BasicState:
        if not self.heralds or keep_herald:
            return s
        new_state = []
        for idx, k in enumerate(s):
            if idx not in self.heralds:
                new_state.append(k)
        return BasicState(new_state)

    def _init_command(self, command_name: str):
        assert self._inputs_map is not None, "Input is missing, please call with_inputs()"
        assert self.available_sampling_method == command_name, \
            f"Cannot call {command_name}(). Available method is {self.available_sampling_method} "
        if self._simulator is None:
            self._setup_simulator()

    def samples(self, count: int, progress_callback=None) -> Dict:
        self._init_command("samples")
        output = []
        not_selected_physical = 0
        not_selected = 0
        selected_inputs = self._inputs_map.sample(count, non_null=False)
        idx = 0
        while len(output) < count:
            selected_input = selected_inputs[idx][0]
            idx += 1
            if idx == count:
                idx = 0
                selected_inputs = self._inputs_map.sample(count, non_null=False)
            if not self._state_preselected_physical(selected_input):
                not_selected_physical += 1
                continue
            sampled_state = self._simulator.sample(selected_input)
            if not self._state_selected_physical(sampled_state):
                not_selected_physical += 1
                continue
            if self._state_selected(sampled_state):
                output.append(self.filter_herald(sampled_state))
            else:
                not_selected += 1
            if progress_callback:
                progress_callback(len(output)/count, "sampling")
        physical_perf = (count + not_selected) / (count + not_selected + not_selected_physical)
        logical_perf = count / (count + not_selected)
        return {'results': output, 'physical_perf': physical_perf, 'logical_perf': logical_perf}

    def probs(self, progress_callback: Callable = None) -> Dict:
        self._init_command("probs")
        output = SVDistribution()
        idx = 0
        input_length = len(self._inputs_map)
        physical_perf = 1
        p_logic_discard = 0

        for input_state, input_prob in self._inputs_map.items():
            for (output_state, p) in self._simulator.allstateprob_iterator(input_state):
                if p < global_params['min_p']:
                    continue
                output_prob = p * input_prob
                if not self._state_selected_physical(output_state):
                    physical_perf -= output_prob
                    continue
                if self._state_selected(output_state):
                    output[self.filter_herald(output_state)] += output_prob
                else:
                    p_logic_discard += output_prob
            idx += 1
            if progress_callback:
                progress_callback(idx/input_length)
        if physical_perf < global_params['min_p']:
            physical_perf = 0
        all_p = sum(v for v in output.values())
        if all_p == 0:
            return {'results': output, 'physical_perf': physical_perf}
        logical_perf = 1 - p_logic_discard / (p_logic_discard + all_p)
        # normalize probabilities
        for k in output.keys():
            output[k] /= all_p
        return {'results': output, 'physical_perf': physical_perf, 'logical_perf': logical_perf}

    def _state_preselected_physical(self, input_state: BasicState):
        return input_state.n >= self._min_mode_post_select

    def _state_selected_physical(self, output_state: BasicState) -> bool:
        modes_with_photons = len([n for n in output_state if n > 0])
        return modes_with_photons >= self._min_mode_post_select

    def _state_selected(self, state: BasicState) -> bool:
        """
        Computes if the state is selected given heralds and post selection function
        """
        for m, v in self.heralds.items():
            if state[m] != v:
                return False
        if self._post_select is not None:
            return self._post_select(state)
        return True

    @property
    def available_sampling_method(self) -> str:
        preferred_command = BACKEND_LIST[self._backend_name].preferred_command()
        if preferred_command == 'samples':
            return 'samples'
        return 'probs'

    def get_circuit_parameters(self) -> Dict[str, Parameter]:
        return {p.name: p for p in self._circuit.get_parameters()}

    def set_circuit_parameters(self, params: Dict[str, float]) -> None:
        circuit_params = self.get_circuit_parameters()
        for param_name, param_value in params.items():
            if param_name in circuit_params:
                circuit_params[param_name].set_value(param_value)
