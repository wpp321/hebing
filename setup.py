from setuptools import setup

setup(
    name="hebing",
    version="0.0.2",
    author="WangXueJie",
    author_email="hajiew@163.com",
    description="merge multiple python files into one python file",
    packages=["hebing"],
    python_requires='>=3.6',
    install_requires=[
        "chardet~=5.0.0"
    ],
    entry_points={'console_scripts': ['hebing=hebing:execute']}
)
