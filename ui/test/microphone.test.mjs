import test from 'node:test'
import assert from 'node:assert/strict'
import {microphoneAvailability,microphoneError} from '../src/microphone.js'
test('insecure IP HTTP must show helpful HTTPS guidance',()=>{
  assert.match(microphoneAvailability({secureContext:false,mediaDevices:undefined}).message,/HTTPS/)
})
test('trusted HTTPS with microphone API is available',()=>{
  assert.equal(microphoneAvailability({secureContext:true,mediaDevices:{getUserMedia(){}}}).available,true)
})
test('missing microphone API does not crash',()=>{
  assert.equal(microphoneAvailability({secureContext:true,mediaDevices:undefined}).available,false)
})
test('permission errors are actionable',()=>{
  assert.match(microphoneError({name:'NotAllowedError'}),/permission was denied/)
})
