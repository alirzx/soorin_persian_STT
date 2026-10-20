// Browser policy: getUserMedia is unavailable on plain HTTP LAN/VPN origins.
export function microphoneAvailability({secureContext, mediaDevices}) {
  if (!secureContext) return {
    available: false,
    message: 'Live microphone needs a trusted HTTPS address (or localhost). Open the secure Studio URL; file uploads remain available.'
  }
  if (typeof mediaDevices?.getUserMedia !== 'function') return {
    available: false,
    message: 'Microphone capture is unavailable in this browser or context. Check browser privacy settings and device support.'
  }
  return {available:true,message:''}
}
