from typing import List

import setuptools

__version__ = '2022.01.1'


def get_long_description() -> str:
    with open('README.md') as fh:
        return fh.read()


def get_required() -> List[str]:
    with open('requirements.txt') as fh:
        return fh.read().splitlines()


setuptools.setup(
    name='decode-config',
    version=__version__,
    license='GPLv3',
    description='Backup/restore and decode configuration tool for Tasmota.',
    author='Norbert Richter',
    author_email='nr@prsolution.eu',
    url='https://github.com/tasmota/decode-config',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    install_requires=get_required(),
    python_requires='>=3.7',
    scripts=['decode-config.py']
)
