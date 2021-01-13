# Copyright (C) 2019,2021 Simon Biggs
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ast
import pathlib

HERE = pathlib.Path(__file__).parent.resolve()
LIB_PATH = HERE.parents[1]

CONVERSIONS = {
    "attr": "attrs",
    "PIL": "Pillow",
    "Image": "Pillow",
    "mpl_toolkits": "matplotlib",
    "dateutil": "python_dateutil",
    "skimage": "scikit-image",
    "yaml": "PyYAML",
}


def get_module_dependencies(
    lib_path=LIB_PATH,
    conversions=None,
    package_name="pymedphys",
    apipkg_name="pymedphys._imports",
):
    if conversions is None:
        conversions = CONVERSIONS

    all_filepaths = list(lib_path.glob("**/*.py"))
    module_to_filepath_map = {
        _path_to_module(filepath, lib_path): filepath for filepath in all_filepaths
    }
    all_internal_modules = set(module_to_filepath_map.keys())

    module_dependencies = {}
    for module, filepath in module_to_filepath_map.items():
        raw_imports = _get_file_imports(filepath, lib_path, apipkg_name)
        module_imports = set()
        for an_import in raw_imports:
            module_name = _convert_import_to_module_name(
                an_import, package_name, all_internal_modules, conversions
            )
            module_imports.add(module_name)

        module_dependencies[module] = module_imports

    return module_dependencies


def _path_to_module(filepath, library_path):
    relative_path = filepath.relative_to(library_path)
    if relative_path.name == "__init__.py":
        relative_path = relative_path.parent

    module_name = ".".join(relative_path.with_suffix("").parts)

    return module_name


def _get_file_imports(filepath, library_path, apipkg_name):
    relative_path = filepath.relative_to(library_path)

    with open(filepath, "r") as file:
        module_contents = file.read()

    parsed = ast.parse(module_contents)

    all_import_nodes = [
        node
        for node in ast.walk(parsed)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    import_nodes = [node for node in all_import_nodes if isinstance(node, ast.Import)]
    import_from_nodes = [
        node for node in all_import_nodes if isinstance(node, ast.ImportFrom)
    ]

    imports = set()
    for node in import_nodes:
        for alias in node.names:
            imports.add(alias.name)

    for node in import_from_nodes:
        if node.level == 0:
            if node.module.startswith(apipkg_name):
                for alias in node.names:
                    imports.add(alias.name)
            else:
                for alias in node.names:
                    imports.add(f"{node.module}.{alias.name}")

        else:
            module = ".".join(relative_path.parts[: -node.level])

            if node.module:
                module = f"{module}.{node.module}"

            for alias in node.names:
                imports.add(f"{module}.{alias.name}")

    return imports


def _convert_import_to_module_name(
    an_import, package_name, all_internal_modules, conversions
):
    if an_import.startswith(package_name):
        if an_import in all_internal_modules:
            return an_import
        else:
            adjusted_import = ".".join(an_import.split(".")[:-1])
            if not adjusted_import in all_internal_modules:
                print(an_import)
                print(adjusted_import)
                raise ValueError()
            return adjusted_import
    else:
        adjusted_import = an_import.split(".")[0].replace("_", "-")
        try:
            adjusted_import = conversions[adjusted_import]
        except KeyError:
            pass

        return adjusted_import
