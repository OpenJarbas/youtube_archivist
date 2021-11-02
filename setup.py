from setuptools import setup

setup(
    name='youtube_archivist',
    version='0.0.2',
    packages=['youtube_archivist'],
    url='https://github.com/OpenJarbas/youtube_archivist',
    license='apache2',
    install_requires=["json_database>=0.3.0", "tutubo", "internetarchive"],
    author='jarbasai',
    author_email='jarbasai@mailfence.com',
    description='youtube indexer - keep track of your favorite channels!'
)
