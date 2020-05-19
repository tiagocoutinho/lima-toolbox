# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup


with open("README.md") as f:
    description = f.read()

install_requires = ["pint", "netifaces"]

extras_require = {
    "basler": ["pylonctl"],
    "eiger": ["aiohttp", "aiodns"]
}
extras_require["all"] = install_requires + list(
    set.union(*(set(i) for i in extras_require.values()))
)

setup(
    name="lima-toolbox",
    author="Jose Tiago Macara Coutinho",
    author_email="coutinhotiago@gmail.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    entry_points={
        "console_scripts": ["lima = Lima.toolbox.cli:main"],
        "lima.cli.camera": [
            "Basler = Lima.toolbox.camera.basler:basler [basler]",
            "Eiger = Lima.toolbox.camera.eiger:eiger [eiger]",
        ],
        "lima.cli.camera.scan": [
            "Basler = Lima.toolbox.camera.basler:scan [basler]",
            "Eiger = Lima.toolbox.camera.eiger:scan [eiger]",
        ],
    },
    install_requires=install_requires,
    extras_require=extras_require,
    description="Lima toolbox",
    long_description=description,
    long_description_content_type="text/markdown",
    keywords="Lima, CLI, toolbox, detector",
    url="https://github.com/tiagocoutinho/lima-toolbox",
    version="0.1.0",
    python_requires=">=3.5",
)
