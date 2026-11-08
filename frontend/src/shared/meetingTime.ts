import type { Meeting } from './api/types'

export function formatTime(time: string): string {
  if (/[ap]m/i.test(time)) return time.trim()
  const [h, m] = time.split(':')
  const hour = parseInt(h, 10)
  if (isNaN(hour)) return time
  return `${hour % 12 || 12}:${m ?? '00'} ${hour >= 12 ? 'PM' : 'AM'}`
}

export function meetingTimeLabel({ start_time, end_time }: Meeting): string {
  return start_time && end_time ? `${formatTime(start_time)}–${formatTime(end_time)}` : 'Time TBA'
}
