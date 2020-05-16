# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as f:
    description = f.read()

extras_require = {
    'basler': ['pylonctl'],
    'eiger': ['aiohttp', 'aiodns']
}
extras_require['all'] = list(set.union(*(set(i) for i in extras_require.values())))

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
    ],
    entry_points={
        'console_scripts': [
            'lima = lima_toolbox.cli:main'
        ],
        'lima.cli.camera': [
            'Basler = lima_toolbox.camera.basler:basler [basler]',
            'Eiger = lima_toolbox.camera.eiger:eiger [eiger]',
        ],
        'lima.cli.camera.scan': [
            'Basler = lima_toolbox.camera.basler:scan [basler]',
            'Eiger = lima_toolbox.camera.eiger:scan [eiger]',
        ],
    },
    extras_require=extras_require,
    description="Lima toolbox",
    license="GPLv3+",
    long_description=description,
    long_description_content_type="text/markdown",
    keywords="Lima, CLI, toolbox, detector",
    packages=find_packages(),
    url="https://github.com/tiagocoutinho/lima-toolbox",
    version="0.0.1",
    python_requires=">=3.5"
)
