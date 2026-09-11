class Sorted_List extends AILibrary {
	function GetAuthor()      { return "Xarick"; }
	function GetName()        { return "Sorted List"; }
	function GetShortName()   { return "QUSL"; }
	function GetDescription() { return "A priority queue implementation using AIList for efficient sorting."; }
	function GetVersion()     { return 3; }
	function GetDate()        { return "2026-03-27"; }
	function CreateInstance() { return "Sorted_List"; }
	function GetCategory()    { return "Queue"; }
}

RegisterLibrary(Sorted_List());
