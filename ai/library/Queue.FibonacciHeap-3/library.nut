/* $Id: library.nut 15092 2009-01-15 16:53:18Z truebrain $ */

/*
 * 2012-04-29 (Version 3) Fix: Don't crash if items with 
 *   priority >= 268435455 is inserted and then all items are pop:ed. /Zuu
 */

class Fibonacci_Heap extends AILibrary {
	function GetAuthor()      { return "OpenTTD NoAI Developers Team"; }
	function GetName()        { return "Fibonacci Heap"; }
	function GetShortName()   { return "QUFH"; }
	function GetDescription() { return "An implementation of a Fibonacci Heap"; }
	function GetVersion()     { return 3; }
	function GetDate()        { return "2012-04-29"; }
	function CreateInstance() { return "Fibonacci_Heap"; }
	function GetCategory()    { return "Queue"; }
}

RegisterLibrary(Fibonacci_Heap());
