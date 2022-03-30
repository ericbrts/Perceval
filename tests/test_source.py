import pytest
import math

from perceval import Source, StateVector

from test_circuit import strip_line_12


def _check_svdistribution(output, expected):
    assert len(output) == len(expected), "size of svdistribution differs"
    for k, v in expected.items():
        svo = StateVector(k)
        if pytest.approx(v) != output[svo]:
            print(output.pdisplay())
            print("==> different value than expected for %s: %f (expected %f)" % (k, output[svo], v))
            assert False


def test_source_pure():
    s = Source()
    svd = s.probability_distribution()
    assert strip_line_12(svd.pdisplay()) == strip_line_12("""
            +--------+-------------+
            | state  | probability |
            +--------+-------------+
            |  |1>   |      1      |
            +--------+-------------+""")
    _check_svdistribution(svd, {"|1>": 1})


def test_source_brightness():
    s = Source(brightness=0.4)
    svd = s.probability_distribution()
    _check_svdistribution(svd, {"|0>": 0.6, "|1>": 0.4})


def test_source_brightness_purity():
    s = Source(brightness=0.4, purity=0.9)
    svd = s.probability_distribution()
    _check_svdistribution(svd, {"|0>": 0.6, "|2>": 0.04, "|1>": 0.36})


def test_source_brightess_purity_indistinguishable():
    s = Source(brightness=0.4, purity=0.9, indistinguishability=0.9)
    svd = s.probability_distribution()
    _check_svdistribution(svd, {"|0>": 0.6, "|{_:0}{_:1}>": 0.04, "|{_:0}>": 0.341526, "|{_:2}>": 0.018474})


def test_source_indistinguishability():
    s = Source(indistinguishability=0.9, indistinguishability_model="linear")
    svd = s.probability_distribution()
    assert len(svd) == 2
    for k, v in svd.items():
        assert len(k) == 1
        state = k[0]
        assert state.n == 1
        annot = state.get_photon_annotations(1)
        assert "_" in annot, "missing distinguishability feature _"
        if annot["_"] != 0:
            assert pytest.approx(v) == 0.1
        else:
            assert pytest.approx(v) == 0.9


def test_source_indistinguishability_homv():
    s = Source(indistinguishability=0.5)
    svd = s.probability_distribution()
    assert len(svd) == 2
    for k, v in svd.items():
        assert len(k) == 1
        state = k[0]
        assert state.n == 1
        annot = state.get_photon_annotations(1)
        assert "_" in annot, "missing distinguishability feature _"
        if annot["_"] != 0:
            assert pytest.approx(1-math.sqrt(0.5)) == v
        else:
            assert pytest.approx(math.sqrt(0.5)) == v
