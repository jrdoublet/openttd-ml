Hello!

Thanks for the interest in this library. 


== What is SuperLib? ==
SuperLib is a library that consists of many sub libraries with
code mainly from CluelessPlus and PAXLink.

A general help and FAQ section exists in the main.nut.
You may also see the TT-forums thread about this library at:
  http://www.tt-forums.net/viewtopic.php?f=65&t=47525 

Open each sub-library file to find the interface documentation.

Over time SuperLib have envolved and contain both low level and
high level methods. For example there are both useful utilities
and methods to build a bus stop in a town.


== Background ==
As you might know CluelessPlus, PAXLink, TownCars and TutorialAI
are all created by the same author (Zuu). To reduce code duplication 
among these AIs, this library was created. Later the library has
additionally been ported to NoGo to allow usage from Game Scripts.
In addition to reduce code duplication among works by the author, 
other AI and GS authors can also use the library.


== Game Script Port ==
The Game Script port is basically just a rename of the API calls so
that it works for Game Scripts. In fact the port is created using an
automatic script that converts the AI library code to a game script
library.

The library itself never make usage of GSCompanyMode. Instead, you
as a user have to take care and use GSCompanyMode before calling
library functions that operate on specific companies.

During the time since this port was started, there have not been any
reports of functions that do not work for Game Scripts and would
better be disabled in the GS port. However, that doesn't mean that
there exist none of those cases. If you spot anything that may need
special care in the GS port, please report that in the SuperLib
thread on the forums.
