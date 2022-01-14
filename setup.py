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
    version = decode_config.METADATA['VERSION'],
    classifiers=[
        decode_config.METADATA['CLASSIFIER'],
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Topic :: Utilities',
        'Environment :: Console'
        ],
    description = decode_config.METADATA['DESCRIPTION'],
    author = decode_config.METADATA['AUTHOR'],
    author_email = decode_config.METADATA['AUTHOR_EMAIL'],
    url = decode_config.METADATA['URL'],
    long_description = get_long_description(),
    long_description_content_type = 'text/markdown',
    install_requires = get_required(),
    python_requires = '>=3.7',
    scripts = ['decode-config.py']
)
