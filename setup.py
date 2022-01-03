from typing import List

import setuptools


decode_config = __import__('decode-config')


def get_long_description() -> str:
    with open('README.md') as fh:
        return fh.read()


def get_required() -> List[str]:
    with open('requirements.txt') as fh:
        return fh.read().splitlines()


setuptools.setup(
    name='decode-config',
    version=decode_config.VER,
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
