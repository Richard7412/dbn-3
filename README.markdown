pydbn
===========

A python implementation of the DBN language
------------------------------

[Design By Numbers](http://www.maedastudio.com/1999/dbn/index.php)
is a book and companion language by John Maeda.
I read the book, but couldn't find an implementation of the language anywhere, so decided to implement it myself.

Currently, the supported statements are

 - `Line`
 - `Paper`
 - `Pen`
 - `Set`
 - `Repeat`
 - `Command`
 
(that's everything through chapter 12 except `Load`)

try `python dbn.py -f tests_dbns/square.dbn` to see an example
