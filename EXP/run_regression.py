from keras import models
from keras import layers
from keras import optimizers
import keras.applications
import keras.callbacks
from keras import backend as K
from keras.utils.np_utils import to_categorical
import sklearn.metrics

import cPickle as pickle
import numpy as np
import os
import sys
import time

import ClevelandMcGill as C


EXPERIMENT = sys.argv[1] # f.e. Angle
DATASET = int(sys.argv[2]) # How many TRUE flags to pass to data generation
CLASSIFIER = sys.argv[3] # 'LeNet'
NOISE = sys.argv[4] # True
JOB_INDEX = int(sys.argv[5])

#
#
#
print 'Running', EXPERIMENT, 'on dataset', DATASET, 'with', CLASSIFIER, 'Noise:', NOISE, 'Job Index', JOB_INDEX

#
#
# PROCESS SOME FLAGS
#
#
SUFFIX = '.'
if NOISE == 'True':
  NOISE = True
  SUFFIX = '_noise.'
else:
  NOISE = False

DATATYPE = eval(EXPERIMENT)

FLAGS = [False] * 10 # never more than 10 flags
for f in range(DATASET):
  FLAGS[f] = True


if os.path.abspath('~').startswith('/n/'):
  # we are on the cluster
  PREFIX = '/n/regal/pfister_lab/PERCEPTION/'
else:
  PREFIX = '/home/manish.mourya001/Prof_Daniel/d'
RESULTS_DIR = PREFIX + 'RESULTS/'

OUTPUT_DIR = RESULTS_DIR + EXPERIMENT + '/' + str(DATASET) + '/' + CLASSIFIER + '/'
if not os.path.exists(OUTPUT_DIR):
  # here can be a race condition
  try:
    os.makedirs(OUTPUT_DIR)
  except:
    print 'Race condition!', os.path.exists(OUTPUT_DIR)

STATSFILE = OUTPUT_DIR + str(JOB_INDEX).zfill(2) + SUFFIX + 'p'
MODELFILE = OUTPUT_DIR + str(JOB_INDEX).zfill(2) + SUFFIX + 'h5'

print 'Working in', OUTPUT_DIR
print 'Storing', STATSFILE
print 'Storing', MODELFILE

if os.path.exists(STATSFILE) and os.path.exists(MODELFILE):
  print 'WAIT A MINUTE!! WE HAVE DONE THIS ONE BEFORE!'
  sys.exit(0)



#
# DATA GENERATION
#
#
train_target = 60000
val_target = 20000
test_target = 20000

# get global min and max
global_min = np.inf
global_max = -np.inf
for N in range(train_target+val_target+test_target):
  
  sparse, image, label, parameters = DATATYPE(FLAGS)
  
  global_min = min(label, global_min)
  global_max = max(label, global_max)
# end of global min max


X_train = np.zeros((train_target, 100, 100), dtype=np.float32)
y_train = np.zeros((train_target), dtype=np.float32)
train_counter = 0

X_val = np.zeros((val_target, 100, 100), dtype=np.float32)
y_val = np.zeros((val_target), dtype=np.float32)
val_counter = 0

X_test = np.zeros((test_target, 100, 100), dtype=np.float32)
y_test = np.zeros((test_target), dtype=np.float32)
test_counter = 0

t0 = time.time()

min_label = np.inf
max_label = -np.inf

all_counter = 0
while train_counter < train_target or val_counter < val_target or test_counter < test_target:
  
  all_counter += 1
  
  sparse, image, label, parameters = DATATYPE(FLAGS)
  
  # if label == 0:
  #   break
  
  # we need float
  image = image.astype(np.float32)
  
  pot = np.random.choice(3)#, p=([.6,.2,.2]))
  
  #
  #
  # special: to allow normalizations, we make sure the global min
  # and the global max for sure go into pot 0
  # this biases in a very slight way towards the mean with 2/n
  # this is ok.
  #
  if label == global_min or label == global_max:
    pot = 0 # for sure training
  
  if pot == 0 and train_counter < train_target:
    # a training candidate
    if label in y_val or label in y_test:
      # no thank you
      continue
      
    # add noise?
    if NOISE:
      image += np.random.uniform(0, 0.05,(100,100))
      
    # safe to add to training
    X_train[train_counter] = image
    y_train[train_counter] = label
    train_counter += 1
    
  elif pot == 1 and val_counter < val_target:
    # a validation candidate
    if label in y_train or label in y_test:
      # no thank you
      continue
      
    # add noise?
    if NOISE:
      image += np.random.uniform(0, 0.05,(100,100))
      
    # safe to add to validation
    X_val[val_counter] = image
    y_val[val_counter] = label
    val_counter += 1
  
  elif pot == 2 and test_counter < test_target:
    # a test candidate
    if label in y_train or label in y_val:
      # no thank you
      continue
      
    # add noise?
    if NOISE:
      image += np.random.uniform(0, 0.05,(100,100))
      
    # safe to add to test
    X_test[test_counter] = image
    y_test[test_counter] = label
    test_counter += 1
  
print 'Done', time.time()-t0, 'seconds (', all_counter, 'iterations)'
#
#
#


#
#
# NORMALIZE DATA IN-PLACE (BUT SEPERATELY)
#
#
X_min = X_train.min()
X_max = X_train.max()
y_min = y_train.min()
y_max = y_train.max()

# scale in place
X_train -= X_min
X_train /= (X_max - X_min)
y_train -= y_min
y_train /= (y_max - y_min)

X_val -= X_min
X_val /= (X_max - X_min)
y_val -= y_min
y_val /= (y_max - y_min)

