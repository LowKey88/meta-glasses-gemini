'use client';

import { useState, Fragment } from 'react';
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react';
import { Popover, Transition } from '@headlessui/react';
import dayjs from 'dayjs';

interface DateSelectorProps {
  selectedDate: Date;
  onDateChange: (date: Date) => void;
}

export default function DateSelector({ selectedDate, onDateChange }: DateSelectorProps) {
  const handlePrevDay = () => {
    onDateChange(dayjs(selectedDate).subtract(1, 'day').toDate());
  };

  const handleNextDay = () => {
    onDateChange(dayjs(selectedDate).add(1, 'day').toDate());
  };

  const handleDateSelect = (date: Date) => {
    onDateChange(date);
  };

  const formattedDate = dayjs(selectedDate).format('MMM D, YYYY');

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={handlePrevDay}
        className="p-1.5 hover:bg-gray-200 dark:hover:bg-slate-700 rounded transition-colors"
      >
        <ChevronLeft className="h-4 w-4 text-gray-500 dark:text-gray-400" />
      </button>

      <Popover className="relative">
        <Popover.Button className="flex items-center gap-2 bg-white dark:bg-slate-800/60 border border-gray-300 dark:border-slate-600 hover:border-blue-400 rounded-lg px-3 py-2 text-sm w-40 transition-colors text-gray-900 dark:text-gray-100">
          <Calendar className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          <span>{formattedDate}</span>
        </Popover.Button>

        <Transition
          as={Fragment}
          enter="transition ease-out duration-200"
          enterFrom="opacity-0 translate-y-1"
          enterTo="opacity-100 translate-y-0"
          leave="transition ease-in duration-150"
          leaveFrom="opacity-100 translate-y-0"
          leaveTo="opacity-0 translate-y-1"
        >
          <Popover.Panel className="absolute z-10 mt-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg p-3">
            <DayPicker selectedDate={selectedDate} onSelect={handleDateSelect} />
          </Popover.Panel>
        </Transition>
      </Popover>

      <button
        onClick={handleNextDay}
        className="p-1.5 hover:bg-gray-200 dark:hover:bg-slate-700 rounded transition-colors"
      >
        <ChevronRight className="h-4 w-4 text-gray-500 dark:text-gray-400" />
      </button>
    </div>
  );
}

interface DayPickerProps {
  selectedDate: Date;
  onSelect: (date: Date) => void;
}

function DayPicker({ selectedDate, onSelect }: DayPickerProps) {
  const [currentMonth, setCurrentMonth] = useState(dayjs(selectedDate));
  
  const startOfMonth = currentMonth.startOf('month');
  const endOfMonth = currentMonth.endOf('month');
  const startOfWeek = startOfMonth.startOf('week');
  const endOfWeek = endOfMonth.endOf('week');
  
  const days = [];
  let day = startOfWeek;
  
  while (day.isBefore(endOfWeek) || day.isSame(endOfWeek)) {
    days.push(day);
    day = day.add(1, 'day');
  }

  return (
    <div className="w-64">
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => setCurrentMonth(currentMonth.subtract(1, 'month'))}
          className="p-1 hover:bg-gray-200 dark:hover:bg-slate-700 rounded transition-colors text-gray-900 dark:text-gray-100"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {currentMonth.format('MMMM YYYY')}
        </span>
        <button
          onClick={() => setCurrentMonth(currentMonth.add(1, 'month'))}
          className="p-1 hover:bg-gray-200 dark:hover:bg-slate-700 rounded transition-colors text-gray-900 dark:text-gray-100"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-xs">
        {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((weekday, i) => (
          <div key={i} className="text-center text-gray-500 dark:text-gray-400 py-1">
            {weekday}
          </div>
        ))}
        
        {days.map((day, i) => {
          const isSelected = day.isSame(selectedDate, 'day');
          const isCurrentMonth = day.isSame(currentMonth, 'month');
          const isToday = day.isSame(dayjs(), 'day');
          
          return (
            <button
              key={i}
              onClick={() => onSelect(day.toDate())}
              className={`
                p-2 text-center rounded transition-colors
                ${isSelected ? 'bg-blue-500 text-white' : ''}
                ${!isSelected && isToday ? 'bg-gray-200 dark:bg-slate-700 text-gray-900 dark:text-gray-100' : ''}
                ${!isSelected && !isToday && isCurrentMonth ? 'hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-900 dark:text-gray-100' : ''}
                ${!isCurrentMonth ? 'text-gray-400 dark:text-gray-600' : ''}
                ${!isSelected && !isToday && isCurrentMonth ? 'text-gray-900 dark:text-gray-100' : ''}
              `}
            >
              {day.format('D')}
            </button>
          );
        })}
      </div>
    </div>
  );
}