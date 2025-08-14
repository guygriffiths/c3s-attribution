import { filterEvents } from '@/lib/utils'
import registerPromiseWorker from 'promise-worker/register'

registerPromiseWorker((message: any) => {
	const { events, filters, eventIndex } = message

	const fullResult = filterEvents(events, filters, eventIndex, true)

	return { filteredEvents: fullResult }
})
