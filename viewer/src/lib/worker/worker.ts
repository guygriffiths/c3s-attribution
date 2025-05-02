import registerPromiseWorker from 'promise-worker/register'

registerPromiseWorker((message: any) => {
	const { messageContent } = message.message

	console.log('Worker received message:', messageContent)
	// Perform some processing with the message
	
	return
})
