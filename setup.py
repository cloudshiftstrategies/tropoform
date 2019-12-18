import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='tropoform',
    version='0.3.4',
    entry_points={'console_scripts': ['tropoform=tropoform.tropoform:main']},
    author="Brian Peterson",
    author_email="brian.peterson@cloudshift.cc",
    description="A Terraform like utility for managing AWS Cloud Formation Stacks with troposphere",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cloudshiftstrategies/tropoform",
    packages=setuptools.find_namespace_packages(),
    install_requires=[
        'boto3',
        'botocore',
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
