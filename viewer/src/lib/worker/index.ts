import PromiseWorker from 'promise-worker'
import Worker from './worker?worker'

const numWorkers = navigator.hardwareConcurrency - 1 || 3 // fallback to 3 if unknown
const workers = Array.from({ length: numWorkers }, () => {
	const w = new Worker()
	return new PromiseWorker(w)
})

let nextWorker = 0

const send = (message: any) => {
	const worker = workers[nextWorker]
	nextWorker = (nextWorker + 1) % workers.length
	return worker.postMessage({
		type: 'message',
		message,
	})
}

export default {
	send,
}
