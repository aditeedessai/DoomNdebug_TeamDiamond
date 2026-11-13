
import { getState } from 'vardhan-maps/data'

const goa = getState('Goa')

if (!goa) {
  throw new Error('Goa boundary was not found')
}

export default goa
