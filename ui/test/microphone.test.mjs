import test from 'node:test'
import assert from 'node:assert/strict'
import {microphoneAvailability} from '../src/microphone.js'

test('insecure LAN HTTP yields actionable warning without accessing mediaDevices',()=>{
  const result=microphoneAvailability({secureContext:false,mediaDevices:undefined})
  assert.equal(result.available,false)
  assert.match(result.message,/HTTPS/)
})
test('secure HTTPS with capture API is available',()=>{
  assert.equal(microphoneAvailability({secureContext:true,mediaDevices:{getUserMedia(){}}}).available,true)
})
test('secure browser without capture API has a graceful explanation',()=>{
  const result=microphoneAvailability({secureContext:true,mediaDevices:undefined})
  assert.equal(result.available,false)
  assert.match(result.message,/unavailable/)
})
