from pathlib import Path

from setuptools import setup, find_packages

home = str(Path.home())

setup(
    name='devops tools',
    packages=find_packages(),
    version='0.1',
    description='It\'s a DevOps tool, highly configurable job chains.',
    author='Zhang Yanwei',
    author_email='verdigris@163.com',
    keywords=['devops', 'job chains'],
    install_requires=[
        'PyYAML >= 3.12',
        'requests'
    ],
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        "Topic :: Utilities"
    ]
)
