export function microphoneAvailability({secureContext,mediaDevices}) {
  if (!secureContext) return {available:false,message:'Live microphone requires trusted HTTPS or localhost. Use the HTTPS Studio address on LAN/VPN; file upload still works.'}
  if (typeof mediaDevices?.getUserMedia !== 'function') return {available:false,message:'Microphone is unavailable. Check certificate trust and browser/device permissions.'}
  return {available:true,message:''}
}
export function microphoneError(error) {
  if (['NotAllowedError','PermissionDeniedError'].includes(error?.name)) return 'Microphone permission was denied. Allow access in browser site settings.'
  if (error?.name==='NotFoundError') return 'No microphone device was found.'
  if (error?.name==='NotReadableError') return 'The microphone is unavailable or busy.'
  if (error?.name==='SecurityError') return 'Browser security policy blocked microphone access. Check trusted HTTPS.'
  return error?.message||'Microphone could not be started.'
}
