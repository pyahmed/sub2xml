=======
sub2xml
=======
Python script to convert subtitles to titles/timeline for Premiere Pro, inspired by other similar tools, see [1] and  [2]. This script does the following:

- create one prtl-file per subtitle
- create one FCP-XML-file containing the correct start/end times

The FCP-XML can be imported into Premiere Pro, giving a timeline with all subtitles as title-objects, correctly layed out over the timeline. Sounds great? There are several limitations, see below. Once it is imported, save the project to embed the prtl-files.


[1] http://www.2writers.com/Eddie/PpTitleCreator.htm

[2] https://github.com/ubershmekel/pytitle

Limitations
------------
- Lots of parameters are hard-coded at the moment, like font-size/frame-rate/resolution etc
- No attempt is made to carry over any of the formatting in the ass-file to the prtl-file
- Not useful for subtitles with more than one style


Requirements
------------
- Python 3.x (Tested on Windows 7) 
- python-ass (for parsing ass-files)
- pillow (for str-width approximation)

Usage
-----
- sub2xml.py mytitle.ass

Also see docs/usage.txt

License
-------
- GPLv2 see docs/LICENSE.txt