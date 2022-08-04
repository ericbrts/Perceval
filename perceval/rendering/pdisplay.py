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

import os
import sys
import warnings
from typing import Literal
from multipledispatch import dispatch

from perceval.components import ACircuit, Circuit, Processor
from perceval.rendering.circuit import get_selected_skin, create_renderer
from perceval.utils.format import simple_float, simple_complex


in_notebook = False
in_pycharm_or_spyder = "PYCHARM_HOSTED" in os.environ or 'SPY_PYTHONPATH' in os.environ

try:
    from IPython import get_ipython
    if 'IPKernelApp' in get_ipython().config:
        in_notebook = True
        from IPython.display import HTML, display
except ImportError:
    pass
except AttributeError:
    pass


def _display_circuit(
        circuit: ACircuit,
        map_param_kid: dict = None,
        output_format: Literal["text", "html", "mplot", "latex"] = "text",
        recursive: bool = False,
        compact: bool = False,
        precision: float = 1e-6,
        nsimplify: bool = True,
        skin=None,
        **opts):
    if skin is None:
        skin = get_selected_skin(compact_display=compact)
    w, h = skin.get_size(circuit, recursive=recursive)
    renderer = create_renderer(circuit.m, output_format=output_format, skin=skin,
                               total_width=w, total_height=h, ** opts)
    if map_param_kid is None:
        map_param_kid = circuit.map_parameters()
    renderer.render_circuit(circuit, map_param_kid, recursive=recursive, precision=precision, nsimplify=nsimplify)
    renderer.add_mode_index()
    return renderer.draw()


def _display_processor(processor: Processor,
                       map_param_kid: dict = None,
                       output_format: Literal["text", "html", "mplot", "latex"] = "text",
                       recursive: bool = False,
                       compact: bool = False,
                       precision: float = 1e-6,
                       nsimplify: bool = True,
                       skin=None,
                       **opts):
    if not recursive:
        display_circ = Circuit(m=processor._circuit.m).add(0, processor._circuit, merge=False)
    else:
        display_circ = processor._circuit
    if skin is None:
        skin = get_selected_skin(compact_display=compact)
    w, h = skin.get_size(display_circ, recursive=recursive)
    renderer = create_renderer(display_circ.m, output_format=output_format, skin=skin,
                              total_width=w, total_height=h, compact=compact, **opts)
    renderer.render_circuit(display_circ,
                           map_param_kid=map_param_kid,
                           recursive=recursive,
                           precision=precision,
                           nsimplify=nsimplify)
    herald_num = 0
    incr_herald_num = False
    for k in range(processor._circuit.m):
        in_display_params = {}
        in_content = ''
        # in port #k name
        if k in processor._in_port_names:  # user defined names have priority...
            in_display_params['name'] = processor._in_port_names[k]
        elif k in processor._heralds:  # ...over autogenerated "herald#n" name
            in_display_params['name'] = f'herald{herald_num}'
            incr_herald_num = True

        # in port #k content
        if k in processor._sources:
            in_content = '1'
        elif k in processor._heralds:
            in_content = str(processor._heralds[k])

        out_display_params = {}
        out_content = ''
        # out port #k name
        if k in processor._out_port_names:
            out_display_params['name'] = processor._out_port_names[k]
        elif k in processor._heralds:
            out_display_params['name'] = f'herald{herald_num}'
            incr_herald_num = True

        # out port #k content
        if k in processor._heralds:
            out_content = str(processor._heralds[k])

        if incr_herald_num:
            incr_herald_num = False
            herald_num += 1

        if k in processor._heralds:
            in_display_params['color'] = 'white'
            out_display_params['color'] = 'white'

        renderer.add_in_port(k, in_content, **in_display_params)
        renderer.add_out_port(k, out_content, **out_display_params)
    return renderer.draw()


@dispatch(object)
def _pdisplay(circuit, **kwargs):
    return None


@dispatch(ACircuit)
def _pdisplay(circuit, **kwargs):
    return _display_circuit(circuit, **kwargs)


@dispatch(Processor)
def _pdisplay(processor, **kwargs):
    return _display_processor(processor, **kwargs)


def _default_output_format(o):
    """
    Deduces the best output format given the nature of the data to be displayed and the execution context
    """
    if in_notebook:
        return "html"
    elif in_pycharm_or_spyder \
            and (isinstance(o, ACircuit) or isinstance(o, Processor)):
        return "mplot"
    return "text"


def pdisplay(o, output_format=None, to_file=None, **opts):
    if output_format is None:
        output_format = _default_output_format(o)
    res = _pdisplay(o, output_format=output_format, **opts)
    if res is None:
        opts_simple = {}
        if "precision" in opts:
            opts_simple["precision"] = opts["precision"]
        if isinstance(o, (int, float)):
            res = simple_float(o, **opts_simple)[1]
        elif isinstance(o, complex):
            res = simple_complex(o, **opts_simple)[1]
        else:
            raise RuntimeError("pdisplay not defined for type %s" % type(o))

    if to_file:
        if 'drawSvg' in sys.modules:  # If drawSvg was imported beforehand
            import drawSvg
            if isinstance(res, drawSvg.Drawing):
                if output_format == "png":
                    res.savePng(to_file)
                else:
                    res.saveSvg(to_file)
                return
        else:
            warnings.warn("to_file parameter requires drawSvg to be installed on your system and manually imported.")

    if 'drawSvg' in sys.modules:  # If drawSvg was imported beforehand
        import drawSvg
        if isinstance(res, drawSvg.Drawing):
            return res
    elif in_notebook and output_format != "text":
        display(HTML(res))
    else:
        print(res)
