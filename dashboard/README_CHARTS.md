# Dashboard Charts Refactor

## Structure
- `/components/charts/` - Reusable chart components
  - `MessageActivityChart.tsx` - 24h line chart
  - `WeeklyActivityChart.tsx` - 7-day bar chart  
  - `ComparisonChart.tsx` - Today vs yesterday line chart
  - `index.ts` - Barrel exports

## Usage
```tsx
import { MessageActivityChart } from '@/components/charts';
<MessageActivityChart data={messageData} />
```

## Features
- Responsive grid: 3 cols (desktop) → 2 cols (tablet) → 1 col (mobile)
- Chart toggle for focused view with smooth transitions
- Uniform 250px height, #3B82F6 primary color
- Dark mode support throughout