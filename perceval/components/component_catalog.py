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
# As a special exception, the copyright holders of exqalibur library give you
# permission to combine exqalibur with code included in the standard release of
# Perceval under the MIT license (or modified versions of such code). You may
# copy and distribute such a combined system following the terms of the MIT
# license for both exqalibur and Perceval. This exception for the usage of
# exqalibur is limited to the python bindings used by Perceval.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import importlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import List

from perceval.utils import Parameter
from perceval.components import Processor, Circuit
from perceval.utils.logging import get_logger, channel


class AsType(Enum):
    CIRCUIT = 0
    PROCESSOR = 1


class CatalogItem(ABC):
    article_ref = None
    description = None
    str_repr = None
    see_also = None
    params_doc = {}

    def __init__(self, name: str):
        self._name = name
        self._default_opts = {
            'type': AsType.PROCESSOR,
            'backend': 'SLOS'
        }
        self._reset_opts()

    def _reset_opts(self):
        self._build_opts = self._default_opts.copy()

    def as_circuit(self):
        self._build_opts['type'] = AsType.CIRCUIT
        return self

    def as_processor(self, backend_name: str = None):
        self._build_opts['type'] = AsType.PROCESSOR
        if backend_name is not None:
            self._build_opts['backend'] = backend_name
        return self

    def _opt(self, key):
        if key in self._build_opts:
            return self._build_opts[key]
        return self._default_opts[key] if key in self._default_opts else None

    @property
    def name(self) -> str:
        """Name of the component

        :return: Name of the component
        """
        return self._name

    @property
    def doc(self):
        content = ''
        if self.description:
            content += f'\n{self.description}\n'
        if self.article_ref:
            content += f'\nScientific article reference: {self.article_ref}\n'
        if self.str_repr:
            content += f'\nSchema:\n{self.str_repr}\n'
        if self.params_doc:
            content += '\nParameters:\n'
            for param_name, param_descr in self.params_doc.items():
                content += f' * {param_name}: {param_descr}\n'
        if self.see_also:
            content += f'\nSee also: {self.see_also}\n'
        if content == '':
            content = 'None'
        title = f'{self._name} documentation\n'.upper()
        title += '-' * len(title) + '\n'
        return title + content

    # @abstractmethod was removed and build method deprecated in all child classes
    # The goal is to get rid of the overkill builder pattern and use build_processor and build_circuit instead
    def build(self):
        pass

    @staticmethod
    def _handle_param(value):
        if isinstance(value, str):
            return Parameter(value)
        return value

    def _init_processor(self, **kwargs):
        return Processor(kwargs.get("backend", "SLOS"), self.build_circuit(**kwargs),
                         name=kwargs.get("name") or self._name.upper())

    @abstractmethod
    def build_circuit(self, **kwargs) -> Circuit:
        """Build the component as circuit

        :return: A Perceval circuit
        """
        pass

    @abstractmethod
    def build_processor(self, **kwargs) -> Processor:
        """Build the component as processor

        kwargs:
            * backend(Union[ABackend, str]): Name or instance of a simulation backend. Default "SLOS"

        :return: A Perceval processor
        """
        pass


class Catalog:
    def __init__(self, path: str):
        self._items = {}
        if path:
            self.add_path(path)

    def add_path(self, path):
        module = importlib.import_module(path)
        if 'catalog_items' in dir(module):
            sub_catalog = getattr(module, 'catalog_items')
            self._add_sub_catalog(sub_catalog)
        else:
            get_logger().warn(f"No sub catalog found at path {path}", channel.user)

    def _add_sub_catalog(self, catalog):
        for cls in catalog:
            obj = cls()
            if isinstance(obj, CatalogItem):
                self._items[obj.name] = obj

    def list(self) -> List[str]:
        return list(self._items.keys())

    def __contains__(self, item: str) -> bool:
        return item in self._items

    def __getitem__(self, item_name: str) -> CatalogItem:
        return self._items[item_name]