X_test -= X_min
X_test /= (X_max - X_min)
y_test -= y_min
y_test /= (y_max - y_min)

# normalize to -.5 .. .5
X_train -= .5
X_val -= .5
X_test -= .5

print 'memory usage', (X_train.nbytes + X_val.nbytes + X_test.nbytes + y_train.nbytes + y_val.nbytes + y_test.nbytes) / 1000000., 'MB'
#
#
#


#
#
# FEATURE GENERATION
#
#
feature_time = 0
if CLASSIFIER == 'VGG19' or CLASSIFIER == 'XCEPTION':
  X_train_3D = np.stack((X_train,)*3, -1)
  X_val_3D = np.stack((X_val,)*3, -1)
  X_test_3D = np.stack((X_test,)*3, -1)
  print 'memory usage', (X_train_3D.nbytes + X_val_3D.nbytes + X_test_3D.nbytes) / 1000000., 'MB'

  if CLASSIFIER == 'VGG19':  
    feature_generator = keras.applications.VGG19(include_top=False, weights='imagenet', input_shape=(100,100,3))
  elif CLASSIFIER == 'XCEPTION':
    feature_generator = keras.applications.Xception(include_top=False, weights='imagenet', input_shape=(100,100,3))
  elif CLASSIFIER == 'RESNET50':
    print 'Not yet - we need some padding and so on!!!'
    sys.exit(1)

  t0 = time.time()
  X_train_3D_features = feature_generator.predict(X_train_3D, verbose=True)
  X_val_3D_features = feature_generator.predict(X_val_3D, verbose=True)
  feature_time = time.time()-t0

  X_test_3D_features = feature_generator.predict(X_test_3D, verbose=True)
  print CLASSIFIER, 'features done after', time.time()-t0
  print 'memory usage', (X_train_3D_features.nbytes + X_val_3D_features.nbytes + X_test_3D_features.nbytes) / 1000000., 'MB'

  # update the shape
  feature_shape = X_train_3D_features.shape[1] * X_train_3D_features.shape[2] * X_train_3D_features.shape[3]

  MLP = models.Sequential()

  X_train = X_train_3D_features.reshape(len(X_train_3D_features), feature_shape)
  X_val = X_val_3D_features.reshape(len(X_val_3D_features), feature_shape)
  X_test = X_test_3D_features.reshape(len(X_test_3D_features), feature_shape)
  ##

elif CLASSIFIER == 'LeNet':

  ##
  classifier = models.Sequential()
  classifier.add(layers.Convolution2D(20, (5, 5), padding="same", input_shape=(100, 100, 1)))
  classifier.add(layers.Activation("relu"))
  classifier.add(layers.MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
  classifier.add(layers.Dropout(0.2))
  classifier.add(layers.Convolution2D(50, (5, 5), padding="same"))
  classifier.add(layers.Activation("relu"))
  classifier.add(layers.MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
  classifier.add(layers.Dropout(0.2))
  classifier.add(layers.Flatten())

  feature_shape = classifier.output_shape
  MLP = classifier

  X_train = X_train.reshape(len(X_train), 100, 100, 1)
  X_val = X_val.reshape(len(X_val), 100, 100, 1)
  X_test = X_test.reshape(len(X_test), 100, 100, 1)
  ##

elif CLASSIFIER == 'MLP':

  ##
  MLP = models.Sequential()

  # flatten the data
  X_train = X_train.reshape(len(X_train), 100*100)
  X_val = X_val.reshape(len(X_val), 100*100)
  X_test = X_test.reshape(len(X_test), 100*100)

  feature_shape = 100*100
  ##

#
#
# THE MLP
#
#
MLP.add(layers.Dense(256, activation='relu', input_dim=feature_shape))
MLP.add(layers.Dropout(0.5))
MLP.add(layers.Dense(1, activation='linear')) # REGRESSION

sgd = optimizers.SGD(lr=0.0001, decay=1e-6, momentum=0.9, nesterov=True)
MLP.compile(loss='mean_squared_error', optimizer=sgd, metrics=['mse', 'mae']) # MSE for regression

#
#
# TRAINING
#
#
t0 = time.time()
callbacks = [keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=0, patience=10, verbose=0, mode='auto'), \
             keras.callbacks.ModelCheckpoint(MODELFILE, monitor='val_loss', verbose=1, save_best_only=True, mode='min')]

history = MLP.fit(X_train, \
                  y_train, \
                  epochs=1000, \
                  batch_size=32, \
                  validation_data=(X_val, y_val),
                  callbacks=callbacks,
                  verbose=True)

fit_time = time.time()-t0

print 'Fitting done', time.time()-t0

#
#
# PREDICTION
#
#
y_pred = MLP.predict(X_test)


#
#
# CLEVELAND MCGILL ERROR
#  MEANS OF LOG ABSOLUTE ERRORS (MLAEs)
#
MLAE = np.log2(sklearn.metrics.mean_absolute_error(y_pred*100, y_test*100)+.125)


#
#
# STORE
#   (THE NETWORK IS ALREADY STORED BASED ON THE CALLBACK FROM ABOVE!)
#

stats = dict(history.history)
# 1. the training history
# 2. the y_pred and y_test values
# 3. the MLAE
stats['time'] = feature_time + fit_time
stats['y_test'] = y_test
stats['y_pred'] = y_pred
stats['MLAE'] = MLAE

with open(STATSFILE, 'w') as f:
  pickle.dump(stats, f)

print 'MLAE', MLAE
print 'Written', STATSFILE
print 'Written', MODELFILE
print 'Sayonara! All done here.'
