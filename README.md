## ebisu-bench ##

A quick-and-dirty implementation of a program which can take an Anki deck and
generate a correct model of all of the cards under a different scheduling
algorithm (in this case, [ebisu][ebisu]).

This is possible because all Anki decks contain the full review history of each
card, allowing us to just replay all reviews to construct a correct model of
how a different scheduler would model the knowledge of the card. The key
question this project aims to answer is whether this would be prohibitively
expensive.

(Also we implement conversion back to an Anki deck to see whether emulating the
Anki algorithm would be painful, but given the Anki algorithm is basically just
a few multiplications this shouldn't be too hard.)

[ebisu]: https://github.com/fasiha/ebisu

### License ###

This project is licensed under the terms of the GNU General Public License,
version 3 (or later).

```
ebisu-bench: import Anki cards into ebisu's scheduler
Copyright (C) 2020 Aleksa Sarai <cyphar@cyphar.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
```
