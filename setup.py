import setuptools
import versioneer


setuptools.setup(
    setup_requires=['pbr'], pbr=True,
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass()
)

"""
setuptools.setup(
    name='tropoform',
    version=verstr,
    entry_points={'console_scripts': ['tropoform=tropoform.tropoform:main']},
    author="Brian Peterson",
    author_email="brian.peterson@cloudshift.cc",
    description="A Terraform like utility for managing AWS Cloud Formation Stacks with troposphere",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cloudshiftstrategies/tropoform",
    packages=setuptools.find_packages(),
    install_requires=[
        'boto3',
        'botocore'
        'troposphere',
        'awacs',
        'PyYAML',
        'colorlog',
        ],
    python_requires='>=3',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
"""
