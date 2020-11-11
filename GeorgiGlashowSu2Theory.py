import tensorflow as tf
import numpy as np
import FieldTools

def getEnergy(scalarField, gaugeField, vev, selfCoupling, gaugeCoupling):
  return tf.math.reduce_sum(getEnergyDensity(scalarField, gaugeField, vev, selfCoupling, gaugeCoupling))

def getEnergyDensity(scalarField, gaugeField, vev, selfCoupling, gaugeCoupling):
  energyDensity = tf.zeros(tf.shape(scalarField)[0:3], dtype=tf.float64)

  energyDensity += getYMTerm(gaugeField, gaugeCoupling)
  energyDensity += getCovDerivTerm(scalarField, gaugeField)
  energyDensity += getScalarPotential(scalarField, vev, selfCoupling)

  return energyDensity

def getYMTerm(gaugeField, gaugeCoupling):
  energyDensity = tf.zeros(tf.shape(gaugeField)[0:3], dtype=tf.float64)

  numDims = 3
  for ii in range(numDims):
    for jj in range(numDims):
      if ii >= jj: continue
      energyDensity += 2/gaugeCoupling**2 * tf.math.real((2 - tf.linalg.trace(getPlaquette(gaugeField, ii, jj))))

  return energyDensity

def getCovDerivTerm(scalarField, gaugeField):
  energyDensity = tf.zeros(tf.shape(scalarField)[0:3], dtype=tf.float64)
  numDims = 3
  for ii in range(numDims):
    covDeriv = getCovDeriv(scalarField, gaugeField, ii)
    energyDensity += tf.math.real(tf.linalg.trace(covDeriv @ covDeriv))
  return energyDensity

def getScalarPotential(scalarField, vev, selfCoupling):
  energyDensity = tf.zeros(tf.shape(scalarField)[0:3], dtype=tf.float64)

  norms = tf.math.real(tf.linalg.trace(scalarField @ scalarField))
  energyDensity += selfCoupling * (vev**2 - norms)**2
  return energyDensity

def getPlaquette(gaugeField, dir1, dir2):
  plaquette = gaugeField[:,:,:,dir1,:,:]
  plaquette = plaquette @ shiftGaugeField(gaugeField, dir1)[:,:,:,dir2,:,:]
  plaquette = plaquette @ tf.linalg.adjoint(shiftGaugeField(gaugeField,dir2)[:,:,:,dir1,:,:])
  plaquette = plaquette @ tf.linalg.adjoint(gaugeField[:,:,:,dir2,:,:])

  return plaquette

def getCovDeriv(scalarField, gaugeField, dir):
  scalarFieldShifted = shiftScalarField(scalarField, dir)
  covDeriv = gaugeField[:,:,:,dir,:,:] @ scalarFieldShifted @ tf.linalg.adjoint(gaugeField[:,:,:,dir,:,:]) - scalarField
  return covDeriv

def getU1Projector(scalarField):
  trScalarSq = tf.linalg.trace(scalarField @ scalarField)
  latSize = tf.shape(trScalarSq)

  normalisedScalarField =  tf.expand_dims(tf.expand_dims(tf.math.sqrt(2.0/trScalarSq), -1),-1) * scalarField

  u1Projector = 0.5*(tf.eye(2, batch_shape=latSize, dtype=tf.complex128) + normalisedScalarField)

  return u1Projector

def getU1Link(gaugeField, scalarField, dir):
  projector = getU1Projector(scalarField)
  projectorShifted = getU1Projector(shiftScalarField(scalarField, dir))

  u1Link = projector @ gaugeField[:,:,:,dir,:,:] @ projectorShifted

  return u1Link

def getU1Plaquette(gaugeField, scalarField, dir1, dir2):
  u1Plaquette = getU1Link(gaugeField, scalarField, dir1)
  u1Plaquette = u1Plaquette @ getU1Link(shiftGaugeField(gaugeField, dir1), shiftScalarField(scalarField, dir1), dir2)
  u1Plaquette = u1Plaquette @ tf.linalg.adjoint(getU1Link(shiftGaugeField(gaugeField, dir2), shiftScalarField(scalarField, dir2), dir1))
  u1Plaquette = u1Plaquette @ tf.linalg.adjoint(getU1Link(gaugeField, scalarField, dir2))

  return u1Plaquette

def getMagneticField(gaugeField, scalarField, gaugeCoupling, dir):
  dir1 = (dir + 1) % 3
  dir2 = (dir + 2) % 3

  magneticField = 2.0/gaugeCoupling * tf.math.angle(tf.linalg.trace(getU1Plaquette(gaugeField, scalarField, dir1, dir2)))

  return magneticField

def shiftScalarField(scalarField, dir):
  shiftedField = tf.roll(scalarField, -1, dir)

  batchShape = list(np.shape(scalarField)[0:3])
  batchShape[dir] -= 1

  complementaryBatchShape = list(np.shape(scalarField)[0:3])
  complementaryBatchShape[dir] = 1

  identities = tf.eye(2, batch_shape=batchShape, dtype=tf.complex128)
  pauliMatrices = 1j*tf.eye(2, batch_shape=complementaryBatchShape, dtype=tf.complex128) @ FieldTools.pauliMatrix(dir)

  boundaryMask = tf.concat([identities, pauliMatrices], dir)

  shiftedField = boundaryMask @ shiftedField @ boundaryMask

  return shiftedField

def shiftGaugeField(gaugeField, dir):
  shiftedField = tf.roll(gaugeField, -1, dir)

  batchShape = list(np.shape(gaugeField)[0:4])
  batchShape[dir] -= 1

  complementaryBatchShape = list(np.shape(gaugeField)[0:4])
  complementaryBatchShape[dir] = 1

  identities = tf.eye(2, batch_shape=batchShape, dtype=tf.complex128)
  pauliMatrices = tf.eye(2, batch_shape=complementaryBatchShape, dtype=tf.complex128) @ FieldTools.pauliMatrix(dir)

  boundaryMask = tf.concat([identities, pauliMatrices], dir)

  shiftedField = boundaryMask @ shiftedField @ boundaryMask

  return shiftedField