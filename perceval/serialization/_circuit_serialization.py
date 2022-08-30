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

from multipledispatch import dispatch

from perceval.serialization import _schema_circuit_pb2 as pb
from perceval.components import ALinearCircuit, Circuit
import perceval.components.base_components as comp
import perceval.components.non_linear_components as nl
from perceval.serialization._matrix_serialization import serialize_matrix
from perceval.serialization._parameter_serialization import serialize_parameter


class ComponentSerializer:
    def __init__(self):
        self._pb = None

    def serialize(self, r: int, c: ALinearCircuit):
        self._pb = pb.Component()
        self._pb.starting_mode = r
        self._pb.n_mode = c.m
        self._serialize(c)
        return self._pb

    @dispatch(comp.GenericBS)
    def _serialize(self, bs: comp.GenericBS):
        pb_bs = pb.BeamSplitterComplex()
        if 'theta' in bs.params:
            pb_bs.theta.CopyFrom(serialize_parameter(bs._theta))
        if 'R' in bs.params:
            pb_bs.R.CopyFrom(serialize_parameter(bs._R))
        pb_bs.phi_a.CopyFrom(serialize_parameter(bs._phi_a))
        pb_bs.phi_b.CopyFrom(serialize_parameter(bs._phi_b))
        pb_bs.phi_d.CopyFrom(serialize_parameter(bs._phi_d))
        self._pb.beam_splitter_complex.CopyFrom(pb_bs)

    @dispatch(comp.SimpleBS)
    def _serialize(self, bs: comp.SimpleBS):
        pb_bs = pb.BeamSplitter()
        if 'theta' in bs.params:
            pb_bs.theta.CopyFrom(serialize_parameter(bs._theta))
        if 'R' in bs.params:
            pb_bs.R.CopyFrom(serialize_parameter(bs._R))
        pb_bs.phi.CopyFrom(serialize_parameter(bs._phi))
        self._pb.beam_splitter.CopyFrom(pb_bs)

    @dispatch(comp.PS)
    def _serialize(self, ps: comp.PS):
        pb_ps = pb.PhaseShifter()
        pb_ps.phi.CopyFrom(serialize_parameter(ps._phi))
        self._pb.phase_shifter.CopyFrom(pb_ps)

    @dispatch(comp.PERM)
    def _serialize(self, p: comp.PERM):
        pb_perm = pb.Permutation()
        pb_perm.permutations.extend(p.perm_vector)
        self._pb.permutation.CopyFrom(pb_perm)

    @dispatch(comp.Unitary)
    def _serialize(self, unitary: comp.Unitary):
        pb_umat = serialize_matrix(unitary.U)
        pb_unitary = pb.Unitary()
        pb_unitary.mat.CopyFrom(pb_umat)
        if unitary.name != comp.Unitary.DEFAULT_NAME:
            pb_unitary.name = unitary.name
        pb_unitary.use_polarization = unitary.requires_polarization
        self._pb.unitary.CopyFrom(pb_unitary)

    @dispatch(comp.PBS)
    def _serialize(self, _):
        pb_pbs = pb.PolarizedBeamSplitter()
        self._pb.polarized_beam_splitter.CopyFrom(pb_pbs)

    @dispatch(comp.QWP)
    def _serialize(self, wp: comp.QWP):
        pb_wp = pb.WavePlate()
        pb_wp.xsi.CopyFrom(serialize_parameter(wp._xsi))
        self._pb.quarter_wave_plate.CopyFrom(pb_wp)

    @dispatch(comp.HWP)
    def _serialize(self, wp: comp.HWP):
        pb_wp = pb.WavePlate()
        pb_wp.xsi.CopyFrom(serialize_parameter(wp._xsi))
        self._pb.half_wave_plate.CopyFrom(pb_wp)

    @dispatch(comp.WP)
    def _serialize(self, wp: comp.WP):
        pb_wp = pb.WavePlate()
        pb_wp.delta.CopyFrom(serialize_parameter(wp._delta))
        pb_wp.xsi.CopyFrom(serialize_parameter(wp._xsi))
        self._pb.wave_plate.CopyFrom(pb_wp)

    @dispatch(nl.TD)
    def _serialize(self, td: nl.TD):
        pb_td = pb.TimeDelay()
        pb_td.dt.CopyFrom(serialize_parameter(td._dt))
        self._pb.time_delay.CopyFrom(pb_td)

    @dispatch(comp.PR)
    def _serialize(self, pr: comp.PR):
        pb_pr = pb.PolarizationRotator()
        pb_pr.delta.CopyFrom(serialize_parameter(pr._delta))
        self._pb.polarization_rotator.CopyFrom(pb_pr)

    @dispatch(Circuit)
    def _serialize(self, circuit: Circuit):
        pb_circ = serialize_circuit(circuit)
        self._pb.circuit.CopyFrom(pb_circ)


def serialize_circuit(circuit: ALinearCircuit) -> pb.Circuit:
    if not isinstance(circuit, Circuit):
        circuit = Circuit(circuit.m).add(0, circuit)

    pb_circuit = pb.Circuit()
    if circuit.name != Circuit.DEFAULT_NAME:
        pb_circuit.name = circuit.name
    pb_circuit.n_mode = circuit.m
    comp_serializer = ComponentSerializer()
    for r, c in circuit._components:
        pb_circuit.components.extend([comp_serializer.serialize(r[0], c)])
    return pb_circuit
