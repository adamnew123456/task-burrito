from setuptools import setup

setup(
    name='task_burrito',
    packages=['task_burrito'],
    entry_points = {
        'console_scripts': 
        ['burrito = task_burrito.app:main',
         'burrito-cgi = task_burrito.cgi:main']
    },
    author='Chris Marchetti',
    version='0.4.1',
    description='Personal project manager',
    author_email='adamnew123456@gmail.com',
    url='http://github.com/adamnew123456/task-burrito',
    keywords=[],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Development Status :: 3 - Alpha',
        'Topic :: Test Processing :: Markup :: HTML'
    ],
    long_description = """
Task Burrito takes task files and renders them into various views.
""")
