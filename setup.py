
from setuptools import find_packages, setup


with open("README.md") as fd:
    long_description = fd.read()

setup(
    name='jobs_done10',
    provides=['jobs_done10'],

    use_scm_version=True,
    setup_requires=['setuptools_scm'],

    #===============================================================================================
    # Requirements
    #===============================================================================================
    install_requires=[
        'click',
        'flask',
        'jenkins-webapi',
        'mailer',
        'pygments',
        'python-dotenv',
        'python-jenkins',
        'pyyaml',
        'requests-mock',
    ],
    extras_require={
        'testing': [
            'pytest',
            'pytest-mock',
        ],
    },

    #===============================================================================================
    # Packaging
    #===============================================================================================
    entry_points={'console_scripts': ['jobs_done=jobs_done10.cli:jobs_done']},
    packages=find_packages('src'),
    package_dir={
        '' : 'src',
    },
    include_package_data=True,

    #===============================================================================================
    # Project description
    #===============================================================================================
    author='ESSS',
    author_email='dev@esss.com.br',

    url='https://github.com/ESSS/jobs_done10',

    license='MIT',
    description=\
        "Job's Done uses a .jobs_done.yaml file in your repository to create Continuous Integration jobs on Jenkins.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords='jenkins continuous integration ci jobs job build',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development',
    ],
)
