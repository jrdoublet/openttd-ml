/**
 * A priority queue implementation using AIList for efficient sorting.
 * Items are stored with unique indexes, and the queue always returns the item
 * with the lowest priority first.
 */
class Sorted_List
{
	_queue = null;   ///< [index -> item] Table mapping item indexes to the actual items.
	_unique = null;  ///< [weakref -> index] Table ensuring each item is inserted only once.
	_sorter = null;  ///< AIList mapping [index -> priority], sorted so the lowest priority is at Begin().
	_index = -1;     ///< Monotonically increasing unique index assigned to each inserted item.

	constructor()
	{
		_queue = {};
		_unique = {};
		_sorter = AIList();
		_sorter.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
		_index = 0;
	}

	/**
	 * Insert a single item into the queue.
	 * @param item     The item to insert. Can be any Squirrel type.
	 *                 Must be unique; duplicate items are ignored.
	 * @param priority The priority associated with the item.
	 * @return true if the item was inserted, false if it already existed.
	 */
	function Insert(item, priority);

	/**
	 * Remove and return the item with the lowest priority.
	 * @return The removed item, or null if the queue is empty.
	 * @pre !IsEmpty()
	 */
	function Pop();

	/**
	 * Return the item with the lowest priority without removing it.
	 * @return The item with the lowest priority, or null if the queue is empty.
	 * @pre !IsEmpty()
	 */
	function Peek();

	/**
	 * Check whether an item is already in the queue.
	 * @param item The item to check.
	 * @return true if the item is already present.
	 */
	function Exists(item);

	/**
	 * Clear the queue. After calling this, Count() returns 0 and IsEmpty() returns true.
	 */
	function Clear();

	/**
	 * Check whether the queue is empty.
	 * @return true if the queue contains no items.
	 */
	function IsEmpty();

	/**
	 * Get the number of items currently in the queue.
	 * @return The number of items.
	 */
	function Count();
};

function Sorted_List::Insert(item, priority)
{
	local ref = item.weakref();
	if (ref in _unique) return false;

	_unique[ref] <- _index;
	_queue[_index] <- item;
	_sorter[_index++] = priority;

	return true;
}

function Sorted_List::Pop()
{
	if (_sorter.IsEmpty()) return null;

	local ret = _sorter.Begin();
	_sorter[ret] = null;
	delete _unique[_queue[ret].weakref()];

	return delete _queue[ret];
}

function Sorted_List::Peek()
{
	return _sorter.IsEmpty() ? null : _queue[_sorter.Begin()];
}

function Sorted_List::Exists(item)
{
	return item.weakref() in _unique;
}

function Sorted_List::Clear()
{
	_queue.clear();
	_unique.clear();
	_sorter.Clear();
	_index = 0;
}

function Sorted_List::IsEmpty()
{
	return _sorter.IsEmpty();
}

function Sorted_List::Count()
{
	return _sorter.Count();
}
