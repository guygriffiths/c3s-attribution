import PromiseWorker from 'promise-worker'
import Worker from './worker?worker'

const numWorkers = navigator.hardwareConcurrency - 1 || 3
const workers = Array.from(
	{ length: numWorkers },
	() => new PromiseWorker(new Worker()),
)

let nextWorker = 0

const send = (message: any) => {
	const worker = workers[nextWorker]
	nextWorker = (nextWorker + 1) % workers.length
	return worker.postMessage(message)
}

export default { send }
