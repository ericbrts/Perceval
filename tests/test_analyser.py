import perceval as pcvl
import perceval.lib.symb as symb
import sympy as sp

from test_circuit import strip_line_12


def test_analyser_full_issue_2():
    simulator_backend = pcvl.BackendFactory().get_backend("Naive")
    chip_QRNG = pcvl.Circuit(4, name='QRNG')
    # Parameters
    phis = [pcvl.Parameter("phi1"), pcvl.Parameter("phi2"),
            pcvl.Parameter("phi3"), pcvl.Parameter("phi4")]
    # Defining the LO elements of chip
    (chip_QRNG
     .add((0, 1), symb.BS())
     .add((2, 3), symb.BS())
     .add((1, 2), symb.PERM([1, 0]))
     .add(0, symb.PS(phis[0]))
     .add(2, symb.PS(phis[2]))
     .add((0, 1), symb.BS())
     .add((2, 3), symb.BS())
     .add(0, symb.PS(phis[1]))
     .add(2, symb.PS(phis[3]))
     .add((0, 1), symb.BS())
     .add((2, 3), symb.BS())
     )
    # Setting parameters value and see how chip specs evolve
    phis[0].set_value(sp.pi/2)
    phis[1].set_value(0.2)
    phis[2].set_value(0)
    phis[3].set_value(0.4)
    s1 = simulator_backend(chip_QRNG.compute_unitary(use_symbolic=False))
    ca = pcvl.CircuitAnalyser(s1, [pcvl.BasicState("[1,0,1,0]"),
                                   pcvl.BasicState("[0,1,1,0]")], "*")
    ca.compute()
    assert strip_line_12(ca.pdisplay()) == strip_line_12("""
            +-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+
            |           | |2,0,0,0> | |1,1,0,0> | |1,0,1,0> | |1,0,0,1> | |0,2,0,0> | |0,1,1,0> | |0,1,0,1> | |0,0,2,0> | |0,0,1,1> | |0,0,0,2> |
            +-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+
            | |1,0,1,0> | 0.004934  | 0.240133  | 0.012162  | 0.237838  | 0.004934  | 0.237838  | 0.012162  | 0.018956  | 0.212088  | 0.018956  |
            | |0,1,1,0> | 0.004934  | 0.240133  | 0.012162  | 0.237838  | 0.004934  | 0.237838  | 0.012162  | 0.018956  | 0.212088  | 0.018956  |
            +-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+-----------+
        """).strip()
