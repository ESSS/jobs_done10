from __future__ import unicode_literals
from setuptools import find_packages, setup

setup(
    name='jobs_done10',
    version='1.0',
    provides=['jobs_done10'],

    #===============================================================================================
    # Requirements
    #===============================================================================================
    install_requires=[
        'boltons',
        'python-jenkins',
        'pyyaml',
    ],

    #===============================================================================================
    # Packaging
    #===============================================================================================
    scripts=['scripts/jobs_done.py'],
    packages=find_packages('source/python'),
    package_dir={
        '' : 'source/python',
    },
    include_package_data=True,

    #===============================================================================================
    # Project description
    #===============================================================================================
    author='Diogo de Campos, Alexandre Motta de Andrade',
    author_email='campos@esss.com.br, ama@esss.com.br',

    url='https://github.com/ESSS/jobs_done10',

    license='LGPL v3+',
    description=\
        "Job's Done is a tool heavily inspired by Travis, where you can configure a file "
        "(.jobs_done.yaml) in your repository to create Continuous Integration jobs. "
        "Unlike Travis, jobs_done focuses on creating jobs in known CI servers instead of running "
        "in anonymous servers over the cloud. Currently only supports Jenkins",

    keywords='jenkins continuous integration ci jobs job build',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
    ],
)
